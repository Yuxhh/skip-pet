"""Pack dsh-pet's verified click geometry onto the approved Sukuna artwork."""
from pathlib import Path
import argparse,base64,json,shutil
p=argparse.ArgumentParser();p.add_argument('--duration-ms',type=float,required=True);a=p.parse_args()
root=Path(__file__).parent;old=root.parent/'head-body-sync'
if not (root/'eyes.js').exists():
    s=(old/'preview.template.html').read_text(encoding='utf-8')
    rules=s[s.index('const Motion='):s.index('</script>',s.index('const Motion='))]
    eyes=s[s.index('function socket('):s.index('// Fixed body, moving head')]
    (root/'eyes.js').write_text(rules+'\n'+eyes,encoding='utf-8')
if not (root/'character.png').exists():
    shutil.copyfile(old/'sukuna-eye-base-v3.png',root/'character.png')
params={'duration_ms':a.duration_ms,'vertical_compression':.15,'horizontal_expansion':.10,
        'pulse':'sin(pi * clamp(progress,0,1))','anchor':'bottom, horizontally centered',
        'source_exe_sha256':'687255faea034bd0e672a870da732650dbbd5b9aae050586e143ac1e55c50407',
        'authority':'read-only Python 3.11 packaged bytecode; runtime observation separately recorded'}
(root/'reference-parameters.json').write_text(json.dumps(params,indent=2),encoding='utf-8')
asset='data:image/png;base64,'+base64.b64encode((root/'character.png').read_bytes()).decode()
s=(root/'preview.template.html').read_text(encoding='utf-8').replace('/*ASSET*/',json.dumps(asset)).replace('/*EYES*/',(root/'eyes.js').read_text(encoding='utf-8')).replace('/*DURATION*/',str(a.duration_ms))
(root/'index.html').write_text(s,encoding='utf-8');print('Packed',len(s),'characters')
