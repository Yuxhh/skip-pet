"""Throwaway bubble prototype. Capture existing native motion; never edit production."""
from pathlib import Path
import base64
import json
import sys

root = Path(__file__).resolve().parent
repo = root.parents[3]
sys.path.insert(0, str(repo / 'src'))
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QApplication
from sukuna_pet.playback import PetApplication
from sukuna_pet.rendering import CharacterRenderer

qt = QApplication.instance() or QApplication([])
renderer = CharacterRenderer()
pet = PetApplication()

def capture():
    image = renderer.render(pet.view, height=480)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, 'WEBP', 85)
    return 'data:image/webp;base64,' + base64.b64encode(bytes(buf.data())).decode()

rest = capture()
transitions = []
for stage in range(4):
    pet.click()
    frames = [capture()]
    for _ in range(16):
        pet.advance(20)
        frames.append(capture())
    transitions.append(frames)
assets = json.dumps({'rest': rest, 'transitions': transitions}, separators=(',', ':'))
source = (root / 'preview.template.html').read_text(encoding='utf-8')
(root / 'index.html').write_text(source.replace('/*ASSETS*/', assets), encoding='utf-8')
print('Built standalone prototype:', root / 'index.html')
