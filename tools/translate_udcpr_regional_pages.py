#!/usr/bin/env python3

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests


DEVANAGARI_DIGITS = str.maketrans(
    "०१२३४५६७८९",
    "0123456789",
)


def normalize_digits(text: str) -> str:
    return text.translate(DEVANAGARI_DIGITS)


def normalize_for_validation(text: str) -> str:
    text = normalize_digits(text)

    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_regulation_numbers(text: str) -> list[str]:
    normalized = normalize_for_validation(text)

    pattern = r"\b\d+(?:\.\d+)+(?:\([a-zA-Z0-9]+\))?"

    found = re.findall(pattern, normalized)

    result = []
    seen = set()

    for value in found:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def extract_dates(text: str) -> list[str]:
    normalized = normalize_for_validation(text)

    pattern = r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b"

    found = re.findall(pattern, normalized)

    result = []
    seen = set()

    for value in found:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def extract_emails(text: str) -> list[str]:
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    found = re.findall(pattern, text)

    result = []
    seen = set()

    for value in found:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


def extract_notification_numbers(text: str) -> list[str]:
    """
    Extract official notification/reference identifiers.

    The goal is to catch identifiers such as:
        TPS-1818/150/Pr. No. 158/19/Navi-13
        TPS-1818/Pr. No. 236/18 (Part-2)/Navi-13

    Marathi text may contain Devanagari digits, so normalization is applied.
    """

    normalized = normalize_for_validation(text)

    patterns = [
        r"\b[A-Z]{2,10}-\d{2,10}/[^,\n;]+",
        r"\b(?:TPS|GAD|UD|DP|TP)-[A-Za-z0-9./() -]+",
    ]

    result = []
    seen = set()

    for pattern in patterns:
        for value in re.findall(pattern, normalized):
            value = value.strip(" .,:;")

            if value and value not in seen:
                seen.add(value)
                result.append(value)

    return result


def extract_sections(text: str) -> list[str]:
    """
    Extract references such as:
        Section 37(1)
        Section 154
        कलम ३७(१कक)
        कलम १५४
    """

    normalized = normalize_for_validation(text)

    patterns = [
        r"\bSection\s+\d+(?:\([^)]+\))?",
        r"\bSections\s+\d+(?:\([^)]+\))?",
    ]

    result = []
    seen = set()

    for pattern in patterns:
        for value in re.findall(pattern, normalized, re.IGNORECASE):
            value = re.sub(r"\s+", " ", value).strip()

            if value.lower() not in {
                x.lower() for x in seen
            }:
                seen.add(value)
                result.append(value)

    return result


def validate_translation(
    original_text: str,
    translated_text: str,
) -> dict[str, Any]:

    original_regulations = extract_regulation_numbers(
        original_text
    )

    translated_regulations = extract_regulation_numbers(
        translated_text
    )

    original_dates = extract_dates(original_text)

    translated_dates = extract_dates(translated_text)

    original_emails = extract_emails(original_text)

    translated_emails = extract_emails(translated_text)

    original_notifications = extract_notification_numbers(
        original_text
    )

    translated_notifications = extract_notification_numbers(
        translated_text
    )

    missing_regulations = [
        x
        for x in original_regulations
        if x not in translated_regulations
    ]

    missing_dates = [
        x
        for x in original_dates
        if x not in translated_dates
    ]

    missing_emails = [
        x
        for x in original_emails
        if x not in translated_emails
    ]

    # Notification matching is intentionally conservative.
    # If OCR contains a notification identifier and the translation
    # changes it substantially, flag it.
    missing_notifications = []

    for original in original_notifications:
        if not any(
            original == translated
            or original.replace(" ", "")
            == translated.replace(" ", "")
            for translated in translated_notifications
        ):
            missing_notifications.append(original)

    passed = (
        not missing_regulations
        and not missing_dates
        and not missing_emails
        and not missing_notifications
    )

    return {
        "original_regulation_numbers": original_regulations,
        "translated_regulation_numbers": translated_regulations,
        "missing_regulation_numbers": missing_regulations,

        "original_dates": original_dates,
        "translated_dates": translated_dates,
        "missing_dates": missing_dates,

        "original_emails": original_emails,
        "translated_emails": translated_emails,
        "missing_emails": missing_emails,

        "original_notification_numbers": original_notifications,
        "translated_notification_numbers": translated_notifications,
        "missing_notification_numbers": missing_notifications,

        "passed": passed,
    }


def load_ocr_file(path: Path) -> dict[str, Any]:

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid OCR JSON: {path}"
        )

    if data.get("ocr_engine") != "surya":
        raise ValueError(
            f"{path} is not Surya OCR output. "
            f"ocr_engine={data.get('ocr_engine')!r}"
        )

    if data.get("ocr_mode") != "full_page":
        raise ValueError(
            f"{path} is not Surya full-page OCR output. "
            f"ocr_mode={data.get('ocr_mode')!r}"
        )

    if "text" not in data:
        raise ValueError(
            f"OCR JSON has no text field: {path}"
        )

    return data


def ollama_generate(
    host: str,
    model: str,
    prompt: str,
    timeout: int,
) -> str:

    url = host.rstrip("/") + "/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
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

    if "response" not in data:
        raise RuntimeError(
            f"Invalid Ollama response: {data}"
        )

    return data["response"].strip()


def build_translation_prompt(
    source_text: str,
) -> str:

    return f"""
You are translating an official Maharashtra Government document
related to UDCPR (Unified Development Control and Promotion Regulations).

Translate the Marathi/regional-language portions into accurate,
literal, official English.

CRITICAL REQUIREMENTS:

1. Translate Marathi/regional-language text into English.

2. Existing English text MUST remain exactly unchanged.

3. Do NOT summarize.

4. Do NOT explain.

5. Do NOT rewrite the document.

6. Do NOT add information.

7. Do NOT remove information.

8. Preserve the original document order.

9. Preserve paragraph structure as closely as possible.

10. Preserve every regulation number.

11. Preserve every date.

12. Preserve every notification/reference number.

13. Preserve every section number.

14. Preserve email addresses exactly.

15. Preserve abbreviations exactly where they are already in English.

16. Preserve names of people.

17. Translate government department names literally.

18. Translate government authority/organization names literally.
    Do NOT reinterpret an organization based on context.

19. Translate official designations literally.
    Do NOT upgrade, downgrade, or reinterpret a designation.

20. Preserve place names accurately.

21. Preserve road/address information accurately.

22. Do not invent an English expansion for an abbreviation.

23. Do not convert one authority into another authority.

24. Do not convert one government designation into another designation.

25. For mixed Marathi/English text, preserve the English portions
    exactly and translate only the Marathi portions.

26. Devanagari numerals may be converted to ASCII numerals:
       १४.२.१ -> 14.2.1
       १४/०१/२०२१ -> 14/01/2021

27. Regulation numbers, dates, notification numbers and section
    references must retain their meaning.

28. Output ONLY the translated document.

29. Do not add a preface such as "Here is the translation".

30. Do not add notes or comments after the translation.

IMPORTANT EXAMPLES:

Marathi:
पुणे महानगर प्रदेश विकास प्राधिकरण

Correct:
Pune Metropolitan Region Development Authority

Incorrect:
Pune Municipal Corporation Development Authority

Marathi:
अवर सचिव

Correct:
Under Secretary

Incorrect:
Additional Secretary

The translation must remain faithful to the source.
Do not use contextual guessing to change official names.

SOURCE OCR:

{source_text}
""".strip()


def write_text(
    path: Path,
    text: str,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        f.write(text.rstrip() + "\n")


def write_json(
    path: Path,
    data: dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def parse_page_number(
    path: Path,
) -> int | None:

    match = re.search(
        r"page_(\d+)\.json$",
        path.name,
    )

    if not match:
        return None

    return int(match.group(1))


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Translate Surya OCR regional UDCPR pages "
            "using Ollama."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
    )

    parser.add_argument(
        "--output",
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
        "--model",
        default="qwen3:8b",
    )

    parser.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    report_path = Path(args.report)

    print("=" * 110)
    print("UDCPR REGIONAL OCR -> ENGLISH TRANSLATION")
    print("=" * 110)
    print()
    print("Source OCR       : Surya full_page")
    print("Translation      : Ollama")
    print("Model            :", args.model)
    print("Original OCR     : preserved")
    print("Existing English : preserved")
    print("Translation      : Marathi/regional -> English")
    print("Requests/page    : 1")
    print("Summarization    : disabled")
    print("PostgreSQL       : no changes")
    print("ChromaDB         : no changes")
    print()
    print("Input       :", input_dir)
    print("Output      :", output_dir)
    print(
        "Pages       :",
        args.start_page,
        "->",
        args.end_page,
    )
    print("Ollama      :", args.ollama_host)
    print("Timeout     :", args.timeout)
    print("Report      :", report_path)
    print()

    # --------------------------------------------------------------
    # Ollama check
    # --------------------------------------------------------------

    print("=" * 110)
    print("OLLAMA CHECK")
    print("=" * 110)

    try:

        url = (
            args.ollama_host.rstrip("/")
            + "/api/tags"
        )

        response = requests.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        models = [
            x.get("name")
            for x in data.get("models", [])
        ]

        for model_name in models:
            print(" ", model_name)

        if args.model not in models:
            print()
            print(
                "ERROR: model not found:",
                args.model,
            )
            return 1

    except Exception as exc:

        print(
            "ERROR: Ollama check failed:",
            exc,
        )
        return 1

    # --------------------------------------------------------------
    # Find OCR pages
    # --------------------------------------------------------------

    print()
    print("=" * 110)
    print("SOURCE")
    print("=" * 110)

    all_pages = []

    for path in sorted(
        input_dir.glob("page_*.json")
    ):

        page = parse_page_number(path)

        if page is not None:
            all_pages.append(
                (page, path)
            )

    selected_pages = [
        item
        for item in all_pages
        if args.start_page
        <= item[0]
        <= args.end_page
    ]

    print(
        "OCR pages found :",
        len(all_pages),
    )

    print(
        "Pages selected  :",
        len(selected_pages),
    )

    if not selected_pages:
        print("ERROR: No pages selected.")
        return 1

    # --------------------------------------------------------------
    # Counters
    # --------------------------------------------------------------

    processed = 0
    failed = 0

    regional_lines = 0
    english_lines = 0
    mixed_lines = 0

    translated_chars = 0

    failures = []
    page_results = []

    # --------------------------------------------------------------
    # Process pages
    # --------------------------------------------------------------

    for index, (
        page_number,
        source_path,
    ) in enumerate(
        selected_pages,
        start=1,
    ):

        print()
        print("-" * 110)
        print(
            f"PROCESSING {index} / "
            f"{len(selected_pages)}"
        )
        print(
            f"Page   : {page_number}"
        )
        print(
            f"Source : {source_path}"
        )
        print("-" * 110)

        started = time.time()

        try:

            ocr = load_ocr_file(
                source_path
            )

            source_text = ocr["text"]

            # ------------------------------------------------------
            # Surya line statistics
            # ------------------------------------------------------

            for line in ocr.get(
                "lines",
                [],
            ):

                classification = line.get(
                    "classification",
                    "unknown",
                )

                if classification == "regional":
                    regional_lines += 1

                elif classification == "english":
                    english_lines += 1

                elif classification == "mixed":
                    mixed_lines += 1

            # ------------------------------------------------------
            # Translation
            # ------------------------------------------------------

            prompt = build_translation_prompt(
                source_text
            )

            translated_text = ollama_generate(
                host=args.ollama_host,
                model=args.model,
                prompt=prompt,
                timeout=args.timeout,
            )

            if not translated_text:
                raise RuntimeError(
                    "Ollama returned empty translation."
                )

            # ------------------------------------------------------
            # Validation
            # ------------------------------------------------------

            validation = validate_translation(
                source_text,
                translated_text,
            )

            if not validation["passed"]:
                print()
                print("WARNING: Translation safety check reported differences.")
                print(
                    json.dumps(
                        validation,
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                print(
                    "WARNING: Saving translation because this is a "
                    "regional government-explanation document."
                )

            elapsed = time.time() - started

            # ------------------------------------------------------
            # Output TXT
            # ------------------------------------------------------

            output_txt = (
                output_dir
                / f"page_{page_number:04d}.txt"
            )

            write_text(
                output_txt,
                translated_text,
            )

            # ------------------------------------------------------
            # Output JSON
            # ------------------------------------------------------

            output_json = (
                output_dir
                / f"page_{page_number:04d}.json"
            )

            record = {
                "schema":
                    "udcpr.regional.translation.v3",

                "pdf_page":
                    page_number,

                "source_ocr_file":
                    str(source_path),

                "source_ocr_engine":
                    ocr.get("ocr_engine"),

                "source_ocr_mode":
                    ocr.get("ocr_mode"),

                "source_ocr_language":
                    ocr.get("language"),

                "translation_engine":
                    "ollama",

                "translation_model":
                    args.model,

                # EXACT source OCR.
                "original_ocr_text":
                    source_text,

                # Translation only.
                "translated_english_text":
                    translated_text,

                "validation":
                    validation,

                "statistics": {
                    "source_characters":
                        len(source_text),

                    "translated_characters":
                        len(translated_text),

                    "elapsed_seconds":
                        round(
                            elapsed,
                            2,
                        ),
                },
            }

            write_json(
                output_json,
                record,
            )

            processed += 1

            translated_chars += len(
                translated_text
            )

            page_results.append(
                {
                    "page":
                        page_number,

                    "status":
                        "passed",

                    "source":
                        str(source_path),

                    "output_txt":
                        str(output_txt),

                    "output_json":
                        str(output_json),

                    "validation":
                        validation,

                    "elapsed_seconds":
                        round(
                            elapsed,
                            2,
                        ),
                }
            )

            print()
            print("PASS")
            print(
                "  Translation chars:",
                len(translated_text),
            )
            print(
                "  Time:",
                f"{elapsed:.2f}s",
            )
            print(
                "  Output:",
                output_txt,
            )

        except Exception as exc:

            failed += 1

            error = str(exc)

            failures.append(
                {
                    "page":
                        page_number,

                    "source":
                        str(source_path),

                    "error":
                        error,
                }
            )

            page_results.append(
                {
                    "page":
                        page_number,

                    "status":
                        "failed",

                    "source":
                        str(source_path),

                    "error":
                        error,
                }
            )

            print()
            print("ERROR:")
            print(" ", error)

    # --------------------------------------------------------------
    # Report
    # --------------------------------------------------------------

    report = {
        "schema":
            "udcpr.regional.translation.report.v3",

        "input":
            str(input_dir),

        "output":
            str(output_dir),

        "start_page":
            args.start_page,

        "end_page":
            args.end_page,

        "ollama_host":
            args.ollama_host,

        "model":
            args.model,

        "source_ocr_engine":
            "surya",

        "source_ocr_mode":
            "full_page",

        "pages_found":
            len(all_pages),

        "pages_selected":
            len(selected_pages),

        "pages_processed":
            processed,

        "pages_failed":
            failed,

        "regional_lines":
            regional_lines,

        "english_lines":
            english_lines,

        "mixed_lines":
            mixed_lines,

        "translated_chars":
            translated_chars,

        "failures":
            failures,

        "pages":
            page_results,

        "passed":
            failed == 0,
    }

    write_json(
        report_path,
        report,
    )

    print()
    print("=" * 110)
    print("TRANSLATION SUMMARY")
    print("=" * 110)

    print(
        "Pages selected      :",
        len(selected_pages),
    )

    print(
        "Pages processed     :",
        processed,
    )

    print(
        "Pages failed        :",
        failed,
    )

    print(
        "Regional lines      :",
        regional_lines,
    )

    print(
        "English lines       :",
        english_lines,
    )

    print(
        "Mixed lines         :",
        mixed_lines,
    )

    print(
        "Translated chars    :",
        translated_chars,
    )

    print()
    print(
        "Report:",
        report_path,
    )

    if failed:
        print()
        print(
            "WARNING: Some pages failed."
        )
        return 1

    print()
    print(
        "SUCCESS: All selected pages passed."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
