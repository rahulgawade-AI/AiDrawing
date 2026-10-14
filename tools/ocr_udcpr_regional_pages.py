#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import fitz
from PIL import Image

from surya.recognition import RecognitionPredictor


DEFAULT_DPI = 200


def classify_text(text: str) -> str:
    """
    Classify OCR text.

    regional:
        Devanagari characters detected.

    english:
        Latin characters detected and no Devanagari.

    mixed:
        Both detected.

    unknown:
        Neither detected.
    """

    if not text:
        return "unknown"

    devanagari = len(
        re.findall(
            r"[\u0900-\u097F]",
            text,
        )
    )

    latin = len(
        re.findall(
            r"[A-Za-z]",
            text,
        )
    )

    if devanagari > 0 and latin > 0:
        return "mixed"

    if devanagari > 0:
        return "regional"

    if latin > 0:
        return "english"

    return "unknown"


def render_pdf_page(
    pdf,
    page_number: int,
    dpi: int,
) -> Image.Image:

    page = pdf.load_page(
        page_number - 1
    )

    scale = dpi / 72.0

    matrix = fitz.Matrix(
        scale,
        scale,
    )

    pix = page.get_pixmap(
        matrix=matrix,
        alpha=False,
    )

    image = Image.frombytes(
        "RGB",
        [
            pix.width,
            pix.height,
        ],
        pix.samples,
    )

    return image


def polygon_to_list(polygon):

    if polygon is None:
        return None

    try:
        return [
            [
                float(point[0]),
                float(point[1]),
            ]
            for point in polygon
        ]

    except Exception:
        pass

    try:
        return [
            float(x)
            for x in polygon
        ]

    except Exception:
        return None


def extract_result_lines(page_result):

    lines = []

    blocks = getattr(
        page_result,
        "blocks",
        None,
    )

    if blocks is None:
        return lines

    for block_index, block in enumerate(
        blocks
    ):

        html = getattr(
            block,
            "html",
            "",
        )

        raw = getattr(
            block,
            "raw",
            None,
        )

        text = ""

        if isinstance(
            html,
            str,
        ):

            text = html

            text = re.sub(
                r"<[^>]+>",
                " ",
                text,
            )

        elif isinstance(
            raw,
            str,
        ):

            text = raw

        text = text.strip()

        if not text:
            continue

        confidence = getattr(
            block,
            "confidence",
            None,
        )

        polygon = getattr(
            block,
            "polygon",
            None,
        )

        label = getattr(
            block,
            "label",
            None,
        )

        classification = classify_text(
            text
        )

        lines.append(
            {
                "block_index":
                    block_index,

                "text":
                    text,

                "classification":
                    classification,

                "confidence":
                    float(confidence)
                    if confidence is not None
                    else None,

                "polygon":
                    polygon_to_list(
                        polygon
                    ),

                "label":
                    str(label)
                    if label is not None
                    else None,
            }
        )

    return lines


def create_ocr():

    print()
    print("=" * 110)
    print("INITIALIZING SURYA OCR")
    print("=" * 110)

    print(
        "OCR engine      : Surya"
    )

    print(
        "Mode            : full-page OCR"
    )

    print(
        "Language        : automatic multilingual recognition"
    )

    print(
        "Detection       : handled internally by Surya"
    )

    print(
        "Recognition     : RecognitionPredictor"
    )

    predictor = RecognitionPredictor()

    print(
        "Status          : READY"
    )

    return predictor


def process_page(
    pdf,
    predictor,
    page_number,
    output_dir,
    dpi,
):

    print()
    print("-" * 110)
    print(
        f"PROCESSING PDF PAGE {page_number}"
    )
    print("-" * 110)

    image = render_pdf_page(
        pdf,
        page_number,
        dpi,
    )

    image_path = (
        output_dir
        / f"page_{page_number:04d}.png"
    )

    image.save(
        image_path,
        format="PNG",
    )

    print(
        "Image          : "
        + str(image_path)
    )

    print(
        "Image size     : "
        + str(image.size)
    )

    # --------------------------------------------------------
    # Installed Surya version:
    #
    #     predictor([image], full_page=True)
    #
    # --------------------------------------------------------

    results = predictor(
        [image],
        full_page=True,
    )

    if not results:
        raise RuntimeError(
            "Surya returned no OCR result."
        )

    page_result = results[0]

    lines = extract_result_lines(
        page_result
    )

    if not lines:
        raise RuntimeError(
            "Surya returned an OCR result "
            "but no text blocks were extracted."
        )

    regional_lines = [
        x
        for x in lines
        if x["classification"]
        in (
            "regional",
            "mixed",
        )
    ]

    english_lines = [
        x
        for x in lines
        if x["classification"]
        == "english"
    ]

    mixed_lines = [
        x
        for x in lines
        if x["classification"]
        == "mixed"
    ]

    # --------------------------------------------------------
    # Preserve Surya OCR order.
    # --------------------------------------------------------

    text_parts = [
        x["text"]
        for x in lines
    ]

    text = "\n".join(
        text_parts
    ).strip()

    if not text:
        raise RuntimeError(
            "OCR text is empty."
        )

    txt_path = (
        output_dir
        / f"page_{page_number:04d}.txt"
    )

    txt_path.write_text(
        text,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    result = {
        "schema":
            "udcpr.regional.ocr.v3",

        "created_at":
            datetime.now().isoformat(),

        "pdf_page":
            page_number,

        "dpi":
            dpi,

        "image":
            str(image_path),

        "ocr_engine":
            "surya",

        "ocr_mode":
            "full_page",

        "language":
            "automatic_multilingual",

        "text":
            text,

        "lines":
            lines,

        "statistics":
            {
                "line_count":
                    len(lines),

                "regional_lines":
                    sum(
                        1
                        for x in lines
                        if x["classification"]
                        == "regional"
                    ),

                "english_lines":
                    len(english_lines),

                "mixed_lines":
                    len(mixed_lines),

                "regional_or_mixed_lines":
                    len(regional_lines),

                "character_count":
                    len(text),
            },
    }

    json_path = (
        output_dir
        / f"page_{page_number:04d}.json"
    )

    json_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "OCR lines      : "
        + str(len(lines))
    )

    print(
        "Regional/mixed : "
        + str(len(regional_lines))
    )

    print(
        "English        : "
        + str(len(english_lines))
    )

    print(
        "Characters     : "
        + str(len(text))
    )

    print(
        "JSON           : "
        + str(json_path)
    )

    print(
        "Text           : "
        + str(txt_path)
    )

    return result


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run Surya OCR on regional-language "
            "UDCPR PDF pages."
        )
    )

    parser.add_argument(
        "--pdf",
        required=True,
    )

    parser.add_argument(
        "--start-page",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--end-page",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
    )

    parser.add_argument(
        "--no-skip",
        action="store_true",
        help=(
            "Reprocess pages even when OCR output "
            "already exists."
        ),
    )

    args = parser.parse_args()

    pdf_path = Path(
        args.pdf
    )

    output_dir = Path(
        args.output
    )

    report_path = Path(
        args.report
    )

    if not pdf_path.exists():

        raise SystemExit(
            f"ERROR: PDF not found: {pdf_path}"
        )

    if args.start_page < 1:

        raise SystemExit(
            "ERROR: start page must be >= 1."
        )

    if args.end_page < args.start_page:

        raise SystemExit(
            "ERROR: end page must be >= start page."
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 110)
    print(
        "UDCPR REGIONAL PAGES - SURYA OCR"
    )
    print("=" * 110)

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Raw OCR only."
    )

    print(
        "OCR engine: Surya."
    )

    print(
        "OCR mode: full_page."
    )

    print(
        "No translation."
    )

    print(
        "No summarization."
    )

    print(
        "No PostgreSQL changes."
    )

    print(
        "No ChromaDB changes."
    )

    print(
        "Original PDF is not modified."
    )

    print()

    print(
        f"PDF       : {pdf_path}"
    )

    print(
        f"Pages     : "
        f"{args.start_page} -> "
        f"{args.end_page}"
    )

    print(
        f"DPI       : {args.dpi}"
    )

    print(
        f"Output    : {output_dir}"
    )

    print(
        f"Report    : {report_path}"
    )

    print(
        "Resume    : "
        + (
            "disabled"
            if args.no_skip
            else "enabled"
        )
    )

    # --------------------------------------------------------
    # Open PDF
    # --------------------------------------------------------

    pdf = fitz.open(
        pdf_path
    )

    pdf_page_count = len(
        pdf
    )

    print()
    print("=" * 110)
    print("PDF")
    print("=" * 110)

    print(
        f"PDF pages : {pdf_page_count}"
    )

    if args.end_page > pdf_page_count:

        pdf.close()

        raise SystemExit(
            f"ERROR: end page {args.end_page} "
            f"exceeds PDF page count "
            f"{pdf_page_count}."
        )

    # --------------------------------------------------------
    # Initialize Surya
    # --------------------------------------------------------

    predictor = create_ocr()

    processed = []
    skipped = []
    failures = []

    total_lines = 0
    regional_pages = 0
    english_pages = 0
    empty_pages = 0

    requested_pages = (
        args.end_page
        - args.start_page
        + 1
    )

    # --------------------------------------------------------
    # Process
    # --------------------------------------------------------

    for page_number in range(
        args.start_page,
        args.end_page + 1,
    ):

        json_path = (
            output_dir
            / f"page_{page_number:04d}.json"
        )

        txt_path = (
            output_dir
            / f"page_{page_number:04d}.txt"
        )

        image_path = (
            output_dir
            / f"page_{page_number:04d}.png"
        )

        # ----------------------------------------------------
        # Resume support
        # ----------------------------------------------------

        if (
            not args.no_skip
            and json_path.exists()
            and txt_path.exists()
            and image_path.exists()
        ):

            try:

                existing = json.loads(
                    json_path.read_text(
                        encoding="utf-8"
                    )
                )

                if (
                    existing.get("ocr_engine")
                    == "surya"
                    and existing.get("ocr_mode")
                    == "full_page"
                    and existing.get("text")
                ):

                    print()
                    print("-" * 110)
                    print(
                        f"SKIPPING PDF PAGE "
                        f"{page_number} "
                        f"(already processed)"
                    )
                    print("-" * 110)

                    skipped.append(
                        {
                            "pdf_page":
                                page_number,

                            "json":
                                str(json_path),

                            "text":
                                str(txt_path),

                            "image":
                                str(image_path),
                        }
                    )

                    continue

            except Exception:
                pass

        try:

            result = process_page(
                pdf,
                predictor,
                page_number,
                output_dir,
                args.dpi,
            )

            processed.append(
                result
            )

            total_lines += (
                result["statistics"][
                    "line_count"
                ]
            )

            if (
                result["statistics"][
                    "regional_or_mixed_lines"
                ]
                > 0
            ):
                regional_pages += 1

            if (
                result["statistics"][
                    "english_lines"
                ]
                > 0
            ):
                english_pages += 1

            if not result["text"]:
                empty_pages += 1

        except Exception as exc:

            print()
            print(
                f"ERROR PAGE {page_number}: "
                f"{exc}"
            )

            failures.append(
                {
                    "pdf_page":
                        page_number,

                    "error":
                        repr(exc),
                }
            )

    pdf.close()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    report = {

        "schema":
            "udcpr.regional.ocr.report.v3",

        "created_at":
            datetime.now().isoformat(),

        "source":
            {
                "pdf":
                    str(pdf_path),

                "pdf_pages":
                    pdf_page_count,

                "start_page":
                    args.start_page,

                "end_page":
                    args.end_page,

                "dpi":
                    args.dpi,

                "ocr_engine":
                    "surya",

                "ocr_mode":
                    "full_page",

                "language":
                    "automatic_multilingual",
            },

        "summary":
            {
                "requested_pages":
                    requested_pages,

                "processed_pages":
                    len(processed),

                "skipped_pages":
                    len(skipped),

                "failed_pages":
                    len(failures),

                "pages_with_regional_text":
                    regional_pages,

                "pages_with_english_text":
                    english_pages,

                "empty_pages":
                    empty_pages,

                "total_ocr_lines":
                    total_lines,
            },

        "pages":
            [
                {
                    "pdf_page":
                        x["pdf_page"],

                    "statistics":
                        x["statistics"],

                    "json":
                        str(
                            output_dir
                            / (
                                f"page_"
                                f"{x['pdf_page']:04d}.json"
                            )
                        ),

                    "text":
                        str(
                            output_dir
                            / (
                                f"page_"
                                f"{x['pdf_page']:04d}.txt"
                            )
                        ),

                    "image":
                        str(
                            output_dir
                            / (
                                f"page_"
                                f"{x['pdf_page']:04d}.png"
                            )
                        ),
                }
                for x in processed
            ],

        "skipped":
            skipped,

        "failures":
            failures,

    }

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 110)
    print(
        "SURYA OCR SUMMARY"
    )
    print("=" * 110)

    print(
        "Requested pages          : "
        + str(requested_pages)
    )

    print(
        "Processed pages          : "
        + str(len(processed))
    )

    print(
        "Skipped pages            : "
        + str(len(skipped))
    )

    print(
        "Failed pages             : "
        + str(len(failures))
    )

    print(
        "Pages with regional text : "
        + str(regional_pages)
    )

    print(
        "Pages with English text  : "
        + str(english_pages)
    )

    print(
        "Empty pages              : "
        + str(empty_pages)
    )

    print(
        "Total OCR lines          : "
        + str(total_lines)
    )

    print()
    print(
        "Report: "
        + str(report_path)
    )

    if failures:

        print()
        print(
            "WARNING: Some pages failed."
        )

        return 1

    print()
    print(
        "PASS: All requested pages "
        "processed or skipped successfully."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
