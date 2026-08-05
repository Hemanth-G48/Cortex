#!/usr/bin/env bash
# Shallow-clone all reference repos from /tmp/repo_list.txt into similar_repos/.
# Usage: bash scripts/clone_similar_repos.sh <start_line> <end_line>
set -u

START="${1:-1}"
END="${2:-69}"

cd /home/hemanth/productivity_app || exit 1

run_one() {
  local r="$1" o d
  o="${r#github.com/}"
  d="similar_repos/$o"
  # Skip only repos with a valid git dir
  if git -C "$d" rev-parse --git-dir >/dev/null 2>&1; then
    echo "SKIP $o"
    return
  fi
  # Clean partial/interrupted clones
  rm -rf "$d"
  GIT_TERMINAL_PROMPT=0 timeout 120 git clone --depth 1 --quiet "https://$r" "$d" 2> /tmp/clone_err_$$
  if [ $? -eq 0 ]; then
    echo "OK $o"
  else
    echo "FAIL $o: $(head -c 160 /tmp/clone_err_$$)"
  fi
}
export -f run_one

sed -n "${START},${END}p" /tmp/repo_list.txt | xargs -P 4 -I {} bash -c 'run_one "$@"' _ {} 2>&1 | grep -E '^(OK|FAIL|SKIP)'
