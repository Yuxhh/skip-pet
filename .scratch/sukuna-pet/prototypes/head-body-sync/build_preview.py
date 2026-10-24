"""Throwaway motion comparison. Source video and installed pet stay untouched."""
from pathlib import Path
import base64, hashlib, io, json, shutil
from PIL import Image, ImageDraw

root = Path(__file__).parent
workspace = root.parents[3]
def uri(data, kind='png'):
    return f'data:image/{kind};base64,' + base64.b64encode(data).decode()
source_sheet = root/'source-sheet.jpg'
if not source_sheet.exists():
    import numpy as np
    frames = np.load(root / 'frames.npy')
    sheet = Image.new('RGB', (288*7, 225*6))
    for i, frame in enumerate(frames):
        sheet.paste(Image.fromarray(frame).crop((0,415,576,865)).resize((288,225)), ((i%7)*288,(i//7)*225))
    sheet.save(source_sheet, 'JPEG', quality=91)
base = root/'sukuna-eye-base-v3.png'
if not base.exists():
    shutil.copyfile(workspace/'src/sukuna_pet/assets/sukuna-eye-base-v3.png',base)
assets = {'source': uri(source_sheet.read_bytes(),'jpeg'), 'base': uri(base.read_bytes()),
          'sha256': hashlib.sha256(base.read_bytes()).hexdigest()}
template = (root/'preview.template.html').read_text(encoding='utf-8')
(root/'index.html').write_text(template.replace('/*ASSETS*/',json.dumps(assets,separators=(',',':'))),encoding='utf-8')
print('Self-contained preview:', (root/'index.html').stat().st_size, 'bytes')
