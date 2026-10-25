from pathlib import Path
import base64,json
root=Path(__file__).parent
components=[{'angle_deg':a,'scale':s} for a,s in [(0,1),(-6.44,1.08),(1.17,1.025),(-9,1.065)]]
params={'components':components,'source_frames':[16,28,39,53],
 'preserve_face_ratio':True,'stage3_angle_degrees':-9,
 'neck_center':[720,735],'source_pivot':[710,650],
 'neck_center_fixed':True,'independent_xy_translation':False,
 'click_bounce':{'duration_ms':220,'width_amplitude':0.10,'height_amplitude':-0.15,'curve':'sin(pi*p)','anchor':[709.5,1108],'repeat':'restart, no accumulation'},
 'note':'Rotation and uniform scale around the fixed neck center; lower neck attachment blends to rest.'}
params.update(json.loads((root/'asset-geometry.json').read_text()))
(root/'motion-parameters.json').write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding='utf-8')
def uri(name,kind='jpeg'):
 return 'data:image/'+kind+';base64,'+base64.b64encode((root/name).read_bytes()).decode()
assets={'base':uri('character.png','png'),'repair':uri('head-neck-repair.png','png'),'rear':uri('rear-collar-complete.png','png'),'references':[uri(f'key-{i}.jpg') for i in range(4)],'videoFrames':uri('source-frames.jpg'),'params':params}
s=(root/'preview.template.html').read_text(encoding='utf-8').replace('/*ASSETS*/',json.dumps(assets,separators=(',',':'))).replace('/*EYES*/',(root/'eyes.js').read_text(encoding='utf-8')).replace('/*BOUNCE*/',(root/'bounce.js').read_text(encoding='utf-8')).replace('/*RIG*/',(root/'rig.js').read_text(encoding='utf-8'))
(root/'index.html').write_text(s,encoding='utf-8');print('Built',len(s),'characters')
