# PlantProof: Troubleshooting & Operational Runbook

**System Version:** v1.0.0  
**Scope:** Local Development, Process Management, Database Triage, and Common Failure Modes  
**Status:** Tested on Windows 11 / Python 3.13 / Node v22.16.0  

---

## 1. Quick Diagnostic Checklist

When encountering unexpected behavior, run through these five quick diagnostic checks:

| Check | Command / Action | Expected Result |
| :--- | :--- | :--- |
| **Backend Health** | `curl http://127.0.0.1:8000/api/v1/health` | Returns `status: "healthy"` and database `status: "connected"`. |
| **Database File** | Check for `plantproof.db` in project root | File exists and has size $> 500\text{ KB}$ after seeding. |
| **Backend Tests** | `.\venv\Scripts\pytest.exe -q` | `97 passed`. |
| **Frontend Tests** | `cd frontend && npm test` | `11 passed (4 test files)`. |
| **Port Conflicts** | `netstat -ano \| findstr :8000` | Process bound to `127.0.0.1:8000`. |

---

## 2. Server Startup & Port Conflicts

### Problem: `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): address already in use`
- **Cause:** Another instance of Uvicorn, Python, or another web server is already running on port 8000.
- **Resolution (Windows PowerShell):**
  1. Identify the process holding port 8000:
     ```powershell
     netstat -ano | findstr :8000
     ```
  2. Note the PID (the number in the rightmost column) and terminate the process:
     ```powershell
     taskkill /PID <PID> /F
     ```
  3. Restart the backend:
     ```powershell
     .\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
     ```

### Problem: Vite Frontend dev server switches to port 5174 or 5175
- **Cause:** Port 5173 is occupied by a previously running Vite process.
- **Resolution:**
  1. Terminate orphaned Node processes:
     ```powershell
     taskkill /IM node.exe /F
     ```
  2. Restart the frontend server on port 5173:
     ```powershell
     cd frontend
     npm run dev
     ```

---

## 3. Database & Migration Triage

### Problem: `sqlite3.OperationalError: database is locked`
- **Cause:** In SQLite, concurrent writes from multiple processes can cause brief file locks.
- **Resolution:**
  1. Ensure you do not have multiple backend server instances or database GUI tools holding exclusive locks on `plantproof.db`.
  2. For high-concurrency local load tests, switch `.env` to PostgreSQL:
     ```env
     DATABASE_URL="postgresql+psycopg2://plantproof_user:password@localhost:5432/plantproof_dev"
     ```

### Problem: `Table or column does not exist` after pulling latest code
- **Cause:** Database schema is out of sync with Alembic migration revisions.
- **Resolution:**
  Run Alembic migrations to apply pending schema changes:
  ```powershell
  .\venv\Scripts\alembic.exe upgrade head
  ```

### Problem: Completely resetting the local database
To wipe and rebuild a clean local SQLite database with base master data and demo personas:
```powershell
# 1. Stop running backend server (Ctrl+C)

# 2. Delete the SQLite database file
Remove-Item -Path ".\plantproof.db" -Force -ErrorAction SilentlyContinue

# 3. Apply database migrations to recreate tables
.\venv\Scripts\alembic.exe upgrade head

# 4. Seed reference master data and demo accounts
.\venv\Scripts\python.exe -m app.seed.demo_data
```

---

## 4. Authentication, Permissions & Rate Limiting

### Problem: `HTTP 401 Unauthorized` on API requests
- **Cause:** Missing, expired, or malformed Bearer token in the `Authorization` header. Access tokens have an 8-hour lifetime (`ACCESS_TOKEN_EXPIRE_MINUTES=480`).
- **Resolution:**
  Re-authenticate at `POST /api/v1/auth/login` to obtain a fresh JWT token:
  ```json
  {
    "email": "rohit.sharma@acme-mfg.in",
    "password": "DemoPass123!"
  }
  ```
  Ensure the header is formatted as `Authorization: Bearer <token>` without extra quotes or spaces.

### Problem: `HTTP 403 Forbidden` (`TENANT_ACCESS_DENIED` or `User role is not authorized`)
- **Cause:**
  1. **Cross-Tenant Violation:** The user belongs to Tenant A (`Acme Manufacturing`) but attempted to access or mutate a resource belonging to Tenant B (`Beta Pharma`).
  2. **RBAC Insufficient Privileges:** A read-only `VIEWER` account attempted to create a facility, invite a user, or view administrative audit logs.
- **Resolution:**
  Verify that the authenticated user holds the required role (`ADMIN`, `PLANT_MANAGER`, or `EHS_MANAGER`) for the operation.

### Problem: `HTTP 429 Too Many Requests` (`Rate limit exceeded`)
- **Cause:** The client exceeded the in-memory sliding-window rate limit on a sensitive endpoint:
  - `/api/v1/auth/login`: Maximum 15 requests per 60 seconds per IP.
  - `/api/v1/documents/upload`: Maximum 30 requests per 60 seconds per IP.
  - `/api/v1/reports`: Maximum 15 requests per 60 seconds per IP.
- **Resolution:**
  Inspect the `Retry-After` header returned in the response (e.g., `Retry-After: 42`). Wait the specified number of seconds before retrying. In automated test scripts, reuse authentication tokens instead of repeatedly calling the login endpoint.

---

## 5. Evidence Vault & Document Upload Issues

### Problem: `HTTP 413 Request Entity Too Large`
- **Cause:** The uploaded file exceeds the 25 MB payload limit (`MAX_UPLOAD_SIZE_BYTES=26214400`).
- **Resolution:**
  Optimize the PDF or image resolution (recommended: 300 DPI for scanned certificates). Files larger than 25MB are blocked at ingress to prevent disk starvation.

### Problem: `HTTP 415 Unsupported Media Type` (`PROHIBITED_FILE_FORMAT`)
- **Cause:** The upload is an executable, script, or archive format (`.exe`, `.zip`, `.tar`, `.sh`, `.bat`), or the file content magic bytes do not match standard document signatures (`%PDF-`, `\xFF\xD8\xFF`, `\x89PNG`).
- **Resolution:**
  Upload original statutory certificates formatted as PDF, JPG, PNG, or TIFF files.

### Problem: Missing vault directories on disk
- **Cause:** Vault root path (`./storage/vault`) does not exist.
- **Resolution:**
  The application automatically creates `storage/vault/{tenant_id}/` on startup and first upload. If directory creation fails due to local Windows permission restrictions, manually create the folder:
  ```powershell
  New-Item -ItemType Directory -Path "storage/vault" -Force
  ```

---

## 6. Frontend & Cross-Origin (CORS) Issues

### Problem: Browser console displays `CORS error: No 'Access-Control-Allow-Origin' header is present`
- **Cause:** The frontend is running on a port or origin not declared in `BACKEND_CORS_ORIGINS` in `.env`.
- **Resolution:**
  Ensure `.env` includes your client URL:
  ```env
  BACKEND_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000","http://127.0.0.1:3000"]
  ```
  Restart the FastAPI server after modifying `.env`.

### Problem: Frontend UI shows stale data after database updates
- **Cause:** TanStack Query client-side cache has not invalidated the query key.
- **Resolution:**
  Press `Ctrl + Shift + R` to perform a hard refresh, or click the **Refresh** button on the respective data table to trigger an immediate server refetch.
