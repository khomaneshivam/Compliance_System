"""
Deterministic Regulatory Diffing & Comparison Engine
Compares prior regulation text with newly extracted gazette text to detect
additions, amendments, numerical threshold modifications, and supersessions.
"""

import difflib
import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class DiffChange(BaseModel):
    change_type: str = Field(..., description="ADDED, REMOVED, MODIFIED")
    old_fragment: Optional[str] = Field(None, description="Pre-existing text snippet")
    new_fragment: Optional[str] = Field(None, description="Amended text snippet")
    explanation: str = Field(..., description="Explainable description of what changed")


class DiffResult(BaseModel):
    detected_change_type: str = Field(..., description="AMENDMENT, ADDITION, REPEAL_SUPERSEDED, DATE_EXTENSION")
    changes: List[DiffChange] = Field(default_factory=list, description="Granular clause changes")
    diff_summary: str = Field(..., description="Human-readable plain language summary of the diff")
    similarity_ratio: float = Field(..., description="Levenshtein/SequenceMatcher similarity (0.0 to 1.0)")
    has_threshold_change: bool = Field(False, description="Whether numeric limits or units were altered")
    has_date_change: bool = Field(False, description="Whether effective dates or deadlines shifted")


class RegulatoryDiffer:
    """
    Compares prior statutory text against newly published amendments.
    Produces deterministic diffs suitable for human legal review.
    """

    NUMERIC_REGEX = re.compile(r"\b\d+(?:\.\d+)?\s*(?:kld|tpa|tph|hp|kw|kva|days?|months?|meters?|sqm|inr|rs\.?)\b", re.IGNORECASE)
    REPEAL_KEYWORDS = {"repeal", "supersede", "rescind", "cancel", "in substitution of", "hereby replaced"}
    EXTENSION_KEYWORDS = {"extend", "grace period", "extended up to", "defer", "postpone"}

    def compare(self, old_text: Optional[str], new_text: str) -> DiffResult:
        """
        Performs semantic diffing between old regulatory text and new text.
        """
        if not old_text or not old_text.strip():
            # Brand new regulation (no prior baseline)
            return DiffResult(
                detected_change_type="ADDITION",
                changes=[
                    DiffChange(
                        change_type="ADDED",
                        old_fragment=None,
                        new_fragment=new_text[:300].strip(),
                        explanation="New statutory obligation introduced into regulatory catalogue.",
                    )
                ],
                diff_summary="New statutory obligation introduced without a prior baseline version.",
                similarity_ratio=0.0,
                has_threshold_change=bool(self.NUMERIC_REGEX.search(new_text)),
                has_date_change=False,
            )

        clean_old = old_text.strip()
        clean_new = new_text.strip()

        # Check sequence similarity ratio
        matcher = difflib.SequenceMatcher(None, clean_old, clean_new)
        ratio = matcher.ratio()

        # Check for repeal / supersession language
        is_repeal = any(kw in clean_new.lower() for kw in self.REPEAL_KEYWORDS)
        # Check for date extension language
        is_extension = any(kw in clean_new.lower() for kw in self.EXTENSION_KEYWORDS)

        # Extract numeric thresholds
        old_numbers = set(self.NUMERIC_REGEX.findall(clean_old.lower()))
        new_numbers = set(self.NUMERIC_REGEX.findall(clean_new.lower()))
        threshold_changed = (old_numbers != new_numbers) and bool(new_numbers or old_numbers)

        changes: List[DiffChange] = []
        old_lines = [l.strip() for l in clean_old.split("\n") if l.strip()]
        new_lines = [l.strip() for l in clean_new.split("\n") if l.strip()]

        diff_lines = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

        added_snippets = []
        removed_snippets = []
        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                added_snippets.append(line[1:].strip())
            elif line.startswith("-") and not line.startswith("---"):
                removed_snippets.append(line[1:].strip())

        if threshold_changed:
            added_thresh = ", ".join(sorted(list(new_numbers - old_numbers)))
            removed_thresh = ", ".join(sorted(list(old_numbers - new_numbers)))
            changes.append(
                DiffChange(
                    change_type="MODIFIED",
                    old_fragment=removed_thresh or None,
                    new_fragment=added_thresh or None,
                    explanation=f"Operational statutory threshold modified: prior [{removed_thresh}] -> amended [{added_thresh}].",
                )
            )

        if added_snippets:
            changes.append(
                DiffChange(
                    change_type="ADDED",
                    old_fragment=None,
                    new_fragment=" ".join(added_snippets[:2]),
                    explanation="New provisions, conditions, or reporting mandates introduced.",
                )
            )

        if removed_snippets:
            changes.append(
                DiffChange(
                    change_type="REMOVED",
                    old_fragment=" ".join(removed_snippets[:2]),
                    new_fragment=None,
                    explanation="Provisions or requirements superseded or omitted in amended text.",
                )
            )

        # Determine overall classification
        if is_repeal:
            detected_type = "REPEAL_SUPERSEDED"
            summary = "Prior regulatory requirement is formally repealed and superseded by this notification."
        elif is_extension:
            detected_type = "DATE_EXTENSION"
            summary = "Compliance timeline or filing grace period extended per gazette amendment."
        elif threshold_changed:
            detected_type = "AMENDMENT"
            summary = f"Statutory thresholds or criteria modified (similarity {ratio:.1%})."
        elif ratio > 0.95:
            detected_type = "AMENDMENT"
            summary = "Minor procedural or textual amendment with identical core thresholds."
        else:
            detected_type = "AMENDMENT"
            summary = f"Operative regulatory provisions amended with substantial textual revisions (similarity {ratio:.1%})."

        return DiffResult(
            detected_change_type=detected_type,
            changes=changes,
            diff_summary=summary,
            similarity_ratio=round(ratio, 4),
            has_threshold_change=threshold_changed,
            has_date_change=is_extension,
        )
