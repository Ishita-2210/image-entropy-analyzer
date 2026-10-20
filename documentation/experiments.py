"""Reproduce documentation measurements using the unchanged project modules."""
from pathlib import Path
import sys, json, hashlib, platform, importlib.metadata
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from entropy import *
from image_utils import *

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)
rng = np.random.default_rng(20261020)
y, x = np.mgrid[0:256, 0:256]
# Procedural landscape: sky, two sinusoidal ridges, a sun and ground shading.
land = 185 - 45*y/255 + 12*np.sin(x/37)
land = np.where(y > 118+20*np.sin(x/42), 100+20*np.sin(x/25)+y/15, land)
land = np.where(y > 175+13*np.sin(x/27), 45+y/5+9*np.cos(x/18), land)
land[(x-195)**2+(y-46)**2 < 19**2] = 240
land = np.clip(np.rint(land),0,255).astype(np.uint8)
images = {
 'Constant': np.full((256,256),128,dtype=np.uint8),
 'Four levels': np.tile(np.repeat(np.array([0,85,170,255],dtype=np.uint8),64),(256,1)),
 'Landscape': land,
 'Noise': rng.integers(0,256,size=(256,256),dtype=np.uint8),
}
records=[]
for name,a in images.items():
 p=ASSETS/(name.lower().replace(' ','_')+'.png')
 Image.fromarray(a).save(p)
 # File bytes -> real loader -> real grayscale conversion -> real calculations.
 result=analyze_image(grayscale_array(load_image(p.read_bytes())))
 records.append({'Image':name,'Width':result['width'],'Height':result['height'],
 'Entropy':result['entropy'],'Normalized':result['normalized_entropy'],
 'Redundancy':result['redundancy'],'Unique levels':result['unique_levels']})
 assert result['histogram'].sum()==65536
 assert np.isclose(result['probabilities'].sum(),1)
pd.DataFrame(records).to_csv(ROOT/'experiment_results.csv',index=False)
checks=[]
def check(label, condition):
 assert condition,label
 checks.append(label)
toy=analyze_image(np.array([[0,0,0,255]],dtype=np.uint8))
check('toy entropy',np.isclose(toy['entropy'],0.8112781244591328))
check('toy normalized',np.isclose(toy['normalized_entropy'],0.1014097655573916))
check('toy redundancy',np.isclose(toy['redundancy'],89.85902344426084))
check('constant entropy',records[0]['Entropy']==0)
check('four equal levels entropy',records[1]['Entropy']==2)
check('uniform full alphabet entropy',analyze_image(np.arange(256,dtype=np.uint8).reshape(16,16))['entropy']==8)
shuffled=land.ravel().copy(); rng.shuffle(shuffled); shuffled=shuffled.reshape(land.shape)
Image.fromarray(shuffled).save(ASSETS/'landscape_shuffled.png')
check('pixel permutation preserves histogram',np.array_equal(calculate_histogram(land),calculate_histogram(shuffled)))
check('pixel permutation preserves entropy',analyze_image(land)['entropy']==analyze_image(shuffled)['entropy'])
for label,a,exc in [('non array',[1],TypeError),('empty',np.empty((0,1)),ValueError),('three dimensional',np.zeros((2,2,3)),ValueError)]:
 try: analyze_image(a)
 except exc: checks.append(label+' rejected')
 else: raise AssertionError(label)
check('clip then truncate',np.array_equal(validate_grayscale_image(np.array([[-1.,12.9,300.]])),[[0,12,255]]))
check('self information zero',np.isinf(calculate_information_content(0)))
check('self information quarter',calculate_information_content(.25)==2)
for b in [b'',b'invalid image']:
 try: load_image(b)
 except ValueError: checks.append('invalid image bytes rejected')
 else: raise AssertionError('bytes validation')
# EXIF orientation 6 rotates a 3x2 encoded image into a 2x3 decoded image.
import io
buf=io.BytesIO(); exif=Image.Exif(); exif[274]=6
Image.new('RGB',(3,2)).save(buf,format='JPEG',exif=exif)
check('EXIF orientation dimensions',load_image(buf.getvalue()).size==(2,3))
rgb=np.stack([land, np.flipud(land), np.full_like(land,64)],axis=2)
Image.fromarray(rgb).save(ASSETS/'colour_demo.png')
channels={k:analyze_image(v)['entropy'] for k,v in rgb_channel_arrays(Image.fromarray(rgb)).items()}
manifest={'seed':20261020,'shape':[256,256],'checks_passed':checks,'toy':{k:v for k,v in toy.items() if not isinstance(v,np.ndarray)},'colour_demo_channel_entropies':channels,
 'python':platform.python_version(),'versions':{k:importlib.metadata.version(k) for k in ['numpy','pillow','pandas','matplotlib','streamlit']},
 'source_sha256':{n:hashlib.sha256((ROOT.parent/n).read_bytes()).hexdigest() for n in ['app.py','entropy.py','image_utils.py','requirements.txt','README.md']}}
(ROOT/'experiment_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#18221c','axes.labelcolor':'#18221c','axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(2,4,figsize=(11,4.7),gridspec_kw={'height_ratios':[1,1]})
for j,(name,a) in enumerate(images.items()):
 axs[0,j].imshow(a,cmap='gray',vmin=0,vmax=255); axs[0,j].axis('off'); axs[0,j].set_title(name,fontsize=11)
 axs[1,j].plot(np.arange(256),calculate_probabilities(calculate_histogram(a)),color='#66866e',lw=1)
 axs[1,j].set_xlim(0,255); axs[1,j].set_xlabel('Intensity'); axs[1,j].tick_params(labelsize=8)
axs[1,0].set_ylabel('Probability')
fig.tight_layout(); fig.savefig(ASSETS/'experiment_panel.png',dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(7,2.8)); ax.bar([r['Image'] for r in records],[r['Entropy'] for r in records],color='#8daa94',width=.55)
ax.set_ylim(0,8.6); ax.set_ylabel('Entropy (bits/pixel)')
for i,r in enumerate(records): ax.text(i,max(0,r['Entropy'])+.14,f"{abs(r['Entropy']):.4f}",ha='center',fontsize=10)
fig.tight_layout();fig.savefig(ASSETS/'entropy_results.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(6,2.7))
for ax,a,t in zip(axs,[land,shuffled],['Procedural landscape','Same pixels, shuffled']):
 ax.imshow(a,cmap='gray',vmin=0,vmax=255);ax.set_title(t,fontsize=10);ax.axis('off')
fig.tight_layout();fig.savefig(ASSETS/'permutation.png',dpi=180);plt.close(fig)
print(pd.DataFrame(records).to_string(index=False))
print(f'{len(checks)} checks passed; RGB demo: {channels}')
