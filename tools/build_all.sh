#!/usr/bin/env bash
# Rebuild every sellable file in course/dist/ from source.
#   bash tools/build_all.sh "Bot's Trading"
set -euo pipefail
cd "$(dirname "$0")/.."
DEFAULT_BRAND="Bot's Trading"
BRAND="${1:-$DEFAULT_BRAND}"
python tools/build_kit.py
node tools/build_pdf.js "$BRAND"
node tools/build_quickstart.js "$BRAND"
ls -la course/dist/*.pdf course/dist/*.zip
