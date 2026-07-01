from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    if text is None:
        return ""

    text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    return text
