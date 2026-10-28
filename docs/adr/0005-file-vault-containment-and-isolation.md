# ADR 0005: File Vault Containment, Tenant Isolation, and Header Sanitization

## Status
**Accepted**

## Context
PlantProof manages sensitive operational evidence documents (MPCB Consent to Operate, PESO explosive licenses, boiler inspection certificates, hazardous waste manifests) and generated executive compliance readiness dossiers. These artifacts are stored in a dedicated file vault on the local filesystem or configured cloud bucket.

Two critical security risks were identified in file storage and download mechanisms:
1. **Path Traversal (CWE-22):** If an adversary manipulates or injects directory traversal tokens (`../`, `..\\`) into document storage keys or report artifact identifiers, an API endpoint could be coerced into reading or exfiltrating arbitrary system files outside the designated vault boundary.
2. **HTTP Response Splitting / Header Injection (CWE-113):** If user-supplied document titles or plant names containing carriage-return (`\r`) or line-feed (`\n`) characters are reflected directly into the `Content-Disposition` header during file downloads, malicious actors could inject arbitrary HTTP response headers or split response streams, causing client-side cache poisoning or cross-site scripting.

## Decision
We enforce strict **Canonical Containment Verification**, **Tenant Directory Isolation**, and **HTTP Header Sanitization** across all file ingestion and streaming paths:

1. **Deterministic Tenant Vault Structure:**
   - Every stored file resides within a tenant-scoped subfolder rooted under `VAULT_BASE_DIR`:
     `storage/vault/{tenant_id}/{document_or_report_id}_{sanitized_basename}`
2. **Canonical Path Containment Verification:**
   - Before serving or deleting any file artifact, the absolute canonical path is resolved using Python's `pathlib.Path.resolve()`.
   - The resolved path is verified to ensure it strictly starts with the expected canonical tenant directory:
     ```python
     resolved_path = Path(storage_key).resolve()
     expected_vault = (VAULT_BASE_DIR / tenant_id).resolve()
     if not str(resolved_path).startswith(str(expected_vault)):
         raise AppException(
             code="STORAGE_SECURITY_VIOLATION",
             message="Directory traversal detected in artifact path.",
             status_code=403,
         )
     ```
   - Attempted access outside the tenant's subdirectory immediately aborts with HTTP 403 Forbidden and writes a high-priority security event to the audit trail.
3. **MIME Validation & Extension Allowlist:**
   - Uploaded files are validated against an explicit MIME-type allowlist (`application/pdf`, `image/jpeg`, `image/png`).
   - Magic bytes are checked using `python-magic` to prevent file extension spoofing (e.g. executable scripts masquerading as PDF certificates).
4. **Content-Disposition CRLF Sanitization:**
   - All download responses sanitize user-supplied filenames using regular expressions before inserting into headers:
     ```python
     clean_filename = re.sub(r'[\r\n"\\\x00-\x1f]', "", original_filename)
     headers = {"Content-Disposition": f'attachment; filename="{clean_filename}"'}
     ```

## Consequences

### Positive
- Completely neutralizes path traversal vulnerabilities; even if an attacker tampers with internal database keys or provides relative paths, canonical directory resolution guarantees access remains bounded within the tenant's isolated folder.
- Eliminates HTTP response splitting and CRLF header injection risks on file download endpoints.
- Maintains multi-tenant physical file isolation on disk.
- Fully verified under automated negative testing (`tests/integration/test_security_hardening.py`).

### Negative / Trade-offs
- File system access requires resolving absolute paths on each request, introducing negligible microseconds of overhead.
- Special characters in original uploaded filenames (such as quotes and non-printable control characters) are stripped in download headers for safety.
