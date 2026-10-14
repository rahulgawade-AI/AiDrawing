from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parent.parent

MODEL_ROOT = ROOT / "models" / "paddle"

MODEL_ROOT.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("Downloading PaddleOCR Models")
print("=" * 70)

commands = [

    [
        "paddlex",
        "--get_model",
        "PP-OCRv5_server_det",
        "--save_dir",
        str(MODEL_ROOT),
    ],

    [
        "paddlex",
        "--get_model",
        "PP-OCRv5_server_rec",
        "--save_dir",
        str(MODEL_ROOT),
    ],

    [
        "paddlex",
        "--get_model",
        "PP-LCNet_x1_0_textline_ori",
        "--save_dir",
        str(MODEL_ROOT),
    ],
]

for cmd in commands:

    print("\nRunning:")
    print(" ".join(cmd))

    subprocess.run(
        cmd,
        check=True,
    )

print("\nDone.")
