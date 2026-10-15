# SplatTricia 1.1 — Testversion

Dieser Zweig enthält die Testversion 1.1. Die [stabile 1.0](https://github.com/muelli1975/SplatTricia/releases/tag/v1.0) bleibt verfügbar.

[English documentation](README.md)

SplatTricia ist ein lokales Windows-Werkzeug zur automatischen Konvertierung einzelner 2D-Bilder oder ganzer Bildordner in Stereo-3D. Aus jedem Bild werden ein paralleles Side-by-Side-Stereobild (SBS) und wahlweise eine Farb- oder Graustufen-Anaglyphe erzeugt.

Die 3D-Rekonstruktion basiert auf **Apple SHARP**. SplatTricia verarbeitet Bilder lokal, führt keine automatischen Modell-Downloads durch und benötigt für die Benutzung keine Cloud oder Online-Verbindung.

[![SplatTricia 1.0](docs/screenshots/SplatTricia.png)](docs/screenshots/SplatTricia.png)

## Voraussetzungen

- Windows 10 oder 11
- kompatible NVIDIA-Grafikkarte mit aktuellem Treiber
- lokal bereitgestellter SHARP-Checkpoint unter `models\sharp_2572gikvuh.pt`

Der SHARP-Checkpoint ist **nicht Bestandteil von SplatTricia** und wird in diesem Repository nicht bereitgestellt. Für das Modell gelten Apples eigene Lizenzbedingungen.

## Bedienung

1. Einzelbild oder Bildordner auswählen.
2. Ausgabe beim Input oder einen eigenen Ausgabeordner festlegen.
3. Gewünschte Deviation und Scheinfensterlage einstellen.
4. Bei Bedarf Floating-Window-Vorhänge setzen.
5. Farb- oder Graustufen-Anaglyphe wählen.
6. **Start** anklicken.

## Stereo-Einstellungen

Die **Deviation** bestimmt die horizontale Tiefenausdehnung der erzeugten Stereoszene. Die **Scheinfensterlage** legt fest, wie diese Tiefe relativ zur Bildebene verteilt wird. Der zusätzliche Scheinfenster-Rückversatz steht nur bei einer Scheinfensterlage von 100 % zur Verfügung. **Floating-Window-Vorhänge** maskieren Randbereiche, ohne die Geometrie der Szene selbst zu verändern.

Automatische 2D-zu-3D-Konvertierung bleibt eine geometrische Schätzung. Für Projektion oder andere anspruchsvolle Anwendungen sollten Deviation, Scheinfensterlage und Bildränder deshalb visuell kontrolliert werden.

## Zusätzliche Ausgaben in 1.1

- **Tiefenkarte als PNG speichern:** relative inverse Tiefe mit 16 Bit, hell nah/dunkel fern, aus der ursprünglichen mittigen Perspektive. Ablage unter `depth_maps`, in den Pixelmaßen des verarbeiteten Einzelbildes. Stereoregler und Vorhänge verändern die Karte nicht.
- **Wiggle-Animation speichern:** Ablage unter `wiggle`. **Einstellungen…** öffnet den Dialog in Programmfarben für Format, maximale Bildgröße, Bildrate und Zyklusdauer. Bildgröße und Bildrate werden je Format gespeichert; die Zyklusdauer gilt für alle Formate.
- MP4: H.264 CRF18/slow, 8 Bit und 4:2:0, 30/60 fps, maximal 1080/2160 Pixel Bildhöhe, fünf Zyklen.
- GIF: 10/20/25 fps, standardmäßig maximal 800 Pixel lange Seite, Endlosschleife.
- PNG-Bildfolge: 30/60 fps, maximal 1080/2160 Pixel Bildhöhe, ein nummerierter Zyklus je Ausgangsbild.

Ein Zyklus dauert standardmäßig zwei Sekunden. Kleinere Bilder werden nicht vergrößert. Wiggle verwendet die vorhandene Deviation/Scheinfensterlage und den PLY-Cache; Floating-Window-Vorhänge werden nicht übernommen. Beide zusätzlichen Ausgaben sind zunächst ausgeschaltet.

## Ausgabe

Im verwendeten Ausgabeordner entstehen:

- `sbs`: parallele Side-by-Side-Stereobilder
- `anaglyph`: Farb- oder Graustufen-Anaglyphen
- `_temp`: zwischengespeicherte PLY-Punktwolken und Prüfdaten

Gültige PLY-Dateien können wiederverwendet werden. Dadurch lassen sich Stereo-Einstellungen schnell neu rendern, ohne SHARP erneut auszuführen. **Temporäre Dateien löschen** entfernt nur `_temp`; fertige Bilder bleiben erhalten.

Vorhandene Ausgabebilder werden ohne Rückfrage ersetzt. Mit **Dateiname um Einstellungen ergänzen** können bewusst erzeugte Varianten nebeneinander erhalten bleiben.

Soweit technisch möglich, übernimmt SplatTricia die Metadaten geeigneter Quelldateien in die fertigen JPEG-Ausgaben.

## Source Code und Nachhaltigkeit

Dieses Repository enthält den SplatTricia-Quellcode sowie Build-Hinweise, eine Release-Checkliste und die dokumentierten Gestaltungs-, Zustands- und Ordnerregeln. Damit sollen Funktionsweise und spätere Weiterentwicklung für die Stereo-Community nachvollziehbar bleiben.

Aktive Betreuung, Support, die Bearbeitung von Issues oder die Prüfung von Pull Requests können nicht zugesichert werden.

Der von Christoph Müller erstellte SplatTricia-Quellcode und die eigene Dokumentation stehen unter der **MIT-Lizenz**. SHARP und alle weiteren Drittanbieter-Komponenten unterliegen weiterhin ausschließlich ihren jeweiligen eigenen Lizenzen.

## Windows-Download und Einrichtung

Alle drei ZIP-Dateien aus dem [Release SplatTricia 1.1](https://github.com/muelli1975/SplatTricia/releases/tag/v1.1-preview1) herunterladen:

- `SplatTricia_1.1.zip` — Programm, Werkzeuge, Dokumentation und Lizenzen
- `SplatTricia_1.1_Runtime_1.zip` — Laufzeitbibliotheken, Teil 1
- `SplatTricia_1.1_Runtime_2.zip` — Laufzeitbibliotheken, Teil 2

1. **Jedes ZIP in denselben Zielordner entpacken** und die Inhalte des gemeinsamen Unterordners `SplatTricia` zusammenführen. Die ZIPs nicht in getrennte Ordner mit den jeweiligen Archivnamen entpacken.
2. Den SHARP-Checkpoint selbst von [Apples offizieller Projektseite](https://github.com/apple-aiml-research/ml-sharp) beziehen. Vor dem Download Apples Modellbedingungen lesen und akzeptieren.
3. `sharp_2572gikvuh.pt` unter `SplatTricia\models` ablegen.
4. `SplatTricia\SplatTricia.exe` starten.

Alle Laufzeitbibliotheken sind enthalten. Python, CUDA-Toolkit und Build-Werkzeuge müssen nicht separat installiert werden. Nach der Einrichtung funktioniert die Verarbeitung offline.

Die nativen Laufzeitbibliotheken werden aus der 1.0 übernommen. Diese Testversion wartet noch auf die Sichtprüfung der Ergebnisse auf einer NVIDIA-GPU. `SplatTricia_1.1_SHA256SUMS.txt` enthält die Prüfsummen aller drei ZIPs.
