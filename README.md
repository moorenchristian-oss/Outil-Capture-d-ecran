<p align="center">
  <img src="data/icons/outil-capture-decran-128.png" alt="Icône Outil Capture d'écran" width="96">
</p>

<h1 align="center">Outil Capture d'écran</h1>

<p align="center">
  Un outil de capture d'écran pour Ubuntu, inspiré de l'Outil Capture d'écran de Windows :
  sélection de zone à la souris, OCR avec sélection de texte directement sur l'image, et annotation.
</p>

## Fonctionnalités

- **Capture d'écran** en session X11 ou Wayland (portail `xdg-desktop-portal`), avec sélection de zone à la souris avant la prise de vue, ou capture plein écran.
- **OCR (reconnaissance de texte)** via Tesseract : le texte détecté peut être sélectionné directement sur l'image avec la souris, puis copié (`Ctrl+C` ou clic droit).
- **Annotation** de la capture : stylet, surligneur, gomme, rectangle, ellipse.
- **Copier / Enregistrer** la capture annotée en PNG.
- **Coupure du son du déclencheur** pendant la capture, activable via un bouton coulissant dans la barre d'outils.

## Installation (Ubuntu)

```bash
git clone <url-du-dépôt>
cd "Outil Capture d'écran"
./install.sh
```

Le script installe les paquets système manquants via `apt` (avec demande de mot de passe si nécessaire), ajoute "Outil Capture d'écran" au menu des applications Ubuntu avec son icône, et crée un lanceur en ligne de commande (`~/.local/bin/outil-capture-decran`). Il est sûr à relancer plusieurs fois.

Détails des dépendances et du lancement en mode développement : voir [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Utilisation

1. Cliquer sur **Nouveau** (ou choisir un mode dans le menu **Mode**).
2. Sélectionner la zone à capturer à la souris (sauf en mode Plein écran).
3. Annoter, copier, enregistrer ou lancer l'OCR sur la capture depuis la barre d'outils.

## Structure du projet

```
main.py              Point d'entrée de l'application
ui/                   Fenêtre principale, sélection OCR, widgets (PyQt6)
capture/              Capture d'écran (X11 / portail Wayland), sélecteur de zone, son
ocr/                  Moteur OCR (Tesseract)
annotation/           Outils de dessin sur la capture (QPainter)
clipboard/            Presse-papiers (texte / image)
database/             Historique des captures (SQLite)
data/icons/           Icône de l'application et icônes de la barre d'outils
```

Voir aussi [PLAN.md](PLAN.md), [MEMOIRE.md](MEMOIRE.md) et [SCHEMA.md](SCHEMA.md) pour le détail de l'architecture.

## Licence

Distribué sous licence MIT — voir [LICENSE](LICENSE).
