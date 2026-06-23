from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .constants import SAVSJO_SCHOOL_NAMES


def skolenhet_lookup(codes: set[str]) -> dict[str, str | None]:
    lookup = {code: None for code in sorted(code for code in codes if code)}
    for code in list(lookup):
        # Register API is primary. If it changes or the network is unavailable,
        # keep the code and let diagnostics expose the missing name resolution.
        urls = [
            f"https://api.skolverket.se/skolenhetsregistret/v2/skolenheter/{urllib.parse.quote(code)}",
            f"https://api.skolverket.se/skolenhetsregistret/v2/sok/skolenheter?skolenhetskod={urllib.parse.quote(code)}",
        ]
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=6) as response:
                    data = json.loads(response.read().decode("utf-8"))
                candidates = data if isinstance(data, list) else data.get("skolenheter") or data.get("hits") or data.get("result") or [data]
                if candidates:
                    item = candidates[0]
                    name = item.get("skolenhetsnamn") or item.get("namn") or item.get("skolEnhetsnamn")
                    if name:
                        lookup[code] = str(name)
                        break
            except Exception:
                continue
        if lookup[code] is None:
            lookup[code] = SAVSJO_SCHOOL_NAMES.get(code)
    return lookup
