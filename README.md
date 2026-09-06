# SplatTricia 1.0

SplatTricia ist ein lokales Windows-Werkzeug zur experimentellen Konvertierung einzelner 2D-Bilder oder ganzer Bildordner in Stereo-3D. Aus jedem Bild werden ein paralleles Side-by-Side-Stereobild (SBS) und wahlweise eine Farb- oder Graustufen-Anaglyphe erzeugt.

Die 3D-Rekonstruktion basiert auf **Apple SHARP**. SplatTricia verarbeitet Bilder lokal, führt keine automatischen Modell-Downloads durch und benötigt für die Benutzung keine Cloud oder Online-Verbindung.

**English documentation:** [README_EN.txt](README_EN.txt)

## Voraussetzungen

- Windows 10 oder 11
- kompatible NVIDIA-Grafikkarte mit aktuellem Treiber
- lokal bereitgestellter SHARP-Checkpoint unter `models\sharp_2572gikvuh.pt`

Der SHARP-Checkpoint ist **nicht Bestandteil von SplatTricia** und wird in diesem Repository nicht bereitgestellt. Für SHARP und das Modell gelten Apples eigene Lizenzbedingungen.

## Grundprinzip

SplatTricia erzeugt aus der von SHARP rekonstruierten Szene zwei parallele Ansichten. Die **Deviation** bestimmt die horizontale Tiefenausdehnung der erzeugten Stereoszene. Die **Scheinfensterlage** legt fest, wie diese Tiefe relativ zur Bildebene verteilt wird. **Floating-Window-Vorhänge** können Randbereiche maskieren, ohne die Geometrie der Szene selbst zu verändern.

Automatische 2D-zu-3D-Konvertierung bleibt eine geometrische Schätzung. Für Projektion oder andere anspruchsvolle Anwendungen sollten Deviation, Scheinfensterlage und Bildränder visuell kontrolliert werden.

## Ausgabe

SplatTricia erzeugt:

- parallele Side-by-Side-Stereobilder
- wahlweise Farb- oder Graustufen-Anaglyphen
- einen wiederverwendbaren PLY-Zwischenspeicher für schnelles erneutes Rendern mit anderen Stereo-Einstellungen

Soweit technisch möglich, werden Metadaten geeigneter Quelldateien in die fertigen JPEG-Ausgaben übernommen.

## Source Code

Dieses Repository dient der Veröffentlichung und langfristigen Verfügbarkeit des SplatTricia-Quellcodes. Build-Hinweise, Release-Checkliste sowie die dokumentierten Gestaltungs-, Zustands- und Ordnerregeln sind ebenfalls enthalten.

Aktive Betreuung, Support oder die Bearbeitung von Issues und Pull Requests können nicht zugesichert werden.

Der von Christoph Müller erstellte SplatTricia-Code und die eigene Dokumentation stehen unter der **MIT-Lizenz**. SHARP sowie alle weiteren Drittanbieter-Komponenten behalten ihre jeweiligen eigenen Lizenzen; die MIT-Lizenz für SplatTricia ändert daran nichts.

## Windows-Version

Die aktuelle Version 1.0 ist derzeit hier verfügbar:

https://traumnarben.de/download/SplatTricia_1.0.zip

Der Download-Link kann später auf die StereoFine-Webseite umziehen.
