"""CiteProof claim-source verification package."""

from citeproof.models import EvidenceSpan, Label, VerificationResult
from citeproof.verifier import verify_claim, verify_draft

__all__ = ["EvidenceSpan", "Label", "VerificationResult", "verify_claim", "verify_draft"]
