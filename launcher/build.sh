#!/usr/bin/env bash
# Build /Applications/fonliman.app from the AppleScript template.
#
# Run this once after cloning, or whenever the project path changes
# (e.g. you moved the repo to a different folder).
#
#   bash launcher/build.sh
#
# Result: Spotlight-searchable "fonliman" app at /Applications/fonliman.app.
# Double-clicking it starts Docker Desktop (if needed), brings the container
# up, waits for the API, and opens http://localhost:8765 in your browser.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHER_DIR="$REPO_ROOT/launcher"

cd "$LAUNCHER_DIR"

# 1) Substitute project path into the AppleScript template.
sed "s|PROJECT_PATH_PLACEHOLDER|$REPO_ROOT|g" \
  fonliman.applescript > fonliman.compiled.applescript

# 2) Compile to an .app bundle.
rm -rf fonliman.app
osacompile -o fonliman.app fonliman.compiled.applescript

# 3) Set bundle metadata so Spotlight surfaces a clean name/version.
INFO="$LAUNCHER_DIR/fonliman.app/Contents/Info.plist"
defaults write "$INFO" CFBundleIdentifier      io.fonliman.launcher
defaults write "$INFO" CFBundleName            fonliman
defaults write "$INFO" CFBundleDisplayName     fonliman
defaults write "$INFO" CFBundleShortVersionString 0.1.1

# 4) Install the icon if it exists (build.sh doesn't render — see README).
if [ -f "$LAUNCHER_DIR/fonliman.icns" ]; then
  cp "$LAUNCHER_DIR/fonliman.icns" \
     "$LAUNCHER_DIR/fonliman.app/Contents/Resources/applet.icns"
fi

# 5) Copy to /Applications and refresh LaunchServices so Spotlight sees it.
rm -rf /Applications/fonliman.app
cp -R "$LAUNCHER_DIR/fonliman.app" /Applications/fonliman.app
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  -f /Applications/fonliman.app

echo "✓ /Applications/fonliman.app installed"
echo "  Cmd+Space → 'fonliman' → Enter"
