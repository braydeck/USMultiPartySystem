#!/usr/bin/env python3
"""Render the two-paradigm cluster comparison: k=5 + residualization (production)
vs k=5 no residualization. From cluster_explorer_data.json."""
import json
D=json.load(open('analysis/efa/cluster_explorer_data.json'))
DATA_JSON=json.dumps(D)

HTML=r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>STV — Residualization: on vs off (k=5)</title>
<style>
:root{
  --ink:#0f172a;--fg2:#475569;--fg3:#94a3b8;--bg:#f8fafc;--card:#fff;--line:#e2e8f0;--sunken:#f1f5f9;
  --good:#16a34a;--good-bg:#dcfce7;--split:#d97706;--split-bg:#fef3c7;--absorb:#64748b;--absorb-bg:#e2e8f0;
  --hi:#b91c1c;--lo:#1d4ed8;--cross:#7c3aed;--cross-bg:#ede9fe;
  font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5}
.wrap{max-width:1080px;margin:0 auto;padding:40px 28px 100px}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--lo)}
h1{font-size:34px;font-weight:800;letter-spacing:-.02em;margin:.2em 0 .15em}
h1 em{font-style:normal;color:var(--lo)}
.sub{color:var(--fg2);font-size:15px;max-width:780px}
.meta{display:flex;gap:24px;flex-wrap:wrap;font-size:12px;color:var(--fg3);border-top:1px solid var(--line);margin-top:18px;padding-top:12px}
h2{font-size:22px;font-weight:700;letter-spacing:-.01em;margin:0}
section{border-top:1px solid var(--line);margin-top:40px;padding-top:24px}
.lede{color:var(--fg2);font-size:14px;max-width:800px;margin:.4em 0 18px}
table.sm{border-collapse:collapse;width:100%;font-size:13px}
table.sm th,table.sm td{padding:8px 10px;text-align:center;border-bottom:1px solid var(--line)}
table.sm th{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--fg3);font-weight:700}
table.sm td.party{text-align:left;font-weight:700}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px;vertical-align:middle}
.verdict{display:inline-block;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px}
.v-preserved{background:var(--good-bg);color:var(--good)}.v-split{background:var(--split-bg);color:var(--split)}
.v-absorbed{background:var(--absorb-bg);color:var(--absorb)}.v-absent{background:#fee2e2;color:#b91c1c}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
.cc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;border-top:4px solid var(--ctop,#94a3b8)}
.cc h3{margin:0 0 2px;font-size:16px;font-weight:700}
.cc .wt{font-size:12px;color:var(--fg3);font-weight:600}
.comp{display:flex;gap:5px;flex-wrap:wrap;margin:8px 0 8px}
.pill{font-size:11px;font-weight:700;color:#fff;padding:2px 8px;border-radius:999px}
.xc{display:inline-block;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px;background:var(--cross-bg);color:var(--cross);margin:2px 0 6px}
.xc.no{background:var(--absorb-bg);color:var(--absorb)}
.fac{margin:8px 0}
.fac .row{display:grid;grid-template-columns:74px 1fr 34px;align-items:center;gap:8px;margin:3px 0}
.fac .lab{font-size:11px;color:var(--fg2);text-align:right}
.fac .fv{font-size:11px;color:var(--fg3);font-variant-numeric:tabular-nums}
.track{position:relative;height:12px;background:var(--sunken);border-radius:6px;overflow:hidden}
.mid{position:absolute;left:50%;top:0;width:1px;height:100%;background:#cbd5e1}
.fill{position:absolute;top:0;height:100%;border-radius:6px;opacity:.85}
.strength{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:12px;color:var(--fg2)}
.sbar{flex:1;height:8px;background:var(--sunken);border-radius:4px;overflow:hidden}
.sfill{height:100%;background:var(--lo);border-radius:4px}
.more{font-size:12px;color:var(--lo);cursor:pointer;font-weight:600;margin-top:6px;display:inline-block}
.detail{display:none;margin-top:12px;border-top:1px dashed var(--line);padding-top:12px}.detail.on{display:block}
.sech{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--fg3);font-weight:700;margin:10px 0 6px}
.pol .row{display:grid;grid-template-columns:1fr 120px 64px;align-items:center;gap:8px;margin:2px 0;font-size:11.5px}
.pol .pl{color:var(--fg2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pbar{position:relative;height:10px;background:var(--sunken);border-radius:5px}
.pfill{position:absolute;left:0;top:0;height:100%;border-radius:5px;background:#cbd5e1}
.pmark{position:absolute;top:-2px;width:2px;height:14px;background:#0f172a}
.dev{font-weight:700}.dev.up{color:var(--hi)}.dev.dn{color:var(--lo)}
.demo{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.demo .d{background:var(--sunken);border-radius:8px;padding:7px 9px}
.demo .dl{font-size:9.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--fg3)}
.demo .dv{font-size:15px;font-weight:700}.demo .dd{font-size:10px;font-weight:700}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid var(--lo);border-radius:0 10px 10px 0;padding:14px 18px;margin:10px 0;font-size:13.5px;color:var(--fg2)}
.callout.x{border-left-color:var(--cross)}.callout.s{border-left-color:var(--split)}
.callout b{color:var(--ink)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--fg2);margin:10px 0}
.note{font-size:11.5px;color:var(--fg3);font-style:italic;margin-top:10px}
</style></head><body><div class="wrap">

<div class="eyebrow">EFA robustness · CES 2024 · k fixed at 5</div>
<h1>Residualization: <em>on vs off</em></h1>
<p class="sub">Both paradigms use the same 5-factor space — the only difference is whether the two culture factors (Religious Traditionalism, Populist Conservatism) are residualized on the enforcement axis before clustering. Holding k constant makes this a clean controlled A/B: every difference below is attributable to residualization alone, so we can read exactly which parties it sharpens and which blends it dissolves.</p>
<div class="meta"><span id="m-n"></span><span>Left: k=5 + residualization (the production 9 parties) · Right: k=5, raw scores</span></div>

<section>
<h2>What residualization does to each party</h2>
<p class="lede">Without residualization, do the production parties still emerge? <b>Preserved</b> = one cluster still captures it; <b>split</b> = scatters; <b>absorbed</b> = folded into another cluster.</p>
<div id="matrix"></div>
<div class="legend">
  <span><span class="dot" style="background:var(--good)"></span>Preserved</span>
  <span><span class="dot" style="background:var(--split)"></span>Split</span>
  <span><span class="dot" style="background:var(--absorb)"></span>Absorbed</span>
  <span style="color:var(--fg3)">·  conf = production assignment confidence (mean max posterior); how cleanly the cluster is defined</span>
</div>
<div id="findings"></div>
</section>

<section>
<h2>Preserved parties — how they shift</h2>
<p class="lede">Six parties survive without residualization. Bars show the no-resid cluster's policy support; the marker is the production baseline and a <span class="dev up">red</span>/<span class="dev dn">blue</span> flag marks any ≥10-point shift. Most move little — confirming these are real structure.</p>
<div class="grid" id="preserved"></div>
</section>

<section>
<h2>The blends residualization hides</h2>
<p class="lede">Where parties split/absorb, residualization-off forms these blends instead. The question that matters: are they <b>genuinely cross-cutting</b> (combining positions the left–right axis separates) — and so worth exploring — or just the weakly-separated left bloc collapsing into coarser groups?</p>
<div id="xc-legend" class="legend"><span><span class="dot" style="background:var(--cross)"></span>Cross-cutting (mixes enforcement / skepticism / values against type)</span><span><span class="dot" style="background:var(--absorb)"></span>Bloc merge (coarser version of existing parties)</span></div>
<div class="grid" id="blends"></div>
<div id="insight"></div>
</section>

<section>
<h2>Reference — the nine baseline parties</h2>
<div class="grid" id="baseline"></div>
</section>

<p class="note" id="govnote"></p>
<p class="note">Reproduction: cached DPGMM labels, N=<span id="m-n2"></span>; approximate re-run (oblimin; "Not sure" govt-trust → midpoint). Strength = production assignment confidence from the real posteriors (typology_cluster_assignments.csv). Scripts in analysis/efa/.</p>

</div>
<script>
const DATA=__DATA__;
const PC={PRG:'#15803d',DSA:'#22c55e',LIB:'#0284c7',SD:'#38bdf8',STY:'#8a70b8',CUP:'#825a27',CON:'#e68c2c',POP:'#d34812',NAT:'#a01d2a',C7:'#9ca3af'};
const PNAME={PRG:'Progressive',DSA:'Dem. Socialist',LIB:'Liberal',SD:'Social Democrat',STY:'Solidarity',CUP:'Civic Union',CON:'Conservative',POP:'Populist',NAT:'Nationalist',C7:'Blue Dog (dropped)'};
const ORDER=['PRG','DSA','LIB','SD','STY','CUP','POP','CON','NAT'];
const POL=DATA.pol_items;
const DEMO=[['ideo','Ideology 1-5'],['dem','% Dem'],['rep','% Rep'],['ind','% Ind'],['age','Median age'],['female','% women'],['college','% 4-yr deg'],['lowinc','% <$50k'],['white','% White'],['black','% Black'],['hisp','% Hispanic'],['city','% big-city'],['rural','% rural'],['bornagain','% born-again']];
const base={}; DATA.baseline.forEach(r=>base[r.party]=r);
const nr=DATA.variants.k5_noresid;
document.getElementById('m-n').textContent='N = '+DATA.meta.N.toLocaleString();
document.getElementById('m-n2').textContent=DATA.meta.N.toLocaleString();
const ge=DATA.meta.govDistEta;
document.getElementById('govnote').innerHTML=`Government Distrust is never residualized (only F4/F5 are), so its scores are identical in both paradigms. Its η² (cluster separation) is essentially unchanged — ${ge.resid} with residualization vs ${ge.noResid} without (production value ≈ ${ge.production}). Not residualizing does <b>not</b> rescue its discriminatory power.`;

function facBar(name,val){const t=Math.max(-2,Math.min(2,val))/2,wd=Math.abs(t)*50,left=t>=0?50:50-wd,col=t>=0?'#b91c1c':'#1d4ed8';
  return `<div class="row"><div class="lab">${name}</div><div class="track"><div class="mid"></div><div class="fill" style="left:${left}%;width:${wd}%;background:${col}"></div></div><div class="fv">${val>=0?'+':''}${val.toFixed(1)}</div></div>`;}
function compPills(c){return Object.entries(c).map(([p,v])=>`<span class="pill" style="background:${PC[p]||'#94a3b8'}">${p} ${v}%</span>`).join('');}
function strengthRow(conf){if(conf==null)return '';return `<div class="strength"><span>strength</span><div class="sbar"><div class="sfill" style="width:${Math.round((conf-0.5)/0.4*100)}%"></div></div><b>${conf.toFixed(2)}</b></div>`;}
function polRows(rec,baseParty){const b=baseParty?base[baseParty]:null;
  return POL.map(it=>{const v=rec.pol[it.key],bv=b?b.pol[it.key]:null,dev=bv!=null?Math.round(v-bv):null;
    let flag=''; if(dev!=null&&Math.abs(dev)>=10)flag=`<span class="dev ${dev>0?'up':'dn'}">${dev>0?'+':''}${dev}</span>`;
    const mark=bv!=null?`<div class="pmark" style="left:${bv}%"></div>`:'';
    return `<div class="row"><span class="pl" title="${it.label}">${it.label}</span><div class="pbar"><div class="pfill" style="width:${v}%"></div>${mark}</div><div style="text-align:right">${v}% ${flag}</div></div>`;}).join('');}
function demoRows(rec,baseParty){const b=baseParty?base[baseParty]:null;
  return DEMO.map(([k,l])=>{const v=rec.demo[k];let dd='';if(b){const d=Math.round((v-b.demo[k])*10)/10;if(Math.abs(d)>=(k==='ideo'?0.3:(k==='age'?4:8)))dd=`<span class="dd ${d>0?'dev up':'dev dn'}"> ${d>0?'+':''}${d}</span>`;}
    return `<div class="d"><div class="dl">${l}</div><div class="dv">${v}${k==='age'||k==='ideo'?'':'%'}${dd}</div></div>`;}).join('');}

// classify no-resid clusters
function classify(rec){const c=rec.composition,ks=Object.keys(c);
  if(ks.length>=2&&(c[ks[0]]<60||c[ks[1]]>=25))return {type:'blend',parties:ks};
  return {type:'party',party:ks[0]};}
function crossVerdict(rec){const f=rec.factors;const enf=f.enforce||0,val=f.values||0,sk=f.elecSkep||0;
  if(Math.sign(enf)!==Math.sign(val)&&Math.abs(enf)>=.3&&Math.abs(val)>=.3)return ['cross','Strongly cross-cutting — tough on enforcement yet progressive on values (or vice-versa)'];
  if(Math.abs(sk)>=.45&&Math.abs(enf)<=.4)return ['cross','Cross-cutting on skepticism — anti-establishment independent of left–right'];
  return ['no','Bloc merge — a coarser version of adjacent parties, not a new axis'];}

function renderMatrix(){let h='<table class="sm"><thead><tr><th class="party">Party</th><th>wt%</th><th>conf</th><th>without residualization</th></tr></thead><tbody>';
  ORDER.forEach(p=>{const b=base[p];const s=nr.survival[p]||'absent';
    h+=`<tr><td class="party"><span class="dot" style="background:${PC[p]}"></span>${PNAME[p]} <span style="color:#94a3b8">(${p})</span></td><td>${b?b.wtPct:''}%</td><td>${b&&b.conf!=null?b.conf.toFixed(2):''}</td><td><span class="verdict v-${s}">${s}</span></td></tr>`;});
  h+='</tbody></table>';document.getElementById('matrix').innerHTML=h;}
function renderFindings(){const robust=ORDER.filter(p=>nr.survival[p]==='preserved');
  document.getElementById('findings').innerHTML=
   `<div class="callout"><b>Preserved without residualization:</b> ${robust.map(p=>PNAME[p]).join(', ')}. These don't need residualization to exist — real structure.</div>
    <div class="callout s"><b>Residualization's real job is the left.</b> Liberal and Dem. Socialist split, Progressive is absorbed — the four left parties sit at cosine 0.72–0.77 in policy space, so only residualizing (removing the enforcement axis's pull) pulls them cleanly apart.</div>`;}
function clusterCard(rec,opts){opts=opts||{};const cl=classify(rec);
  let title,top,baseParty=null,topbar='#94a3b8',xc='';
  if(cl.type==='party'){baseParty=cl.party;top=PNAME[baseParty];topbar=PC[baseParty];title=`${top} <span style="color:#94a3b8;font-weight:600">(${baseParty})</span>`;}
  else{const [v,txt]=crossVerdict(rec);xc=`<span class="xc ${v==='cross'?'':'no'}">${v==='cross'?'✦ cross-cutting':'bloc merge'}</span><div class="tagline" style="font-size:12px;color:var(--fg2);margin-bottom:6px">${txt}</div>`;
    title='Blend — '+cl.parties.slice(0,3).join(' + ');topbar=PC[cl.parties[0]]||'#7c3aed';}
  const uid=(opts.pfx||'c')+'_'+rec.id;
  return `<div class="cc" style="--ctop:${topbar}">
    <h3>${title}</h3><div class="wt">${rec.wtPct}% of electorate</div>
    <div class="comp">${compPills(rec.composition)}</div>${xc}
    ${strengthRow(rec.conf)}
    <div class="fac">${Object.entries(rec.factors).map(([n,v])=>facBar(n,v)).join('')}</div>
    <span class="more" onclick="document.getElementById('det_${uid}').classList.toggle('on')">▸ policy &amp; demographics${baseParty?' (Δ vs '+baseParty+' baseline)':''}</span>
    <div class="detail" id="det_${uid}">
      <div class="sech">Policy support${baseParty?' · marker = baseline, flag = ≥10pt shift':''}</div><div class="pol">${polRows(rec,baseParty)}</div>
      <div class="sech">Demographics${baseParty?' · Δ vs baseline':''}</div><div class="demo">${demoRows(rec,baseParty)}</div>
    </div></div>`;}
function renderPreserved(){const recs=nr.clusters.filter(r=>classify(r).type==='party').sort((a,b)=>b.wtPct-a.wtPct);
  document.getElementById('preserved').innerHTML=recs.map(r=>clusterCard(r,{pfx:'pre'})).join('');}
function renderBlends(){const recs=nr.clusters.filter(r=>classify(r).type==='blend').sort((a,b)=>b.wtPct-a.wtPct);
  document.getElementById('blends').innerHTML=recs.map(r=>clusterCard(r,{pfx:'bl'})).join('');}
function renderInsight(){document.getElementById('insight').innerHTML=
  `<div class="callout x"><b>Are the blends worth exploring? Partly.</b> Three of the four are the left/Blue-Dog bloc re-collapsing (Liberal+DSA secular left; Progressive+Blue Dog; a left-populist mix) — coarser groupings, not new axes. <b>One is genuinely cross-cutting and interesting:</b> the <b>"law-and-order Democrat"</b> (≈C7+CON+LIB) — high enforcement (100% back more police) yet progressive on race, pro-institution, and Democratic-leaning. The production model has no home for these voters; they scatter into Conservative. Worth surfacing — but note it's ≈40% the deliberately-dropped Blue Dog cluster, so it's more "Blue Dogs resurfacing" than a hidden new party. <b>Net: residualization mainly sharpens the weak left separation; it hides one legitimately cross-pressured group rather than a whole obscured multiparty layer.</b></div>`;}
function renderBaseline(){document.getElementById('baseline').innerHTML=ORDER.map(p=>{const rec=base[p];if(!rec)return '';
  const uid='base_'+p;return `<div class="cc" style="--ctop:${PC[p]}"><h3>${PNAME[p]} <span style="color:#94a3b8;font-weight:600">(${p})</span></h3>
    <div class="wt">${rec.wtPct}% of electorate</div>${strengthRow(rec.conf)}
    <div class="fac">${Object.entries(rec.factors).map(([n,v])=>facBar(n,v)).join('')}</div>
    <span class="more" onclick="document.getElementById('det_${uid}').classList.toggle('on')">▸ policy &amp; demographics</span>
    <div class="detail" id="det_${uid}"><div class="sech">Policy support</div><div class="pol">${polRows(rec,null)}</div>
    <div class="sech">Demographics</div><div class="demo">${demoRows(rec,null)}</div></div></div>`;}).join('');}
renderMatrix();renderFindings();renderPreserved();renderBlends();renderInsight();renderBaseline();
</script></body></html>"""
open('analysis/efa/cluster_explorer.html','w').write(HTML.replace('__DATA__',DATA_JSON))
print("wrote analysis/efa/cluster_explorer.html",len(HTML)//1024,"kb")
