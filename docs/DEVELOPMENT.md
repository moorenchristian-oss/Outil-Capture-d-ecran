# Installation et développement — Outil Capture d'écran

## Installation (utilisateur)

Depuis le dossier du projet :

```bash
./install.sh
```

Ce script installe les paquets système manquants (via `apt`, avec une demande de mot de passe si nécessaire), puis ajoute "Outil Capture d'écran" au menu des applications Ubuntu (avec son icône) et crée un lanceur en ligne de commande (`~/.local/bin/outil-capture-decran`). Il est sûr à relancer plusieurs fois : il ne réinstalle que ce qui manque.

## Dépendances système (apt)

Installées automatiquement par `install.sh` :

- `python3-pyqt6` — interface graphique
- `python3-dbus`, `python3-gi`, `gir1.2-glib-2.0` — appels au portail Wayland (capture d'écran)
- `python3-xlib` — capture d'écran en session X11 (repli, la machine cible est Wayland par défaut)
- `tesseract-ocr`, `tesseract-ocr-fra`, `tesseract-ocr-eng` — reconnaissance de texte (OCR)
- `wireplumber` — coupe le son du déclencheur pendant la capture (`wpctl`)

Aucun environnement virtuel Python n'est utilisé : l'application tourne avec le Python système et ces paquets apt (l'environnement est "externally managed", `pip`/`venv` ne sont pas nécessaires).

## Lancer l'application (développement)

```bash
cd "Outil Capture d'écran"
python3 main.py
```

## Session Wayland vs X11

```bash
echo $XDG_SESSION_TYPE
```

- `wayland` (cas de cette machine) : `capture/backend.py` passe par `xdg-desktop-portal` (D-Bus) pour la capture d'écran.
- `x11` : `capture/backend.py` utilise `python3-xlib` via la bibliothèque `mss` (à installer séparément si besoin : `pip install --user mss --break-system-packages`, aucun paquet apt officiel).

## Note : terminal intégré VS Code (installation snap)

Si VS Code est installé en snap, son terminal intégré exporte des variables (`GTK_PATH`, `GTK_EXE_PREFIX`, `GDK_PIXBUF_MODULE_FILE`, `SNAP`, etc.) qui pointent vers les bibliothèques du snap et provoquent un conflit de version (`symbol lookup error … libpthread.so.0`) au lancement d'une app Qt/GTK. Ce problème n'existe **pas** en dehors de VS Code (lancement normal depuis le menu des applications ou un terminal système). Contournement pour développer depuis le terminal intégré VS Code :

```bash
env -u GTK_PATH -u GTK_EXE_PREFIX -u GDK_PIXBUF_MODULE_FILE -u GDK_PIXBUF_MODULEDIR \
    -u GTK_IM_MODULE_FILE -u GIO_MODULE_DIR -u GSETTINGS_SCHEMA_DIR -u LOCPATH \
    -u SNAP -u SNAP_LIBRARY_PATH python3 main.py
```

## Voir aussi

- [../PLAN.md](../PLAN.md)
- [../MEMOIRE.md](../MEMOIRE.md)
- [../SCHEMA.md](../SCHEMA.md)
