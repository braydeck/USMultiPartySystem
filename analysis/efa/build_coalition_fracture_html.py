#!/usr/bin/env python3
"""Render the coalition-fracture comparison (current middle parties vs the new 6-D
coalitions) as dot-plots over factor space + bills, plus the party-discipline
legislation table. From coalition_fracture.json."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
D=json.load(open(ROOT/'analysis/efa/coalition_fracture.json'))
DATA=json.dumps(D)
HTML=r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>STV — Fracturing the middle (foreign-policy realignment)</title>
<style>
:root{--ink:#0f172a;--fg2:#475569;--fg3:#94a3b8;--bg:#f8fafc;--card:#fff;--line:#e2e8f0;--sunken:#f1f5f9;--hi:#b91c1c;--lo:#1d4ed8;--fp:#0d9488;
 font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5}
.wrap{max-width:1020px;margin:0 auto;padding:40px 28px 100px}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--fp)}
h1{font-size:32px;font-weight:800;letter-spacing:-.02em;margin:.2em 0 .15em}h1 em{font-style:normal;color:var(--fp)}
.sub{color:var(--fg2);font-size:15px;max-width:800px}
h2{font-size:21px;font-weight:700;margin:0}
section{border-top:1px solid var(--line);margin-top:36px;padding-top:22px}
.lede{color:var(--fg2);font-size:14px;max-width:820px;margin:.4em 0 16px}
.callout{background:#fff;border:1px solid var(--line);border-left:4px solid var(--fp);border-radius:0 10px 10px 0;padding:14px 18px;margin:12px 0;font-size:13.5px;color:var(--fg2)}.callout b{color:var(--ink)}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin:12px 0 18px;font-size:12px}
.lg{display:flex;align-items:center;gap:6px;color:var(--fg2)}
.mk{width:14px;height:14px;border-radius:50%;display:inline-block}
.mk.cur{background:#fff}.mk.dia{border-radius:2px;transform:rotate(45deg)}
.metric{display:grid;grid-template-columns:200px 1fr;gap:12px;align-items:center;margin:7px 0}
.mlabel{font-size:12px;color:var(--fg2);text-align:right}
.track{position:relative;height:26px;background:var(--sunken);border-radius:6px}
.mid{position:absolute;left:50%;top:0;width:1px;height:100%;background:#cbd5e1}
.dot{position:absolute;top:50%;width:14px;height:14px;border-radius:50%;transform:translate(-50%,-50%);border:2px solid #fff;cursor:default}
.dot.cur{background:#fff!important;}
.dot.dia{border-radius:2px;width:13px;height:13px;transform:translate(-50%,-50%) rotate(45deg)}
.axend{display:flex;justify-content:space-between;font-size:10px;color:var(--fg3);margin-top:2px;padding:0 2px}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:center}
th{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--fg3)}
td.l{text-align:left}
.flip{background:#fef3c7}.pass{color:#16a34a;font-weight:700}.fail{color:#b91c1c;font-weight:700}
.note{font-size:11.5px;color:var(--fg3);font-style:italic;margin-top:10px}
</style></head><body><div class="wrap">
<div class="eyebrow">6-D foreign-policy variant · what it portends</div>
<h1>Fracturing the <em>cross-pressured middle</em></h1>
<p class="sub">If foreign policy became party-defining, the ideological poles barely move — but the cross-pressured middle (Social Democrats, Solidarity, Populists) splits into more sharply separated camps along an engagement↔isolationism axis. These dot-plots show where the new 6-D coalitions sit relative to today's parties; the table shows how a House of the new parties would vote differently under party discipline.</p>
<div id="legend" class="legend"></div>

<section><h2>Factor space — where the new coalitions land</h2>
<p class="lede">Hollow = today's party; filled diamond = a new 6-D coalition drawn from it. The middle parties spread apart, especially on foreign-policy engagement.</p>
<div id="facs"></div></section>

<section><h2>Policy — where preferences diverge</h2>
<p class="lede">Foreign-policy and immigration bills are where the new coalitions separate most from their parent parties.</p>
<div id="bills"></div></section>

<section><h2>Legislation — a House of new parties vs today's</h2>
<p class="lede">Party-discipline model (each party/cluster votes its majority; % = share of seats in YES-voting blocs; seats ∝ population). The electorate is identical, so most outcomes hold — but the re-sorted blocs flip two knife-edge immigration bills and make foreign-policy votes more decisive.</p>
<div id="legis"></div></section>
<p class="note" id="foot"></p>
</div>
<script>
const D=__DATA__;
const G=D.groups, FN=D.factor_names;
const CUR=['cur:STY','cur:SD','cur:POP'];
const NEW=['6D:SD/STY','6D:POP/STY','6D:POP/STY/CON (isolationist)','6D:SD/LIB'];
const COL={'cur:STY':'#8a70b8','cur:SD':'#38bdf8','cur:POP':'#d34812',
 '6D:SD/STY':'#7c6f9e','6D:POP/STY':'#b0567f','6D:POP/STY/CON (isolationist)':'#111827','6D:SD/LIB':'#0ea5e9'};
const NAME={'cur:STY':'STY (now)','cur:SD':'SD (now)','cur:POP':'POP (now)',
 '6D:SD/STY':'SD/STY bloc','6D:POP/STY':'POP/STY bloc','6D:POP/STY/CON (isolationist)':'Isolationist bloc','6D:SD/LIB':'Internationalist SD'};
const ALL=CUR.concat(NEW);
document.getElementById('legend').innerHTML=ALL.map(g=>`<span class="lg"><span class="mk ${CUR.includes(g)?'cur':'dia'}" style="${CUR.includes(g)?('border:2px solid '+COL[g]):('background:'+COL[g])}"></span>${NAME[g]}${G[g].comp?' <span style="color:#94a3b8">('+Object.entries(G[g].comp).slice(0,2).map(([p,v])=>p+v).join(' ')+')</span>':''}</span>`).join('');
function dot(g,xpct){const cur=CUR.includes(g);
  return `<div class="dot ${cur?'cur':'dia'}" title="${NAME[g]}: ${xpct.v}" style="left:${xpct.x}%;${cur?('border-color:'+COL[g]):('background:'+COL[g]+';border-color:#fff')}"></div>`;}
function facRow(fn){const lo=fn==='FPengage'?'isolationist':(fn==='values'?'progressive':(fn==='enforce'?'civil-libertarian':(fn==='elecSkep'?'trusts elections':'low'))) ;
  const hi=fn==='FPengage'?'internationalist':(fn==='values'?'racial-conservative':(fn==='enforce'?'enforcement':(fn==='elecSkep'?'skeptic':'high')));
  let dots='';ALL.forEach(g=>{const v=G[g].factors[fn];const x=Math.max(0,Math.min(100,(Math.max(-2,Math.min(2,v))+2)/4*100));dots+=dot(g,{x,v:v.toFixed(2)});});
  return `<div class="metric"><div class="mlabel">${fn}</div><div><div class="track"><div class="mid"></div>${dots}</div><div class="axend"><span>${lo}</span><span>${hi}</span></div></div></div>`;}
function billRow(b){let dots='';ALL.forEach(g=>{const v=G[g].bills[b.key];if(v==null)return;dots+=dot(g,{x:v,v:v+'%'});});
  return `<div class="metric"><div class="mlabel">${b.label}</div><div><div class="track">${dots}</div></div></div>`;}
document.getElementById('facs').innerHTML=['FPengage','enforce','values','elecSkep'].map(facRow).join('');
const showBills=['CC24_308a_1','CC24_308a_4','CC24_308a_3','CC24_420_5','CC24_323a','CC24_323d','CC24_340f','CC24_340c','CC24_321d'];
const bmap={}; D.bills.forEach(b=>bmap[b.key]=b);
document.getElementById('bills').innerHTML=showBills.map(k=>billRow(bmap[k])).join('');
let h='<table><thead><tr><th class="l">Bill</th><th>Overall support</th><th>9-party House</th><th>6-D House</th><th>Effect</th></tr></thead><tbody>';
D.legislation.forEach(L=>{h+=`<tr class="${L.flip?'flip':''}"><td class="l">${L.label}</td><td>${L.overall}%</td><td class="${L.pass9?'pass':'fail'}">${L.house9}% ${L.pass9?'pass':'fail'}</td><td class="${L.pass6?'pass':'fail'}">${L.house6}% ${L.pass6?'pass':'fail'}</td><td>${L.flip?'<b>FLIPS</b>':''}</td></tr>`;});
h+='</tbody></table>';document.getElementById('legis').innerHTML=h;
document.getElementById('foot').textContent='Party-discipline pass model (perfect cohesion); seats ∝ population share (proportional House). Same electorate in both, so flips come from how re-sorted blocs vote as units, not changed minds. Source: analysis/efa/coalition_fracture.py.';
</script></body></html>"""
open(ROOT/'analysis/efa/coalition_fracture.html','w').write(HTML.replace('__DATA__',DATA))
print("wrote analysis/efa/coalition_fracture.html")
