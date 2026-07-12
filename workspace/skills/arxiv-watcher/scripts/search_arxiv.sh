#!/usr/bin/env bash
# scripts/search_arxiv.sh
QUERY=$1
COUNT=${2:-5}
# Delegate to the Python script so ArXiv queries are normalized and URL-encoded safely.
python "$(dirname "$0")/search_arxiv.py" "$QUERY" "$COUNT"
