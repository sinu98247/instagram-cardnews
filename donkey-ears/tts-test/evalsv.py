import json, urllib.request, collections, os, glob, time, sys, warnings
warnings.filterwarnings('ignore')
import torch, librosa, numpy as np
from transformers import Wav2Vec2FeatureExtractor, WavLMForXVector
# held-out real utterances (not in the reference)
by=collections.defaultdict(list)
for sp in ('test','train'):
    u=f"https://datasets-server.huggingface.co/first-rows?dataset=kresnik/zeroth_korean&config=default&split={sp}"
    for r in json.load(urllib.request.urlopen(u, timeout=60))['rows']:
        r=r['row']; by[r['speaker_id']].append(r['audio'][0]['src'])
os.makedirs('held', exist_ok=True)
for spk, srcs in by.items():
    for i, src in enumerate(srcs[6:10]):
        fn=f'held/spk{spk}_{i}.wav'
        if not os.path.exists(fn): urllib.request.urlretrieve(src, fn)
fe = Wav2Vec2FeatureExtractor.from_pretrained('microsoft/wavlm-base-plus-sv')
m = WavLMForXVector.from_pretrained('microsoft/wavlm-base-plus-sv').eval()
# 구버전 가중치 이름(weight_g/weight_v)을 새 이름으로 직접 넣어줌
from huggingface_hub import hf_hub_download
sd = torch.load(hf_hub_download('microsoft/wavlm-base-plus-sv','pytorch_model.bin'), map_location='cpu')
pc = m.wavlm.encoder.pos_conv_embed.conv.parametrizations.weight
pc.original0.data.copy_(sd['wavlm.encoder.pos_conv_embed.conv.weight_g']); pc.original1.data.copy_(sd['wavlm.encoder.pos_conv_embed.conv.weight_v'])
def emb(fn):
    y,_ = librosa.load(fn, sr=16000)
    with torch.no_grad():
        e = m(**fe(y, sampling_rate=16000, return_tensors='pt')).embeddings
    return torch.nn.functional.normalize(e, dim=-1)[0]
def f0(fn):
    y,sr = librosa.load(fn, sr=16000)
    f,_,_ = librosa.pyin(y, fmin=65, fmax=400, sr=sr)
    return float(np.nanmedian(f))
spks = sorted(by)
ref = {s: emb(f'ref/spk{s}.wav') for s in spks}
sents = ['s1','s2','s3','s4']
base = [emb(f'out/base_{k}.wav') for k in sents]
res = {}
for s in spks:
    held = np.mean([float(ref[s] @ emb(f)) for f in glob.glob(f'held/spk{s}_*.wav')])
    other = np.mean([float(ref[s] @ emb(f)) for o in spks if o != s for f in glob.glob(f'held/spk{o}_*.wav')])
    clone = np.mean([float(ref[s] @ emb(f'out/spk{s}_{k}.wav')) for k in sents])
    b = np.mean([float(ref[s] @ e) for e in base])
    res[s] = dict(real_same=round(held,3), clone=round(clone,3), base_tts=round(b,3), real_other=round(other,3),
                  f0_ref=round(f0(f'ref/spk{s}.wav')), f0_clone=round(np.mean([f0(f'out/spk{s}_{k}.wav') for k in ['s2','s3']])))
    print(s, res[s], flush=True)
print('f0_base', round(np.mean([f0(f'out/base_{k}.wav') for k in ['s2','s3']])))
json.dump({str(k):v for k,v in res.items()}, open('sv.json','w'))

# 발음 정확도: Whisper로 받아쓰기
from transformers import pipeline
asr = pipeline('automatic-speech-recognition', model='openai/whisper-small', generate_kwargs={'language':'korean','task':'transcribe'})
for f in ['out/base_s1.wav','out/base_s2.wav','out/base_s3.wav','out/base_s4.wav'] + [f'out/spk{s}_{k}.wav' for s in (105,187) for k in sents]:
    print(f, '→', asr(f)['text'].strip(), flush=True)
