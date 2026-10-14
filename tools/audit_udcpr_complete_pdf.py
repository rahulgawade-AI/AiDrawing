#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import fitz


PDF = Path(
    "/home/ubuntu/llmproject/ai-town-planning/"
    "data/regulations/UDCPR.pdf"
)

MANIFEST = Path(
    "data/regulations/udcpr_canonical_manifest.json"
)

OUTPUT = Path(
    "data/regulations/udcpr_complete_pdf_audit.json"
)


MAIN_PDF_START = 17
MAIN_PDF_END = 439

PRINTED_START = 1
PRINTED_END = 423


REGULATION_RE = re.compile(
    r"^\s*"
    r"(?P<number>"
    r"\d+(?:\.\d+)*"
    r"(?:\s*\([a-z]\))?"
    r")"
    r"(?:\s+|\s*$)"
    r"(?P<title>.+?)"
    r"\s*$",
    re.IGNORECASE,
)


CHAPTER_RE = re.compile(
    r"CHAPTER\s*[-–—]\s*(\d+)",
    re.IGNORECASE,
)


APPENDIX_RE = re.compile(
    r"APPENDIX\s*[-–—]?\s*([A-Z](?:-\d+)?)",
    re.IGNORECASE,
)


TABLE_RE = re.compile(
    r"\bTABLE\b",
    re.IGNORECASE,
)


def clean(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def footer_page(
    page: fitz.Page,
):
    """
    Read only the verified bottom-right footer.
    """

    width = page.rect.width
    height = page.rect.height

    candidates = []

    for block in page.get_text(
        "blocks",
        sort=True,
    ):

        x0, y0, x1, y1, text = block[:5]

        text = clean(text)

        if not text:
            continue

        if x0 < width * 0.80:
            continue

        if y0 < height * 0.90:
            continue

        if not re.fullmatch(
            r"\d{1,3}",
            text,
        ):
            continue

        value = int(text)

        if 1 <= value <= 999:

            candidates.append(
                (
                    y0,
                    x0,
                    value,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        reverse=True
    )

    return candidates[0][2]


def extract_page_text(
    page: fitz.Page,
):
    return page.get_text(
        "text",
        sort=True,
    )


def extract_blocks(
    page: fitz.Page,
):
    result = []

    for block in page.get_text(
        "blocks",
        sort=True,
    ):

        x0, y0, x1, y1, text = block[:5]

        text = clean(text)

        if text:
            result.append(
                {
                    "x0": round(x0, 2),
                    "y0": round(y0, 2),
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "text": text,
                }
            )

    return result


def detect_regulation_candidates(
    blocks,
):
    found = []

    for block in blocks:

        text = block["text"]

        m = REGULATION_RE.match(
            text
        )

        if not m:
            continue

        number = m.group(
            "number"
        )

        title = clean(
            m.group("title")
        )

        # Avoid treating ordinary numbered list
        # items such as "1. Name..." as regulations.
        if "." not in number:
            continue

        found.append(
            {
                "number": number,
                "title": title,
                "text": text,
                "y0": block["y0"],
                "y1": block["y1"],
            }
        )

    return found


def detect_chapters(
    text: str,
):
    return CHAPTER_RE.findall(
        text
    )


def detect_appendices(
    text: str,
):
    result = []

    for match in APPENDIX_RE.finditer(
        text
    ):
        result.append(
            match.group(1)
        )

    return result


def detect_tables(
    page: fitz.Page,
):
    """
    Structural table detection.

    This is deliberately conservative.

    We record pages containing:
      - TABLE text
      - multiple text blocks aligned into columns
      - actual PDF table structures when available
    """

    text = page.get_text(
        "text",
        sort=True,
    )

    has_table_word = bool(
        TABLE_RE.search(text)
    )

    tables = []

    try:

        pdf_tables = page.find_tables()

        for table in pdf_tables.tables:

            bbox = table.bbox

            tables.append(
                {
                    "bbox": [
                        round(x, 2)
                        for x in bbox
                    ],
                    "rows": (
                        len(table.rows)
                        if table.rows
                        else 0
                    ),
                    "cols": (
                        len(table.columns)
                        if table.columns
                        else 0
                    ),
                    "source": "pymupdf_find_tables",
                }
            )

    except Exception:
        pass

    return {
        "table_word": has_table_word,
        "detected_tables": tables,
    }


def normalize_number(
    number: str,
):
    return re.sub(
        r"\s+",
        "",
        number.lower(),
    )


def main():

    print("=" * 100)
    print("COMPLETE UDCPR PDF STRUCTURAL AUDIT")
    print("=" * 100)

    if not PDF.exists():
        raise FileNotFoundError(PDF)

    if not MANIFEST.exists():
        raise FileNotFoundError(MANIFEST)

    with MANIFEST.open(
        encoding="utf-8"
    ) as f:
        manifest = json.load(f)

    canonical = manifest[
        "regulations"
    ]

    canonical_by_number = defaultdict(
        list
    )

    for entry in canonical:

        canonical_by_number[
            normalize_number(
                entry["number"]
            )
        ].append(entry)

    doc = fitz.open(
        str(PDF)
    )

    try:

        print(
            "PDF pages:",
            len(doc),
        )

        print(
            "Canonical regulations:",
            len(canonical),
        )

        print()

        # ====================================================
        # Page-level audit
        # ====================================================

        page_records = []

        footer_missing = []
        footer_mismatch = []

        chapters = defaultdict(
            list
        )

        appendices = defaultdict(
            list
        )

        detected_numbers = defaultdict(
            list
        )

        table_pages = []

        empty_pages = []

        text_pages = []

        for pdf_no in range(
            1,
            len(doc) + 1,
        ):

            page = doc[
                pdf_no - 1
            ]

            text = extract_page_text(
                page
            )

            blocks = extract_blocks(
                page
            )

            printed = footer_page(
                page
            )

            page_type = "unknown"

            if pdf_no < MAIN_PDF_START:
                page_type = "front_matter"

            elif (
                MAIN_PDF_START
                <= pdf_no
                <= MAIN_PDF_END
            ):
                page_type = "main_udcpr"

            else:
                page_type = "post_udcpr"

            if (
                page_type == "main_udcpr"
                and printed is None
            ):
                footer_missing.append(
                    pdf_no
                )

            if (
                page_type == "main_udcpr"
                and printed is not None
            ):

                expected = (
                    pdf_no - 16
                )

                if printed != expected:

                    footer_mismatch.append(
                        {
                            "pdf_page": pdf_no,
                            "expected": expected,
                            "detected": printed,
                        }
                    )

            if not text.strip():
                empty_pages.append(
                    pdf_no
                )
            else:
                text_pages.append(
                    pdf_no
                )

            chapter_matches = detect_chapters(
                text
            )

            for chapter in chapter_matches:

                chapters[
                    chapter
                ].append(
                    pdf_no
                )

            appendix_matches = detect_appendices(
                text
            )

            for appendix in appendix_matches:

                appendices[
                    appendix
                ].append(
                    pdf_no
                )

            regulation_candidates = (
                detect_regulation_candidates(
                    blocks
                )
            )

            for candidate in regulation_candidates:

                key = normalize_number(
                    candidate["number"]
                )

                detected_numbers[
                    key
                ].append(
                    {
                        "pdf_page":
                            pdf_no,
                        "printed_page":
                            printed,
                        "title":
                            candidate[
                                "title"
                            ],
                    }
                )

            table_info = detect_tables(
                page
            )

            if (
                table_info["table_word"]
                or table_info[
                    "detected_tables"
                ]
            ):

                table_pages.append(
                    {
                        "pdf_page":
                            pdf_no,
                        "printed_page":
                            printed,
                        **table_info,
                    }
                )

            page_records.append(
                {
                    "pdf_page":
                        pdf_no,
                    "printed_page":
                        printed,
                    "page_type":
                        page_type,
                    "text_chars":
                        len(text),
                    "block_count":
                        len(blocks),
                    "regulation_candidate_count":
                        len(
                            regulation_candidates
                        ),
                    "chapter_count":
                        len(
                            chapter_matches
                        ),
                    "appendix_count":
                        len(
                            appendix_matches
                        ),
                    "has_table":
                        bool(
                            table_info[
                                "table_word"
                            ]
                            or table_info[
                                "detected_tables"
                            ]
                        ),
                }
            )

            if pdf_no % 25 == 0:

                print(
                    f"Scanned PDF page "
                    f"{pdf_no}/{len(doc)}"
                )

        # ====================================================
        # Canonical regulation checks
        # ====================================================

        missing_canonical = []
        detected_canonical = []

        for entry in canonical:

            number = normalize_number(
                entry["number"]
            )

            matches = detected_numbers.get(
                number,
                []
            )

            if not matches:

                missing_canonical.append(
                    {
                        "number":
                            entry["number"],
                        "title":
                            entry["title"],
                        "index_printed_page":
                            entry[
                                "printed_page_start"
                            ],
                        "index_pdf_page":
                            entry[
                                "pdf_page_start"
                            ],
                    }
                )

            else:

                detected_canonical.append(
                    {
                        "number":
                            entry["number"],
                        "title":
                            entry["title"],
                        "index_printed_page":
                            entry[
                                "printed_page_start"
                            ],
                        "index_pdf_page":
                            entry[
                                "pdf_page_start"
                            ],
                        "detected":
                            matches,
                    }
                )

        # ====================================================
        # Unknown regulation-like headings
        # ====================================================

        canonical_keys = set(
            canonical_by_number.keys()
        )

        unknown_candidates = []

        for number, matches in (
            detected_numbers.items()
        ):

            if number not in canonical_keys:

                unknown_candidates.append(
                    {
                        "number":
                            number,
                        "occurrences":
                            matches,
                    }
                )

        # ====================================================
        # Duplicate detection
        # ====================================================

        detected_duplicates = []

        for number, matches in (
            detected_numbers.items()
        ):

            if len(matches) > 1:

                detected_duplicates.append(
                    {
                        "number":
                            number,
                        "count":
                            len(matches),
                        "occurrences":
                            matches,
                    }
                )

        # ====================================================
        # Main-page pagination coverage
        # ====================================================

        expected_main_pdf = set(
            range(
                MAIN_PDF_START,
                MAIN_PDF_END + 1,
            )
        )

        scanned_main_pdf = set(
            x["pdf_page"]
            for x in page_records
            if x["page_type"]
            == "main_udcpr"
        )

        missing_main_pdf = sorted(
            expected_main_pdf
            - scanned_main_pdf
        )

        # ====================================================
        # Write audit
        # ====================================================

        audit = {
            "source": str(PDF),

            "pdf_pages":
                len(doc),

            "main_udcpr": {
                "pdf_start":
                    MAIN_PDF_START,
                "pdf_end":
                    MAIN_PDF_END,
                "printed_start":
                    PRINTED_START,
                "printed_end":
                    PRINTED_END,
            },

            "canonical": {
                "count":
                    len(canonical),
                "missing":
                    missing_canonical,
                "detected":
                    detected_canonical,
            },

            "pagination": {
                "expected_formula":
                    "pdf_page = printed_page + 16",
                "missing_footer_pages":
                    footer_missing,
                "footer_mismatches":
                    footer_mismatch,
                "missing_main_pdf_pages":
                    missing_main_pdf,
            },

            "chapters": {
                key: sorted(
                    value
                )
                for key, value
                in chapters.items()
            },

            "appendices": {
                key: sorted(
                    value
                )
                for key, value
                in appendices.items()
            },

            "tables": {
                "count":
                    len(table_pages),
                "pages":
                    table_pages,
            },

            "unknown_regulation_candidates":
                unknown_candidates,

            "detected_duplicates":
                detected_duplicates,

            "empty_pages":
                empty_pages,

            "page_records":
                page_records,
        }

        OUTPUT.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        OUTPUT.write_text(
            json.dumps(
                audit,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # ====================================================
        # Console summary
        # ====================================================

        print()
        print("=" * 100)
        print("AUDIT SUMMARY")
        print("=" * 100)

        print(
            "Total PDF pages       :",
            len(doc),
        )

        print(
            "Main UDCPR pages      :",
            len(scanned_main_pdf),
        )

        print(
            "Text pages             :",
            len(text_pages),
        )

        print(
            "Empty pages            :",
            len(empty_pages),
        )

        print(
            "Canonical regulations  :",
            len(canonical),
        )

        print(
            "Missing canonical      :",
            len(missing_canonical),
        )

        print(
            "Unknown candidates    :",
            len(unknown_candidates),
        )

        print(
            "Detected duplicates    :",
            len(detected_duplicates),
        )

        print(
            "Table pages            :",
            len(table_pages),
        )

        print(
            "Footer missing         :",
            len(footer_missing),
        )

        print(
            "Footer mismatches      :",
            len(footer_mismatch),
        )

        print(
            "Missing main PDF pages :",
            len(missing_main_pdf),
        )

        print()
        print("CHAPTERS")
        print("-" * 100)

        for chapter in sorted(
            chapters,
            key=lambda x: int(x),
        ):

            pages = chapters[
                chapter
            ]

            print(
                f"Chapter {chapter:>2}: "
                f"{len(pages)} occurrences "
                f"PDF {min(pages)}-{max(pages)}"
            )

        print()
        print("APPENDICES")
        print("-" * 100)

        for appendix in sorted(
            appendices
        ):

            pages = appendices[
                appendix
            ]

            print(
                f"Appendix {appendix:<8} "
                f"PDF {min(pages)}-{max(pages)}"
            )

        print()
        print("CANONICAL REGULATION CHECK")
        print("-" * 100)

        if missing_canonical:

            for item in missing_canonical[
                :50
            ]:

                print(
                    "MISSING:",
                    item,
                )

        else:

            print(
                "ALL CANONICAL REGULATIONS "
                "HAVE PDF HEADING CANDIDATES."
            )

        print()
        print("PAGINATION CHECK")
        print("-" * 100)

        if footer_missing:
            print(
                "Missing footer pages:",
                footer_missing[:50],
            )
        else:
            print(
                "No missing main-body "
                "footer numbers."
            )

        if footer_mismatch:
            print(
                "Footer mismatches:"
            )

            for item in footer_mismatch[
                :50
            ]:

                print(
                    item
                )
        else:
            print(
                "All detected main-body "
                "footers match PDF = printed + 16."
            )

        print()
        print("TABLE PAGES")
        print("-" * 100)

        for item in table_pages[:100]:

            print(
                f"PDF {item['pdf_page']:3} | "
                f"printed "
                f"{str(item['printed_page']):>3} | "
                f"find_tables="
                f"{len(item['detected_tables'])} | "
                f"TABLE word="
                f"{item['table_word']}"
            )

        print()
        print(
            "AUDIT FILE:"
        )

        print(
            OUTPUT
        )

        print()
        print("=" * 100)
        print("COMPLETE PDF AUDIT FINISHED")
        print("=" * 100)

    finally:

        doc.close()


if __name__ == "__main__":
    main()
