# SplatTricia 1.0

[English documentation](README.md)

SplatTricia ist ein lokales Windows-Werkzeug zur automatischen Konvertierung einzelner 2D-Bilder oder ganzer Bildordner in Stereo-3D. Aus jedem Bild werden ein paralleles Side-by-Side-Stereobild (SBS) und wahlweise eine Farb- oder Graustufen-Anaglyphe erzeugt.

Die 3D-Rekonstruktion basiert auf **Apple SHARP**. SplatTricia verarbeitet Bilder lokal, führt keine automatischen Modell-Downloads durch und benötigt für die Benutzung keine Cloud oder Online-Verbindung.

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

Fertige Windows-Pakete werden unter **GitHub Releases** veröffentlicht.
