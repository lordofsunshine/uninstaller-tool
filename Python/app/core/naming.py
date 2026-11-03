from __future__ import annotations

import re

_NON_WORD = re.compile(r"[^\w]+")


def normalize_name(value: str | None) -> str:
    return _NON_WORD.sub("", str(value or "").casefold())
