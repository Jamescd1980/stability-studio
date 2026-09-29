#!/usr/bin/env bash
set -euo pipefail
cd /d/studio-agent
export GIT_AUTHOR_NAME=Jamescd1980
export GIT_AUTHOR_EMAIL=Jamescd1980@users.noreply.github.com
export GIT_COMMITTER_NAME=Jamescd1980
export GIT_COMMITTER_EMAIL=Jamescd1980@users.noreply.github.com
TREE=$(git rev-parse 'HEAD^{tree}')
echo "TREE=$TREE"
ORPHAN=$(git commit-tree "$TREE" -m "Private tip: ComfyBox CUDA 5090, Blender MCP, Hunyuan (~123 tools) orphan snapshot.")
echo "ORPHAN=$ORPHAN"
git push private "$ORPHAN:refs/heads/comfybox-cuda-5090"
git ls-remote private 'refs/heads/comfybox-cuda-5090'
git tag -f private-comfybox-cuda-5090-orphan "$ORPHAN"
echo "OK local=$(git rev-parse --short HEAD) orphan=$(git rev-parse --short "$ORPHAN")"
