#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PACKAGES=(
    python3-pyqt6
    python3-dbus
    python3-gi
    gir1.2-glib-2.0
    python3-xlib
    tesseract-ocr
    tesseract-ocr-fra
    tesseract-ocr-eng
    wireplumber
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
