#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SUPPORTED_VERSIONS=("22.04" "24.04" "26.04")
UBUNTU_VERSION=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    UBUNTU_VERSION="${VERSION_ID:-}"
fi

if [ -n "$UBUNTU_VERSION" ]; then
    SUPPORTED=false
    for v in "${SUPPORTED_VERSIONS[@]}"; do
        [ "$v" = "$UBUNTU_VERSION" ] && SUPPORTED=true
    done
    if [ "$SUPPORTED" = false ]; then
        echo "Attention : Ubuntu $UBUNTU_VERSION n'a pas été testé avec cette application"
        echo "(versions testées : ${SUPPORTED_VERSIONS[*]}). L'installation continue quand même."
        echo
    fi
fi

PACKAGES=(
    python3-dbus
    python3-gi
    gir1.2-glib-2.0
    python3-xlib
    tesseract-ocr
    tesseract-ocr-fra
    tesseract-ocr-eng
    wireplumber
    gstreamer1.0-tools
    gstreamer1.0-pipewire
    gstreamer1.0-plugins-good
)

MISSING=()
for pkg in "${PACKAGES[@]}"; do
    dpkg -s "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
done

if [ "${#MISSING[@]}" -gt 0 ]; then
    echo "Installation des paquets manquants : ${MISSING[*]}"
    sudo apt update
    sudo apt install -y "${MISSING[@]}"
else
    echo "Toutes les dépendances système sont déjà installées."
fi

# python3-pyqt6 n'existe dans les dépôts Ubuntu qu'à partir de la 24.04 — absent
# sur la 22.04 (Jammy). Repli sur pip dans ce cas.
if dpkg -s python3-pyqt6 >/dev/null 2>&1; then
    : # déjà installé
elif apt-cache show python3-pyqt6 >/dev/null 2>&1; then
    echo "Installation de python3-pyqt6..."
    sudo apt update
    sudo apt install -y python3-pyqt6
else
    echo "python3-pyqt6 n'est pas disponible via apt sur cette version d'Ubuntu — installation via pip..."
    PIP_LOG="$(mktemp)"
    if ! python3 -m pip install --user PyQt6 >"$PIP_LOG" 2>&1; then
        if grep -q "externally-managed-environment" "$PIP_LOG"; then
            python3 -m pip install --user --break-system-packages PyQt6
        else
            cat "$PIP_LOG"
            rm -f "$PIP_LOG"
            exit 1
        fi
    fi
    rm -f "$PIP_LOG"
fi

BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$BIN_DIR" "$DESKTOP_DIR"

LAUNCHER="$BIN_DIR/outil-capture-decran"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
cd "$APP_DIR"
exec python3 main.py "\$@"
EOF
chmod +x "$LAUNCHER"

DESKTOP_FILE="$DESKTOP_DIR/outil-capture-decran.desktop"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Outil Capture d'écran
Comment=Capture d'écran, OCR et annotation pour Ubuntu
Exec=$LAUNCHER
Icon=$APP_DIR/data/icons/outil-capture-decran-256.png
Categories=Utility;Graphics;
Terminal=false
EOF

update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

echo
echo "Installation terminée."
echo "L'application \"Outil Capture d'écran\" est disponible dans le menu des applications Ubuntu."
echo "Lancement en ligne de commande : $LAUNCHER"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo
    echo "Remarque : $BIN_DIR n'est pas dans ton PATH. Ajoute cette ligne à ~/.bashrc si tu veux lancer \"outil-capture-decran\" depuis un terminal :"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
