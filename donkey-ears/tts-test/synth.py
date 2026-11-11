import sys, time, os, glob, torch
sys.path.insert(0, '/home/user/myshell-ai/melotts'); sys.path.insert(0, '/home/user/myshell-ai/openvoice')
torch.set_num_threads(4)
import types, melo.text
for m in ('chinese','japanese','english','chinese_mix','french','spanish','chinese_bert','english_bert','spanish_bert','french_bert'):  # 한국어만 쓰므로 다른 언어 모듈은 빈 모듈로 대체
    mod = types.ModuleType('melo.text.'+m); mod.get_bert_feature = None; sys.modules['melo.text.'+m] = mod; setattr(melo.text, m, mod)
from melo.api import TTS
from openvoice.api import ToneColorConverter
t=time.time()
tts = TTS(language='KR', device='cpu', config_path='ckpt_melo_kr/config.json', ckpt_path='ckpt_melo_kr/checkpoint.pth')
class _WM:
    def to(self, d): return self
_wm = types.ModuleType('wavmark'); _wm.load_model = lambda: _WM(); sys.modules['wavmark'] = _wm  # 테스트에선 워터마크 모델 생략
conv = ToneColorConverter('ckpt_ov2/converter/config.json', device='cpu')
conv.watermark_model = None
conv.load_ckpt('ckpt_ov2/converter/checkpoint.pth')
print('load', round(time.time()-t,1), 's', tts.hps.data.spk2id)
src_se = torch.load('ckpt_ov2/base_speakers/ses/kr.pth', map_location='cpu')
SENT = {
 's1': '임금님 귀는 당나귀 귀!',
 's2': '김부장님, 퇴근 좀 시켜주세요. 진짜 너무하시네요.',
 's3': '회의를 또 한다고? 미쳤어 진짜. 아, 짜증나.',
 's4': '아 씨, 진짜 개빡치네. 이걸 지금 나한테 시킨다고?',
}
os.makedirs('out', exist_ok=True)
spk_id = list(tts.hps.data.spk2id.values())[0]
for k, s in SENT.items():
    t=time.time(); tts.tts_to_file(s, spk_id, f'out/base_{k}.wav', speed=1.0, quiet=True); print('tts', k, round(time.time()-t,2))
for ref in sorted(glob.glob('ref/spk???.wav')):
    name = os.path.basename(ref)[:-4]
    t=time.time(); tgt_se = conv.extract_se([ref]); print('extract', name, round(time.time()-t,2))
    for k in SENT:
        t=time.time()
        conv.convert(audio_src_path=f'out/base_{k}.wav', src_se=src_se, tgt_se=tgt_se, output_path=f'out/{name}_{k}.wav')
        print('convert', name, k, round(time.time()-t,2))
