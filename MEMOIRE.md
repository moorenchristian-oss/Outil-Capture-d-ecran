# Mémoire du projet — Ubuntu Screen Capture Tool

## Objectif général

Créer une application native Ubuntu, comparable au Snipping Tool de Windows, mais **exclusivement pour Ubuntu**. Rapide, locale (pas de dépendance cloud), simple d'usage : un raccourci clavier, une sélection de zone à la souris, un résultat immédiatement disponible.

## Priorités absolues du projet

Trois fonctionnalités ont été désignées dès le départ comme **essentielles et prioritaires**, à soigner en premier tant sur la précision que sur la simplicité d'usage :

1. **OCR de haute précision** — reconnaissance de caractères et de texte avec une excellente précision, pour copier/coller facilement le texte reconnu à partir d'images ou de captures d'écran.
2. **Sélection libre à la souris pour l'OCR** — dessiner librement une zone à l'écran, en extraire le texte détecté, et le copier directement dans le presse-papiers.
3. **Enregistrement vidéo d'une zone** — enregistrer une vidéo limitée à une zone sélectionnée de l'écran, et non l'écran entier.

Les autres fonctionnalités (capture plein écran/fenêtre, annotation, historique, raccourcis, paramètres) complètent l'outil mais ne doivent pas retarder le soin apporté à ces trois priorités.

## Périmètre fonctionnel complet

- **Capture écran** : plein écran, fenêtre, rectangle, sélection libre à la souris → image PNG.
- **OCR** : lecture du texte dans une image, détection des caractères, reconnaissance multilingue (français + anglais par défaut), correction simple des erreurs, copie automatique dans le presse-papiers.
- **Presse-papiers** : copie automatique du texte OCR ou de l'image, collage compatible avec LibreOffice, navigateur, terminal, éditeur de texte.
- **Vidéo** : sélection de zone → démarrer/arrêter l'enregistrement → export MP4/H264.
- **Annotation** : stylo, rectangle, flèche, texte, surlignage, gomme.
- **Historique** : stockage local (SQLite) des captures images, textes OCR et vidéos, avec date, nom de fichier, texte extrait.
- **Raccourcis clavier** : Ctrl+Maj+S (capture écran), Ctrl+Maj+O (OCR direct), Ctrl+Maj+R (enregistrement vidéo).
- **Configuration** : dossiers de sortie, moteur/langues OCR par défaut, qualité vidéo, raccourcis.

## Choix technologiques et justification

| Domaine | Choix | Pourquoi |
|---|---|---|
| Langage | Python 3 | Développement rapide, écosystème riche (OpenCV, Tesseract, PyQt, ffmpeg via subprocess) |
| Interface graphique | PyQt6 | Toolkit mature, complet (widgets, QPainter pour l'annotation, QClipboard multiplateforme X11/Wayland) |
| Capture écran | `mss` + `Xlib` (X11), `xdg-desktop-portal` (Wayland) | Nécessaire car la machine de développement tourne sous **Wayland**, où `mss`/`Xlib` ne peuvent pas capturer l'écran — le portail est la seule voie possible sous Wayland |
| OCR | Tesseract (défaut) + PaddleOCR (optionnel) | Tesseract : gratuit, hors-ligne, rapide. PaddleOCR : option pour pousser la précision plus loin sur les cas difficiles |
| Vidéo | FFmpeg | Standard de fait pour l'encodage vidéo ; pilotage direct sous X11 (`x11grab`), via flux de frames sous Wayland (portail + PipeWire) |
| Base de données | SQLite | Légère, locale, aucun serveur à gérer, adaptée à un historique personnel |

## Contrainte technique clé : Wayland

La machine de développement (Ubuntu 26.04 LTS, GNOME) tourne en **session Wayland**. Sous Wayland :
- `mss` et `Xlib` ne peuvent pas capturer l'écran directement (restriction de sécurité du protocole).
- `ffmpeg -f x11grab` ne fonctionne pas.
- Toute capture (image ou vidéo) doit passer par `xdg-desktop-portal` (`org.freedesktop.portal.Screenshot` / `org.freedesktop.portal.ScreenCast` + PipeWire).
- Les raccourcis clavier globaux ne peuvent pas être captés directement par l'application — il faut passer par le portail `org.freedesktop.portal.GlobalShortcuts`.

L'application détecte donc la session active (`XDG_SESSION_TYPE`) et choisit le bon backend de capture, afin de fonctionner aussi bien sous X11 que sous Wayland sans dupliquer la logique métier (OCR, annotation, historique, etc.).

## Voir aussi

- [PLAN.md](PLAN.md) — plan d'implémentation détaillé, feuille de route par étapes.
- [SCHEMA.md](SCHEMA.md) — diagrammes d'architecture et de flux.
