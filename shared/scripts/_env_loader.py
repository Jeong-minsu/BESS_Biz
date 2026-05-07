"""
Section-aware .env loader for the BESS_Biz project.

The user's .env groups credentials under '# <Vendor> Credentials' headers.
Several vendors reuse generic key names (USERNAME, PASSWORD), so a flat dict
loader silently overwrites earlier values. This module returns one dict per
section so each vendor's USERNAME/PASSWORD survives intact.

Recognized section keywords (case-insensitive substring match against the
comment line):

    yes_energy_s3   ← "yes energy datalake"
    yes_energy      ← "yes energy api"  (or just "yes energy")
    ercot           ← "ercot"
    enverus         ← "enverus"
    ag2             ← "ag2"
    smartbidder     ← "smartbidder" / "smartbid"
    tenaska         ← "tenaska"

Lines before any header land in the special section "_default".

Usage:

    from _env_loader import load_env_sections
    s = load_env_sections()                       # all sections
    yenv = s.get("yes_energy", {})
    ye_user = yenv["YES_ENERGY_USERNAME"]
    sb = s.get("smartbidder", {})
    sb_resource = sb.get("Resource") or sb.get("SMARTBIDDER_RESOURCE", "Kiskadee Storage")
"""
from __future__ import annotations

from pathlib import Path

# Order matters — longest/most specific keywords first so "yes energy datalake"
# wins over "yes energy". Each tuple is (lowercase keyword, section name).
_SECTION_RULES: list[tuple[str, str]] = [
    ("yes energy datalake", "yes_energy_s3"),
    ("yes energy",          "yes_energy"),
    ("ercot",               "ercot"),
    ("enverus",             "enverus"),
    ("ag2",                 "ag2"),
    ("smartbidder",         "smartbidder"),
    ("smartbid",            "smartbidder"),
    ("tenaska",             "tenaska"),
]


def _classify(comment_text: str) -> str | None:
    """Return the section name if `comment_text` matches a known section
    keyword, else None. Case-insensitive substring match."""
    t = comment_text.lower()
    for kw, sec in _SECTION_RULES:
        if kw in t:
            return sec
    return None


def load_env_sections(env_path: Path | str | None = None) -> dict[str, dict[str, str]]:
    """
    Parse the .env file grouped by '# <Vendor>' header lines.

    Returns:
        {section_name: {KEY: VALUE, ...}, ...}

    Whitespace around keys/values and surrounding quotes are stripped.
    Lines before the first recognized header are stored under "_default".
    Comments not matching any section keyword leave the current section
    unchanged (so a stray comment doesn't reset the parser).
    """
    if env_path is None:
        # Default: BESS_Biz/.env — two levels up from this file
        env_path = Path(__file__).resolve().parents[2] / ".env"
    env_path = Path(env_path)

    sections: dict[str, dict[str, str]] = {"_default": {}}
    current = "_default"

    if not env_path.exists():
        return sections

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            inner = line.lstrip("#").strip()
            sec = _classify(inner)
            if sec is not None:
                current = sec
                sections.setdefault(current, {})
            # else: keep current section (stray comment)
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'").strip()
        sections.setdefault(current, {})[k] = v

    return sections


def first(d: dict[str, str], *keys: str, default: str | None = None) -> str | None:
    """Return the first key found in d, else default. Useful when a vendor
    has multiple acceptable key names (e.g. Resource vs SMARTBIDDER_RESOURCE)."""
    for k in keys:
        if k in d and d[k] != "":
            return d[k]
    return default


# ---------- self-check (no secrets printed) ----------
if __name__ == "__main__":
    s = load_env_sections()
    print("Sections found:")
    for name, kv in s.items():
        if not kv:
            continue
        print(f"  [{name}]")
        for k, v in kv.items():
            print(f"    {k:30s} ***({len(v)} chars)")
