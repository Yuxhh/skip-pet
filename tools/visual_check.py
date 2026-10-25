"""Native Qt visual evidence; uses the production application and renderer.

Run: python tools/visual_check.py [--show]
The PNG is a rendered contact sheet, not a desktop screenshot or timing test.
"""

from pathlib import Path
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

from sukuna_pet.playback import PetApplication
from sukuna_pet.rendering import CharacterRenderer


app = QApplication(sys.argv)
renderer = CharacterRenderer()
pet = PetApplication()
views = [("Gaze 0 / idle", pet.view)]
for stage, elapsed in ((1, 181), (2, 153), (3, 120)):
    pet.click()
    pet.advance(elapsed)
    views.append((f"Gaze {stage}" if stage != 3 else "Closed / 120ms", pet.view))
pet.advance(120)
views.append(("Gaze 3 / 240ms", pet.view))

sheet = QImage(1350, 1005, QImage.Format.Format_ARGB32_Premultiplied)
sheet.fill(Qt.GlobalColor.white)
painter = QPainter(sheet)
painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
for row, background in enumerate(("#f3f2ee", "#263347", "checker")):
    for col, (name, view) in enumerate(views):
        x, y = col * 270, row * 335
        if background == "checker":
            for cx in range(0, 270, 15):
                for cy in range(0, 335, 15):
                    color = "#c7c7c7" if (cx // 15 + cy // 15) % 2 else "#eeeeee"
                    painter.fillRect(x + cx, y + cy, 15, 15, QColor(color))
        else:
            painter.fillRect(x, y, 270, 335, QColor(background))
        painter.setPen(QColor("white" if row == 1 else "#25332e"))
        painter.drawText(x + 10, y + 20, name)
        frame = renderer.render(view)
        painter.drawImage(QRectF(x + 8, y + 30, 253, 247), frame)
painter.end()
output = Path("docs/verification/issue-23/qt-contact-sheet.png")
output.parent.mkdir(parents=True, exist_ok=True)
if not sheet.save(str(output)):
    raise RuntimeError(f"Could not write {output}")
print(output)

if "--show" in sys.argv:
    label = QLabel()
    label.setPixmap(QPixmap.fromImage(sheet))
    scroll = QScrollArea()
    scroll.setWindowTitle("宿傩桌宠 · 原生绘制验收")
    scroll.setWidget(label)
    scroll.resize(1380, 950)
    scroll.show()
    raise SystemExit(app.exec())
