from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from sukuna_pet.credentials import CredentialStore
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings_window import SettingsWindow


class UnavailableVault:
    def read(self):
        raise OSError()
    def write(self, value):
        raise OSError()
    def delete(self):
        raise OSError()


app = QApplication([])
pet = PetWindow(PetApplication(), credentials=CredentialStore(UnavailableVault()))
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
for name, suffix in (("桌宠", "pet"), ("任务联动", "bridge"), ("AI 对话", "ai"), ("关于", "about")):
    pet.open_settings(name)
    app.processEvents()
    settings = pet.findChild(SettingsWindow)
    settings.resize(560, 440)
    app.processEvents()
    assert settings.grab().save(str(output / f"settings-{suffix}.png"))
pet.close()
