"""
Private Document Vault Storage Service
Stores documents under random internal storage keys isolated by tenant directory.
Never uses original filenames as filesystem paths.
"""

import os
import uuid
from pathlib import Path
from typing import Tuple, Optional

from app.core.config import settings
from app.core.exceptions import EntityNotFoundError, InsufficientPermissionsError


class StorageSecurityError(Exception):
    pass


class SecureVaultStorageService:
    """
    Manages private on-premise vault storage.
    Enforces random storage keys, tenant directory isolation, and path containment.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, content: bytes, tenant_id: str) -> Tuple[str, str]:
        """
        Stores file content under a cryptographic random storage key.
        Never uses original filename in filesystem paths.
        
        Returns:
            Tuple[storage_key, relative_storage_path]
        """
        if not tenant_id or ".." in tenant_id or "/" in tenant_id or "\\" in tenant_id:
            raise StorageSecurityError("Invalid tenant isolation identifier.")

        random_uuid = uuid.uuid4().hex
        storage_key = f"{random_uuid}.bin"
        
        tenant_vault = (self.base_dir / tenant_id).resolve()
        # Verify tenant directory is strictly within base_dir
        if not str(tenant_vault).startswith(str(self.base_dir)):
            raise StorageSecurityError("Path traversal attempt detected in tenant storage.")

        tenant_vault.mkdir(parents=True, exist_ok=True)
        file_path = (tenant_vault / storage_key).resolve()

        with open(file_path, "wb") as f:
            f.write(content)

        # Return relative storage path for portability across environments
        relative_path = f"{tenant_id}/{storage_key}"
        return storage_key, relative_path

    def get_file(self, relative_path: str, tenant_id: Optional[str] = None) -> bytes:
        """
        Retrieves file bytes with strict tenant scoping and boundary checks.
        """
        target_path = (self.base_dir / relative_path).resolve()

        # Enforce containment within base_dir
        if not str(target_path).startswith(str(self.base_dir)):
            raise StorageSecurityError("Directory traversal detected in document retrieval.")

        # Enforce tenant isolation check
        if tenant_id and not relative_path.startswith(f"{tenant_id}/"):
            raise InsufficientPermissionsError("Cross-tenant document access denied.")

        if not target_path.exists() or not target_path.is_file():
            raise EntityNotFoundError("ComplianceDocumentFile", relative_path)

        with open(target_path, "rb") as f:
            return f.read()

    def get_absolute_path(self, relative_path: str, tenant_id: Optional[str] = None) -> Path:
        """Returns verified absolute filesystem Path."""
        target_path = (self.base_dir / relative_path).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise StorageSecurityError("Directory traversal detected.")
        if tenant_id and not relative_path.startswith(f"{tenant_id}/"):
            raise InsufficientPermissionsError("Cross-tenant document access denied.")
        return target_path

    def delete_file(self, relative_path: str, tenant_id: Optional[str] = None) -> bool:
        """Deletes file from storage according to retention policies."""
        try:
            target_path = self.get_absolute_path(relative_path, tenant_id)
            if target_path.exists():
                os.remove(target_path)
                return True
        except Exception:
            pass
        return False


vault_storage = SecureVaultStorageService()
