# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""The ini dialect of fcitx5, as src/ngosen-ibus-config.cpp reads it."""

ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "f": "\f", "r": "\r", "t": "\t", "v": "\v"}
ESCAPED = {char: "\\" + letter for letter, char in ESCAPES.items()}
NEEDS_QUOTES = set(' \f\r\t\v"\\\n')
SPACE = " \t\r\f\v"


def unescape(value):
    """The value fcitx5 reads, or None when it drops the line."""
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return value
    out = []
    chars = iter(value[1:-1])
    for char in chars:
        if char == '"':
            return None
        if char != "\\":
            out.append(char)
            continue
        letter = next(chars, None)
        if letter not in ESCAPES:
            return None
        out.append(ESCAPES[letter])
    return "".join(out)


def escape(value):
    if not NEEDS_QUOTES.intersection(value):
        return value
    return '"' + "".join(ESCAPED.get(char, char) for char in value) + '"'


def parse(text):
    """Keys before the first section, and each section's keys."""
    top, sections = {}, {}
    current = top
    for line in text.splitlines():
        line = line.strip(SPACE)
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], {})
            continue
        key, equal, raw = line.partition("=")
        if not equal:
            continue
        value = unescape(raw)
        if value is not None:
            current[key] = value
    return top, sections


def read_list(sections, name):
    """Key/Value pairs of [name/0], [name/1]…; fcitx5 stops at the first gap."""
    entries = []
    while (section := sections.get(f"{name}/{len(entries)}")) is not None:
        entries.append((section.get("Key", ""), section.get("Value", "")))
    return entries


def list_text(name, entries):
    return "".join(
        f"[{name}/{i}]\nKey={escape(key)}\nValue={escape(value)}\n\n"
        for i, (key, value) in enumerate(entries)
    )


def set_value(text, key, value):
    """text with key set to value, keeping every other line as it was."""
    lines = text.splitlines()
    first_section = next(
        (i for i, line in enumerate(lines) if line.strip(SPACE).startswith("[")), len(lines)
    )
    new_line = f"{key}={escape(value)}"
    found = False
    for i in range(first_section):
        if lines[i].strip(SPACE).partition("=")[0] == key and "=" in lines[i]:
            lines[i] = new_line
            found = True
    if not found:
        lines.insert(first_section, new_line)
    return "\n".join(lines) + "\n"
