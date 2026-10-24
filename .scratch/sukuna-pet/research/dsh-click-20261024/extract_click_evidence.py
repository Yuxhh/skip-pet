"""Static-only PyInstaller CArchive/PYZ click inspection; never executes code.

Requires xdis 6.3.0 in .tools next to this script. The inspected executable and
its installed directory are never written. Outputs are local research artifacts.
"""
from pathlib import Path
import hashlib, json, marshal, struct, sys, zlib

ROOT = Path(__file__).resolve().parent
SOURCE = Path(r'D:\dsh-pet\app\dsh-pet-standalone-webm-chat.exe')
sys.path.insert(0, str(ROOT / '.tools'))
from xdis.unmarshal import load_code
from xdis.bytecode import Bytecode
from xdis.opcodes import opcode_311

raw = SOURCE.read_bytes()
cookie = raw.rfind(b'MEI\014\013\012\013\016')
_, pkglen, tocoff, toclen, pyver, pylib = struct.unpack('!8sIIII64s', raw[cookie:cookie+88])
start = cookie + 88 - pkglen
toc = raw[start+tocoff:start+tocoff+toclen]
entries = []
cursor = 0
while cursor < len(toc):
    size, off, clen, ulen, flag, kind = struct.unpack('!IIIIBc', toc[cursor:cursor+18])
    name = toc[cursor+18:cursor+size].split(b'\0')[0].decode('utf-8')
    entries.append(dict(name=name, kind=kind.decode(), absolute_offset=start+off,
                        compressed_bytes=clen, uncompressed_bytes=ulen, compression=flag))
    cursor += size
pyzentry = next(e for e in entries if e['kind'] == 'z' and e['name'] == 'PYZ.pyz')
pyz = raw[pyzentry['absolute_offset']:pyzentry['absolute_offset']+pyzentry['compressed_bytes']]
magic = int.from_bytes(pyz[4:6], 'little')
pyztoc = dict(marshal.loads(pyz[struct.unpack('!I', pyz[8:12])[0]:]))

targets = {
    'pet.window': {'_squash_geometry', 'PetWindow.__init__', 'PetWindow._start_squash',
                   'PetWindow._on_squash_tick', 'PetWindow._frame_draw_rect',
                   'PetWindow.mouseReleaseEvent', 'PetWindow._on_click'},
    'pet.pet_sprite': {'<module>', 'PetSprite.squash', 'PetSprite._squashed_rect',
                       'PetSprite.advance', 'PetSprite.paint'},
    'pet.overlay_shell': {'ShellOverlayWindow.mouseReleaseEvent'},
}
records = []
texts = []
modules = []
def visit(code, module):
    name = getattr(code, 'co_qualname', code.co_name)
    if name in targets[module]:
        inst = [i for i in Bytecode(code, opcode_311) if i.opname != 'CACHE']
        if name in {'PetWindow.__init__', 'PetSprite.advance', '<module>'}:
            keep = set()
            for i, op in enumerate(inst):
                if 'squash' in str(op.argval).lower():
                    keep.update(range(max(0, i-5), min(len(inst), i+9)))
        else:
            keep = set(range(len(inst)))
        records.append(dict(module=module, qualname=name, original_file=code.co_filename,
                            original_first_line=code.co_firstlineno,
                            bytecode_sha256=hashlib.sha256(code.co_code).hexdigest(),
                            complete_method=name not in {'PetWindow.__init__','PetSprite.advance','<module>'}))
        texts.append(f'\n### {module}:{name} — {code.co_filename}:{code.co_firstlineno}\n')
        texts.extend(f'{i.starts_line or "":>5} {i.offset:>6} {i.opname:<28} {i.argrepr}\n'
                     for j, i in enumerate(inst) if j in keep)
    for nested in code.co_consts:
        if hasattr(nested, 'co_code'):
            visit(nested, module)
for module in targets:
    kind, off, size = pyztoc[module]
    payload = zlib.decompress(pyz[off:off+size])
    modules.append(dict(module=module, pyz_offset=off, compressed_bytes=size,
                        marshal_sha256=hashlib.sha256(payload).hexdigest()))
    visit(load_code(payload, magic, code_objects={}), module)

result = dict(source=str(SOURCE), source_sha256=hashlib.sha256(raw).hexdigest(),
              source_bytes=len(raw), cookie_offset=cookie, archive_start=start,
              python_version=pyver, python_magic_int=magic, pyz_archive_entry=pyzentry,
              method='custom CArchive/PYZ parser + xdis 6.3.0 version-independent marshal/opcode311',
              target_code_execution=False, modules=modules, records=records,
              limitation='Static control flow and constants; not an observed UI click or active configuration.')
(ROOT/'click-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'click-evidence.txt').write_text(''.join(texts),encoding='utf-8')
print(json.dumps({'source_sha256':result['source_sha256'],'methods':len(records),'execution':False}))
