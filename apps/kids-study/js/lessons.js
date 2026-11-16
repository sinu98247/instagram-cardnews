/* 배우기: 그림 영상(내레이션 + 단계별 애니메이션) 플레이어 */
const SC={timers:[],T(ms,fn){this.timers.push(setTimeout(fn,ms))},stop(){this.timers.forEach(clearTimeout);this.timers=[]}};
const svgNS=(w,h,body)=>`<svg viewBox="0 0 ${w} ${h}" class="scn">${body}</svg>`;

/* ---------- 장면(scene) 모음: (stage, p) => 재생 시간(ms) ---------- */
const SCENES={
 combine(st,p){const c=CHO[p.c],j=JUNG[p.j],s=syl(p.c,p.j);st.innerHTML=`<div class="sc-row"><span class="sc-tile" id="scA">${c}</span><span class="sc-plus" id="scP">+</span><span class="sc-tile" id="scB">${j}</span></div><div class="sc-result" id="scR">${s}</div>`;
   SC.T(900,()=>{$('scA').style.transform='translateX(60px)';$('scB').style.transform='translateX(-60px)';$('scP').style.opacity=0});SC.T(2000,()=>{$('scR').classList.add('on')});return 3200},
 blend(st,p){const L=p.w.split('');st.innerHTML=`<div class="sc-row" id="scW">${L.map((x,i)=>`<span class="sc-tile en" id="scL${i}" style="opacity:0;margin:0 14px">${x}</span>`).join('')}</div><div class="sc-emo" id="scE" style="opacity:0">${p.e||''}</div>`;
   L.forEach((x,i)=>SC.T(500+i*900,()=>{$('scL'+i).style.opacity=1;narrateOnly(x,'en')}));const t=500+L.length*900;SC.T(t,()=>L.forEach((x,i)=>$('scL'+i).style.margin='0 1px'));SC.T(t+700,()=>{$('scE').style.opacity=1;narrateOnly(p.w,'en')});return t+2200},
 count(st,p){const e=p.e||'🍎';st.innerHTML=`<div class="sc-emo-grid" id="scG"></div><div class="sc-big" id="scN">0</div>`;for(let i=0;i<p.n;i++)SC.T(400+i*450,()=>{$('scG').insertAdjacentHTML('beforeend',`<span class="sc-pop">${e}</span>`);$('scN').textContent=i+1});return 600+p.n*450+800},
 tens(st,p){const t=Math.floor(p.n/10),o=p.n%10;st.innerHTML=`<div class="tens" id="scT" style="font-size:1rem;min-height:150px"></div><div class="sc-big" id="scN"></div>`;let k=0;
   for(let i=0;i<t;i++){SC.T(300+k*700,()=>{$('scT').insertAdjacentHTML('beforeend','<div class="ten sc-pop">'+'<i></i>'.repeat(10)+'</div>');$('scN').textContent=`10씩 ${i+1}묶음`});k++}
   if(o)SC.T(300+k*700,()=>{$('scT').insertAdjacentHTML('beforeend','<div class="one sc-pop">'+'<i></i>'.repeat(o)+'</div>');$('scN').textContent=`10씩 ${t}묶음과 낱개 ${o}개`});SC.T(300+(k+1)*700+300,()=>{$('scN').textContent=`= ${p.n}`});return 300+(k+2)*700+1200},
 place(st,p){const d=String(p.n).split('');const names=['천','백','십','일'].slice(4-d.length);st.innerHTML=`<table class="sc-place"><tr>${names.map(n=>`<th>${n}의 자리</th>`).join('')}</tr><tr>${d.map((x,i)=>`<td><span id="scD${i}" class="sc-drop">${x}</span></td>`).join('')}</tr></table><div class="sc-big" id="scN"></div>`;
   d.forEach((x,i)=>SC.T(500+i*900,()=>{$('scD'+i).classList.add('on')}));SC.T(600+d.length*900,()=>{$('scN').textContent=d.map((x,i)=>x+'0'.repeat(d.length-1-i)).filter(v=>+v).join(' + ')+' = '+p.n});return 1800+d.length*900},
 jump(st,p){const steps=p.steps,vals=[p.start];steps.forEach(s=>vals.push(vals[vals.length-1]+s));const lo=Math.min(...vals),hi=Math.max(...vals);const pad=(hi-lo)*.12||2;const X=v=>20+(v-lo+pad)/(hi-lo+2*pad)*360;
   let g=`<line x1="10" y1="90" x2="390" y2="90" class="sc-axis"/>`+vals.map((v,i)=>`<g id="scV${i}" style="opacity:${i?0:1}"><line x1="${X(v)}" y1="82" x2="${X(v)}" y2="98" class="sc-axis"/><text x="${X(v)}" y="116" text-anchor="middle" class="sc-txt">${v}</text></g>`).join('')+`<circle id="scDot" cx="${X(vals[0])}" cy="90" r="7" class="sc-dot"/>`;
   steps.forEach((s,i)=>{const a=X(vals[i]),b=X(vals[i+1]),m=(a+b)/2;g+=`<path id="scJ${i}" d="M${a} 86 Q${m} ${s>0?20:20} ${b} 86" class="sc-arc" style="stroke-dasharray:400;stroke-dashoffset:400"/><text id="scJT${i}" x="${m}" y="34" text-anchor="middle" class="sc-txt sc-acc" style="opacity:0">${s>0?'+':'−'}${Math.abs(s)}</text>`});
   st.innerHTML=svgNS(400,130,g);steps.forEach((s,i)=>SC.T(700+i*1500,()=>{$('scJ'+i).style.strokeDashoffset=0;$('scJT'+i).style.opacity=1;SC.T(700,()=>{$('scV'+(i+1)).style.opacity=1;$('scDot').setAttribute('cx',X(vals[i+1]))})}));return 900+steps.length*1500+800},
 groups(st,p){const e=p.e||'🍎';st.innerHTML=`<div class="sc-row" id="scG" style="flex-wrap:wrap;gap:10px"></div><div class="sc-big" id="scN"></div>`;for(let i=0;i<p.m;i++)SC.T(400+i*800,()=>{$('scG').insertAdjacentHTML('beforeend',`<span class="grp sc-pop" style="font-size:1.8rem">${e.repeat(p.n)}</span>`);$('scN').textContent=`${p.n} × ${i+1} = ${p.n*(i+1)}`});return 600+p.m*800+1000},
 share(st,p){const e=p.e||'🍪';st.innerHTML=`<div class="sc-row" style="gap:14px;flex-wrap:wrap">${Array.from({length:p.k},(_,i)=>`<div class="sc-plate" id="scP${i}"></div>`).join('')}</div><div class="sc-emo-grid" id="scLeft" style="font-size:1.6rem">${e.repeat(p.total)}</div><div class="sc-big" id="scN"></div>`;
   const q=Math.floor(p.total/p.k);let left=p.total;for(let i=0;i<q*p.k;i++)SC.T(400+i*300,()=>{left--;$('scLeft').textContent=e.repeat(left);$('scP'+(i%p.k)).insertAdjacentHTML('beforeend',`<span class="sc-pop">${e}</span>`)});
   SC.T(500+q*p.k*300,()=>{$('scN').textContent=`${p.total} ÷ ${p.k} = ${q}`+(left?` ··· 나머지 ${left}`:'')});return 1600+q*p.k*300},
 pie(st,p){const d=p.d;const from=p.from||0;st.innerHTML=`<div class="vis svgc" id="scF"></div><div class="sc-big" id="scN"></div>`;const draw=n=>{$('scF').innerHTML=fracSVG(n,d,p.bar?'bar':'');$('scN').innerHTML=fmtMath(p.bar&&d===10?`${n}/10 = 0.${n}`:`${n}/${d}`)};draw(from);
   for(let i=from+1;i<=p.n;i++)SC.T(400+(i-from)*700,()=>draw(i));return 800+(p.n-from)*700+900},
 clock(st,p){st.innerHTML=`<div class="vis svgc" id="scC"></div><div class="sc-big" id="scN">${p.h}시</div>`;let m=0;const tick=()=>{$('scC').innerHTML=clockSVG(p.h,m);if(m<60){m+=5;SC.T(260,tick)}else{$('scC').innerHTML=clockSVG(p.h+1,0);$('scN').textContent=`${p.h%12+1}시 · 60분 = 1시간`}};SC.T(500,tick);return 500+13*260+1500},
 angle(st,p){st.innerHTML=`<div class="vis svgr" id="scA"></div>`;let d=0;const tick=()=>{$('scA').innerHTML=angleSVG(d,true);if(d<p.deg){d=Math.min(p.deg,d+5);SC.T(40,tick)}};SC.T(300,tick);return 300+p.deg/5*40+1200},
 area(st,p){const s=Math.min(30,300/p.w);let g='';for(let y=0;y<p.h;y++)for(let x=0;x<p.w;x++)g+=`<rect id="scQ${y}_${x}" x="${10+x*s}" y="${10+y*s}" width="${s-2}" height="${s-2}" class="sc-cell"/>`;st.innerHTML=svgNS(p.w*s+20,p.h*s+20,g)+`<div class="sc-big" id="scN"></div>`;
   for(let y=0;y<p.h;y++)SC.T(400+y*700,()=>{for(let x=0;x<p.w;x++)$(`scQ${y}_${x}`).classList.add('on');$('scN').textContent=`${p.w} × ${y+1} = ${p.w*(y+1)}${p.unit||''}`});return 600+p.h*700+900},
 cycle(st,p){st.innerHTML=`<div class="sc-cycle">${p.items.map(([e,l],i)=>`${i?`<span class="sc-arrow" id="scR${i}" style="opacity:0">→</span>`:''}<span class="sc-step" id="scS${i}" style="opacity:0"><b>${e}</b>${l}</span>`).join('')}${p.loop?`<span class="sc-arrow" id="scLoop" style="opacity:0">↺</span>`:''}</div>`;
   p.items.forEach((_,i)=>SC.T(400+i*1100,()=>{$('scS'+i).style.opacity=1;if(i)$('scR'+i).style.opacity=1}));if(p.loop)SC.T(400+p.items.length*1100,()=>$('scLoop').style.opacity=1);return 600+p.items.length*1100+900},
 picture(st,p){st.innerHTML=`<div class="sc-pic sc-pop">${p.html}</div>`;return 2500},
};
/* ---------- 단원별 개념 설명 ---------- */
const LEARN={
 '1.kor.0':[{say:'낱말의 첫소리는 맨 처음 나는 소리예요. 곰은 그, 기역으로 시작해요.',scene:'picture',p:{html:'<div style="font-size:5rem">🐻</div><div class="sc-big">곰 → ㄱ</div>'}}],
 '1.kor.3':[{say:'자음과 모음을 합치면 글자가 돼요. 기역과 아를 합치면 가!',scene:'combine',p:{c:0,j:0}},{say:'니은과 오를 합치면 노!',scene:'combine',p:{c:2,j:8}}],
 '1.math.0':[{say:'하나씩 짚으며 세어 봐요. 마지막에 센 수가 모두의 개수예요.',scene:'count',p:{n:7,e:'⭐'}}],
 '1.math.2':[{say:'3에서 4만큼 앞으로 뛰면 7이에요. 3 더하기 4는 7!',scene:'jump',p:{start:3,steps:[1,1,1,1]}}],
 '1.math.3':[{say:'8에서 3만큼 뒤로 가면 5예요. 8 빼기 3은 5!',scene:'jump',p:{start:8,steps:[-1,-1,-1]}}],
 '1.math.4':[{say:'낱개 10개를 모으면 10개씩 묶음 하나가 돼요. 묶음 3개와 낱개 4개는 34예요.',scene:'tens',p:{n:34}}],
 '1.math.5':[{say:'긴바늘이 한 바퀴 돌면 60분이 지나고, 짧은바늘은 숫자 하나만큼 움직여요.',scene:'clock',p:{h:3}}],
 '1.math.7':[{say:'상자 모양, 둥근기둥 모양, 공 모양이 있어요. 3D로 돌려 보며 평평한 면과 둥근 면을 찾아봐요.',scene:'picture',p:{html:'<div style="font-size:4.5rem">📦 🥫 ⚽</div>'}}],
 '1.eng.2':[{say:'c, a, t. 소리를 이어서 읽으면 cat!',scene:'blend',p:{w:'cat',e:'🐱'}},{say:'p, i, g. pig!',scene:'blend',p:{w:'pig',e:'🐷'}}],
 '1.sci.4':[{say:'나무나 고무처럼 가벼운 것은 물에 뜨고, 돌이나 쇠는 가라앉아요.',scene:'picture',p:{html:'<div style="font-size:3.5rem">🪵🦆 <span style="font-size:2rem">뜸</span><br>🪨🔑 <span style="font-size:2rem">가라앉음</span></div>'}}],
 '2.kor.0':[{say:'먹어요는 소리 내어 읽으면 머거요예요. 받침 기역이 뒤로 넘어가서 소리 나지만, 쓸 때는 먹어요라고 써요.',scene:'picture',p:{html:'<div class="sc-big" style="font-size:3rem">먹 + 어요</div><div style="font-size:2rem">↓ 소리</div><div class="sc-big" style="font-size:3rem;color:var(--muted)">[머거요]</div>'}}],
 '2.kor.3':[{say:'깡충깡충은 토끼가 뛰는 모양, 멍멍은 강아지 소리를 흉내 낸 말이에요.',scene:'picture',p:{html:'<div style="font-size:4rem">🐰 깡충깡충<br>🐶 멍멍</div>'}}],
 '2.math.0':[{say:'세 자리 수는 백의 자리, 십의 자리, 일의 자리로 나눠요. 347은 300 더하기 40 더하기 7이에요.',scene:'place',p:{n:347}}],
 '2.math.1':[{say:'37 더하기 45는 먼저 40을 더해 77, 다음에 5를 더해 82예요.',scene:'jump',p:{start:37,steps:[40,5]}}],
 '2.math.2':[{say:'62 빼기 38은 먼저 30을 빼서 32, 다음에 8을 빼서 24예요.',scene:'jump',p:{start:62,steps:[-30,-8]}}],
 '2.math.4':[{say:'3씩 4묶음은 3을 네 번 더한 것과 같아요. 곱셈식으로 3 곱하기 4는 12!',scene:'groups',p:{n:3,m:4,e:'🍎'}}],
 '2.math.5':[{say:'6단은 6씩 커져요. 6, 12, 18, 24.',scene:'groups',p:{n:6,m:4,e:'⭐'}}],
 '2.math.6':[{say:'자의 눈금 0에 맞추고 끝이 닿은 눈금을 읽어요. 100센티미터는 1미터예요.',scene:'picture',p:{html:'<div class="vis svgr">'+'__RULER__'+'</div>'}}],
 '2.math.7':[{say:'긴바늘이 숫자 1을 가리키면 5분, 2를 가리키면 10분이에요. 한 칸에 5분씩!',scene:'clock',p:{h:2}}],
 '2.math.9':[{say:'삼각형은 변과 꼭짓점이 3개, 사각형은 4개예요. 쌓기나무는 3D로 돌려 볼 수 있어요.',scene:'picture',p:{html:'<div style="font-size:4rem">🔺 ⬛ ⬟ ⬢</div>'}}],
 '2.eng.1':[{say:'c, a, t. 가운데 모음 a가 애 소리를 내요.',scene:'blend',p:{w:'cat',e:'🐱'}},{say:'b, e, d. bed!',scene:'blend',p:{w:'bed',e:'🛏️'}}],
 '2.sci.2':[{say:'나비는 알, 애벌레, 번데기를 거쳐 나비가 돼요.',scene:'cycle',p:{items:[['🥚','알'],['🐛','애벌레'],['🫘','번데기'],['🦋','나비']],loop:true}}],
 '3.math.1':[{say:'12개를 3명에게 하나씩 차례로 나눠 주면 한 명에 4개씩이에요. 12 나누기 3은 4!',scene:'share',p:{total:12,k:3,e:'🍪'}}],
 '3.math.3':[{say:'14개를 4명에게 똑같이 나누면 3개씩 주고 2개가 남아요. 몫은 3, 나머지는 2예요.',scene:'share',p:{total:14,k:4,e:'🍬'}}],
 '3.math.4':[{say:'전체를 똑같이 4로 나눈 것 중 3을 4분의 3이라고 해요.',scene:'pie',p:{n:3,d:4}}],
 '3.math.5':[{say:'전체를 10칸으로 나눈 것 중 1칸은 0.1이에요. 3칸은 0.3!',scene:'pie',p:{n:3,d:10,bar:true}}],
 '3.math.7':[{say:'원의 중심에서 원 위의 한 점까지가 반지름, 원을 가로지르는 가장 긴 선이 지름이에요. 지름은 반지름의 2배!',scene:'picture',p:{html:'__CIRCLE__'}}],
 '3.sci.1':[{say:'배추흰나비는 알, 애벌레, 번데기, 어른벌레 순서로 자라요. 이것을 완전 탈바꿈이라고 해요.',scene:'cycle',p:{items:[['🥚','알'],['🐛','애벌레'],['🫘','번데기'],['🦋','어른벌레']],loop:true}}],
 '3.sci.2':[{say:'지구는 둥근 공 모양이고 바다가 육지보다 넓어요. 3D로 지구가 도는 모습을 볼 수 있어요.',scene:'picture',p:{html:'<div style="font-size:5rem">🌍 🌕</div>'}}],
 '4.math.3':[{say:'직각보다 작은 각은 예각이에요.',scene:'angle',p:{deg:60}},{say:'직각보다 크고 180도보다 작은 각은 둔각이에요.',scene:'angle',p:{deg:130}}],
 '4.math.4':[{say:'분모가 같으면 분자끼리 더해요. 6분의 2 더하기 6분의 3은 6분의 5!',scene:'pie',p:{from:2,n:5,d:6}}],
 '4.sci.4':[{say:'얼음이 녹으면 물, 물이 끓거나 증발하면 수증기가 돼요. 3D로 알갱이의 움직임을 볼 수 있어요.',scene:'cycle',p:{items:[['🧊','얼음 (고체)'],['💧','물 (액체)'],['♨️','수증기 (기체)']]}}],
 '4.sci.0':[{say:'지층은 아래부터 차례로 쌓여요. 보통 아래층이 더 오래되었어요.',scene:'picture',p:{html:'<div class="sc-layers"><i style="background:#d9c39a"></i><i style="background:#b08d5b"></i><i style="background:#8a6a43"></i><i style="background:#5f4a33"></i></div>'}}],
 '4.sci.1':[{say:'강낭콩은 씨가 싹 트고, 자라서 꽃이 피고, 열매를 맺어요.',scene:'cycle',p:{items:[['🫘','씨'],['🌱','싹'],['🌿','자람'],['🌸','꽃'],['🫛','열매']],loop:true}}],
 '4.sci.7':[{say:'바다의 물이 증발해 구름이 되고, 비가 되어 내려 다시 강과 바다로 가요.',scene:'cycle',p:{items:[['🌊','바다'],['♨️','증발'],['☁️','구름'],['🌧️','비'],['🏞️','강']],loop:true}}],
 '5.math.3':[{say:'4분의 2와 2분의 1은 크기가 같아요. 분모와 분자를 같은 수로 나누는 것을 약분이라고 해요.',scene:'pie',p:{n:2,d:4}}],
 '5.math.5':[{say:'직사각형의 넓이는 가로 곱하기 세로예요. 한 줄에 5칸씩 3줄이면 15제곱센티미터!',scene:'area',p:{w:5,h:3,unit:' cm²'}}],
 '5.math.8':[{say:'직육면체는 면 6개, 모서리 12개, 꼭짓점 8개예요. 3D 전개도로 접고 펴 보세요.',scene:'picture',p:{html:'<div style="font-size:5rem">📦</div>'}}],
 '5.sci.1':[{say:'태양에서 가까운 순서로 수성, 금성, 지구, 화성, 목성, 토성, 천왕성, 해왕성이에요.',scene:'cycle',p:{items:[['☀️','태양'],['🪨','수성'],['🟡','금성'],['🌍','지구'],['🔴','화성'],['🟠','목성'],['🪐','토성']]}}],
 '5.sci.7':[{say:'음식물은 입, 식도, 위, 작은창자, 큰창자를 차례로 지나가요.',scene:'cycle',p:{items:[['👄','입'],['🟫','식도'],['🫃','위'],['〰️','작은창자'],['🌀','큰창자']]}}],
 '6.math.2':[{say:'각기둥은 위아래 두 밑면이 평행하고 합동이에요. 3D로 면, 모서리, 꼭짓점을 세어 봐요.',scene:'picture',p:{html:'<div style="font-size:5rem">🧊 🔺</div>'}}],
 '6.math.5':[{say:'부피는 한 층의 쌓기 개수에 층수를 곱해요. 가로 4, 세로 3이면 한 층에 12개!',scene:'area',p:{w:4,h:3,unit:'개 (한 층)'}}],
 '6.math.6':[{say:'위에서 본 모양의 각 칸에 쓰인 수를 모두 더하면 쌓기나무의 개수예요. 3D로 돌려 확인해 봐요.',scene:'picture',p:{html:'__TOPGRID__'}}],
 '6.sci.0':[{say:'달은 초승달, 상현달, 보름달, 하현달, 그믐달 순서로 모양이 바뀌어요.',scene:'cycle',p:{items:[['🌒','초승달'],['🌓','상현달'],['🌕','보름달'],['🌗','하현달'],['🌘','그믐달']],loop:true}}],
 '6.sci.6':[{say:'풀을 메뚜기가 먹고, 메뚜기를 개구리가, 개구리를 뱀이 먹어요. 이것이 먹이 사슬이에요.',scene:'cycle',p:{items:[['🌾','벼'],['🦗','메뚜기'],['🐸','개구리'],['🐍','뱀']]}}],
};
function learnSteps(g,k,lv){const st=(LEARN[`${g}.${k}.${lv}`]||[]).map(s=>({...s,p:{...s.p}}));st.forEach(s=>{if(s.p.html){s.p.html=s.p.html.replace('__RULER__',rulerSVG(0,7)).replace('__CIRCLE__',`<div class="vis svgc">${circleSVG(5,'반지름 5 cm')}</div><div class="sc-big">지름 = 10 cm</div>`).replace('__TOPGRID__',topGridHTML([[2,1,0],[1,3,1],[1,0,0]])+'<div class="sc-big">2+1+1+3+1+1 = 9개</div>')}});return st}

/* ---------- 내레이션 ---------- */
function narrateOnly(t,lang){if(!S.voice)return;try{const u=new SpeechSynthesisUtterance(t);u.lang=lang==='en'?'en-US':'ko-KR';const v=voices.find(v=>v.lang&&v.lang.replace('_','-').startsWith(lang==='en'?'en':'ko'));if(v)u.voice=v;u.rate=lang==='en'?.8:.95;speechSynthesis.speak(u)}catch(e){}}
function narrate(t,lang,cb){let done=false;const fin=()=>{if(!done){done=true;cb&&cb()}};const est=Math.max(2200,t.length*(lang==='en'?90:140));
  if(!S.voice||!window.speechSynthesis){SC.T(est,fin);return}
  try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t);u.lang=lang==='en'?'en-US':'ko-KR';const v=voices.find(v=>v.lang&&v.lang.replace('_','-').startsWith(lang==='en'?'en':'ko'));if(v)u.voice=v;u.rate=lang==='en'?.8:.95;u.onend=fin;u.onerror=fin;speechSynthesis.speak(u);SC.T(est*2.2,fin)}catch(e){SC.T(est,fin)}}

/* ---------- 플레이어 ---------- */
let LS=null;
function openLesson(k,lv,after){const g=S.grade,L=LEVELS[k][lv];
  const steps=[{kind:'intro',say:`${L.name}. ${L.desc}.`}];learnSteps(g,k,lv).forEach(s=>steps.push({kind:'scene',...s}));
  genSet(k,lv,2).forEach((q,i)=>steps.push({kind:'example',q,i}));steps.push({kind:'end'});
  LS={k,lv,g,steps,i:0,playing:true,after};
  $('lsTag').textContent=`${g}학년 ${SUBJ[k].name} ${lv+1}단계`;$('lsTag').style.background=SUBJ[k].soft;$('lsTag').style.color=SUBJ[k].color;$('lsTitle').textContent=L.name;
  show('learn');playStep()}
function lsBar(){$('lsBar').innerHTML=LS.steps.map((_,i)=>`<i class="${i<LS.i?'ok':i===LS.i?'now':''}"></i>`).join('');$('lsPlay').textContent=LS.playing?'일시정지':'재생'}
function playStep(){SC.stop();try{speechSynthesis.cancel()}catch(e){}const s=LS.steps[LS.i],st=$('lsStage');lsBar();$('lsCap').textContent='';$('lsEnd').hidden=true;st.hidden=false;
  const next=()=>{if(LS&&LS.playing)SC.T(900,()=>lsGo(1))};
  if(s.kind==='intro'){const L=LEVELS[LS.k][LS.lv];st.innerHTML=`<div class="sc-intro" style="background:${SUBJ[LS.k].soft}"><span class="tag" style="background:var(--surface)">${esc(L.area||'')}</span><h2 style="font-size:2rem;color:${SUBJ[LS.k].color}">${esc(L.name)}</h2><p>${esc(L.desc)}</p></div>`;$('lsCap').textContent=s.say;narrate(s.say,'ko',next);return}
  if(s.kind==='scene'){const dur=SCENES[s.scene](st,s.p);$('lsCap').textContent=s.say;let a=false,b=false;const both=()=>{if(a&&b)next()};SC.T(dur,()=>{a=true;both()});narrate(s.say,'ko',()=>{b=true;both()});return}
  if(s.kind==='example'){const q=s.q;const ch=q.input==='num'?`<div class="numdisp" id="exAns" style="max-width:260px;margin:0 auto">?</div>`:`<div class="choices ${q.choices.length===3&&!q.choices.some(x=>String(x).length>7)?'c3':''} ${q.choices.some(x=>String(x).length>7)?'long':''}">${q.choices.map(x=>`<button disabled data-a="${esc(x)}" class="${q.big?'bigc':''}${String(x).length>7?' txt':''}">${fmtMath(esc(x))}${q.labels&&q.labels[x]?`<small>${esc(q.labels[x])}</small>`:''}</button>`).join('')}</div>`;
    st.innerHTML=`<div class="sc-ex"><span class="tag" style="background:var(--sun-soft)">예제 ${s.i+1}</span><div class="vis">${q.vis||''}</div><p class="qtext">${esc(q.text)}</p>${ch}<div class="fb" id="exFb"></div></div>`;
    $('lsCap').textContent='예제를 함께 풀어 봐요. 먼저 생각해 보세요.';
    narrate(q.say,q.lang||'ko',()=>{let n=3;const cd=()=>{if(!LS)return;$('exFb').textContent=n?`생각할 시간… ${n}`:'';if(n>0){n--;SC.T(1000,cd)}else{
      const lab=q.labels&&q.labels[q.ans]?q.labels[q.ans]:q.ans;if(q.input==='num'){$('exAns').textContent=q.ans;$('exAns').classList.add('right')}else st.querySelectorAll('button[data-a]').forEach(b=>{if(b.dataset.a===q.ans)b.classList.add('right')});
      $('exFb').className='fb ok';$('exFb').innerHTML=`정답은 ${fmtMath(esc(lab))}${q.reveal?` · ${esc(q.reveal)}`:''}`;narrate(`정답은 ${String(lab).replace(/(\d+)\/(\d+)/g,'$2분의 $1')}`,q.ansLang&&!q.input?q.ansLang:'ko',next)}};cd()});return}
  /* end */
  st.hidden=true;$('lsEnd').hidden=false;const L=LEVELS[LS.k][LS.lv];$('ls3d').hidden=!L.d3;
  const qs=encodeURIComponent(`EBS 초등 ${LS.g}학년 ${SUBJ[LS.k].name} ${L.name}`);$('lsVideo').href=`https://www.youtube.com/results?search_query=${qs}`;
  $('lsCap').textContent='이제 직접 풀어 볼까요?';narrate('이제 직접 풀어 볼까요?','ko');S.learned=S.learned||{};S.learned[`${LS.g}.${LS.k}.${LS.lv}`]=1;save();lsBar()}
function lsGo(d){if(!LS)return;const n=LS.i+d;if(n<0||n>=LS.steps.length)return;LS.i=n;playStep()}
function closeLesson(){SC.stop();try{speechSynthesis.cancel()}catch(e){}LS=null}
document.addEventListener('DOMContentLoaded',()=>{});
