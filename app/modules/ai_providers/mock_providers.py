"""
Local Reference & Test Implementations of Provider Interfaces
"""

import os
import re
from pathlib import Path
from app.modules.ai_providers.base import (
    DocumentParserProvider,
    RegulatoryLLMProvider,
    StorageProvider,
    ParsedDocumentResult,
    ExtractedFieldDTO,
    ValidationCheckDTO,
    RegulatorySummaryResult,
)


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage adapter."""

    def __init__(self, base_dir: str = "./storage/vault"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, content: bytes, destination_path: str) -> str:
        target_path = self.base_dir / destination_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(content)
        return str(target_path)

    def get_file(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()


class HeuristicDocumentParserProvider(DocumentParserProvider):
    """
    Reference parser simulating realistic Indian manufacturing certificate extraction.
    Handles Boiler Inspection Certificates, Consent to Operate, and Factory Licences.
    """

    def parse_document(self, file_bytes: bytes, filename: str) -> ParsedDocumentResult:
        # Check filename or simulated content for document type
        lower_name = filename.lower()
        if "boiler" in lower_name:
            doc_type = "Boiler Inspection Certificate"
            fields = [
                ExtractedFieldDTO(key="certificate_number", value="MH/B/2025/1042", confidence_score=0.98, confidence_band="HIGH"),
                ExtractedFieldDTO(key="authority", value="Chief Inspector of Boilers", confidence_score=0.96, confidence_band="HIGH"),
                ExtractedFieldDTO(key="equipment", value="Steam Boiler", confidence_score=0.95, confidence_band="HIGH"),
                ExtractedFieldDTO(key="inspection_date", value="2025-06-15", confidence_score=0.94, confidence_band="HIGH"),
                ExtractedFieldDTO(key="valid_until", value="2026-06-14", confidence_score=0.95, confidence_band="HIGH"),
                ExtractedFieldDTO(key="issuing_location", value="Maharashtra", confidence_score=0.82, confidence_band="MEDIUM"),
            ]
            checks = [
                ValidationCheckDTO(check_code="DOC_TYPE_MATCH", check_name="Document type identified", status="PASSED", details="Boiler Inspection Certificate recognized"),
                ValidationCheckDTO(check_code="VALID_DATE_WINDOW", check_name="Dates are valid", status="PASSED", details="Valid until is later than inspection date"),
                ValidationCheckDTO(check_code="CERT_FORMAT_VALID", check_name="Certificate number format is valid", status="PASSED", details="Matches pattern MH/B/YYYY/NNNN"),
                ValidationCheckDTO(check_code="EQUIPMENT_MATCH", check_name="Matches equipment in register", status="PASSED", details="Linked to registered steam boiler BLR-01"),
            ]
        elif "consent" in lower_name or "cto" in lower_name:
            doc_type = "Consent to Operate"
            fields = [
                ExtractedFieldDTO(key="consent_number", value="MPCB/RO-PUNE/CTO/2025/892", confidence_score=0.97, confidence_band="HIGH"),
                ExtractedFieldDTO(key="authority", value="Maharashtra Pollution Control Board", confidence_score=0.99, confidence_band="HIGH"),
                ExtractedFieldDTO(key="valid_until", value="2025-10-15", confidence_score=0.95, confidence_band="HIGH"),
            ]
            checks = [
                ValidationCheckDTO(check_code="DOC_TYPE_MATCH", check_name="Document type identified", status="PASSED", details="MPCB Consent to Operate recognized"),
                ValidationCheckDTO(check_code="VALID_DATE_WINDOW", check_name="Dates are valid", status="PASSED", details="Certificate date within active validity"),
            ]
        else:
            doc_type = "Statutory Compliance Document"
            fields = [
                ExtractedFieldDTO(key="document_title", value=Path(filename).stem, confidence_score=0.75, confidence_band="MEDIUM"),
            ]
            checks = [
                ValidationCheckDTO(check_code="DOC_TYPE_MATCH", check_name="Document type identified", status="WARNING", details="Generic document classification applied"),
            ]

        return ParsedDocumentResult(
            document_type_detected=doc_type,
            fields=fields,
            validation_checks=checks,
            raw_text="Simulated OCR extraction text."
        )


class HeuristicRegulatoryLLMProvider(RegulatoryLLMProvider):
    """
    Reference LLM provider providing plain-language summaries for gazette notifications.
    """

    def summarize_notification(self, raw_text: str, authority: str, notification_ref: str) -> RegulatorySummaryResult:
        return RegulatorySummaryResult(
            summary_plain_language=(
                f"The notification {notification_ref} issued by {authority} amends certain statutory provisions, "
                "including updated categorisation, revised thresholds for storage, and new compliance reporting requirements."
            ),
            key_changes=[
                "Revised list of hazardous waste categories",
                "Updated storage threshold limits",
                "New requirement for annual return filing in prescribed format",
                "Clarification on co-processing and disposal procedures",
            ],
            who_may_be_affected=[
                "Generate, store or handle hazardous waste",
                "Operate in manufacturing, chemicals, pharmaceuticals, or automotive sectors",
                "Are located in Maharashtra and other notified industrial states",
                "Fall under the revised threshold limits",
            ],
            candidate_impact_rating="HIGH"
        )
