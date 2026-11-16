/* 공통 그림 도구: 분수, 각도, 그래프, 도형 (3~6학년) */
const gcd=(a,b)=>b?gcd(b,a%b):a;
const lcm=(a,b)=>a/gcd(a,b)*b;
const dec=x=>String(+(+x).toFixed(3));
const fr=(n,d)=>`${n}/${d}`;
function frSimp(n,d){const g=gcd(n,d);return fr(n/g,d/g)}
function frMixed(n,d){const g=gcd(n,d);n/=g;d/=g;if(d===1)return String(n);if(n>d)return `${Math.floor(n/d)} ${n%d}/${d}`;return fr(n,d)}
/* "3/5", "1 2/3" 를 세로 분수로 */
function fmtMath(s){return String(s).replace(/(\d+)\/(\d+)/g,'<span class="frac"><i>$1</i><i>$2</i></span>')}
function fracSVG(n,d,type){if(type==='bar'){const w=220/d;let g=`<svg viewBox="0 0 230 50" class="fsvg">`;for(let i=0;i<d;i++)g+=`<rect x="${5+i*w}" y="5" width="${w}" height="40" class="${i<n?'fon':'foff'}"/>`;return g+'</svg>'}
  let g='<svg viewBox="0 0 100 100" class="fsvg">';if(d===1)return g+`<circle cx="50" cy="50" r="44" class="${n?'fon':'foff'}"/></svg>`;
  for(let i=0;i<d;i++){const a0=(i/d)*2*Math.PI-Math.PI/2,a1=((i+1)/d)*2*Math.PI-Math.PI/2;const big=1/d>.5?1:0;g+=`<path d="M50 50 L${50+44*Math.cos(a0)} ${50+44*Math.sin(a0)} A44 44 0 ${big} 1 ${50+44*Math.cos(a1)} ${50+44*Math.sin(a1)}Z" class="${i<n?'fon':'foff'}"/>`}return g+'</svg>'}
function angleSVG(deg,showNum){const r=Math.PI/180;const x=100+80*Math.cos(-deg*r),y=100+80*Math.sin(-deg*r);const ax=100+28*Math.cos(-deg*r),ay=100+28*Math.sin(-deg*r);
  return `<svg viewBox="0 0 200 120" class="asvg"><line x1="100" y1="100" x2="185" y2="100" class="aray"/><line x1="100" y1="100" x2="${x}" y2="${y}" class="aray"/><path d="M128 100 A28 28 0 ${deg>180?1:0} 0 ${ax} ${ay}" class="aarc"/>${deg===90?'<rect x="100" y="88" width="12" height="12" class="aarc"/>':''}${showNum?`<text x="140" y="80" class="atxt">${deg}°</text>`:''}<circle cx="100" cy="100" r="3" class="adot"/></svg>`}
function lineChartSVG(labels,vals,unit){const W=280,H=150,L=30,B=24,mx=Math.ceil(Math.max(...vals)/5)*5||5;const x=i=>L+i*(W-L-10)/(labels.length-1),y=v=>H-B-(v/mx)*(H-B-12);
  let g=`<svg viewBox="0 0 ${W} ${H}" class="csvg">`;for(let v=0;v<=mx;v+=mx/5)g+=`<line x1="${L}" x2="${W-6}" y1="${y(v)}" y2="${y(v)}" class="cgrid"/><text x="${L-4}" y="${y(v)+3}" text-anchor="end" class="ctxt">${v}</text>`;
  g+=`<polyline points="${vals.map((v,i)=>x(i)+','+y(v)).join(' ')}" class="cline"/>`+vals.map((v,i)=>`<circle cx="${x(i)}" cy="${y(v)}" r="3.5" class="cdot"/><text x="${x(i)}" y="${H-8}" text-anchor="middle" class="ctxt">${labels[i]}</text>`).join('');
  return g+`<text x="${L}" y="9" class="ctxt">(${unit})</text></svg>`}
function pieChartSVG(parts){let a=-Math.PI/2,g='<svg viewBox="0 0 220 120" class="csvg">';const cols=['var(--kor)','var(--math)','var(--sci)','var(--sun)','var(--eng)'];
  parts.forEach(([lab,p],i)=>{const a1=a+p/100*2*Math.PI;const big=p>50?1:0;g+=`<path d="M60 60 L${60+52*Math.cos(a)} ${60+52*Math.sin(a)} A52 52 0 ${big} 1 ${60+52*Math.cos(a1)} ${60+52*Math.sin(a1)}Z" style="fill:${cols[i]}" class="cpie"/>`;g+=`<rect x="128" y="${14+i*20}" width="12" height="12" style="fill:${cols[i]}"/><text x="146" y="${24+i*20}" class="ctxt" style="font-size:11px">${lab} ${p}%</text>`;a=a1});return g+'</svg>'}
function rectSVG(w,h,kind){/* kind: rect | tri | para */const s=Math.min(200/w,100/h,22);const W=w*s,H=h*s,ox=20,oy=10;let shape;
  if(kind==='tri')shape=`<polygon points="${ox},${oy+H} ${ox+W},${oy+H} ${ox+W*0.35},${oy}" class="shape"/><line x1="${ox+W*0.35}" y1="${oy}" x2="${ox+W*0.35}" y2="${oy+H}" class="dash"/>`;
  else if(kind==='para')shape=`<polygon points="${ox+W*0.25},${oy} ${ox+W*1.25},${oy} ${ox+W},${oy+H} ${ox},${oy+H}" class="shape"/><line x1="${ox+W*0.25}" y1="${oy}" x2="${ox+W*0.25}" y2="${oy+H}" class="dash"/>`;
  else shape=`<rect x="${ox}" y="${oy}" width="${W}" height="${H}" class="shape"/>`;
  const ex=kind==='para'?W*0.25:0;
  return `<svg viewBox="0 0 ${W*(kind==='para'?1.25:1)+70} ${H+40}" class="rsvg">${shape}<text x="${ox+W/2}" y="${oy+H+20}" text-anchor="middle" class="ctxt" style="font-size:13px">${w} cm</text><text x="${ox+W*(kind==='para'?1.25:1)+6}" y="${oy+H/2+4}" class="ctxt" style="font-size:13px">${h} cm${kind&&kind!=='rect'?' (높이)':''}</text></svg>`}
function circleSVG(r,label){return `<svg viewBox="0 0 140 120" class="rsvg"><circle cx="60" cy="60" r="48" class="shape"/><line x1="60" y1="60" x2="108" y2="60" class="aray"/><circle cx="60" cy="60" r="3" class="adot"/><text x="84" y="52" text-anchor="middle" class="ctxt" style="font-size:13px">${label||r+' cm'}</text></svg>`}
function topGridHTML(h){return `<table class="tgrid">${h.map(r=>`<tr>${r.map(v=>`<td>${v||''}</td>`).join('')}</tr>`).join('')}</table>`}
function picGraphHTML(rows,big,small,unit){return `<table class="tbl pg">${rows.map(([n,v])=>`<tr><td>${n}</td><td style="text-align:left">${big.repeat(Math.floor(v/10))}${small.repeat(v%10)}</td></tr>`).join('')}</table><div class="small muted" style="font-size:.9rem">${big} 10${unit} · ${small} 1${unit}</div>`}
const numKo=n=>{const u=['','만','억','조'];let out=[],i=0;while(n>0){const c=n%10000;if(c)out.unshift(c+u[i]);n=Math.floor(n/10000);i++}return out.join(' ')};
