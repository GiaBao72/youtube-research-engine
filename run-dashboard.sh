#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d ../.venv ]; then
  echo "Missing ../.venv. Create it first: python3 -m venv ../.venv && source ../.venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi
source ../.venv/bin/activate
export PYTHONPATH=src
streamlit run src/youtube_research/dashboard_streamlit.py
