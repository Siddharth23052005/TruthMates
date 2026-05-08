from __future__ import annotations

import hashlib
import re


def normalize_claim_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def build_analysis_key(
    *,
    claim: str,
    input_type: str = "text",
    source_ref: str = "",
) -> str:
    normalized_claim = normalize_claim_text(claim)
    normalized_source = (source_ref or "").strip().lower()
    raw_key = f"{(input_type or 'text').strip().lower()}|{normalized_source}|{normalized_claim}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
