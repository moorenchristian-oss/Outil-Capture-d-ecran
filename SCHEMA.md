# Schéma d'architecture — Ubuntu Screen Capture Tool

## Arborescence des modules

```mermaid
graph TD
    A[Ubuntu Screen Capture Tool] --> UI[Interface graphique - PyQt6]
    A --> CAP[Module Capture écran]
    A --> SEL[Module Sélection zone souris]
    A --> OCR[Module OCR]
    A --> CLIP[Module Presse-papiers]
    A --> VID[Module Vidéo]
    A --> ANN[Module Annotation]
    A --> HIST[Module Historique]
    A --> CFG[Configuration]

    CAP --> CAPX[Backend X11: mss + Xlib]
    CAP --> CAPW[Backend Wayland: xdg-desktop-portal]

    OCR --> OCRT[Moteur Tesseract - défaut]
    OCR --> OCRP[Moteur PaddleOCR - optionnel]

    VID --> VIDF[FFmpeg]

    HIST --> DB[(SQLite)]
```

## Flux 1 — Capture + OCR + presse-papiers (priorité #1 et #2)

```mermaid
flowchart LR
    U[Utilisateur] -->|Raccourci Ctrl+Maj+O ou clic| TRIG[Déclenchement]
    TRIG --> SEL[Sélection libre de zone à la souris]
    SEL --> GRAB[Capture de la zone - backend X11/Wayland]
    GRAB --> PRE[Prétraitement OpenCV\nniveaux de gris, upscale, seuillage adaptatif]
    PRE --> OCR[Reconnaissance Tesseract / PaddleOCR]
    OCR --> CORR[Correction simple des erreurs - optionnel]
    CORR --> CLIP[Copie dans le presse-papiers]
    CLIP --> HIST[(Historique SQLite:\ntexte + date + fichier)]
    CLIP --> NOTIF[Notification: texte copié]
```

## Flux 2 — Enregistrement vidéo d'une zone (priorité #3)

```mermaid
flowchart LR
    U[Utilisateur] -->|Raccourci Ctrl+Maj+R ou clic| TRIG[Déclenchement]
    TRIG --> SEL[Sélection libre de zone à la souris]
    SEL --> START[Démarrer l'enregistrement]
    START --> BACKEND{Session}
    BACKEND -->|X11| FFX[ffmpeg -f x11grab sur la zone]
    BACKEND -->|Wayland| PORTAL[Portail ScreenCast + PipeWire]
    PORTAL --> CROP[Recadrage à la zone sélectionnée]
    CROP --> FFW[ffmpeg - flux rawvideo vers MP4/H264]
    FFX --> STOP[Utilisateur clique Arrêter]
    FFW --> STOP
    STOP --> FILE[Fichier vidéo MP4]
    FILE --> HIST[(Historique SQLite)]
```

## Flux 3 — Capture image simple / annotation

```mermaid
flowchart LR
    U[Utilisateur] --> SEL[Sélection: plein écran / fenêtre / rectangle]
    SEL --> IMG[Image PNG]
    IMG --> CHOICE{Action}
    CHOICE -->|Annoter| ANN[Éditeur d'annotation\nstylo, rectangle, flèche, texte, surlignage, gomme]
    CHOICE -->|Copier| CLIP[Presse-papiers]
    CHOICE -->|Enregistrer| SAVE[Fichier PNG]
    ANN --> SAVE
    SAVE --> HIST[(Historique SQLite)]
```

## Wireframe — Fenêtre principale

```
+--------------------------------+
|  Ubuntu Screen Capture         |
|                                 |
|  [ Capture Image ]              |
|  [ OCR Texte ]                  |
|  [ Enregistrer Vidéo ]          |
|  [ Historique ]                 |
|  [ Paramètres ]                 |
+--------------------------------+
```

## Voir aussi

- [PLAN.md](PLAN.md) — plan d'implémentation par étapes.
- [MEMOIRE.md](MEMOIRE.md) — objectifs, priorités et justification des choix techniques.
