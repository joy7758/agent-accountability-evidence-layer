#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python scripts/validate_all_examples.py
