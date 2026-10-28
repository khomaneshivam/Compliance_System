"""
Deterministic Rule-Based Validation for Compliance Documents
Validates dates, certificate numbers, authorities, and confidence scores.
"""

import re
from datetime import date, datetime
from typing import List, Optional, Dict
from app.modules.documents.schemas import ExtractedFieldData, ValidationCheckData


KNOWN_AUTHORITIES = [
    "Maharashtra Pollution Control Board",
    "Central Pollution Control Board",
    "Directorate of Industrial Safety and Health",
    "Directorate of Industrial Safety and Health, Maharashtra",
    "Chief Inspector of Boilers",
    "Chief Inspector of Boilers, Maharashtra",
    "Petroleum and Explosives Safety Organization (PESO)",
    "Ministry of Environment, Forest and Climate Change",
    "State Level Environment Impact Assessment Authority (SEIAA)",
    "Maharashtra Fire Services",
]

IDENTIFIER_PATTERNS: Dict[str, re.Pattern] = {
    "Boiler Inspection Certificate": re.compile(r"^(?:MH|GJ|IN)[\/\-]B[\/\-]\d{4}[\/\-]\d+$", re.IGNORECASE),
    "Consent to Operate": re.compile(r"^(?:MPCB|CPCB|GPCB)[\/\-][A-Z0-9\-\/]+$", re.IGNORECASE),
    "Factory Licence": re.compile(r"^(?:DISH|FL|FAC)[\/\-][A-Z0-9\-\/]+$", re.IGNORECASE),
    "Hazardous Waste Authorization": re.compile(r"^(?:HWMR|FORM\-2|MPCB)[\/\-][A-Z0-9\-\/]+$", re.IGNORECASE),
    "Fire Safety NOC": re.compile(r"^(?:NOC|FIRE|MFS)[\/\-][A-Z0-9\-\/]+$", re.IGNORECASE),
}


class DocumentRuleValidator:
    """
    Executes deterministic compliance rules against extracted document parameters.
    """

    def validate(
        self,
        document_type: str,
        fields: List[ExtractedFieldData],
        detected_issue_date: Optional[date] = None,
        detected_expiry_date: Optional[date] = None,
        has_expiry: bool = True,
    ) -> List[ValidationCheckData]:
        """Runs all deterministic validation checks and returns check results."""
        checks: List[ValidationCheckData] = []

        field_map = {f.key: f.value for f in fields}

        # 1. Document Type Check
        if document_type and document_type != "Unknown Document":
            checks.append(
                ValidationCheckData(
                    check_code="DOC_TYPE_MATCH",
                    check_name="Document Type Classification",
                    status="PASSED",
                    details=f"Document recognized as '{document_type}'.",
                )
            )
        else:
            checks.append(
                ValidationCheckData(
                    check_code="DOC_TYPE_MATCH",
                    check_name="Document Type Classification",
                    status="WARNING",
                    details="Generic or uncertain document classification applied. Reviewer confirmation advised.",
                )
            )

        # 2. Date Window & Expiry Rules
        today = date.today()
        if not has_expiry or detected_expiry_date is None:
            # Cardinal Rule: Never invent an expiry date when a document is permanent/perpetual!
            checks.append(
                ValidationCheckData(
                    check_code="NO_EXPIRY_PERMANENT",
                    check_name="Statutory Validity Period",
                    status="PASSED",
                    details="Permanent or perpetual statutory certificate without expiration date (no synthetic expiry invented).",
                )
            )
        else:
            if detected_issue_date and detected_expiry_date:
                if detected_expiry_date > detected_issue_date:
                    checks.append(
                        ValidationCheckData(
                            check_code="VALID_DATE_WINDOW",
                            check_name="Validity Window Consistency",
                            status="PASSED",
                            details=f"Valid date sequence: Issued on {detected_issue_date.isoformat()} and valid until {detected_expiry_date.isoformat()}.",
                        )
                    )
                else:
                    checks.append(
                        ValidationCheckData(
                            check_code="VALID_DATE_WINDOW",
                            check_name="Validity Window Consistency",
                            status="FAILED",
                            details=f"Inconsistent date window: Expiry date ({detected_expiry_date.isoformat()}) cannot be earlier than or equal to issue date ({detected_issue_date.isoformat()}).",
                        )
                    )

            if detected_expiry_date < today:
                checks.append(
                    ValidationCheckData(
                        check_code="CERTIFICATE_EXPIRED",
                        check_name="Active Expiry Check",
                        status="WARNING",
                        details=f"Statutory document expired on {detected_expiry_date.isoformat()}. Renewal or extension required.",
                    )
                )

        # 3. Certificate Number / Identifier Format Check
        cert_num = field_map.get("certificate_number") or field_map.get("consent_number") or field_map.get("licence_number") or field_map.get("authorization_number")
        if cert_num:
            pattern = IDENTIFIER_PATTERNS.get(document_type)
            if pattern and pattern.match(cert_num.strip()):
                checks.append(
                    ValidationCheckData(
                        check_code="CERT_FORMAT_VALID",
                        check_name="Identifier Syntax Verification",
                        status="PASSED",
                        details=f"Identifier '{cert_num}' conforms to {document_type} standard numbering format.",
                    )
                )
            else:
                checks.append(
                    ValidationCheckData(
                        check_code="CERT_FORMAT_VALID",
                        check_name="Identifier Syntax Verification",
                        status="WARNING",
                        details=f"Identifier '{cert_num}' format deviates from typical regulatory pattern.",
                    )
                )
        else:
            checks.append(
                ValidationCheckData(
                    check_code="CERT_FORMAT_VALID",
                    check_name="Identifier Syntax Verification",
                    status="WARNING",
                    details="No explicit statutory certificate/licence number identified.",
                )
            )

        # 4. Issuing Authority Check
        authority = field_map.get("authority") or field_map.get("issuing_authority")
        if authority:
            is_recognized = any(known.lower() in authority.lower() for known in KNOWN_AUTHORITIES)
            if is_recognized:
                checks.append(
                    ValidationCheckData(
                        check_code="AUTHORITY_RECOGNIZED",
                        check_name="Regulatory Authority Verification",
                        status="PASSED",
                        details=f"Issuing body '{authority}' is a recognized statutory authority.",
                    )
                )
            else:
                checks.append(
                    ValidationCheckData(
                        check_code="AUTHORITY_RECOGNIZED",
                        check_name="Regulatory Authority Verification",
                        status="WARNING",
                        details=f"Issuing body '{authority}' not in primary Indian statutory registry. Manual verification suggested.",
                    )
                )

        # 5. Extraction Confidence Score Inspection
        low_conf_fields = [f for f in fields if f.confidence_score < 0.80]
        if low_conf_fields:
            names = ", ".join([f.key for f in low_conf_fields])
            checks.append(
                ValidationCheckData(
                    check_code="LOW_CONFIDENCE_FIELD",
                    check_name="Extraction Confidence Review",
                    status="WARNING",
                    details=f"Fields requiring manual review due to low extraction confidence: {names}.",
                )
            )
        else:
            checks.append(
                ValidationCheckData(
                    check_code="CONFIDENCE_METRICS_PASS",
                    check_name="Extraction Confidence Review",
                    status="PASSED",
                    details="All extracted parameters exceed the minimum 80% confidence threshold.",
                )
            )

        return checks


validator = DocumentRuleValidator()
