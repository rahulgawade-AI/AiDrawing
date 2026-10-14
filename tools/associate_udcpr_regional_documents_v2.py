#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TRANSLATION_DIR = (
    PROJECT_ROOT
    / "data"
    / "regulations"
    / "regional_translation"
)

OCR_DIR = (
    PROJECT_ROOT
    / "data"
    / "regulations"
    / "regional_ocr"
)

CANONICAL_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "regulations"
    / "udcpr_canonical_manifest.json"
)

OUTPUT_JSON = Path(
    "/tmp/udcpr_regional_associations_v2.json"
)

OUTPUT_TXT = Path(
    "/tmp/udcpr_regional_associations_v2.txt"
)


# ============================================================================
# REGULATION NUMBER
# ============================================================================

REGULATION_NUMBER = r"""
\d+(?:\.\d+)+
(?:\s*\([a-zA-ZivxIVX]+\))?
(?:\s*\([a-zA-ZivxIVX]+\))?
"""

REGULATION_CONTEXT_RE = re.compile(
    rf"""
    \b
    (?:
        regulation
        |
        rule
        |
        provision\s+(?:of\s+)?regulation
        |
        regulation\s+no
        |
        regulation\s+number
        |
        regulation\s+no\.
        |
        rule\s+no
        |
        rule\s+no\.
    )
    \s*
    (?:
        number
        |
        no
        |
        no\.
    )?
    \s*
    (?P<number>{REGULATION_NUMBER})
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalize_number(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+", "", value)
    return value


def base_number(value: str) -> str:
    return re.sub(
        r"\([a-zA-ZivxIVX]+\)",
        "",
        value,
    )


# ============================================================================
# JSON
# ============================================================================

def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# CANONICAL MANIFEST
# ============================================================================

def load_manifest() -> dict[str, dict[str, Any]]:

    data = load_json(CANONICAL_MANIFEST)

    if isinstance(data, list):
        records = data

    elif isinstance(data, dict):

        if isinstance(data.get("regulations"), list):
            records = data["regulations"]

        elif isinstance(data.get("items"), list):
            records = data["items"]

        elif isinstance(data.get("records"), list):
            records = data["records"]

        else:
            raise RuntimeError(
                "Unable to locate regulation list in canonical manifest."
            )

    else:
        raise RuntimeError(
            "Invalid canonical manifest."
        )

    result = {}

    for record in records:

        number = (
            record.get("number")
            or record.get("regulation_number")
        )

        if not number:
            continue

        number = normalize_number(str(number))

        result[number] = record

        base = base_number(number)

        if base not in result:
            result[base] = record

    return result


# ============================================================================
# TEXT
# ============================================================================

def normalize_text(text: str) -> str:

    if not text:
        return ""

    text = text.replace("\x00", " ")

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Ignore OCR page number lines.
        if re.fullmatch(
            r"\d{3}(?:\s*/think)?",
            line,
        ):
            continue

        lines.append(line)

    return "\n".join(lines)


def first_nonempty_lines(
    text: str,
    count: int = 40,
) -> list[str]:

    return [
        x.strip()
        for x in text.splitlines()
        if x.strip()
    ][:count]


# ============================================================================
# REGULATION EXTRACTION
# ============================================================================

def extract_references(text: str) -> list[dict[str, Any]]:

    result = []

    seen = set()

    for match in REGULATION_CONTEXT_RE.finditer(text):

        number = normalize_number(
            match.group("number")
        )

        key = (
            number,
            match.start(),
        )

        if key in seen:
            continue

        seen.add(key)

        start = max(
            0,
            match.start() - 120,
        )

        end = min(
            len(text),
            match.end() + 180,
        )

        context = re.sub(
            r"\s+",
            " ",
            text[start:end],
        ).strip()

        result.append(
            {
                "number": number,
                "base_number": base_number(number),
                "context": context,
                "position": match.start(),
            }
        )

    return result


# ============================================================================
# SUBJECT
# ============================================================================

def extract_subject(text: str) -> str:

    lines = first_nonempty_lines(
        text,
        100,
    )

    for i, line in enumerate(lines):

        if re.search(
            r"\bsubject\b",
            line,
            re.IGNORECASE,
        ):

            # Subject on same line.
            if ":" in line:
                return line

            # Subject on following line.
            if i + 1 < len(lines):
                return (
                    line
                    + " "
                    + lines[i + 1]
                )

    return ""


# ============================================================================
# DOCUMENT START DETECTION
# ============================================================================

def looks_like_new_document(
    translated: str,
    original_ocr: str,
) -> bool:

    text = (
        translated
        + "\n"
        + original_ocr
    )

    head = "\n".join(
        first_nonempty_lines(
            text,
            45,
        )
    )

    has_government = bool(
        re.search(
            r"Maharashtra Government|"
            r"Government of Maharashtra|"
            r"महाराष्ट्र शासन|"
            r"महाराष्ट्र सरकार|"
            r"Urban Development Department|"
            r"Urban Development|"
            r"नगर विकास विभाग",
            head,
            re.IGNORECASE,
        )
    )

    has_subject = bool(
        re.search(
            r"\bsubject\b|"
            r"\bविषय\b",
            head,
            re.IGNORECASE,
        )
    )

    has_order = bool(
        re.search(
            r"\bOrder\b|"
            r"\bGovernment Order\b|"
            r"\bक्रमांक\b|"
            r"\bआदेश\b|"
            r"\bNo\.\s*:",
            head,
            re.IGNORECASE,
        )
    )

    # A page with government header + subject/order is strongly indicative
    # of a new document.
    if has_government and (
        has_subject
        or has_order
    ):
        return True

    return False


# ============================================================================
# GROUP PAGES
# ============================================================================

def load_pages() -> list[dict[str, Any]]:

    pages = []

    for path in sorted(
        TRANSLATION_DIR.glob("page_*.json")
    ):

        match = re.fullmatch(
            r"page_(\d+)\.json",
            path.name,
        )

        if not match:
            continue

        page_number = int(match.group(1))

        if not 441 <= page_number <= 511:
            continue

        data = load_json(path)

        translated = data.get(
            "translated_english_text",
            "",
        )

        original = data.get(
            "original_ocr_text",
            "",
        )

        pages.append(
            {
                "pdf_page": page_number,
                "translation_file": str(path),
                "translated_text": translated,
                "original_ocr_text": original,
            }
        )

    return pages


def group_pages(
    pages: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:

    groups = []

    current = []

    for page in pages:

        page_number = page["pdf_page"]

        is_new = looks_like_new_document(
            page["translated_text"],
            page["original_ocr_text"],
        )

        if not current:

            current = [page]
            continue

        previous_page = current[-1]["pdf_page"]

        # Missing page means we cannot safely join across the gap.
        contiguous = (
            page_number == previous_page + 1
        )

        if is_new and contiguous:

            groups.append(current)
            current = [page]

        elif not contiguous:

            groups.append(current)
            current = [page]

        else:

            current.append(page)

    if current:
        groups.append(current)

    return groups


# ============================================================================
# ASSOCIATION CLASSIFICATION
# ============================================================================

def resolve_reference(
    number: str,
    manifest: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:

    exact = manifest.get(number)

    if exact:
        return exact

    return manifest.get(
        base_number(number)
    )


def is_19v(number: str) -> bool:

    normalized = normalize_number(
        number
    ).lower()

    return normalized in {
        "1.9(v)",
        "1.9(vii)",
    } or normalized.startswith(
        "1.9(v)"
    )


def classify_document(
    group: list[dict[str, Any]],
    manifest: dict[str, dict[str, Any]],
) -> dict[str, Any]:

    full_text = "\n".join(
        normalize_text(
            p["translated_text"]
        )
        for p in group
    )

    subjects = []

    for page in group:

        subject = extract_subject(
            normalize_text(
                page["translated_text"]
            )
        )

        if subject:
            subjects.append(subject)

    subject = subjects[0] if subjects else ""

    subject_refs = [
        x["number"]
        for x in extract_references(subject)
    ]

    all_refs = extract_references(
        full_text
    )

    # Preserve first appearance.
    unique = []

    seen = set()

    for ref in all_refs:

        number = ref["number"]

        if number in seen:
            continue

        seen.add(number)

        unique.append(ref)

    # ----------------------------------------------------------------------
    # Resolve only references that actually exist in the canonical manifest.
    # ----------------------------------------------------------------------

    resolved = {}

    for ref in unique:

        record = resolve_reference(
            ref["number"],
            manifest,
        )

        if record is not None:

            resolved[
                ref["number"]
            ] = {
                "ref": ref,
                "record": record,
            }

    primary = []
    secondary = []
    procedural = []
    historical = []

    # ----------------------------------------------------------------------
    # SUBJECT REFERENCES ARE STRONG.
    # ----------------------------------------------------------------------

    for number in subject_refs:

        if number not in resolved:
            continue

        if number not in primary:

            primary.append(number)

    # ----------------------------------------------------------------------
    # SPECIAL HANDLING FOR 1.9(v)
    # ----------------------------------------------------------------------

    if primary:

        if any(
            is_19v(x)
            for x in primary
        ):

            # If there is another substantive subject regulation,
            # 1.9(v) is procedural.
            substantive = [
                x
                for x in primary
                if not is_19v(x)
            ]

            if substantive:

                primary = substantive

                for x in subject_refs:

                    if (
                        is_19v(x)
                        and x in resolved
                        and x not in procedural
                    ):
                        procedural.append(x)

    # ----------------------------------------------------------------------
    # BODY CLASSIFICATION
    # ----------------------------------------------------------------------

    for number, item in resolved.items():

        if number in primary:
            continue

        ref = item["ref"]

        context = ref["context"].lower()

        # 1.9(v) is procedural when used as the authority for issuing
        # clarification/order.
        if is_19v(number):

            procedural.append(number)
            continue

        # Strong historical/reference-list indicators.
        historical_patterns = [
            r"\breference\b",
            r"\bprevious order\b",
            r"\bearlier order\b",
            r"\bgovernment order no\.",
            r"\bdated\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4}",
            r"\bnotification no\.",
        ]

        historical_hit = any(
            re.search(
                pattern,
                context,
                re.IGNORECASE,
            )
            for pattern in historical_patterns
        )

        # Strong substantive language.
        substantive_patterns = [
            r"as per regulation",
            r"under regulation",
            r"in accordance with regulation",
            r"provision of regulation",
            r"provisions of regulation",
            r"following explanatory",
            r"clarification regarding regulation",
            r"clarification.*regulation",
            r"shall be",
            r"shall apply",
            r"shall be allowed",
            r"shall be considered",
            r"shall be permitted",
            r"is applicable",
            r"entitled to",
            r"subject to",
        ]

        substantive_hit = any(
            re.search(
                pattern,
                context,
                re.IGNORECASE,
            )
            for pattern in substantive_patterns
        )

        if substantive_hit and not historical_hit:

            if number not in secondary:
                secondary.append(number)

        elif historical_hit:

            if number not in historical:
                historical.append(number)

    # ----------------------------------------------------------------------
    # Subject references always outrank secondary/historical.
    # ----------------------------------------------------------------------

    secondary = [
        x
        for x in secondary
        if x not in primary
    ]

    historical = [
        x
        for x in historical
        if x not in primary
        and x not in secondary
    ]

    procedural = list(
        dict.fromkeys(procedural)
    )

    primary = list(
        dict.fromkeys(primary)
    )

    secondary = list(
        dict.fromkeys(secondary)
    )

    # ----------------------------------------------------------------------
    # Standalone
    # ----------------------------------------------------------------------

    standalone = (
        len(primary) == 0
        and len(secondary) == 0
    )

    if primary:

        confidence = "high"

    elif secondary:

        confidence = "medium"

    elif procedural:

        confidence = "low"

    else:

        confidence = "none"

    # ----------------------------------------------------------------------
    # Canonical output
    # ----------------------------------------------------------------------

    matches = []

    ordered_numbers = (
        primary
        + secondary
        + procedural
        + historical
    )

    for number in ordered_numbers:

        item = resolved.get(number)

        if not item:
            continue

        record = item["record"]

        if number in primary:
            association_type = "primary"

        elif number in secondary:
            association_type = "secondary"

        elif number in procedural:
            association_type = "procedural"

        else:
            association_type = "historical_reference"

        matches.append(
            {
                "reference_number": number,
                "canonical_number": (
                    record.get("number")
                    or record.get(
                        "regulation_number"
                    )
                ),
                "canonical_title": (
                    record.get("title")
                    or record.get(
                        "regulation_title"
                    )
                    or ""
                ),
                "canonical_key": (
                    record.get("canonical_key")
                    or record.get("key")
                    or ""
                ),
                "association_type": association_type,
            }
        )

    return {
        "pdf_page_start": group[0]["pdf_page"],
        "pdf_page_end": group[-1]["pdf_page"],
        "pages": [
            x["pdf_page"]
            for x in group
        ],
        "translation_files": [
            x["translation_file"]
            for x in group
        ],
        "subject": subject,
        "primary_regulations": primary,
        "secondary_regulations": secondary,
        "procedural_regulations": procedural,
        "historical_references": historical,
        "standalone": standalone,
        "confidence": confidence,
        "canonical_matches": matches,
        "all_detected_references": [
            {
                "number": x["number"],
                "base_number": x["base_number"],
                "context": x["context"],
            }
            for x in unique
        ],
        "translated_text": full_text,
    }


# ============================================================================
# MAIN
# ============================================================================

def main():

    print("=" * 100)
    print("UDCPR REGIONAL DOCUMENT ASSOCIATION V2")
    print("=" * 100)

    manifest = load_manifest()

    pages = load_pages()

    print(
        f"Translation pages loaded : {len(pages)}"
    )

    expected = set(
        range(441, 512)
    )

    found = {
        x["pdf_page"]
        for x in pages
    }

    missing = sorted(
        expected - found
    )

    if missing:

        print(
            "Missing pages:",
            missing,
        )

    groups = group_pages(
        pages
    )

    print(
        f"Document groups detected  : {len(groups)}"
    )

    results = []

    for index, group in enumerate(
        groups,
        start=1,
    ):

        result = classify_document(
            group,
            manifest,
        )

        result["document_id"] = (
            f"regional-{index:03d}"
        )

        results.append(result)

        print(
            f"[{index:03d}] "
            f"pages "
            f"{result['pdf_page_start']}-"
            f"{result['pdf_page_end']} "
            f"| primary="
            f"{result['primary_regulations']} "
            f"| secondary="
            f"{result['secondary_regulations']} "
            f"| procedural="
            f"{result['procedural_regulations']} "
            f"| standalone="
            f"{result['standalone']}"
        )

    summary = {
        "translation_pages_found": len(pages),
        "expected_pages": 71,
        "missing_pages": missing,
        "document_groups": len(results),
        "linked_documents": sum(
            not x["standalone"]
            for x in results
        ),
        "standalone_documents": sum(
            x["standalone"]
            for x in results
        ),
        "multiple_primary_documents": sum(
            len(x["primary_regulations"]) > 1
            for x in results
        ),
    }

    # Do not store massive translated text in JSON report twice.
    report_documents = []

    for result in results:

        copy = dict(result)

        # Keep a short preview in the report.
        text = copy.pop(
            "translated_text"
        )

        copy["translated_preview"] = (
            text[:4000]
        )

        report_documents.append(copy)

    report = {
        "schema": (
            "udcpr.regional.association.v2"
        ),
        "read_only": True,
        "summary": summary,
        "documents": report_documents,
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with OUTPUT_TXT.open(
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "UDCPR REGIONAL DOCUMENT ASSOCIATION V2\n"
        )

        f.write(
            "=" * 100
            + "\n\n"
        )

        f.write(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
            )
        )

        f.write("\n")

        for result in results:

            f.write(
                "\n"
                + "=" * 100
                + "\n"
            )

            f.write(
                f"DOCUMENT {result['document_id']}\n"
            )

            f.write(
                f"PAGES: "
                f"{result['pdf_page_start']}-"
                f"{result['pdf_page_end']}\n"
            )

            f.write(
                f"SUBJECT: "
                f"{result['subject']}\n"
            )

            f.write(
                f"PRIMARY: "
                f"{result['primary_regulations']}\n"
            )

            f.write(
                f"SECONDARY: "
                f"{result['secondary_regulations']}\n"
            )

            f.write(
                f"PROCEDURAL: "
                f"{result['procedural_regulations']}\n"
            )

            f.write(
                f"HISTORICAL: "
                f"{result['historical_references']}\n"
            )

            f.write(
                f"STANDALONE: "
                f"{result['standalone']}\n"
            )

            f.write(
                f"CONFIDENCE: "
                f"{result['confidence']}\n"
            )

            f.write(
                "\nCANONICAL MATCHES:\n"
            )

            for match in result[
                "canonical_matches"
            ]:

                f.write(
                    "  "
                    f"{match['reference_number']}"
                    " -> "
                    f"{match['canonical_number']}"
                    " | "
                    f"{match['canonical_title']}"
                    " | "
                    f"{match['association_type']}"
                    "\n"
                )

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(
        "JSON:",
        OUTPUT_JSON,
    )

    print(
        "TXT :",
        OUTPUT_TXT,
    )

    print()
    print(
        "NO DATABASE OR CHROMA CHANGES WERE MADE."
    )


if __name__ == "__main__":
    main()
