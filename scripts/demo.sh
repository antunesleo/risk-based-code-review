#!/usr/bin/env bash
# Catalogs tiers of the committed example codebase once (base), then applies each patch
# in demo/scenarios, catalogs the patched tree (head), classifies the diff, and reverts
# the patch.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "demo: working tree has changes; commit or stash them first" >&2
  exit 1
fi
if [ -n "$(git ls-files --others --exclude-standard example-codebase tier-review demo)" ]; then
  echo "demo: untracked project files would be classified as new code; commit them first" >&2
  exit 1
fi

docker compose build --quiet catalog-tiers tier-review

# The base catalog: the committed tree, before any scenario is applied.
echo "cataloging tiers of HEAD (base)..."
make --no-print-directory catalog-tiers-base BASE=HEAD > /dev/null

for patch in demo/scenarios/*.patch; do
  title=$(sed -n 's/^# //p' "$patch" | head -1)
  printf '\n\033[1m=== %s\033[0m\n    %s\n\n' "$(basename "$patch" .patch)" "$title"
  git apply "$patch"
  trap 'git apply -R "$patch"' EXIT
  CATALOG=head docker compose run --rm -T catalog-tiers > /dev/null
  docker compose run --rm -T tier-review
  git apply -R "$patch"
  trap - EXIT
done
