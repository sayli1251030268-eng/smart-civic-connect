#!/usr/bin/env bash
# Smart Civic Connect - One Command Launch Script
set -e

cd "$(dirname "$0")"
python3 run.py "$@"
