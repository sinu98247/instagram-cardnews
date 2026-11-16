/* 3D 입체 학습 (Three.js r128, cdnjs) */
let threeP=null;
function loadThree(){if(window.THREE)return Promise.resolve();if(threeP)return threeP;threeP=new Promise((res,rej)=>{const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';s.onload=res;s.onerror=()=>{threeP=null;rej()};document.head.appendChild(s)});return threeP}
const D3={ren:null,raf:0,cleanup:null};
const D3_TITLE={solids:'입체도형 돌려 보기',solids1:'여러 가지 모양',net:'직육면체 전개도 접기',stack:'쌓기나무',earth:'지구와 달의 운동',solar:'태양계',states:'물질의 상태와 알갱이',layers:'지층과 화석'};
async function open3D(kind){show('d3');$('d3Title').textContent=D3_TITLE[kind]||'3D';$('d3Info').textContent='3D 도구를 불러오는 중…';$('d3Ctl').innerHTML='';$('d3Ctl').onclick=null;
  try{await loadThree()}catch(e){$('d3Info').textContent='3D 도구를 불러오지 못했어요. 인터넷 연결을 확인한 뒤 다시 열어 주세요.';return}
  close3D(true);const box=$('d3Stage');const w=box.clientWidth,h=Math.max(300,Math.min(520,w*0.8));
  const ren=new THREE.WebGLRenderer({antialias:true,alpha:true});ren.setPixelRatio(Math.min(2,devicePixelRatio||1));ren.setSize(w,h);box.innerHTML='';box.appendChild(ren.domElement);
  const scene=new THREE.Scene();const cam=new THREE.PerspectiveCamera(45,w/h,.1,200);cam.position.set(0,1.6,6);cam.lookAt(0,0,0);
  scene.add(new THREE.AmbientLight(0xffffff,.55));const dl=new THREE.DirectionalLight(0xffffff,.8);dl.position.set(3,5,4);scene.add(dl);
  const root=new THREE.Group();scene.add(root);
  /* 드래그로 돌리기 */
  let drag=null,rx=.35,ry=-.6,auto=true;const el=ren.domElement;el.style.touchAction='none';
  el.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY];auto=false;el.setPointerCapture(e.pointerId)});
  el.addEventListener('pointermove',e=>{if(!drag)return;ry+=(e.clientX-drag[0])*.01;rx=Math.max(-1.4,Math.min(1.4,rx+(e.clientY-drag[1])*.01));drag=[e.clientX,e.clientY]});
  el.addEventListener('pointerup',()=>drag=null);
  const ctx={scene,root,cam,ren,tick:null,setRot:(a,b)=>{rx=a;ry=b;auto=false},noRotate:false};
  D3.ren=ren;(D3_SCENES[kind]||D3_SCENES.solids)(ctx);
  let t0=performance.now();const loop=t=>{const dt=(t-t0)/1000;t0=t;if(!ctx.noRotate){if(auto)ry+=dt*.4;root.rotation.set(rx,ry,0)}ctx.tick&&ctx.tick(dt,t/1000);ren.render(scene,cam);D3.raf=requestAnimationFrame(loop)};D3.raf=requestAnimationFrame(loop);
  $('d3Hint').textContent=ctx.noRotate?'':'손가락으로 끌어서 돌려 보세요.'}
function close3D(keepView){cancelAnimationFrame(D3.raf);if(D3.ren){D3.ren.dispose();D3.ren.forceContextLoss&&D3.ren.forceContextLoss();D3.ren=null}if(!keepView)$('d3Stage').innerHTML=''}
const mat=(c,o={})=>new THREE.MeshStandardMaterial({color:c,roughness:.55,metalness:.05,...o});
function edged(geo,color){const g=new THREE.Group();g.add(new THREE.Mesh(geo,mat(color,{polygonOffset:true,polygonOffsetFactor:1})));g.add(new THREE.LineSegments(new THREE.EdgesGeometry(geo,25),new THREE.LineBasicMaterial({color:0x1e2940})));return g}
function ctlButtons(list,onPick){$('d3Ctl').innerHTML=list.map((x,i)=>`<button data-i="${i}" aria-pressed="${i===0}">${x}</button>`).join('');$('d3Ctl').onclick=e=>{const b=e.target.closest('button');if(!b)return;$('d3Ctl').querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));onPick(+b.dataset.i)};onPick(0)}
function label(text,color='#1e2940'){const c=document.createElement('canvas');c.width=256;c.height=64;const x=c.getContext('2d');x.font='bold 34px sans-serif';x.fillStyle=color;x.textAlign='center';x.fillText(text,128,44);const s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(c),depthTest:false}));s.scale.set(1.4,.35,1);return s}

const D3_SCENES={
 solids(ctx,simple){const list=simple?[['상자 모양',()=>new THREE.BoxGeometry(1.8,1.2,1.2),'평평한 면만 있어요. 잘 쌓을 수 있어요.'],['둥근기둥 모양',()=>new THREE.CylinderGeometry(.8,.8,1.6,48),'눕히면 굴러가고 세우면 쌓을 수 있어요.'],['공 모양',()=>new THREE.SphereGeometry(1,48,32),'모든 방향으로 잘 굴러가요. 쌓기 어려워요.']]
   :[['정육면체',()=>new THREE.BoxGeometry(1.5,1.5,1.5),'면 6 · 모서리 12 · 꼭짓점 8'],['직육면체',()=>new THREE.BoxGeometry(2.2,1.3,1),'면 6 · 모서리 12 · 꼭짓점 8'],['삼각기둥',()=>new THREE.CylinderGeometry(1,1,1.8,3),'면 5 · 모서리 9 · 꼭짓점 6'],['오각기둥',()=>new THREE.CylinderGeometry(1,1,1.6,5),'면 7 · 모서리 15 · 꼭짓점 10'],['사각뿔',()=>new THREE.ConeGeometry(1.2,1.8,4),'면 5 · 모서리 8 · 꼭짓점 5'],['원기둥',()=>new THREE.CylinderGeometry(.9,.9,1.8,48),'밑면 2개(원) · 옆면은 굽은 면'],['원뿔',()=>new THREE.ConeGeometry(1,1.9,48),'밑면 1개(원) · 꼭짓점 1개'],['구',()=>new THREE.SphereGeometry(1.1,48,32),'어느 방향에서 보아도 원 모양']];
   let cur=null;const cols=[0x2c78dc,0xe2553f,0x24945f,0x8656d3,0xf2b01e,0x2c78dc,0xe2553f,0x24945f];
   ctlButtons(list.map(x=>x[0]),i=>{if(cur)ctx.root.remove(cur);cur=edged(list[i][1](),cols[i%cols.length]);ctx.root.add(cur);$('d3Info').textContent=`${list[i][0]}: ${list[i][2]}`})},
 solids1(ctx){D3_SCENES.solids(ctx,true)},
 net(ctx){const g=new THREE.Group();ctx.root.add(g);const cols=[0xf2b01e,0x2c78dc,0xe2553f,0x24945f,0x8656d3,0x5fd49a];const plane=c=>{const m=new THREE.Mesh(new THREE.PlaneGeometry(1,1),mat(c,{side:THREE.DoubleSide}));m.rotation.x=-Math.PI/2;const w=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.PlaneGeometry(1,1)),new THREE.LineBasicMaterial({color:0x1e2940}));w.rotation.x=-Math.PI/2;const o=new THREE.Group();o.add(m,w);return o};
   const bottom=plane(cols[0]);g.add(bottom);const hinges=[];let topH;
   for(let i=0;i<4;i++){const turn=new THREE.Group();turn.rotation.y=i*Math.PI/2;const h=new THREE.Group();h.position.z=.5;const f=plane(cols[i+1]);f.position.z=.5;h.add(f);turn.add(h);g.add(turn);hinges.push(h);
     if(i===0){topH=new THREE.Group();topH.position.z=1;const tf=plane(cols[5]);tf.position.z=.5;topH.add(tf);h.add(topH);hinges.push(topH)}}
   g.position.y=-.3;g.scale.setScalar(1.05);let t=0,target=0;
   $('d3Ctl').innerHTML='<button id="nFold">접기</button><button id="nOpen">펼치기</button><label class="small" style="display:flex;align-items:center;gap:8px">펼친 정도 <input type="range" id="nR" min="0" max="100" value="0"></label>';
   $('nFold').onclick=()=>target=0;$('nOpen').onclick=()=>target=1;$('nR').oninput=e=>{target=t=+e.target.value/100};
   ctx.tick=dt=>{if(Math.abs(target-t)>.001)t+=Math.sign(target-t)*Math.min(Math.abs(target-t),dt*.6);const a=(1-t)*Math.PI/2;hinges.forEach(h=>h.rotation.x=-a);g.position.z=-.55*t;$('nR').value=Math.round(t*100)};
   $('d3Info').textContent='정육면체를 펼치면 정사각형 6개로 된 전개도가 돼요. 같은 색끼리 마주 보는 면은 없어요.'},
 stack(ctx){let grp=null,h;const build=()=>{if(grp)ctx.root.remove(grp);grp=new THREE.Group();h=Array.from({length:3},()=>Array.from({length:3},()=>Math.floor(Math.random()*4)));h[1][1]=Math.max(1,h[1][1]);const geo=new THREE.BoxGeometry(.96,.96,.96);
   h.forEach((r,z)=>r.forEach((n,x)=>{for(let y=0;y<n;y++){const c=edged(geo,[0xf2b01e,0x2c78dc,0xe2553f][y]);c.position.set(x-1,y-.9,z-1);grp.add(c)}}));ctx.root.add(grp);$('d3Info').textContent='쌓기나무는 모두 몇 개일까요? 돌려 보며 세어 보세요.'};
   build();ctlButtons(['돌려 보기','위에서','앞에서','옆에서','정답 보기','새로 쌓기'],i=>{if(i===1)ctx.setRot(Math.PI/2,0);if(i===2)ctx.setRot(0,0);if(i===3)ctx.setRot(0,-Math.PI/2);if(i===4)$('d3Info').textContent=`모두 ${h.flat().reduce((a,b)=>a+b,0)}개 · 위에서 본 칸의 수: ${h.map(r=>r.join(' ')).join(' / ')}`;if(i===5)build()})},
 earth(ctx){ctx.noRotate=true;ctx.cam.position.set(0,5,9);ctx.cam.lookAt(0,0,0);const sun=new THREE.Mesh(new THREE.SphereGeometry(1,32,24),new THREE.MeshBasicMaterial({color:0xffc94d}));ctx.scene.add(sun);const pl=new THREE.PointLight(0xffffff,1.6,0);ctx.scene.add(pl);ctx.scene.children.forEach(o=>{if(o.isDirectionalLight)o.intensity=0});
   const orbit=new THREE.Group();ctx.scene.add(orbit);const tilt=new THREE.Group();tilt.position.x=5;tilt.rotation.z=23.5*Math.PI/180;orbit.add(tilt);
   const c=document.createElement('canvas');c.width=256;c.height=128;const x=c.getContext('2d');x.fillStyle='#2c78dc';x.fillRect(0,0,256,128);x.fillStyle='#3fae6a';[[30,40,40,30],[100,30,30,50],[150,60,50,35],[200,30,35,40]].forEach(r=>x.fillRect(...r));
   const earth=new THREE.Mesh(new THREE.SphereGeometry(.6,32,24),new THREE.MeshStandardMaterial({map:new THREE.CanvasTexture(c)}));tilt.add(earth);
   const axis=new THREE.Mesh(new THREE.CylinderGeometry(.02,.02,1.7),new THREE.MeshBasicMaterial({color:0xd2483a}));tilt.add(axis);
   const moonO=new THREE.Group();moonO.position.x=5;orbit.add(moonO);const moon=new THREE.Mesh(new THREE.SphereGeometry(.18,24,16),mat(0xdddddd));moon.position.x=1.3;moonO.add(moon);
   const ring=new THREE.Mesh(new THREE.RingGeometry(4.98,5.02,96),new THREE.MeshBasicMaterial({color:0x8899aa,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ctx.scene.add(ring);
   let sp=1,mode=0;ctlButtons(['자전 + 공전','자전만 (낮과 밤)','달의 모양','빠르게','느리게'],i=>{if(i<3)mode=i;if(i===3)sp=3;if(i===4)sp=.4;
     $('d3Info').textContent=['지구는 하루에 한 바퀴 자전하고, 1년에 한 바퀴 태양 둘레를 공전해요. 자전축(빨간 막대)이 기울어져 계절이 생겨요.','태양 빛을 받는 쪽은 낮, 반대쪽은 밤이에요. 지구가 자전하면서 낮과 밤이 바뀌어요.','달은 약 한 달에 한 번 지구 둘레를 돌아요. 태양 빛을 받는 부분이 보이는 모양이 바뀌어 달의 모양이 변해요.'][mode]+(i>2?` (속도 ×${sp})`:'')});
   ctx.tick=dt=>{earth.rotation.y+=dt*2*sp;if(mode!==1)orbit.rotation.y+=dt*.15*sp;moonO.rotation.y+=dt*(mode===2?.9:.6)*sp;if(mode===2){ctx.cam.position.lerp(new THREE.Vector3(Math.cos(-orbit.rotation.y)*7.5,1.5,Math.sin(-orbit.rotation.y)*7.5),.05)}else ctx.cam.position.lerp(new THREE.Vector3(0,5,9),.05);ctx.cam.lookAt(mode===2?new THREE.Vector3(Math.cos(-orbit.rotation.y)*5,0,Math.sin(-orbit.rotation.y)*5):new THREE.Vector3(0,0,0))}},
 solar(ctx){ctx.noRotate=true;ctx.cam.position.set(0,14,18);ctx.cam.lookAt(0,0,0);ctx.scene.children.forEach(o=>{if(o.isDirectionalLight)o.intensity=0});ctx.scene.add(new THREE.PointLight(0xffffff,1.5,0));
   ctx.scene.add(new THREE.Mesh(new THREE.SphereGeometry(1,32,24),new THREE.MeshBasicMaterial({color:0xffc94d})));const lab=label('태양','#b07a00');lab.position.y=1.5;ctx.scene.add(lab);
   const P=[['수성',.15,1.8,0x9c9c9c,4.1],['금성',.25,2.5,0xe6c27a,1.6],['지구',.27,3.3,0x2c78dc,1],['화성',.2,4.1,0xd2483a,.53],['목성',.6,5.4,0xd9a066,.084],['토성',.5,6.8,0xe8d08a,.034],['천왕성',.35,8,0x8fd3e8,.012],['해왕성',.34,9,0x3d5fd9,.006]];
   const objs=P.map(([n,r,d,c,s])=>{const o=new THREE.Group();ctx.scene.add(o);const m=new THREE.Mesh(new THREE.SphereGeometry(r,24,16),mat(c));m.position.x=d;o.add(m);if(n==='토성'){const rg=new THREE.Mesh(new THREE.RingGeometry(r*1.3,r*2,48),new THREE.MeshBasicMaterial({color:0xcbb67a,side:THREE.DoubleSide}));rg.rotation.x=-Math.PI/2.4;m.add(rg)}const l=label(n);l.position.set(d,r+.45,0);o.add(l);
     const ring=new THREE.Mesh(new THREE.RingGeometry(d-.01,d+.01,128),new THREE.MeshBasicMaterial({color:0x667788,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ctx.scene.add(ring);o.rotation.y=Math.random()*6;return[o,s]});
   let sp=1;ctlButtons(['보통 속도','빠르게','멈추기'],i=>{sp=[1,4,0][i]});$('d3Info').textContent='태양에서 가까운 순서: 수성, 금성, 지구, 화성, 목성, 토성, 천왕성, 해왕성. 가까운 행성일수록 빨리 돌아요. (크기와 거리는 실제 비율이 아니에요)';
   ctx.tick=dt=>objs.forEach(([o,s])=>o.rotation.y+=dt*s*.8*sp)},
 states(ctx){const N=64,parts=[];const geo=new THREE.SphereGeometry(.13,16,12);const m=mat(0x2c78dc);for(let i=0;i<N;i++){const p=new THREE.Mesh(geo,m);ctx.root.add(p);parts.push({m:p,v:new THREE.Vector3((Math.random()-.5),(Math.random()-.5),(Math.random()-.5)),home:new THREE.Vector3((i%4)*.4-.6,Math.floor(i/16)*.4-1.2,(Math.floor(i/4)%4)*.4-.6)})}
   const boxG=new THREE.BoxGeometry(3,3,3);ctx.root.add(new THREE.LineSegments(new THREE.EdgesGeometry(boxG),new THREE.LineBasicMaterial({color:0x5d6a84})));parts.forEach(p=>p.m.position.copy(p.home));
   let mode=0;ctlButtons(['고체 (얼음)','액체 (물)','기체 (수증기)'],i=>{mode=i;m.color.set([0x9fd3ff,0x2c78dc,0xc8d3e6][i]);$('d3Info').textContent=['고체: 알갱이가 제자리에서 떨기만 해요. 모양과 부피가 일정해요.','액체: 알갱이가 서로 붙어 미끄러지듯 움직여요. 그릇에 따라 모양이 바뀌어요.','기체: 알갱이가 멀리 떨어져 빠르게 날아다녀요. 그릇을 가득 채워요.'][i]});
   ctx.tick=(dt,t)=>{parts.forEach((p,i)=>{const pos=p.m.position;if(mode===0){pos.set(p.home.x+Math.sin(t*20+i)*.03,p.home.y+Math.cos(t*23+i)*.03,p.home.z+Math.sin(t*17+i*2)*.03)}else{const sp=mode===1?.8:3.2;pos.addScaledVector(p.v,dt*sp);if(mode===1)p.v.y-=dt*1.5;
     ['x','y','z'].forEach(a=>{const lim=1.37;if(pos[a]<-lim){pos[a]=-lim;p.v[a]=Math.abs(p.v[a])*(mode===1&&a==='y'?.3:1)}if(pos[a]>(mode===1&&a==='y'?-.2:lim)){pos[a]=mode===1&&a==='y'?-.2:lim;p.v[a]=-Math.abs(p.v[a])}});if(mode===2&&p.v.length()<.6)p.v.multiplyScalar(1.5)}})}},
 layers(ctx){const cols=[0x5f4a33,0x8a6a43,0xb08d5b,0xd9c39a,0xa7b9c9];const names=['진흙이 굳은 층 (가장 오래됨)','모래층','자갈층','모래층','흙 (가장 최근)'];const g=new THREE.Group();ctx.root.add(g);const ls=[];
   cols.forEach((c,i)=>{const b=edged(new THREE.BoxGeometry(3,.45,2),c);b.position.y=i*.47-1;g.add(b);ls.push(b)});const shell=new THREE.Mesh(new THREE.SphereGeometry(.22,16,12,0,Math.PI*2,0,Math.PI/2),mat(0xf0e6d2));shell.position.set(.6,ls[1].position.y,1.01);shell.rotation.x=Math.PI/2;g.add(shell);
   let t=0,target=0;ctlButtons(['쌓인 모습','층 나누어 보기'],i=>{target=i});$('d3Info').textContent='지층은 아래부터 차례로 쌓여요. 아래층이 더 오래되었어요. 둘째 층에 조개 화석이 있어요. 옛날 이곳은 바다였을 거예요.';
   ctx.tick=dt=>{t+=(target-t)*Math.min(1,dt*3);ls.forEach((b,i)=>b.position.y=i*(.47+t*.35)-1-t*.6);shell.position.y=ls[1].position.y}},
};
