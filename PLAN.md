# Ubuntu Screen Capture Tool — Plan d'implémentation

## Contexte

L'utilisateur veut une alternative Windows Snipping Tool, mais **exclusivement pour Ubuntu**. Trois besoins ont été désignés comme priorité absolue dès le départ : OCR très précis avec copie presse-papiers, sélection libre de zone à la souris pour l'OCR, et enregistrement vidéo limité à une zone (pas plein écran). L'utilisateur a ensuite fourni sa propre spécification complète et détaillée (architecture, stack, modules, arborescence de fichiers, étapes) et a demandé explicitement qu'elle soit respectée telle quelle — ce plan **adopte cette spécification comme socle** et comble uniquement les détails techniques d'implémentation qu'elle laisse ouverts (notamment la gestion Wayland, la machine de dev tournant sous Ubuntu 26.04 / GNOME / **Wayland**, ce qui a des conséquences concrètes sur `mss`/`Xlib`/`ffmpeg`).

Trois livrables ont aussi été demandés explicitement : un **plan**, un **fichier mémoire** (document de spécification/mémoire du projet), et un **schéma** (diagrammes d'architecture). Les trois seront créés lors du scaffolding initial (Étape 1).

## Stack technique (telle que spécifiée par l'utilisateur)

- **Langage** : Python 3
- **GUI** : PyQt6
- **Capture écran** : `mss` + `Xlib` (X11) ; portail `xdg-desktop-portal` (Wayland)
- **OCR** : Tesseract (moteur par défaut) + PaddleOCR (moteur optionnel, plus précis)
- **Vidéo** : FFmpeg
- **Base de données** : SQLite (historique)

### Point technique important : Wayland vs X11

La machine de développement tourne en **session Wayland** (confirmé : `XDG_SESSION_TYPE=wayland`, GNOME). Sous Wayland, `mss` et `Xlib` ne peuvent **pas** capturer l'écran (restriction de sécurité du protocole) — seul le portail `xdg-desktop-portal` le peut. `ffmpeg -f x11grab` ne fonctionne pas non plus sous Wayland. La spec de l'utilisateur liste déjà les trois briques (mss, portal, Xlib) — le plan formalise donc une **couche d'abstraction de capture** qui choisit le bon backend à l'exécution selon `XDG_SESSION_TYPE`, pour que l'app fonctionne aussi bien en session X11 qu'en session Wayland (celle réellement utilisée sur cette machine) sans deux implémentations parallèles à maintenir dans le reste du code.

## Architecture des modules

Arborescence reprise telle que spécifiée par l'utilisateur :

```
screen_capture_tool/
├── main.py
├── ui/
│   ├── window.py          # QMainWindow principale (boutons: Capture, OCR, Vidéo, Historique, Paramètres)
│   └── settings.py        # Fenêtre Paramètres
├── capture/
│   ├── backend.py         # NOUVEAU — détecte X11/Wayland, expose une interface commune
│   ├── screenshot.py       # grab plein écran / fenêtre / rectangle
│   └── selector.py         # overlay PyQt6 plein écran, sélection libre à la souris (rubber-band)
├── ocr/
│   └── ocr_engine.py       # classe OCREngine, moteurs Tesseract (défaut) / PaddleOCR (optionnel)
├── video/
│   └── recorder.py         # pilote ffmpeg (x11grab direct sous X11, pipe rawvideo sous Wayland)
├── clipboard/
│   └── manager.py          # QGuiApplication.clipboard() — texte OCR ou image
├── annotation/
│   └── painter.py          # QPainter sur QPixmap — stylo, rectangle, flèche, texte, surlignage, gomme
├── database/
│   └── history.py          # SQLite : captures(id, type, filename, extracted_text, created_at)
└── config/
    └── settings.json       # dossiers de sortie, moteur OCR/langues par défaut, qualité vidéo, raccourcis
```

### Détails par module

- **`capture/backend.py`** : détecte `XDG_SESSION_TYPE`. `X11Backend` = `mss` pour le grab plein écran/rectangle + `Xlib`/`wmctrl` pour la liste des fenêtres. `WaylandBackend` = appels D-Bus à `org.freedesktop.portal.Screenshot` (capture ponctuelle) et `org.freedesktop.portal.ScreenCast` (session persistante réutilisée pour la vidéo, avec `restore_token` pour éviter de redemander la permission à chaque fois). Capture par fenêtre : simple sous X11 (Xlib/wmctrl), limitée sous Wayland (à documenter comme restriction connue, pas bloquante puisque la priorité est la sélection libre de zone).
- **`capture/selector.py`** : `QWidget` plein écran, sans bordure, translucide, affichant la frame capturée en fond avec un rectangle de sélection dessiné en direct au drag souris. Composant **partagé** entre le flux OCR et le flux vidéo (même interaction, callback différent après sélection). Gère Échap pour annuler.
- **`ocr/ocr_engine.py`** : prétraitement OpenCV (niveaux de gris, inversion auto si thème sombre, upscale conditionnel, seuillage adaptatif, léger padding) avant reconnaissance — c'est ce prétraitement, plus que le choix du moteur, qui a le plus d'impact sur la précision. `TesseractEngine` par défaut (`pytesseract`/`tesserocr`, langues `fra+eng`, `--psm 6` pour un extrait ciblé). `PaddleOCREngine` optionnel, chargé paresseusement si installé, sélectionnable dans Paramètres pour les cas où l'utilisateur veut pousser la précision au maximum. Correction simple des erreurs OCR en option (passe orthographique légère).
- **`clipboard/manager.py`** : `QGuiApplication.clipboard().setText(...)` / `setImage(...)` — fonctionne nativement sous X11 et Wayland via Qt, pas besoin de `wl-copy`.
- **`video/recorder.py`** : sous X11, `ffmpeg -f x11grab -video_size WxH -i :0.0+X,Y -c:v libx264 sortie.mp4` directement sur le rectangle sélectionné. Sous Wayland (le cas réel de cette machine), pas d'équivalent direct : la session `ScreenCast` du portail fournit les frames via PipeWire, qui sont recadrées à la zone choisie puis envoyées en flux `rawvideo` sur l'entrée standard d'un process `ffmpeg -f rawvideo -pix_fmt bgr24 -s WxH -i - -c:v libx264 sortie.mp4`. Contrôlé par une petite fenêtre flottante REC avec bouton Stop.
- **`annotation/painter.py`** : canvas `QWidget` avec la capture en `QPixmap`, barre d'outils (Stylo, Rectangle, Flèche, Texte, Surlignage, Gomme) implémentés en `QPainter`, boutons Enregistrer/Copier.
- **`database/history.py`** : table SQLite `captures(id, type, filename, extracted_text, created_at)`, CRUD simple + liste affichée dans la fenêtre Historique.
- **Raccourcis clavier globaux** (`Ctrl+Maj+S` capture, `Ctrl+Maj+O` OCR direct, `Ctrl+Maj+R` vidéo) : sous Wayland une app ne peut pas capter un raccourci global directement — utiliser `org.freedesktop.portal.GlobalShortcuts` (D-Bus) pour enregistrer les trois actions ; documenter en repli une entrée `custom-keybinding` GNOME pointant vers `main.py --capture/--ocr/--record` pour les cas où le portail ne serait pas disponible.

## Trois livrables demandés

1. **`PLAN.md`** (racine du projet) — version persistée de ce plan.
2. **`MEMOIRE.md`** — document de spécification/mémoire du projet en français : objectifs, priorités, architecture, choix technologiques et justifications, consolidant la spec fournie par l'utilisateur.
3. **`SCHEMA.md`** — diagrammes Mermaid : arborescence des modules, flux OCR (capture → sélection → prétraitement → OCR → presse-papiers), flux vidéo (sélection → session portail/PipeWire → ffmpeg → fichier), wireframe de la fenêtre principale.

## Feuille de route (reprend les étapes de l'utilisateur)

- **Étape 1 — Scaffolding** : arborescence complète (fichiers stubs), `requirements.txt` (PyQt6, mss, python-xlib, pytesseract ou tesserocr, opencv-python, numpy), `main.py` qui lance une fenêtre PyQt6 vide avec les 5 boutons, `PLAN.md`/`MEMOIRE.md`/`SCHEMA.md`, `docs/DEVELOPMENT.md` listant les paquets apt nécessaires (`tesseract-ocr`, `tesseract-ocr-fra`, `ffmpeg`, etc.).
- **Étape 2 — Capture écran** : `capture/backend.py` (détection X11/Wayland), `capture/selector.py` (overlay sélection libre), `capture/screenshot.py` (plein écran, rectangle), sauvegarde PNG. *Soigné en priorité* car c'est le composant partagé par OCR et vidéo.
- **Étape 3 — OCR** : `ocr_engine.py` avec prétraitement + Tesseract, extraction + copie presse-papiers automatique. *Priorité absolue de précision* — ajouter un petit corpus de test (captures représentatives + texte de référence) pour mesurer le taux d'erreur avant de considérer cette étape terminée.
- **Étape 4 — Vidéo** : sélection de zone (réutilise `selector.py`), pilotage ffmpeg selon backend X11/Wayland, boutons Démarrer/Arrêter, export MP4/H264.
- **Étape 5 — Annotation** : `painter.py` avec les 6 outils.
- **Étape 6 — Finalisation** : Paramètres (`ui/settings.py`, `config/settings.json`), raccourcis clavier globaux (portail GlobalShortcuts), packaging/installation Ubuntu (script ou `.desktop`), tests bout-en-bout.

## Vérification

- Étape 1 : `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python3 main.py` doit ouvrir la fenêtre principale sans erreur.
- Étape 2 : sélection à la souris doit produire un rectangle en pixels exacts, vérifié en loggant les coordonnées puis en comparant au PNG sauvegardé.
- Étape 3 : script d'évaluation OCR (taux d'erreur caractère) sur un petit corpus de captures d'écran réelles (VS Code, terminal, navigateur), objectif <2% d'erreur avant de considérer l'étape terminée.
- Étape 4 : enregistrement d'une zone de test, relecture du MP4 généré pour confirmer que seule la zone sélectionnée est présente.
- Étape 6 : test des trois raccourcis clavier en conditions réelles sur la session Wayland de la machine.
