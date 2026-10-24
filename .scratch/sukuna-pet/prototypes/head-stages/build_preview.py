from pathlib import Path
from PIL import Image,ImageDraw
import base64,json,shutil,hashlib
import numpy as np
root=Path(__file__).parent
research=root.parents[1]/'research/head-stages-20261025'
def uri(p,kind='jpeg'):
 return 'data:image/'+kind+';base64,'+base64.b64encode(p.read_bytes()).decode()
shutil.copyfile(root.parent/'dsh-click/eyes.js',root/'eyes.js')
shutil.copyfile(root.parent/'dsh-click/character.png',root/'character.png')
fits=json.loads((research/'pose-fit.json').read_text()) if (research/'pose-fit.json').exists() else json.loads((root/'motion-parameters.json').read_text())['fitting']
rows=[]
for r in fits['rows']:
 A=r['affine'];p=r['head_landmarks_stabilized'][-1]
 rows.append([A[0][0],A[1][0],A[0][1],A[1][1],(p[0]-304)*320/163,(p[1]-332)*320/163])
rows[0]=[1,0,0,1,0,0]
params={'poses':rows,'bounds':[0,13,24,34,41],'source_frames':[16,28,39,53],
 'method':'manual landmarks, coat-button similarity normalization, face affine fit, actual chin anchoring',
 'approximation':'2D deformation of approved sprite, no 3D yaw reconstruction; closing loop is interpolated, not measured',
 'fitting':fits}
(root/'motion-parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding='utf-8')
if (research/'frames.rgb').exists():
 frames=np.fromfile(research/'frames.rgb',dtype=np.uint8).reshape(-1,1280,576,3)
 sheet=Image.new('RGB',(288*8,290*5))
 for i,n in enumerate(range(16,54)):
  im=Image.fromarray(frames[n]).crop((0,305,576,885)).resize((288,290))
  sheet.paste(im,(i%8*288,i//8*290))
 sheet.save(root/'source-frames.jpg',quality=87)
for i in range(4):
 if (research/f'key-{i}.jpg').exists():shutil.copyfile(research/f'key-{i}.jpg',root/f'key-{i}.jpg')
assets={'base':uri(root/'character.png','png'),'references':[uri(root/f'key-{i}.jpg') for i in range(4)],'videoFrames':uri(root/'source-frames.jpg'),'params':params}
s=(root/'preview.template.html').read_text(encoding='utf-8').replace('/*ASSETS*/',json.dumps(assets,separators=(',',':'))).replace('/*EYES*/',(root/'eyes.js').read_text(encoding='utf-8'))
(root/'index.html').write_text(s,encoding='utf-8')
print('Built',root/'index.html',(root/'index.html').stat().st_size)
