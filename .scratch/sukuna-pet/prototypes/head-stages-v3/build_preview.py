from pathlib import Path
import base64,json,math
root=Path(__file__).parent
old=json.loads((root.parent/'head-stages/motion-parameters.json').read_text())
components=[]
for i,(angle,scale) in enumerate([(0,1),(-6.44,1.08),(1.17,1.025),(-9,1.065)]):
 components.append({'angle_deg':angle,'scale':scale,'dx':old['poses'][i][4],'dy':old['poses'][i][5]})
params={'components':components,'source_frames':[16,28,39,53],
 'preserve_face_ratio':True,'stage3_angle_degrees':-9,
 'head_plate_alignment':{},'neck_mesh':{},
 'note':'Head uses rotation and uniform scale; neck blends to fixed collar anchor. Awaiting visual confirmation.'}
if (root/'asset-geometry.json').exists():params.update(json.loads((root/'asset-geometry.json').read_text()))
(root/'motion-parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding='utf-8')
def uri(name,kind='jpeg'):
 return 'data:image/'+kind+';base64,'+base64.b64encode((root/name).read_bytes()).decode()
assets={'base':uri('character.png','png'),'repair':uri('head-neck-repair.png','png'),'rear':uri('rear-collar-complete.png','png'),'references':[uri(f'key-{i}.jpg') for i in range(4)],'videoFrames':uri('source-frames.jpg'),'params':params}
s=(root/'preview.template.html').read_text(encoding='utf-8').replace('/*ASSETS*/',json.dumps(assets,separators=(',',':'))).replace('/*EYES*/',(root/'eyes.js').read_text(encoding='utf-8'))
(root/'index.html').write_text(s,encoding='utf-8')
print('Built',len(s),'characters')
