#!/usr/bin/env bash
# Survey one repo: README head, license, languages, size, top-level structure.
# Usage: bash scripts/survey_repo.sh <repo_path>
set -u
R="$1"
echo "===== REPO: ${R#similar_repos/} ====="
echo "-- LICENSE: $(find "$R" -maxdepth 1 -iname 'license*' -o -maxdepth 1 -iname 'copying*' 2>/dev/null | head -1 | xargs -r basename || echo none)"
echo "-- FILE COUNT: $(find "$R" -type f -not -path '*/.git/*' 2>/dev/null | wc -l)"
echo "-- TOP-LEVEL ENTRIES:"
ls -1 "$R" 2>/dev/null | head -25 | sed 's/^/    /'
echo "-- LANGUAGE SPREAD (by extension, top 8):"
find "$R" -type f -not -path '*/.git/*' 2>/dev/null | grep -oE '\.[A-Za-z0-9]+$' | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn | head -8 | sed 's/^/    /'
echo "-- README (first 18 lines):"
readme=$(find "$R" -maxdepth 2 -iname 'readme*' 2>/dev/null | head -1)
if [ -n "$readme" ]; then
  head -18 "$readme" 2>/dev/null
else
  echo "    (no README)"
fi
echo ""
