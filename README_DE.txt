SplatTricia 1.1
=================

SplatTricia ist ein lokales Windows-Werkzeug zur automatischen Konvertierung
einzelner 2D-Bilder oder ganzer Bildordner in Stereo-3D. Aus jedem Bild werden
ein paralleles Side-by-Side-Stereobild (SBS) und wahlweise eine Farb- oder
Graustufen-Anaglyphe erzeugt.

Die 3D-Rekonstruktion basiert auf Apple SHARP. SplatTricia verarbeitet Bilder
lokal, führt keine automatischen Modell-Downloads durch und benötigt für die
Benutzung keine Cloud oder Online-Verbindung.

Voraussetzungen
---------------
- Windows 10 oder 11
- kompatible NVIDIA-Grafikkarte mit aktuellem Treiber
- lokal bereitgestellter SHARP-Checkpoint:

    models\sharp_2572gikvuh.pt

Der SHARP-Checkpoint ist nicht Bestandteil von SplatTricia und muss vom Nutzer
selbst im Ordner models bereitgestellt werden. Für das Modell gelten Apples
Lizenzbedingungen; siehe LICENSES.txt.

Bedienung
---------
1. Einzelbild oder Bildordner auswählen.
2. Ausgabe beim Input oder einen eigenen Ausgabeordner festlegen.
3. Gewünschte Deviation und Scheinfensterlage einstellen.
4. Bei Bedarf Floating-Window-Vorhänge setzen.
5. Farb- oder Graustufen-Anaglyphe wählen.
6. „Start“ anklicken.

Stereo-Einstellungen
--------------------
Deviation bestimmt die horizontale Tiefenausdehnung der erzeugten Stereoszene.
Die Scheinfensterlage legt fest, wie diese Tiefe relativ zur Bildebene verteilt
wird. Der zusätzliche Scheinfenster-Rückversatz steht nur bei einer
Scheinfensterlage von 100 % zur Verfügung. Floating-Window-Vorhänge maskieren
Randbereiche, ohne die Geometrie der Szene selbst zu verändern.

Automatische 2D-zu-3D-Konvertierung bleibt eine geometrische Schätzung. Für
Projektion oder andere anspruchsvolle Anwendungen sollten Deviation,
Scheinfensterlage und Bildränder deshalb visuell kontrolliert werden.

Ausgabe
-------
Im verwendeten Ausgabeordner entstehen:

- sbs: parallele Side-by-Side-Stereobilder
- anaglyph: Farb- oder Graustufen-Anaglyphen
- _temp: zwischengespeicherte PLY-Punktwolken und Prüfdaten

Gültige PLY-Dateien können wiederverwendet werden. Dadurch lassen sich
Stereo-Einstellungen schnell neu rendern, ohne SHARP erneut auszuführen.
„Temporäre Dateien löschen“ entfernt nur _temp; fertige Bilder bleiben erhalten.

Vorhandene Ausgabebilder werden ohne Rückfrage ersetzt. Mit „Dateiname um
Einstellungen ergänzen“ können bewusst erzeugte Varianten nebeneinander
erhalten bleiben.

Metadaten
---------
Soweit technisch möglich, übernimmt SplatTricia die Metadaten geeigneter
Quelldateien in die fertigen JPEG-Ausgaben. Die Bildorientierung wird bereits
bei der Verarbeitung berücksichtigt.

Source Code und Nachhaltigkeit
------------------------------
Der portable Ordner enthält unter source den zu dieser Version gehörenden
SplatTricia-Quellstand, Build-Hinweise und eine Release-Checkliste. Damit sollen
Funktionsweise, Wartung und spätere Weiterentwicklung nachvollziehbar bleiben.
Der von Christoph Müller erstellte SplatTricia-Quellcode und die eigene
Dokumentation stehen unter der MIT-Lizenz. Drittanbieter-Komponenten und SHARP
unterliegen weiterhin ausschließlich ihren jeweiligen eigenen Lizenzen.

Lizenzen
--------
LICENSE.txt enthält die MIT-Lizenz für SplatTricia selbst. LICENSES.txt enthält
die Lizenzbedingungen und Hinweise zu SHARP und den verwendeten
Drittanbieter-Komponenten.

Fehlerprotokoll
---------------
Bei technischen Fehlern schreibt SplatTricia Details in splattricia_error.log
neben die EXE.

Zusätzliche Ausgaben in 1.1

- Tiefenkarte als PNG speichern: relative inverse Tiefe mit 16 Bit, hell nah/dunkel fern, aus der ursprünglichen mittigen Perspektive. Ablage unter depth_maps, in den Pixelmaßen des verarbeiteten Einzelbildes. Stereoregler und Vorhänge verändern die Karte nicht.
- Wiggle-Animation speichern: Ablage unter wiggle. Einstellungen… öffnet den Dialog in Programmfarben für Format, maximale Bildgröße, Bildrate und Zyklusdauer. Bildgröße und Bildrate werden je Format gespeichert; die Zyklusdauer gilt für alle Formate.
- MP4: H.264 CRF18/slow, 8 Bit und 4:2:0, 30/60 fps, maximal 720/1080/2160 Pixel Bildhöhe, fünf Zyklen.
- WebP: Qualität 85, 30/60 fps, maximal 720/1080/2160 Pixel Bildhöhe (Standard 1080p/30 fps), Endlosschleife.
- AVIF: Qualität 60, 4:4:4, gleiche Größen/Bildraten und Standard 1080p/30 fps, Endlosschleife.
- GIF: 10/15/20/25 fps (Standard: 15 fps), standardmäßig maximal 800 Pixel lange Seite, Endlosschleife.
- PNG-Bildfolge: 30/60 fps, maximal 1080/2160 Pixel Bildhöhe, ein nummerierter Zyklus je Ausgangsbild.

Ein Zyklus dauert standardmäßig zwei Sekunden. Kleinere Bilder werden nicht vergrößert. Wiggle verwendet die vorhandene Deviation/Scheinfensterlage und den PLY-Cache; Floating-Window-Vorhänge werden nicht übernommen. Beide zusätzlichen Ausgaben sind zunächst ausgeschaltet.


Einrichtung: Alle drei 1.1-ZIPs in denselben Ordner entpacken. Siehe INSTALLATION.txt.
