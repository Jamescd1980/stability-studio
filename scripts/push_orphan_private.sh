#!/usr/bin/env bash
set -euo pipefail
cd /d/studio-agent
TREE=$(git rev-parse 'HEAD^{tree}')
echo "TREE=$TREE"
ORPHAN=$(git commit-tree "$TREE" -m "Fern gold smoke + studio-edge lessons (orphan snapshot for private).")
echo "ORPHAN=$ORPHAN"
git push private "$ORPHAN:refs/heads/studio-edge-lessons-2026-07-19" --force
git ls-remote private 'refs/heads/studio-edge-lessons-2026-07-19'
