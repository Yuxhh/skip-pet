"""THROWAWAY: pixel-preserving extraction samples, not production animation.
Run with Pillow + numpy. SOURCE is read only. All outputs are local.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source-dir',type=Path,default=ROOT.parents[1]/'research/diagnostics')
args = parser.parse_args()

SOURCE = args.source_dir
OUT = ROOT / 'assets'
OUT.mkdir(exist_ok=True)
FONT = r'C:\Windows\Fonts\msyh.ttc'

# Hand-marked silhouette seeds in diagnostic crop coordinates (576 x 450).
# These hand-drawn masks only produce alpha; source RGB pixels are unchanged.
POLYS = {
    0: [(96,449),(96,373),(107,346),(137,314),(171,284),(194,268),
        (194,233),(187,211),(204,195),(220,185),(204,164),(199,146),
        (186,151),(195,133),(182,132),(192,116),(182,119),(196,102),
        (186,94),(204,89),(197,76),(215,78),(208,62),(226,65),
        (225,45),(243,56),(245,34),(258,49),(272,27),(275,47),
        (292,21),(294,43),(316,17),(310,43),(344,29),(330,52),
        (372,43),(349,64),(389,62),(361,82),(386,86),(366,100),
        (390,110),(367,115),(374,135),(365,158),(354,181),
        (376,191),(399,211),(397,264),(426,299),(458,326),
        (482,350),(492,371),(491,412),(483,449)],
    36: [(111,449),(107,400),(108,387),(132,359),(164,332),(193,305),
         (202,288),(198,264),(191,249),(210,228),(218,219),
         (199,196),(194,178),(180,177),(188,159),(178,160),
         (190,143),(180,146),(193,128),(185,130),(198,111),
         (192,103),(206,94),(203,80),(219,81),(215,63),
         (231,70),(231,50),(245,63),(251,41),(260,61),
         (278,36),(276,60),(299,39),(293,62),(321,44),
         (306,68),(338,62),(322,83),(352,80),(333,100),
         (354,104),(337,119),(359,126),(342,137),(349,153),
         (340,164),(339,190),(334,204),(358,209),(375,224),
         (378,268),(397,292),(429,318),(461,346),(477,367),
         (481,388),(473,449)],
    64: [(78,449),(78,381),(92,358),(124,327),(155,303),(182,279),
         (188,265),(184,236),(180,216),(187,204),(206,190),
         (197,169),(192,147),(185,138),(183,117),(175,115),
         (184,97),(175,98),(189,79),(181,76),(196,60),
         (191,53),(212,43),(206,31),(228,32),(227,13),
         (246,22),(255,2),(267,14),(276,2),(289,12),
         (309,2),(315,13),(342,2),(336,22),(371,8),
         (353,35),(389,26),(365,51),(391,50),(370,73),
         (394,80),(371,92),(384,108),(370,125),(370,151),
         (362,177),(387,182),(407,203),(408,253),(431,281),
         (459,306),(486,334),(503,359),(508,383),(500,449)]
}
FRAMES = [0, 36, 64]
manifest = {'purpose':'throwaway transparency preview; no loop/timing validation',
            'source_crop_xyxy':[0,415,576,865], 'fps':24,
            'method':{'name':'manual polygon + dark narrow-band refinement',
                      'band_radius_px':3,'dark_threshold_mean_rgb':68,
                      'outward_band_only_above_y':160,
                      'face_band_xyxy':[190,125,377,260],
                      'clothes_opening_size_px':3,'clothes_opening_from_y':260,
                      'alpha_blur_radius_px':0.45,'bottom_clear_from_y':447,
                      'B_fade_length_px':28,'C_crop_from_y':380},
            'rgb_modified':False, 'frames':[]}

for index in FRAMES:
    path = SOURCE / f'spot-{index:03d}.png'
    im = Image.open(path).convert('RGB')
    rgb = np.array(im)
    seed = Image.new('L', im.size)
    ImageDraw.Draw(seed).polygon(POLYS[index], fill=255)
    p = np.array(seed)
    inner = np.array(seed.filter(ImageFilter.MinFilter(7)))
    outer = np.array(seed.filter(ImageFilter.MaxFilter(7)))
    gray = rgb.astype(np.float32).mean(axis=2)
    # Narrow-band refinement for the dark hair and clothes. This is intentionally
    # cheap: it cannot distinguish a black railing from adjacent black hair.
    yy,xx=np.indices(p.shape)
    boundary_limit=np.where(yy<160,outer,p)
    mask = np.where((inner>0)|((boundary_limit>0)&(gray<68)),255,0).astype(np.uint8)
    face_band=(yy>125)&(yy<260)&(xx>190)&(xx<377)
    mask[face_band]=p[face_band]
    # Suppress thin railing specks on the clothes; leave the hair untouched.
    smooth=np.array(Image.fromarray(mask).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3)))
    mask[yy>=260]=smooth[yy>=260]
    connected=Image.fromarray(mask).copy()
    ImageDraw.floodfill(connected,(288,300),128)
    mask=np.where(np.array(connected)==128,255,0).astype(np.uint8)
    assert np.count_nonzero(mask)>70000, 'Foreground mask unexpectedly empty'
    alpha = np.array(Image.fromarray(mask).filter(ImageFilter.GaussianBlur(.45)))
    # The source's final 3 rows are its lower frame boundary, never body pixels.
    alpha[447:] = 0
    variants={}
    for variant in ['A','B','C']:
        a = alpha.copy()
        if variant=='B':
            a = (a * np.clip((447-np.arange(450))/28,0,1)[:,None]).astype(np.uint8)
        elif variant=='C':
            a[380:] = 0
        rgba = np.dstack((rgb,a))
        file = f'f{index:03d}-{variant}.png'
        Image.fromarray(rgba).save(OUT/file)
        assert np.array_equal(rgba[:,:,:3],rgb)
        variants[variant]=file
    im.save(OUT/f'f{index:03d}-source.png')
    Image.fromarray(alpha).save(OUT/f'f{index:03d}-alpha.png')
    manifest['frames'].append({'frame':index,'seconds':index/24,
        'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'seed_polygon':POLYS[index],'variants':variants,
        'alpha_nonzero_pixels':int(np.count_nonzero(alpha))})

def font(size): return ImageFont.truetype(FONT,size)
def background(kind,size):
    if kind=='浅色': return Image.new('RGB',size,'#f5f1e7')
    if kind=='深色': return Image.new('RGB',size,'#263347')
    im=Image.new('RGB',size,'#e2e2e2');d=ImageDraw.Draw(im)
    for y in range(0,size[1],16):
        for x in range(0,size[0],16):
            if (x//16+y//16)%2: d.rectangle((x,y,x+15,y+15),fill='#bdbdbd')
    return im

# Readable at normal display scale: same three source frames on three backgrounds.
sheet=Image.new('RGB',(1200,1140),'#ffffff');d=ImageDraw.Draw(sheet)
d.text((22,12),'透明半身素材 · 原视频像素提取预览',font=font(27),fill='#111111')
d.text((22,52),'A 保留原截断｜静止候选 f000 · 倾斜候选 f036 · 模糊压力帧 f064',font=font(18),fill='#444444')
for r,idx in enumerate(FRAMES):
    for c,bg in enumerate(['浅色','深色','纹理']):
        x=c*400;y=90+r*350
        tile=background(bg,(390,315))
        cut=Image.open(OUT/f'f{idx:03d}-A.png').resize((384,300),Image.Resampling.LANCZOS)
        tile.paste(cut,(3,8),cut)
        sheet.paste(tile,(x+5,y+28))
        d.text((x+12,y),f'f{idx:03d} · {idx/24:.3f}s · {bg}',font=font(17),fill='#222222')
sheet.save(ROOT/'transparency-contact-sheet.jpg',quality=95)

sheet=Image.new('RGB',(1200,440),'white');d=ImageDraw.Draw(sheet)
for c,(v,title) in enumerate([('A','A 原截断'),('B','B 下沿 28px 渐隐'),('C','C 上移截断至 y380')]):
    x=c*400
    d.text((x+16,12),title,font=font(22),fill='#111111')
    tile=background('浅色',(390,335));cut=Image.open(OUT/f'f036-{v}.png').resize((384,300),Image.Resampling.LANCZOS)
    tile.paste(cut,(3,8),cut);sheet.paste(tile,(x+5,50))
    d.text((x+16,392),['保留胸前文字与可见衣服','仅改透明度，底端会半透明','丢弃更多衣服与胸前文字'][c],font=font(17),fill='#444444')
sheet.save(ROOT/'lower-edge-options.jpg',quality=95)

(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'method':'hand-mask + dark narrow-band refinement','output':str(ROOT),'frames':FRAMES,'source_rgb_preserved':True},ensure_ascii=False))
