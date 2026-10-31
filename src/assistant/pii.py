"""PII detection and redaction. Used on input, on output and before logging."""

from __future__ import annotations

import re

# Order matters: SSN before the generic VA file number pattern.
PII_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}[- ]\d{2}[- ]\d{4}\b|(?<=ssn)\W{0,5}\d{9}\b", re.IGNORECASE),
    "VA_FILE_NUMBER": re.compile(r"\b[cC]?\d{8,9}\b"),
    "PHONE": re.compile(r"(?<!\d)(\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
    "DOB": re.compile(
        r"\b(dob|date of birth|born( on)?)( is|:)?\W{0,3}\d{1,4}[/-]\d{1,2}[/-]\d{1,4}\b",
        re.IGNORECASE,
    ),
    "BANK_ACCOUNT": re.compile(r"\b(account|routing)( number| no\.?| #)?\W{0,3}\d{6,17}\b", re.IGNORECASE),
}

PII_WARNING = (
    "For your safety, I removed the personal identifiers from your message and did not "
    "store or share them. Please don't enter Social Security numbers, VA file numbers, "
    "bank details or medical records in this chat. [D23]"
)


def redact(text: str) -> tuple[str, list[str]]:
    found = []
    for label, pattern in PII_PATTERNS.items():
        text, n = pattern.subn(f"[REDACTED_{label}]", text)
        if n:
            found.append(label)
    return text, found
