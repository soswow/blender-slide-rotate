#!/bin/sh
# Symlink this checkout into Blender 5.1 for edit/reload development.

set -eu

BLENDER_BIN="${BLENDER_BIN:-/Applications/Blender 5.1.app/Contents/MacOS/blender}"
BLENDER_VERSION="${BLENDER_VERSION:-5.1}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
EXT_ROOT="${HOME}/Library/Application Support/Blender/${BLENDER_VERSION}/extensions/user_default"
TARGET="${EXT_ROOT}/slide_tools"

if [ ! -x "$BLENDER_BIN" ]; then
    printf 'Blender binary not found: %s\n' "$BLENDER_BIN" >&2
    printf 'Override with BLENDER_BIN=/path/to/blender\n' >&2
    exit 1
fi

if [ ! -f "${REPO_ROOT}/blender_manifest.toml" ] || [ ! -f "${REPO_ROOT}/__init__.py" ]; then
    printf 'This does not look like the Slide Tools extension root: %s\n' "$REPO_ROOT" >&2
    exit 1
fi

mkdir -p "$EXT_ROOT"
if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
    printf 'Replacing existing Slide Tools install: %s\n' "$TARGET"
    rm -rf "$TARGET"
fi
ln -s "$REPO_ROOT" "$TARGET"

printf 'Linked:\n  %s\n→ %s\n\n' "$TARGET" "$REPO_ROOT"
printf 'Enable Slide Tools, then use its sidebar Reload button after edits.\n'
printf 'Restart Blender after RNA property schema changes.\n'
