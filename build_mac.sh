#!/usr/bin/env bash
# ============================================================
#  Video Downloader — macOS Build Script
#  Run this script ONCE on the Mac to generate the .app file.
#  Usage: bash build_mac.sh
# ============================================================
set -e

BOLD="\033[1m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
RESET="\033[0m"

info()    { echo -e "${BOLD}==> $*${RESET}"; }
success() { echo -e "${GREEN}✅  $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠️   $*${RESET}"; }
error()   { echo -e "${RED}❌  $*${RESET}"; exit 1; }

# ── 1. Require Python 3.9+ ────────────────────────────────────────────────────
info "Checking Python 3…"
if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Download it from https://www.python.org/downloads/ and try again."
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]); then
    error "Python 3.9 or newer is required (found $PY_VER). Download from https://www.python.org/downloads/"
fi
success "Python $PY_VER found."

# ── 2. Install Homebrew (if missing) ──────────────────────────────────────────
info "Checking Homebrew…"
if ! command -v brew &>/dev/null; then
    warn "Homebrew not found. Installing now (this may take a few minutes)…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon Macs
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi
success "Homebrew ready."

# ── 3. Install ffmpeg ─────────────────────────────────────────────────────────
info "Checking ffmpeg…"
if ! command -v ffmpeg &>/dev/null; then
    info "Installing ffmpeg via Homebrew…"
    brew install ffmpeg
fi

FFMPEG_PATH=$(command -v ffmpeg)
success "ffmpeg found at: $FFMPEG_PATH"

# ── 4. Install Node.js ────────────────────────────────────────────────────────
info "Checking Node.js…"
if ! command -v node &>/dev/null; then
    info "Installing Node.js via Homebrew…"
    brew install node
fi

NODE_PATH=$(command -v node)
success "Node.js found at: $NODE_PATH"

# ── 5. Set up Python virtual environment ─────────────────────────────────────
info "Setting up Python virtual environment…"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
success "Virtual environment ready."

# ── 6. Install Python dependencies ────────────────────────────────────────────
info "Installing Python dependencies (yt-dlp, pyinstaller)…"
pip install -r requirements.txt --quiet
success "Dependencies installed."

# ── 7. Build the .app with PyInstaller ───────────────────────────────────────
info "Building the macOS .app bundle (this will take a minute)…"

APP_NAME="Video Downloader"
ICON_ARG=""
if [ -f "app_icon.icns" ]; then
    ICON_ARG="--icon=app_icon.icns"
fi

pyinstaller \
    --name "$APP_NAME" \
    --windowed \
    --noconfirm \
    --clean \
    --onedir \
    --add-binary "$FFMPEG_PATH:." \
    $ICON_ARG \
    downloader.py

# ── 8. Done ───────────────────────────────────────────────────────────────────
APP_PATH="$(pwd)/dist/${APP_NAME}.app"

echo ""
echo "============================================================"
success "Build complete!"
echo ""
echo -e "  📦  App location:"
echo -e "      ${BOLD}$APP_PATH${RESET}"
echo ""
echo -e "  Next steps:"
echo -e "  1. Open Finder and go to the ${BOLD}dist/${RESET} folder"
echo -e "  2. Drag ${BOLD}\"Video Downloader.app\"${RESET} to your Applications folder"
echo -e "  3. On first launch, right-click → Open (to bypass Gatekeeper)"
echo "============================================================"
