"""Utilities for handling UXML data from Unity bundles."""

from __future__ import annotations
from pathlib import Path
import re
from collections import namedtuple
from typing import List

StringHit = namedtuple("StringHit", ["offset", "text"])

UI_KEYWORDS = [
    "VisualElement",
    "Label",
    "ScrollView",
    "ListView",
    "Button",
    "Toggle",
    "Calendar",
    "CalendarTool",
    "TextField",
    "DropdownField",
    "Foldout",
    "Box",
    "IMGUIContainer",
    "Template",
    "Element",
]


def extract_strings_with_offsets(filename: Path) -> List[StringHit]:
    """Extract strings with offsets from a binary file."""
    hits = []
    with open(filename, "rb") as f:
        data = f.read()
    pattern = re.compile(rb"[ -~]{3,}")
    for match in pattern.finditer(data):
        offset = match.start()
        text = match.group().decode("utf-8", errors="ignore")
        hits.append(StringHit(offset, text))
    return hits


def build_uxml_tree(hits: List[StringHit]) -> str:
    """Build a UXML-like tree from string hits."""
    xml_lines = ["<UXML>"]
    indent = 1
    last_offset = 0
    open_elements = []

    for hit in hits:
        text = hit.text.strip()
        if not text or len(text) > 200:
            continue

        if any(k in text for k in UI_KEYWORDS):
            # Guess indent based on offset difference
            if hit.offset - last_offset > 300:
                indent = max(1, indent - 1)
            elif hit.offset - last_offset < 120:
                indent = min(indent + 1, 6)
            xml_lines.append("  " * indent + f'<Element name="{text}" offset="{hit.offset}">')
            open_elements.append(indent)
        else:
            classes, style = detect_class_or_style(text)
            if classes or style:
                attr_line = []
                if classes:
                    attr_line.append(f'class="{" ".join(classes)}"')
                if style:
                    attr_line.append(f'style="{style}"')
                xml_lines.append("  " * (indent + 1) + f"<Style {' '.join(attr_line)} />")
            elif text.lower().startswith("uxmlserializeddata"):
                xml_lines.append("  " * (indent + 1) + "<!-- SerializedData marker -->")
            elif len(text) < 60:
                xml_lines.append("  " * (indent + 1) + f"<!-- attr: {text} -->")

        last_offset = hit.offset

    # Close elements
    for _ in range(len(open_elements)):
        indent = open_elements.pop()
        xml_lines.append("  " * indent + "</Element>")
    xml_lines.append("</UXML>")
    return "\n".join(xml_lines)


def detect_class_or_style(text: str) -> tuple:
    """Detect classes or inline styles in text."""
    classes, style = [], None
    if re.match(r"^[.#]?[A-Za-z0-9_\-]+$", text) or "class" in text.lower():
        if text.startswith("."):
            classes.append(text.strip())
        elif "class" in text.lower():
            parts = re.findall(r"[A-Za-z0-9_\-]+", text)
            classes.extend(parts[1:]) if len(parts) > 1 else classes
    if ":" in text and ";" in text:
        style = text.strip()
    return classes, style
