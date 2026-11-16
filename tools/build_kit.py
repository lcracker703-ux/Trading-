"""Build the sellable course bundle:
  course/dist/Trading-Bot-Kit.zip   - flat code kit buyers upload to GitHub (iPad friendly)
  course/dist/*.pdf                 - built separately by tools/build_pdf.js

The kit is generated from the real code in trading_signals/, so it never drifts.
  python tools/build_kit.py
"""
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = "Bot's Trading"  # change to your shop/brand name, then rebuild
DIST = ROOT / "course" / "dist"
KIT = DIST / "Trading-Bot-Kit"

MODULES = ["indicators", "strategy", "strategies", "data", "notify", "main", "backtest", "compare", "check"]
WORKFLOWS = [  # (source, kit filename, path buyers must create)
    ("signals.yml", "1-signals.yml.txt"),
    ("check-setup.yml", "2-check-setup.yml.txt"),
    ("backtest.yml", "3-backtest.yml.txt"),
    ("compare.yml", "4-compare.yml.txt"),
]


def flatten_imports(src: str) -> str:
    src = src.replace("python -m trading_signals.", "python -m ")
    src = re.sub(r"from \. import ", "import ", src)
    src = re.sub(r"from \.(\w+) import ", r"from \1 import ", src)
    return src


def kit_workflow(src: str) -> str:
    src = src.replace("python -m trading_signals.", "python -m ")
    # The kit ships without the developer test-suite
    src = re.split(r"\n  tests:\n", src)[0].rstrip() + "\n"
    return src


SETUP_TXT = """TRADING BOT KIT - by {brand}
=============================

Follow the PDF guide, chapters 5 to 7. In short:

1. Create a new PRIVATE repository on github.com.
2. Upload every file in this folder EXCEPT the "workflows" folder.
3. For each file in the "workflows" folder, create a new file in GitHub named
       .github/workflows/<name>.yml
   (e.g. .github/workflows/signals.yml) and paste the file's contents in.
4. Add your two secrets: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
5. Actions tab -> "Check setup" -> Run workflow.

Not financial advice - see DISCLAIMER.md.
"""

LICENSE_TXT = """PERSONAL USE LICENCE - Trading Bot Kit and guide
Copyright (c) 2026 {brand}. All rights reserved.

You (the buyer) may:
  - use this kit and guide for your own personal trading alerts;
  - change the code and settings for your own use.

You may not:
  - resell, share, give away, or publish this kit, the guide, or modified
    versions of them (including in public GitHub repositories);
  - sell signals produced by this kit to others.

Keep your GitHub repository PRIVATE.

No warranty: the software is provided "as is", without warranty of any kind.
The authors are not liable for any losses. This is not financial advice -
see DISCLAIMER.md.
"""


def build() -> Path:
    if KIT.exists():
        shutil.rmtree(KIT)
    (KIT / "workflows").mkdir(parents=True)
    for m in MODULES:
        src = (ROOT / "trading_signals" / f"{m}.py").read_text()
        (KIT / f"{m}.py").write_text(flatten_imports(src))
    for f in ("config.yaml", "requirements.txt", "DISCLAIMER.md"):
        shutil.copy(ROOT / f, KIT / f)
    for src, dst in WORKFLOWS:
        (KIT / "workflows" / dst).write_text(kit_workflow((ROOT / ".github" / "workflows" / src).read_text()))
    (KIT / "START-HERE.txt").write_text(SETUP_TXT.format(brand=BRAND))
    (KIT / "LICENSE.txt").write_text(LICENSE_TXT.format(brand=BRAND))

    zpath = DIST / "Trading-Bot-Kit.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(KIT.rglob("*")):
            if p.is_file():
                z.write(p, Path("Trading-Bot-Kit") / p.relative_to(KIT))
    return zpath


if __name__ == "__main__":
    print(build())
