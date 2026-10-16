#!/usr/bin/env bash
# Applies each patch in demo/scenarios to the helpdesk, rebuilds the coverage map,
# asks tier-review for a decision, then reverts the patch.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "demo: working tree has changes; commit or stash them first" >&2
  exit 1
fi
if [ -n "$(git ls-files --others --exclude-standard helpdesk tier-review demo)" ]; then
  echo "demo: untracked project files would be classified as new code; commit them first" >&2
  exit 1
fi

docker compose build --quiet coverage-map tier-review

for patch in demo/scenarios/*.patch; do
  title=$(sed -n 's/^# //p' "$patch" | head -1)
  printf '\n\033[1m=== %s\033[0m\n    %s\n\n' "$(basename "$patch" .patch)" "$title"
  git apply "$patch"
  trap 'git apply -R "$patch"' EXIT
  docker compose run --rm -T coverage-map > /dev/null
  docker compose run --rm -T tier-review
  git apply -R "$patch"
  trap - EXIT
done
