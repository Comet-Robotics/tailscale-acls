#!/usr/bin/env python3
"""Validate and format the tailnet policy file.

policy.hujson is HuJSON (JSON with comments and trailing commas). Prettier, Biome
and ruff can't parse that, so this is a small stdlib-only substitute doing the two
things we actually care about:

  1. the policy still parses, and
  2. every member of a group is on its own line, so a PR adding or removing one
     person is a one-line diff instead of a rewritten array.

  python3 scripts/fmt_policy.py --check   # exit 1 if reformatting is needed (CI)
  python3 scripts/fmt_policy.py           # rewrite in place

Membership lists under these top-level keys get expanded one-per-line. Empty
arrays are left as []. Add a key here if we grow another list that PRs churn.
"""
import sys
from pathlib import Path

POLICY = Path(__file__).resolve().parent.parent / "policy.hujson"
EXPAND_UNDER = ("groups", "tagOwners")

CODE, STR, COMMENT = 0, 1, 2


def classify(text):
    """Tag every character as code, string or comment."""
    kinds = bytearray(len(text))
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            start = i
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            for j in range(start, min(i, n)):
                kinds[j] = STR
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            start = i
            while i < n and text[i] != "\n":
                i += 1
            for j in range(start, i):
                kinds[j] = COMMENT
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            start = i
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            for j in range(start, i):
                kinds[j] = COMMENT
            continue
        kinds[i] = CODE
        i += 1
    return kinds


def to_strict_json(text, kinds):
    """HuJSON -> JSON: blank out comments, drop trailing commas."""
    out = []
    for ch, k in zip(text, kinds):
        out.append(("\n" if ch == "\n" else " ") if k == COMMENT else ch)
    s = "".join(out)
    k2 = classify(s)
    res, n = [], len(s)
    for i, ch in enumerate(s):
        if ch == "," and k2[i] == CODE:
            j = i + 1
            while j < n and s[j].isspace():
                j += 1
            if j < n and s[j] in "}]":
                res.append(" ")
                continue
        res.append(ch)
    return "".join(res)


def match_bracket(text, kinds, start):
    """Index of the bracket closing the one at `start`."""
    opener = text[start]
    closer = {"{": "}", "[": "]"}[opener]
    depth = 0
    for i in range(start, len(text)):
        if kinds[i] != CODE:
            continue
        if text[i] == opener:
            depth += 1
        elif text[i] == closer:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"unbalanced {opener} at offset {start}")


def top_level_value(text, kinds, key):
    """Span of the value for a depth-1 `key`, or None."""
    depth, i, n = 0, 0, len(text)
    target = f'"{key}"'
    while i < n:
        if kinds[i] == CODE and text[i] in "{[":
            depth += 1
        elif kinds[i] == CODE and text[i] in "}]":
            depth -= 1
        elif kinds[i] == STR and depth == 1 and text.startswith(target, i):
            j = i + len(target)
            while j < n and (text[j].isspace() or kinds[j] == COMMENT):
                j += 1
            if j < n and text[j] == ":":
                j += 1
                while j < n and (text[j].isspace() or kinds[j] == COMMENT):
                    j += 1
                return j
        i += 1
    return None


def split_elements(text, kinds, open_idx, close_idx):
    """Top-level comma-separated element spans inside an array."""
    parts, depth, cur = [], 0, open_idx + 1
    for i in range(open_idx + 1, close_idx):
        if kinds[i] != CODE:
            continue
        if text[i] in "{[":
            depth += 1
        elif text[i] in "}]":
            depth -= 1
        elif text[i] == "," and depth == 0:
            parts.append(text[cur:i])
            cur = i + 1
    parts.append(text[cur:close_idx])
    return [p.strip() for p in parts if p.strip()]


def indent_unit(text):
    for line in text.splitlines():
        if line.startswith("\t"):
            return "\t"
    return "    "


def format_text(text):
    """Expand membership arrays one-per-line. Returns (new_text, notes)."""
    notes = []
    unit = indent_unit(text)
    edits = []

    for top_key in EXPAND_UNDER:
        kinds = classify(text)
        vstart = top_level_value(text, kinds, top_key)
        if vstart is None or text[vstart] != "{":
            continue
        obj_end = match_bracket(text, kinds, vstart)

        i = vstart + 1
        while i < obj_end:
            if kinds[i] != STR or text[i] != '"':
                i += 1
                continue
            key_start = i
            key_end = i
            while key_end < obj_end and kinds[key_end] == STR:
                key_end += 1
            j = key_end
            while j < obj_end and (text[j].isspace() or kinds[j] == COMMENT):
                j += 1
            if j >= obj_end or text[j] != ":":
                i = key_end
                continue
            j += 1
            while j < obj_end and (text[j].isspace() or kinds[j] == COMMENT):
                j += 1
            if j >= obj_end or text[j] != "[":
                i = max(key_end, j)
                continue

            arr_end = match_bracket(text, kinds, j)
            if any(kinds[k] == COMMENT for k in range(j, arr_end)):
                notes.append(f"{text[key_start:key_end]}: has inline comments, left alone")
                i = arr_end
                continue

            elements = split_elements(text, kinds, j, arr_end)
            line_start = text.rfind("\n", 0, key_start) + 1
            base = text[line_start:key_start]
            base = base[: len(base) - len(base.lstrip())]

            if not elements:
                new = "[]"
            else:
                inner = base + unit
                body = "".join(f"{inner}{e},\n" for e in elements)
                new = "[\n" + body + base + "]"

            if new != text[j:arr_end + 1]:
                edits.append((j, arr_end + 1, new))
            i = arr_end

    for start, end, new in sorted(edits, reverse=True):
        text = text[:start] + new + text[end:]
    return text, notes


def main():
    check = "--check" in sys.argv
    raw = POLICY.read_text()

    try:
        import json
        json.loads(to_strict_json(raw, classify(raw)))
    except Exception as e:
        print(f"::error file=policy.hujson::policy.hujson is not valid HuJSON: {e}")
        return 1

    formatted, notes = format_text(raw)
    for n in notes:
        print(f"note: {n}")

    if formatted == raw:
        print("policy.hujson: valid, formatting OK")
        return 0

    if check:
        print("::error file=policy.hujson::group members must be one per line. "
              "Run: python3 scripts/fmt_policy.py")
        import difflib
        sys.stdout.writelines(difflib.unified_diff(
            raw.splitlines(True), formatted.splitlines(True),
            fromfile="policy.hujson", tofile="policy.hujson (formatted)"))
        return 1

    POLICY.write_text(formatted)
    print("policy.hujson: reformatted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
