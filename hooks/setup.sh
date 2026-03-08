#!/bin/bash

# One-time setup: copies the pre-push hook into .git/hooks/
# Run this after pulling the hooks folder.

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOK_SOURCE="$REPO_ROOT/hooks/pre-push"
HOOK_TARGET="$REPO_ROOT/.git/hooks/pre-push"

if [ ! -f "$HOOK_SOURCE" ]; then
    echo "Error: $HOOK_SOURCE not found."
    exit 1
fi

cp "$HOOK_SOURCE" "$HOOK_TARGET"
chmod +x "$HOOK_TARGET"

echo "Pre-push hook installed successfully."
