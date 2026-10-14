#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import requests


# ============================================================
# DEFAULT CONFIGURATION
# ============================================================

DEFAULT_PDF = Path(
    "data/regulations/UDCPR.pdf"
)

DEFAULT_START_PDF_PAGE = 441

DEFAULT_OUTPUT_JSON = Path(
    "/tmp/udcpr_regional_explanations.json"
)

DEFAULT_REVIEW_FILE = Path(
    "/tmp/udcpr_regional_explanations_review.txt"
)

DEFAULT_RAW_FILE = Path(
    "/tmp/udcpr_regional_pages_raw.txt"
)

DEFAULT_OLLAMA_HOST = "http://localhost:11434"

DEFAULT_OLLAMA_MODEL = "llama3.2"

DEFAULT_TIMEOUT = 600


# ============================================================
# REGIONAL LANGUAGE DETECTION
# ============================================================

DEVANAGARI_RE = re.compile(
    r"[\u0900-\u097F]"
)

LATIN_RE = re.compile(
    r"[A-Za-z]"
)

NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)*"
)


def contains_devanagari(text: str) -> bool:
    return bool(
        DEVANAGARI_RE.search(text or "")
    )


def devanagari_count(text: str) -> int:
    return len(
        DEVANAGARI_RE.findall(text or "")
    )


def latin_count(text: str) -> int:
    return len(
        LATIN_RE.findall(text or "")
    )


def classify_line(text: str) -> str:
    """
    Classify one extracted line.

    Returns:

        MARATHI
        ENGLISH
        MIXED
        OTHER
    """

    text = text.strip()

    if not text:
        return "OTHER"

    d = devanagari_count(text)
    e = latin_count(text)

    if d > 0 and e > 0:
        return "MIXED"

    if d > 0:
        return "MARATHI"

    if e > 0:
        return "ENGLISH"

    return "OTHER"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_line(text: str) -> str:
    """
    Normalize PDF extraction artifacts without translating.
    """

    text = text.replace(
        "\u00a0",
        " "
    )

    text = text.replace(
        "\u200b",
        ""
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


def normalize_page_text(text: str) -> str:

    lines = []

    for raw in text.splitlines():

        line = normalize_line(
            raw
        )

        if line:
            lines.append(line)

    return "\n".join(lines)


# ============================================================
# ENGLISH / MARATHI SEGMENTATION
# ============================================================

def split_mixed_text(text: str) -> list[dict[str, str]]:
    """
    Split text into approximate language segments.

    This deliberately works conservatively.

    We do NOT attempt to translate English text.

    Lines containing both Devanagari and English are classified
    as MIXED and sent to the translator with an explicit
    instruction to preserve English verbatim.
    """

    segments = []

    current_type = None
    current_lines = []

    for raw_line in text.splitlines():

        line = normalize_line(
            raw_line
        )

        if not line:
            continue

        line_type = classify_line(
            line
        )

        if current_type is None:

            current_type = line_type
            current_lines = [line]
            continue

        if line_type == current_type:

            current_lines.append(
                line
            )

        else:

            segments.append(
                {
                    "type": current_type,
                    "text": "\n".join(
                        current_lines
                    ),
                }
            )

            current_type = line_type
            current_lines = [line]

    if current_lines:

        segments.append(
            {
                "type": current_type,
                "text": "\n".join(
                    current_lines
                ),
            }
        )

    return segments


# ============================================================
# SECTION DETECTION
# ============================================================

SECTION_NUMBER_RE = re.compile(
    r"^\s*"
    r"(?P<number>"
    r"(?:\d+\.)+"
    r"(?:\([a-zA-Z0-9]+\))?"
    r")"
    r"\s+"
    r"(?P<title>.+?)"
    r"\s*$"
)


def looks_like_section_heading(
    line: str,
) -> bool:
    """
    Detect likely numbered explanatory sections.

    Examples:

        3.4
        4.2.1
        5.3(a)
        2.2.5(b) ...

    We intentionally do not assume every heading is a
    regulation. These will be reviewed before ingestion.
    """

    line = normalize_line(
        line
    )

    if not line:
        return False

    match = SECTION_NUMBER_RE.match(
        line
    )

    if match:
        return True

    return False


def extract_heading(
    line: str,
) -> tuple[str | None, str | None]:

    line = normalize_line(
        line
    )

    match = SECTION_NUMBER_RE.match(
        line
    )

    if not match:
        return None, None

    return (
        match.group("number"),
        match.group("title"),
    )


# ============================================================
# PAGE EXTRACTION
# ============================================================

@dataclass
class PDFPage:
    pdf_page: int
    text: str


def extract_pdf_pages(
    pdf_path: Path,
    start_page: int,
) -> list[PDFPage]:

    if not pdf_path.exists():

        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    document = fitz.open(
        pdf_path
    )

    try:

        total_pages = document.page_count

        if start_page < 1:

            raise ValueError(
                "start_page must be >= 1"
            )

        if start_page > total_pages:

            raise ValueError(
                f"start_page={start_page} "
                f"but PDF contains only "
                f"{total_pages} pages."
            )

        pages = []

        for page_index in range(
            start_page - 1,
            total_pages,
        ):

            page = document[
                page_index
            ]

            raw_text = page.get_text(
                "text"
            )

            text = normalize_page_text(
                raw_text
            )

            pages.append(
                PDFPage(
                    pdf_page=page_index + 1,
                    text=text,
                )
            )

        return pages

    finally:

        document.close()


# ============================================================
# SECTION BUILDING
# ============================================================

def build_sections(
    pages: list[PDFPage],
) -> list[dict[str, Any]]:
    """
    Build candidate standalone explanatory sections.

    A new section starts when a numbered heading is found.

    Pages before the first heading are retained as an
    UNNUMBERED section.

    This is analysis output only.
    """

    sections = []

    current = None

    for page in pages:

        lines = page.text.splitlines()

        for line in lines:

            line = normalize_line(
                line
            )

            if not line:
                continue

            number, title = extract_heading(
                line
            )

            if number is not None:

                if current is not None:

                    sections.append(
                        current
                    )

                section_key = (
                    f"{number}|"
                    f"{title.lower()}"
                )

                current = {
                    "section_id": None,
                    "number": number,
                    "title": title,
                    "type": (
                        "REGIONAL_EXPLANATION"
                    ),
                    "source_pdf_pages": [],
                    "original_text": "",
                    "language_analysis": {},
                    "translation": None,
                    "canonical_key_candidate":
                        section_key,
                }

            if current is None:

                current = {
                    "section_id": None,
                    "number": None,
                    "title": (
                        "Unnumbered Regional "
                        "Explanation"
                    ),
                    "type": (
                        "REGIONAL_EXPLANATION"
                    ),
                    "source_pdf_pages": [],
                    "original_text": "",
                    "language_analysis": {},
                    "translation": None,
                    "canonical_key_candidate":
                        None,
                }

            if page.pdf_page not in (
                current["source_pdf_pages"]
            ):

                current[
                    "source_pdf_pages"
                ].append(
                    page.pdf_page
                )

            current[
                "original_text"
            ] += line + "\n"

    if current is not None:

        sections.append(
            current
        )

    # --------------------------------------------------------
    # Remove empty sections.
    # --------------------------------------------------------

    cleaned = []

    for section in sections:

        text = section[
            "original_text"
        ].strip()

        if not text:
            continue

        section[
            "original_text"
        ] = text

        cleaned.append(
            section
        )

    return cleaned


# ============================================================
# LANGUAGE ANALYSIS
# ============================================================

def analyze_languages(
    text: str,
) -> dict[str, Any]:

    segments = split_mixed_text(
        text
    )

    counts = {
        "MARATHI": 0,
        "ENGLISH": 0,
        "MIXED": 0,
        "OTHER": 0,
    }

    for segment in segments:

        segment_type = segment[
            "type"
        ]

        if segment_type in counts:

            counts[
                segment_type
            ] += 1

    devanagari = devanagari_count(
        text
    )

    latin = latin_count(
        text
    )

    if devanagari > 0 and latin > 0:

        dominant = "MIXED"

    elif devanagari > 0:

        dominant = "MARATHI"

    elif latin > 0:

        dominant = "ENGLISH"

    else:

        dominant = "OTHER"

    return {
        "dominant_language": dominant,
        "devanagari_characters": devanagari,
        "latin_characters": latin,
        "segments": segments,
        "segment_counts": counts,
    }


# ============================================================
# OLLAMA TRANSLATION
# ============================================================

TRANSLATION_SYSTEM_PROMPT = """
You are translating extracted Maharashtra UDCPR PDF
content from Marathi into English.

STRICT RULES:

1. Translate Marathi text into accurate English.
2. DO NOT translate text that is already English.
3. Preserve existing English wording exactly.
4. Preserve regulation numbers exactly.
5. Preserve numerical values exactly.
6. Preserve units exactly.
7. Preserve table references exactly.
8. Preserve section references exactly.
9. Preserve names of authorities exactly when already in English.
10. Do not add explanations.
11. Do not summarize.
12. Do not invent missing context.
13. Do not remove text.
14. Keep the original order.
15. The result must be suitable for regulatory/document use.

If a line contains both Marathi and English:
- translate only the Marathi portion;
- leave the English portion unchanged.

Return ONLY the translated English text.
"""


def ollama_translate(
    text: str,
    host: str,
    model: str,
    timeout: int,
) -> str:

    if not text.strip():
        return ""

    url = (
        host.rstrip("/")
        + "/api/chat"
    )

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content":
                    TRANSLATION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        "options": {
            "temperature": 0,
        },
    }

    response = requests.post(
        url,
        json=payload,
        timeout=timeout,
    )

    response.raise_for_status()

    data = response.json()

    message = data.get(
        "message"
    )

    if not isinstance(
        message,
        dict,
    ):

        raise RuntimeError(
            "Unexpected Ollama response."
        )

    result = message.get(
        "content"
    )

    if not isinstance(
        result,
        str,
    ):

        raise RuntimeError(
            "Ollama response did not "
            "contain message.content."
        )

    return result.strip()


# ============================================================
# ENGLISH PRESERVATION CHECK
# ============================================================

def english_fragments(
    text: str,
) -> list[str]:

    fragments = []

    for segment in split_mixed_text(
        text
    ):

        if segment["type"] == "ENGLISH":

            fragments.append(
                segment["text"]
            )

    return fragments


def verify_english_preserved(
    original: str,
    translated: str,
) -> list[str]:
    """
    Best-effort audit.

    We do NOT fail the translation automatically because
    punctuation/line wrapping may change.

    We report English fragments that disappeared.
    """

    missing = []

    for fragment in english_fragments(
        original
    ):

        compact = re.sub(
            r"\s+",
            " ",
            fragment,
        ).strip()

        if len(compact) < 5:
            continue

        translated_compact = re.sub(
            r"\s+",
            " ",
            translated,
        )

        if compact not in translated_compact:

            missing.append(
                fragment
            )

    return missing


# ============================================================
# DETERMINISTIC ID
# ============================================================

def make_section_id(
    section: dict[str, Any],
) -> str:

    first_page = (
        section[
            "source_pdf_pages"
        ][0]
    )

    number = (
        section.get("number")
        or "UNNUMBERED"
    )

    title = (
        section.get("title")
        or ""
    )

    raw = (
        f"UDCPR-REGIONAL|"
        f"{first_page}|"
        f"{number}|"
        f"{title}"
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    return (
        "UDCPR-REGIONAL-"
        + digest
    )


# ============================================================
# REVIEW FILE
# ============================================================

def write_review(
    path: Path,
    sections: list[dict[str, Any]],
) -> None:

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "=" * 120
            + "\n"
        )

        f.write(
            "UDCPR REGIONAL-LANGUAGE "
            "EXPLANATION REVIEW\n"
        )

        f.write(
            "=" * 120
            + "\n\n"
        )

        f.write(
            "IMPORTANT:\n"
        )

        f.write(
            "These are candidate standalone "
            "explanatory regulations.\n"
        )

        f.write(
            "They have NOT been inserted into "
            "PostgreSQL or Chroma.\n\n"
        )

        for index, section in enumerate(
            sections,
            start=1,
        ):

            f.write(
                "\n"
                + "=" * 120
                + "\n"
            )

            f.write(
                f"CANDIDATE {index}\n"
            )

            f.write(
                "=" * 120
                + "\n"
            )

            f.write(
                f"ID          : "
                f"{section['section_id']}\n"
            )

            f.write(
                f"Number      : "
                f"{section.get('number')}\n"
            )

            f.write(
                f"Title       : "
                f"{section.get('title')}\n"
            )

            f.write(
                f"PDF pages   : "
                f"{section['source_pdf_pages']}\n"
            )

            analysis = section[
                "language_analysis"
            ]

            f.write(
                f"Language    : "
                f"{analysis['dominant_language']}\n"
            )

            f.write(
                "\n"
                "---------------- ORIGINAL PDF TEXT "
                "----------------\n"
            )

            f.write(
                section[
                    "original_text"
                ]
            )

            f.write(
                "\n\n"
                "---------------- ENGLISH TRANSLATION "
                "----------------\n"
            )

            translation = (
                section.get(
                    "translation"
                )
                or ""
            )

            f.write(
                translation
            )

            f.write(
                "\n\n"
                "---------------- ENGLISH PRESERVATION "
                "CHECK ----------------\n"
            )

            missing = section.get(
                "english_preservation_issues",
                [],
            )

            if missing:

                f.write(
                    "WARNING: English fragments "
                    "possibly changed:\n"
                )

                for item in missing:

                    f.write(
                        "  - "
                        + item
                        + "\n"
                    )

            else:

                f.write(
                    "PASS: No obvious lost "
                    "English fragments detected.\n"
                )

            f.write("\n")


# ============================================================
# RAW PDF EXTRACTION
# ============================================================

def write_raw_pages(
    path: Path,
    pages: list[PDFPage],
) -> None:

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "=" * 120
            + "\n"
        )

        f.write(
            "UDCPR RAW REGIONAL PDF PAGE EXTRACTION\n"
        )

        f.write(
            "=" * 120
            + "\n"
        )

        for page in pages:

            f.write(
                "\n"
                + "=" * 120
                + "\n"
            )

            f.write(
                f"PDF PAGE {page.pdf_page}\n"
            )

            f.write(
                "=" * 120
                + "\n\n"
            )

            f.write(
                page.text
            )

            f.write(
                "\n"
            )


# ============================================================
# JSON OUTPUT
# ============================================================

def write_json(
    path: Path,
    pdf_path: Path,
    start_page: int,
    pages: list[PDFPage],
    sections: list[dict[str, Any]],
    ollama_host: str,
    ollama_model: str,
) -> None:

    payload = {
        "schema": (
            "udcpr_regional_explanations_v1"
        ),
        "status": (
            "ANALYSIS_ONLY_NOT_INGESTED"
        ),
        "source": {
            "pdf": str(pdf_path),
            "pdf_start_page": start_page,
            "pdf_end_page": (
                pages[-1].pdf_page
                if pages
                else None
            ),
            "physical_pdf_pages": len(
                pages
            ),
        },
        "translation": {
            "provider": "ollama",
            "host": ollama_host,
            "model": ollama_model,
            "policy": {
                "marathi": (
                    "translate_to_english"
                ),
                "english": (
                    "preserve_verbatim"
                ),
                "mixed": (
                    "translate_marathi_only"
                ),
            },
        },
        "candidate_count": len(
            sections
        ),
        "candidates": sections,
    }

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Analyze UDCPR regional-language "
            "pages as standalone explanations."
        )
    )

    parser.add_argument(
        "--pdf",
        default=str(
            DEFAULT_PDF
        ),
    )

    parser.add_argument(
        "--start-page",
        type=int,
        default=DEFAULT_START_PDF_PAGE,
        help=(
            "Physical PDF page number, "
            "not printed page number."
        ),
    )

    parser.add_argument(
        "--output",
        default=str(
            DEFAULT_OUTPUT_JSON
        ),
    )

    parser.add_argument(
        "--review",
        default=str(
            DEFAULT_REVIEW_FILE
        ),
    )

    parser.add_argument(
        "--raw",
        default=str(
            DEFAULT_RAW_FILE
        ),
    )

    parser.add_argument(
        "--ollama-host",
        default=DEFAULT_OLLAMA_HOST,
    )

    parser.add_argument(
        "--ollama-model",
        default=DEFAULT_OLLAMA_MODEL,
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
    )

    parser.add_argument(
        "--no-translate",
        action="store_true",
        help=(
            "Extract/analyze only. "
            "Do not call Ollama."
        ),
    )

    args = parser.parse_args()

    pdf_path = Path(
        args.pdf
    )

    output_path = Path(
        args.output
    )

    review_path = Path(
        args.review
    )

    raw_path = Path(
        args.raw
    )

    print(
        "=" * 110
    )

    print(
        "UDCPR REGIONAL-LANGUAGE "
        "EXPLANATION ANALYSIS"
    )

    print(
        "=" * 110
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This script does NOT modify PostgreSQL."
    )

    print(
        "This script does NOT modify Chroma."
    )

    print(
        "This script does NOT modify the "
        "329 canonical regulations."
    )

    print()
    print(
        f"PDF          : {pdf_path}"
    )

    print(
        f"Physical start page : "
        f"{args.start_page}"
    )

    print(
        f"Ollama host  : {args.ollama_host}"
    )

    print(
        f"Ollama model : {args.ollama_model}"
    )

    # --------------------------------------------------------
    # Extract PDF
    # --------------------------------------------------------

    print()
    print(
        "=" * 110
    )

    print(
        "EXTRACTING PDF PAGES"
    )

    print(
        "=" * 110
    )

    pages = extract_pdf_pages(
        pdf_path,
        args.start_page,
    )

    print(
        f"PDF pages extracted: "
        f"{len(pages)}"
    )

    print(
        f"First PDF page: "
        f"{pages[0].pdf_page}"
    )

    print(
        f"Last PDF page: "
        f"{pages[-1].pdf_page}"
    )

    # --------------------------------------------------------
    # Raw output
    # --------------------------------------------------------

    write_raw_pages(
        raw_path,
        pages,
    )

    print(
        f"Raw extraction: "
        f"{raw_path}"
    )

    # --------------------------------------------------------
    # Build sections
    # --------------------------------------------------------

    print()
    print(
        "=" * 110
    )

    print(
        "BUILDING CANDIDATE EXPLANATIONS"
    )

    print(
        "=" * 110
    )

    sections = build_sections(
        pages
    )

    print(
        f"Candidate sections: "
        f"{len(sections)}"
    )

    # --------------------------------------------------------
    # Language analysis + translation
    # --------------------------------------------------------

    print()
    print(
        "=" * 110
    )

    print(
        "LANGUAGE ANALYSIS / TRANSLATION"
    )

    print(
        "=" * 110
    )

    for index, section in enumerate(
        sections,
        start=1,
    ):

        section[
            "section_id"
        ] = make_section_id(
            section
        )

        analysis = analyze_languages(
            section[
                "original_text"
            ]
        )

        section[
            "language_analysis"
        ] = analysis

        dominant = (
            analysis[
                "dominant_language"
            ]
        )

        print()
        print(
            f"[{index}/{len(sections)}]"
        )

        print(
            "ID       : "
            + section[
                "section_id"
            ]
        )

        print(
            "Number   : "
            + str(
                section.get(
                    "number"
                )
            )
        )

        print(
            "Title    : "
            + str(
                section.get(
                    "title"
                )
            )
        )

        print(
            "PDF pages: "
            + str(
                section[
                    "source_pdf_pages"
                ]
            )
        )

        print(
            "Language : "
            + dominant
        )

        if args.no_translate:

            section[
                "translation"
            ] = None

            section[
                "translation_status"
            ] = "NOT_REQUESTED"

            section[
                "english_preservation_issues"
            ] = []

            continue

        # ----------------------------------------------------
        # Translate ONLY when regional text exists.
        # ----------------------------------------------------

        if not contains_devanagari(
            section[
                "original_text"
            ]
        ):

            # Entire section appears to be English.
            # Preserve it exactly.
            section[
                "translation"
            ] = section[
                "original_text"
            ]

            section[
                "translation_status"
            ] = (
                "ENGLISH_PRESERVED"
            )

            section[
                "english_preservation_issues"
            ] = []

            print(
                "Action   : English preserved"
            )

            continue

        print(
            "Action   : Translating regional "
            "language with Ollama..."
        )

        try:

            translated = ollama_translate(
                section[
                    "original_text"
                ],
                args.ollama_host,
                args.ollama_model,
                args.timeout,
            )

            section[
                "translation"
            ] = translated

            section[
                "translation_status"
            ] = "TRANSLATED"

            section[
                "english_preservation_issues"
            ] = verify_english_preserved(
                section[
                    "original_text"
                ],
                translated,
            )

            if section[
                "english_preservation_issues"
            ]:

                print(
                    "WARNING: possible English "
                    "preservation issue"
                )

            else:

                print(
                    "Translation check: PASS"
                )

        except Exception as exc:

            section[
                "translation"
            ] = None

            section[
                "translation_status"
            ] = "TRANSLATION_FAILED"

            section[
                "translation_error"
            ] = str(
                exc
            )

            section[
                "english_preservation_issues"
            ] = []

            print(
                "TRANSLATION ERROR:"
            )

            print(
                "  "
                + str(exc)
            )

            print(
                "Continuing analysis..."
            )

        # Small delay to avoid hammering Ollama.
        time.sleep(
            0.05
        )

    # --------------------------------------------------------
    # Write outputs
    # --------------------------------------------------------

    write_json(
        output_path,
        pdf_path,
        args.start_page,
        pages,
        sections,
        args.ollama_host,
        args.ollama_model,
    )

    write_review(
        review_path,
        sections,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    regional = 0
    english = 0
    mixed = 0
    failed = 0

    for section in sections:

        dominant = section[
            "language_analysis"
        ][
            "dominant_language"
        ]

        if dominant == "MARATHI":
            regional += 1

        elif dominant == "ENGLISH":
            english += 1

        elif dominant == "MIXED":
            mixed += 1

        if section.get(
            "translation_status"
        ) == "TRANSLATION_FAILED":

            failed += 1

    print()
    print(
        "=" * 110
    )

    print(
        "ANALYSIS COMPLETE"
    )

    print(
        "=" * 110
    )

    print(
        f"PDF pages analyzed : "
        f"{len(pages)}"
    )

    print(
        f"Candidate sections : "
        f"{len(sections)}"
    )

    print(
        f"Regional language  : "
        f"{regional}"
    )

    print(
        f"English            : "
        f"{english}"
    )

    print(
        f"Mixed              : "
        f"{mixed}"
    )

    print(
        f"Translation failed : "
        f"{failed}"
    )

    print()
    print(
        "OUTPUTS"
    )

    print(
        f"JSON   : {output_path}"
    )

    print(
        f"Review : {review_path}"
    )

    print(
        f"Raw    : {raw_path}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "No PostgreSQL changes were made."
    )

    print(
        "No Chroma changes were made."
    )

    print(
        "No canonical regulation was modified."
    )

    print()
    print(
        "Review the candidate sections before "
        "ingesting them."
    )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print(
            "\nInterrupted."
        )

        sys.exit(130)

    except Exception as exc:

        print()
        print(
            "=" * 110
        )

        print(
            "ANALYSIS FAILED"
        )

        print(
            "=" * 110
        )

        print(
            "ERROR:"
        )

        print(
            str(exc)
        )

        sys.exit(1)