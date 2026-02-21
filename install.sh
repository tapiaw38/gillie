#!/usr/bin/env bash
set -e

PYTHON=${PYTHON:-python3}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      Gillie ✨🐟 Install             ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Check Python version ──────────────────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: '$PYTHON' not found. Install Python 3.10+ first."
    exit 1
fi

PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

if ! "$PYTHON" -c "import sys; assert sys.version_info >= (3,10), ''" 2>/dev/null; then
    echo "ERROR: Python 3.10+ required (found $PYTHON_VERSION)"
    echo "       Set PYTHON=/path/to/python3.10 to override"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"

# ── System dependencies check (optional) ─────────────────────────────────────
echo ""
echo "Checking optional system dependencies..."

check_dep() {
    if command -v "$1" &>/dev/null; then
        echo "  ✓ $1"
    else
        echo "  ⚠ $1 not found (optional: $2)"
    fi
}

check_dep docker          "needed for ./gillie db start"
check_dep tesseract       "needed for PDF OCR processing"
check_dep ffmpeg          "needed for audio processing (TTS/STT)"

# ── Virtual environment ───────────────────────────────────────────────────────
echo ""
cd "$SCRIPT_DIR"

if [ -d ".venv" ]; then
    echo "✓ Virtual environment exists (.venv)"
    CREATED_VENV=false
else
    echo "Creating virtual environment..."
    "$PYTHON" -m venv .venv
    echo "✓ Virtual environment created (.venv)"
    CREATED_VENV=true
fi

source .venv/bin/activate

# ── Install dependencies ──────────────────────────────────────────────────────
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip -q

# Read packages from requirements.txt (skip empty lines and comments)
packages=()
while IFS= read -r line; do
    line="${line%%#*}"         # strip inline comments
    line="${line// /}"        # strip spaces
    [[ -z "$line" ]] && continue
    packages+=("$line")
done < "$SCRIPT_DIR/requirements.txt"

total=${#packages[@]}
current=0
failed=()
BAR_WIDTH=30

print_bar() {
    local current=$1 total=$2 pkg=$3
    local pct=$(( current * 100 / total ))
    local filled=$(( current * BAR_WIDTH / total ))
    local bar="" empty=""
    for ((i=0; i<filled; i++));          do bar+="█"; done
    for ((i=filled; i<BAR_WIDTH; i++));  do empty+="░"; done
    printf "\r  [%s%s] %3d%% (%d/%d) %-28s" "$bar" "$empty" "$pct" "$current" "$total" "${pkg:0:28}"
}

for pkg in "${packages[@]}"; do
    current=$(( current + 1 ))
    print_bar "$current" "$total" "$pkg"
    if ! pip install "$pkg" -q --disable-pip-version-check 2>/dev/null; then
        failed+=("$pkg")
    fi
done

# Final bar at 100%
print_bar "$total" "$total" "done"
echo ""
echo ""

if [ ${#failed[@]} -gt 0 ]; then
    echo "⚠ Some packages failed to install:"
    for pkg in "${failed[@]}"; do
        echo "  ✗ $pkg"
    done
    echo ""
fi

echo "✓ Dependencies installed ($total packages)"

# ── Make CLI executable ───────────────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/gillie"
echo "✓ CLI script ready (./gillie)"

# ── Add to PATH ───────────────────────────────────────────────────────────────
echo ""
echo "Do you want to add 'gillie' to your PATH so you can run it from anywhere?"
echo "  1) zsh  (~/.zshrc)"
echo "  2) bash (~/.bashrc)"
echo "  3) Skip"
echo ""
printf "Choose [1/2/3]: "
read SHELL_CHOICE

EXPORT_LINE="export PATH=\"$SCRIPT_DIR:\$PATH\""

case "$SHELL_CHOICE" in
    1)
        RC_FILE="$HOME/.zshrc"
        if grep -qF "$SCRIPT_DIR" "$RC_FILE" 2>/dev/null; then
            echo "✓ PATH already set in $RC_FILE"
        else
            echo "" >> "$RC_FILE"
            echo "# Gillie CLI" >> "$RC_FILE"
            echo "$EXPORT_LINE" >> "$RC_FILE"
            echo "✓ Added to $RC_FILE"
            echo ""
            echo "  Run: source ~/.zshrc"
            echo "  Or open a new terminal, then use: gillie"
        fi
        ;;
    2)
        RC_FILE="$HOME/.bashrc"
        if grep -qF "$SCRIPT_DIR" "$RC_FILE" 2>/dev/null; then
            echo "✓ PATH already set in $RC_FILE"
        else
            echo "" >> "$RC_FILE"
            echo "# Gillie CLI" >> "$RC_FILE"
            echo "$EXPORT_LINE" >> "$RC_FILE"
            echo "✓ Added to $RC_FILE"
            echo ""
            echo "  Run: source ~/.bashrc"
            echo "  Or open a new terminal, then use: gillie"
        fi
        ;;
    *)
        echo "  Skipped. You can run the CLI with: ./gillie"
        ;;
esac

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Installation complete!                                  ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Next steps:                                             ║"
echo "║                                                          ║"
echo "║  1. Configure:  gillie init                              ║"
echo "║  2. Start DB:   gillie db start                          ║"
echo "║  3. Start API:  gillie start                             ║"
echo "║                                                          ║"
echo "║  Run as daemon:                                          ║"
echo "║     gillie service install                               ║"
echo "║     gillie service start                                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
