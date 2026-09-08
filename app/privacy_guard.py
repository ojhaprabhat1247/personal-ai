import re
from dataclasses import dataclass


@dataclass
class PrivacyResult:
    sensitive: bool
    reasons: list[str]


class PrivacyGuard:

    SENSITIVE_PATTERNS = {
        "password": [
            r"\bpassword\b",
            r"\bpasscode\b",
            r"\bpin\b",
            r"\botp\b",
        ],

        "financial": [
            r"\bcredit card\b",
            r"\bdebit card\b",
            r"\bbank account\b",
            r"\baccount number\b",
            r"\bcvv\b",
            r"\bupi pin\b",
        ],

        "identity": [
            r"\baadhaar\b",
            r"\baadhar\b",
            r"\bpan card\b",
            r"\bpassport number\b",
        ],

        "medical": [
            r"\bmedical record\b",
            r"\bmedical report\b",
            r"\bdiagnosis\b",
            r"\bprescription\b",
        ],

        "private_data": [
            r"\bprivate file\b",
            r"\bpersonal document\b",
            r"\bconfidential\b",
            r"\bsecret\b",
        ],
    }

    def analyze(
        self,
        text: str
    ) -> PrivacyResult:

        normalized = text.lower()

        reasons = []

        for category, patterns in (
            self.SENSITIVE_PATTERNS.items()
        ):
            for pattern in patterns:

                if re.search(
                    pattern,
                    normalized
                ):
                    reasons.append(category)
                    break

        return PrivacyResult(
            sensitive=bool(reasons),
            reasons=reasons
        )

    def is_sensitive(
        self,
        text: str
    ) -> bool:

        return self.analyze(
            text
        ).sensitive