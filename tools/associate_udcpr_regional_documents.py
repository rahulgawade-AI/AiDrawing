#!/usr/bin/env python3

"""
Associate translated UDCPR regional government documents with canonical
UDCPR regulations.

IMPORTANT:
    - READ ONLY
    - Does NOT modify PostgreSQL
    - Does NOT modify Chroma
    - Does NOT modify canonical regulation text

Input:
    data/regulations/regional_translation/page_*.json

Output:
    /tmp/udcpr_regional_associations_final.json
    /tmp/udcpr_regional_associations_final.txt

Association logic:
    1. Explicit "Subject" regulation references have highest priority.
    2. Explicit substantive references in the body are next.
    3. Regulation 1.9(v) is treated as PROCEDURAL unless the subject/body
       clearly makes it the actual subject.
    4. Dates and measurements are never treated as regulation references.
    5. Multiple substantive regulations are allowed.
    6. Documents without a reliable regulation association are standalone.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TRANSLATION_DIR = (
    PROJECT_ROOT
    / "data"
    / "regulations"
    / "regional_translation"
)

# Canonical manifest created during the clean UDCPR rebuild.
CANONICAL_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "regulations"
    / "udcpr_canonical_manifest.json"
)

OUTPUT_JSON = Path(
    "/tmp/udcpr_regional_associations_final.json"
)

OUTPUT_TXT = Path(
    "/tmp/udcpr_regional_associations_final.txt"
)


# ---------------------------------------------------------------------------
# Regulation reference handling
# ---------------------------------------------------------------------------

# Regulation references must appear in a regulatory context.
#
# Examples accepted:
#
#   Regulation No. 10.10.1
#   Regulation 10.10.1
#   regulation no. 3.5.1(i)
#   under Regulation No. 11.2.5
#   as per Regulation 4.12.1(ii)
#
# Examples deliberately NOT accepted:
#
#   10.05.2021
#   14.06.2021
#   0.40 hectare
#   2.0 hectare
#   15.00 m
#   9.00 m
#   465 sq.mt.
#
REGULATION_CONTEXT_RE = re.compile(
    r"""
    \b
    (?:
        regulation
        |
        rule
        |
        provision\s+of\s+regulation
        |
        provision\s+no\.
        |
        regulation\s+no\.
    )
    \s*
    (?:
        no\.
        |
        number
        |
    )?
    \s*
    (?P<number>
        \d+(?:\.\d+)+
        (?:\s*\([a-zivx]+\))?
        (?:\s*\([a-zivx]+\))?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# A stricter standalone form is useful when the text says:
#
#   Regulation No. 3.4.1 (i)
#
# and OCR has inserted spaces.
#
REGULATION_NUMBER_RE = re.compile(
    r"""
    (?P<number>
        \d+(?:\.\d+)+
        (?:\s*\([a-zivx]+\))?
        (?:\s*\([a-zivx]+\))?
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def normalize_regulation_number(value: str) -> str:
    """
    Normalize formatting but do not semantically alter the regulation.

    Examples:
        "3.4.1 (i)" -> "3.4.1(i)"
        "14.2.1.2.4 (ii)" -> "14.2.1.2.4(ii)"
    """
    value = value.strip()
    value = re.sub(r"\s+", "", value)
    return value


def regulation_base(number: str) -> str:
    """
    Return base regulation.

    3.4.1(i) -> 3.4.1
    14.2.1.2.4(ii) -> 14.2.1.2.4
    """
    return re.sub(r"\([a-zivx]+\)", "", number, flags=re.IGNORECASE)


def is_probable_date(text: str, start: int, end: int) -> bool:
    """
    Protect against dates being interpreted as regulation numbers.

    This is mostly defensive because our main regex requires regulatory
    context.
    """
    left = text[max(0, start - 15):start]
    right = text[end:end + 15]

    surrounding = left + text[start:end] + right

    if re.search(
        r"\b(?:dated|date|dt\.?)\b",
        surrounding,
        re.IGNORECASE,
    ):
        return True

    # YYYY-style date components / dd.mm.yyyy
    if re.fullmatch(
        r"\d{1,2}\.\d{1,2}\.\d{4}",
        text[start:end],
    ):
        return True

    return False


def clean_text(text: str) -> str:
    """
    Remove obvious page markers and normalize whitespace for analysis only.
    Original source text is never modified in the saved association report.
    """
    if not text:
        return ""

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Remove OCR page number markers such as:
        # 464
        # 465 /think
        if re.fullmatch(r"\d{3}(?:\s*/think)?", line):
            continue

        lines.append(line)

    return "\n".join(lines)


def first_lines(text: str, count: int = 25) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ][:count]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Canonical regulation loading
# ---------------------------------------------------------------------------

def load_canonical_manifest() -> dict[str, dict[str, Any]]:
    """
    Load the canonical 329-regulation manifest.

    We deliberately do NOT use arbitrary rows from PostgreSQL here because
    PostgreSQL currently also contains historical/fragment rows.
    """

    if not CANONICAL_MANIFEST.exists():
        raise FileNotFoundError(
            f"Canonical manifest not found:\n"
            f"  {CANONICAL_MANIFEST}"
        )

    data = load_json(CANONICAL_MANIFEST)

    records: list[dict[str, Any]]

    if isinstance(data, list):
        records = data

    elif isinstance(data, dict):
        # Support common manifest structures.
        if isinstance(data.get("regulations"), list):
            records = data["regulations"]
        elif isinstance(data.get("items"), list):
            records = data["items"]
        elif isinstance(data.get("records"), list):
            records = data["records"]
        else:
            raise ValueError(
                "Could not find regulation list in canonical manifest."
            )
    else:
        raise ValueError(
            "Unexpected canonical manifest format."
        )

    result: dict[str, dict[str, Any]] = {}

    for record in records:
        number = (
            record.get("number")
            or record.get("regulation_number")
        )

        if not number:
            continue

        number = normalize_regulation_number(str(number))

        result[number] = record

        # Also allow base-number lookup.
        base = regulation_base(number)

        if base not in result:
            result[base] = record

    return result


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------

def extract_references(
    text: str,
) -> list[dict[str, Any]]:
    """
    Extract only regulation references appearing in regulatory context.
    """

    references: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for match in REGULATION_CONTEXT_RE.finditer(text):

        raw = match.group("number")

        if not raw:
            continue

        number = normalize_regulation_number(raw)

        if is_probable_date(
            text,
            match.start("number"),
            match.end("number"),
        ):
            continue

        key = (number, match.start())

        if key in seen:
            continue

        seen.add(key)

        context_start = max(0, match.start() - 100)
        context_end = min(len(text), match.end() + 150)

        context = text[context_start:context_end]
        context = re.sub(r"\s+", " ", context).strip()

        references.append(
            {
                "number": number,
                "base_number": regulation_base(number),
                "position": match.start(),
                "context": context,
            }
        )

    return references


# ---------------------------------------------------------------------------
# Subject extraction
# ---------------------------------------------------------------------------

def extract_subject(text: str) -> str:
    """
    Extract the subject line from the translated document.
    """

    lines = first_lines(text, 60)

    for line in lines:

        if re.search(
            r"\bsubject\s*[:\-]",
            line,
            re.IGNORECASE,
        ):
            return line

    return ""


def extract_subject_references(
    subject: str,
) -> list[str]:
    if not subject:
        return []

    return [
        ref["number"]
        for ref in extract_references(subject)
    ]


# ---------------------------------------------------------------------------
# Procedural reference classification
# ---------------------------------------------------------------------------

def is_procedural_19v_context(
    reference: dict[str, Any],
) -> bool:

    number = reference["number"]

    if regulation_base(number) != "1.9":
        return False

    # 1.9 without subsection is not automatically procedural.
    if "(v)" not in number.lower():
        return False

    context = reference["context"].lower()

    procedural_phrases = [
        "in accordance with regulation",
        "provision regarding the issuance of orders",
        "issuance of orders by the government",
        "government has issued guidance",
        "according to regulation",
        "in accordance with the provision",
    ]

    return any(
        phrase in context
        for phrase in procedural_phrases
    )


# ---------------------------------------------------------------------------
# Document association
# ---------------------------------------------------------------------------

def associate_document(
    page: int,
    translated_text: str,
    canonical: dict[str, dict[str, Any]],
) -> dict[str, Any]:

    analysis_text = clean_text(translated_text)

    subject = extract_subject(analysis_text)

    all_refs = extract_references(analysis_text)

    # -----------------------------------------------------------------------
    # Deduplicate references while preserving order.
    # -----------------------------------------------------------------------

    unique_refs: list[dict[str, Any]] = []
    seen_numbers: set[str] = set()

    for ref in all_refs:

        number = ref["number"]

        if number in seen_numbers:
            continue

        seen_numbers.add(number)
        unique_refs.append(ref)

    # -----------------------------------------------------------------------
    # Subject references
    # -----------------------------------------------------------------------

    subject_refs = extract_subject_references(subject)

    subject_refs = list(dict.fromkeys(subject_refs))

    # -----------------------------------------------------------------------
    # Resolve against canonical manifest.
    # -----------------------------------------------------------------------

    resolved: dict[str, dict[str, Any]] = {}

    for ref in unique_refs:

        number = ref["number"]
        base = ref["base_number"]

        record = canonical.get(number)

        if record is None:
            record = canonical.get(base)

        if record is not None:
            resolved[number] = {
                "reference": ref,
                "canonical_record": record,
            }

    # -----------------------------------------------------------------------
    # Primary candidates
    # -----------------------------------------------------------------------

    primary: list[str] = []
    secondary: list[str] = []
    procedural: list[str] = []
    historical: list[str] = []

    # First: subject references.
    for number in subject_refs:

        if number not in resolved:
            continue

        if number.lower().startswith("1.9(v".lower()):
            # Subject explicitly names 1.9(v), therefore it is PRIMARY.
            primary.append(number)
        else:
            primary.append(number)

    # Second: body references.
    for number, item in resolved.items():

        ref = item["reference"]

        if number in primary:
            continue

        if is_procedural_19v_context(ref):
            procedural.append(number)
            continue

        context = ref["context"].lower()

        # Historical references usually occur alongside dates/orders.
        historical_phrases = [
            "previous order",
            "earlier order",
            "government order no.",
            "clarification order",
            "amendment document",
            "dated",
            "reference:",
            "reference :-",
        ]

        # Do not automatically classify every reference as historical
        # merely because it appears in a reference list.
        #
        # A regulation appearing in substantive sentences remains secondary.
        if any(
            phrase in context
            for phrase in historical_phrases
        ):
            secondary.append(number)
        else:
            primary.append(number)

    # -----------------------------------------------------------------------
    # De-duplicate and establish deterministic order.
    # -----------------------------------------------------------------------

    def unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    primary = unique(primary)
    secondary = unique(secondary)
    procedural = unique(procedural)
    historical = unique(historical)

    # Anything procedural should not also be primary.
    primary = [
        x for x in primary
        if x not in procedural
    ]

    # Anything primary should not also be secondary.
    secondary = [
        x for x in secondary
        if x not in primary
    ]

    # -----------------------------------------------------------------------
    # Standalone decision.
    # -----------------------------------------------------------------------

    standalone = len(primary) == 0

    if standalone and secondary:
        standalone = False

    # If only procedural 1.9(v) exists and the subject does not explicitly
    # discuss it, keep the document standalone rather than falsely attaching
    # it to 1.9(v).
    if (
        not primary
        and procedural
        and not subject_refs
    ):
        standalone = True

    # -----------------------------------------------------------------------
    # Confidence.
    # -----------------------------------------------------------------------

    if subject_refs:
        confidence = "high"

    elif len(primary) == 1:
        confidence = "high"

    elif len(primary) > 1:
        confidence = "medium"

    elif secondary:
        confidence = "low"

    else:
        confidence = "none"

    # -----------------------------------------------------------------------
    # Evidence.
    # -----------------------------------------------------------------------

    evidence: list[str] = []

    if subject:
        evidence.append(
            f"Subject: {subject}"
        )

    if primary:
        evidence.append(
            "Primary regulation(s) identified from explicit "
            "subject/substantive regulatory references."
        )

    if procedural:
        evidence.append(
            "Regulation 1.9(v) classified as procedural because "
            "the surrounding text describes Government clarification/order "
            "authority rather than the substantive subject."
        )

    if not primary and not secondary:
        evidence.append(
            "No reliable canonical UDCPR regulation association found; "
            "document should remain standalone."
        )

    # -----------------------------------------------------------------------
    # Build final report record.
    # -----------------------------------------------------------------------

    canonical_matches = []

    for number in unique(
        primary
        + secondary
        + procedural
        + historical
    ):
        item = resolved.get(number)

        if not item:
            continue

        record = item["canonical_record"]

        canonical_matches.append(
            {
                "reference_number": number,
                "canonical_number": (
                    record.get("number")
                    or record.get("regulation_number")
                ),
                "canonical_title": (
                    record.get("title")
                    or record.get("regulation_title")
                    or ""
                ),
                "canonical_key": (
                    record.get("canonical_key")
                    or record.get("key")
                    or ""
                ),
                "association_type": (
                    "primary"
                    if number in primary
                    else
                    "secondary"
                    if number in secondary
                    else
                    "procedural"
                    if number in procedural
                    else
                    "historical_reference"
                ),
            }
        )

    return {
        "pdf_page": page,
        "subject": subject,
        "primary_regulations": primary,
        "secondary_regulations": secondary,
        "procedural_regulations": procedural,
        "historical_references": historical,
        "standalone": standalone,
        "confidence": confidence,
        "all_detected_regulation_references": [
            {
                "number": ref["number"],
                "base_number": ref["base_number"],
                "context": ref["context"],
            }
            for ref in unique_refs
        ],
        "canonical_matches": canonical_matches,
        "evidence": evidence,
        "translated_preview": first_lines(
            translated_text,
            30,
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:

    print("=" * 100)
    print("UDCPR REGIONAL DOCUMENT ASSOCIATION")
    print("=" * 100)

    print(f"Project root       : {PROJECT_ROOT}")
    print(f"Translation dir    : {TRANSLATION_DIR}")
    print(f"Canonical manifest  : {CANONICAL_MANIFEST}")
    print()

    if not TRANSLATION_DIR.exists():
        print(
            f"ERROR: Translation directory does not exist:\n"
            f"  {TRANSLATION_DIR}"
        )
        return 1

    canonical = load_canonical_manifest()

    # Base + exact keys exist in this dictionary, so number of unique
    # underlying canonical records is calculated separately.
    canonical_unique_keys = set()

    for record in canonical.values():

        key = (
            record.get("canonical_key")
            or record.get("key")
            or record.get("id")
            or json.dumps(
                record,
                sort_keys=True,
            )
        )

        canonical_unique_keys.add(str(key))

    print(
        f"Canonical manifest records: "
        f"{len(canonical_unique_keys)}"
    )

    files = []

    for path in sorted(
        TRANSLATION_DIR.glob("page_*.json")
    ):
        match = re.fullmatch(
            r"page_(\d+)\.json",
            path.name,
        )

        if not match:
            continue

        page = int(match.group(1))

        if not 441 <= page <= 511:
            continue

        files.append((page, path))

    print(
        f"Regional translation files found: {len(files)}"
    )

    expected_pages = set(range(441, 512))
    found_pages = {page for page, _ in files}

    missing_pages = sorted(
        expected_pages - found_pages
    )

    if missing_pages:
        print()
        print(
            "WARNING: Missing translation pages:"
        )
        print(
            "  "
            + ", ".join(
                map(str, missing_pages)
            )
        )

    results = []

    for index, (page, path) in enumerate(
        files,
        start=1,
    ):

        try:
            data = load_json(path)

            translated_text = data.get(
                "translated_english_text",
                "",
            )

            if not translated_text:
                translated_text = data.get(
                    "translation",
                    "",
                )

            if not translated_text:
                translated_text = data.get(
                    "translated_text",
                    "",
                )

            result = associate_document(
                page=page,
                translated_text=translated_text,
                canonical=canonical,
            )

            result["translation_file"] = str(path)

            results.append(result)

            print(
                f"[{index:02}/{len(files):02}] "
                f"PAGE {page}: "
                f"primary={result['primary_regulations']} "
                f"procedural={result['procedural_regulations']} "
                f"standalone={result['standalone']} "
                f"confidence={result['confidence']}"
            )

        except Exception as exc:

            print(
                f"[{index:02}/{len(files):02}] "
                f"PAGE {page}: ERROR: {exc}"
            )

            results.append(
                {
                    "pdf_page": page,
                    "translation_file": str(path),
                    "error": str(exc),
                    "standalone": True,
                    "confidence": "error",
                }
            )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------

    linked = [
        x for x in results
        if not x.get("standalone")
        and "error" not in x
    ]

    standalone = [
        x for x in results
        if x.get("standalone")
        and "error" not in x
    ]

    errors = [
        x for x in results
        if "error" in x
    ]

    multiple = [
        x for x in linked
        if len(x.get("primary_regulations", [])) > 1
    ]

    summary = {
        "translation_files_found": len(files),
        "expected_pages": 71,
        "processed": len(results),
        "missing_pages": missing_pages,
        "linked": len(linked),
        "multiple_primary_associations": len(multiple),
        "standalone": len(standalone),
        "errors": len(errors),
    }

    report = {
        "schema": "udcpr.regional.association.v1",
        "read_only": True,
        "canonical_manifest": str(
            CANONICAL_MANIFEST
        ),
        "translation_directory": str(
            TRANSLATION_DIR
        ),
        "summary": summary,
        "documents": results,
    }

    OUTPUT_JSON.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -----------------------------------------------------------------------
    # Human-readable report
    # -----------------------------------------------------------------------

    with OUTPUT_TXT.open(
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "UDCPR REGIONAL DOCUMENT ASSOCIATION REPORT\n"
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

        f.write("\n\n")

        for result in results:

            f.write(
                "\n"
                + "=" * 100
                + "\n"
            )

            f.write(
                f"PAGE {result.get('pdf_page')}\n"
            )

            f.write(
                "=" * 100
                + "\n"
            )

            if "error" in result:
                f.write(
                    f"ERROR: {result['error']}\n"
                )
                continue

            f.write(
                f"Subject: "
                f"{result.get('subject', '')}\n"
            )

            f.write(
                f"Primary: "
                f"{result.get('primary_regulations', [])}\n"
            )

            f.write(
                f"Secondary: "
                f"{result.get('secondary_regulations', [])}\n"
            )

            f.write(
                f"Procedural: "
                f"{result.get('procedural_regulations', [])}\n"
            )

            f.write(
                f"Historical: "
                f"{result.get('historical_references', [])}\n"
            )

            f.write(
                f"Standalone: "
                f"{result.get('standalone')}\n"
            )

            f.write(
                f"Confidence: "
                f"{result.get('confidence')}\n"
            )

            f.write("\nCanonical matches:\n")

            for match in result.get(
                "canonical_matches",
                [],
            ):
                f.write(
                    "  - "
                    f"{match.get('reference_number')} "
                    f"=> "
                    f"{match.get('canonical_number')} "
                    f"| "
                    f"{match.get('canonical_title')} "
                    f"| "
                    f"{match.get('association_type')}\n"
                )

            f.write("\nEvidence:\n")

            for evidence in result.get(
                "evidence",
                [],
            ):
                f.write(
                    f"  - {evidence}\n"
                )

            f.write(
                "\nTranslated preview:\n"
            )

            for line in result.get(
                "translated_preview",
                [],
            ):
                f.write(
                    f"  {line}\n"
                )

    # -----------------------------------------------------------------------
    # Console summary
    # -----------------------------------------------------------------------

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)

    print(
        f"Translation files : {summary['translation_files_found']}"
    )
    print(
        f"Processed         : {summary['processed']}"
    )
    print(
        f"Missing pages     : {summary['missing_pages']}"
    )
    print(
        f"Linked            : {summary['linked']}"
    )
    print(
        f"Multiple primary  : {summary['multiple_primary_associations']}"
    )
    print(
        f"Standalone        : {summary['standalone']}"
    )
    print(
        f"Errors            : {summary['errors']}"
    )

    print()
    print(
        f"JSON report       : {OUTPUT_JSON}"
    )
    print(
        f"Text report       : {OUTPUT_TXT}"
    )

    print()
    print(
        "IMPORTANT: No PostgreSQL or Chroma changes were made."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
