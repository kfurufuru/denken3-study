#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os
from datetime import date, timedelta
from collections import defaultdict, Counter

RECORDS_PATH = "data/records.json"
OUTPUT_PATH  = "quiz.html"
SUBJECT_ORDER = ["\u7406\u8ad6", "\u96fb\u529b", "\u6a5f\u68b0", "\u6cd5\u898f"]
REVIEW_DAYS   = {"SR1": 1, "SR2": 3, "SR3": 7, "SR4": 14, "SR5": 30, "done": 9999}

def load():
    try:
        with open(RECORDS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def dominant(results):
    for r in ["ng", "risky", "ok"]:
        if r in results: return r
    return ""

def cell_style(result):
    s = {"ok": ("#166534","#4ade80"), "risky": ("#78350f","#fbbf24"), "ng": ("#7f1d1d","#f87171")}
    return s.get(result, ("#1e293b","#64748b"))

def badge(result):
    labels = {"ok":"OK","risky":"Risky","ng":"NG"}
    bg, fg = cell_style(result)
    return f'<span style="background:{bg};color:{fg};padding:2px 7px;border-radius:4px;font-size:.68rem;font-weight:700">{labels.get(result,result.upper())}</span>'

def generate():
    records = load()
    today = date.today()

    total = len(records)
    rc = Counter(r.get("result","") for r in records)
    ok_n, risky_n, ng_n = rc["ok"], rc["risky"], rc["ng"]
    ok_rate = round(ok_n/total*100) if total else 0

    due = []
    for r in records:
        d, nr = r.get("date",""), r.get("next_review","")
        if not d or not nr or nr=="done": continue
        try:
            due_date = date.fromisoformat(d) + timedelta(days=REVIEW_DAYS.get(nr,7))
            if due_date <= today: due.append({**r,"due_date":due_date.isoformat()})
        except: pass
    due.sort(key=lambda x: x.get("date",""))

    bmap = defaultdict(lambda: defaultdict(list))
    subjects, themes = set(), set()
    for r in records:
        s,t,res = r.get("subject","?"), r.get("theme","?"), r.get("result","")
        subjects.add(s); themes.add(t); bmap[t][s].append(res)
    subjects = [s for s in SUBJECT_ORDER if s in subjects] + sorted(s for s in subjects if s not in SUBJECT_ORDER)
    themes   = sorted(themes)

    phase_stats = defaultdict(Counter)
    for r in records:
        phase_stats[r.get("phase","?")][r.get("result","")] += 1

    dcounts = Counter(r.get("date","") for r in records)
    act_labels = [(today-timedelta(days=i)).strftime("%-m/%-d") for i in range(29,-1,-1)]
    act_data   = [dcounts.get((today-timedelta(days=i)).isoformat(),0) for i in range(29,-1,-1)]

    recent = sorted(records, key=lambda x: x.get("date",""), reverse=True)[:10]

    th = "".join(f"<th>{s}</th>" for s in subjects)
    rows = ""
    for t in themes:
        cells = ""
        for s in subjects:
            rs = bmap[t][s]
            if not rs: cells += '<td style="color:#2d3f55;text-align:center">\uff0d</td>'
            else:
                dom = dominant(rs); bg,fg = cell_style(dom)
                cnt = Counter(rs)
                tip = f"OK:{cnt['ok']} Risky:{cnt['risky']} NG:{cnt['ng']}"
                lbl = {"ok":"OK","risky":"Risky","ng":"NG"}.get(dom,dom)
                cells += f'<td style="background:{bg};color:{fg};text-align:center;padding:5px 8px;border-radius:5px;font-weight:700;font-size:.7rem;cursor:default" title="{tip}">{lbl}</td>'
        rows += f"<tr><td style='color:#94a3b8;white-space:nowrap;font-size:.72rem;padding:5px 10px'>{t}</td>{cells}</tr>"
    bugmap_html = f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:separate;border-spacing:3px"><thead><tr><th style="text-align:left;color:#64748b;padding:6px 10px">\u30c6\u30fc\u30de\\\u79d1\u76ee</th>{th}</tr></thead><tbody>{rows}</tbody></table></div>'

    phase_html = ""
    for ph, cnt in sorted(phase_stats.items()):
        tot = sum(cnt.values())
        if not tot: continue
        bars = "".join(f'<div style="width:{round(cnt.get(r,0)/tot*100)}%;background:{"#22c55e" if r=="ok" else "#f59e0b" if r=="risky" else "#ef4444"};height:100%" title="{r}:{cnt.get(r,0)}"></div>' for r in ["ok","risky","ng"])
        phase_html += f'<div style="margin-bottom:14px"><div style="display:flex;align-items:center;gap:8px;margin-bottom:5px"><span style="color:#cbd5e1;font-weight:600;font-size:.85rem">Phase {ph}</span><span style="color:#64748b;font-size:.72rem">{tot}\u554f</span></div><div style="height:10px;background:#0a0f1e;border-radius:5px;overflow:hidden;display:flex">{bars}</div><div style="font-size:.trem;margin-top:4px;display:flex;gap:12px"><span style="color:#4ade80">\u2713 {cnt.get("ok",0)}</span><span style="color:#fbbf24">\u26a0 {cnt.get("risky",0)}</span><span style="color:#f87171">\u2717 {cnt.get("ng",0)}</span></div></div>'

    due_html = '<p style="color:#22c55e;padding:16px 0">\U0001f389 \u672c\u65e5\u306e\u30ec\u30d3\u30e5\u30fc\u5bfe\u8c61\u306f\u3042\u308a\u307e\u305b\u3093\uff01</p>' if not due else "".join(
        f'<div style="display:flex;align-items:center;gap:8px;padding:9px 0;border-bottom:1px solid #1a2535;font-size:.8rem">{badge(d.get("result",""))}<span style="color:#60a5fa;font-weight:600">[{d.get("subject","")}]</span><span style="flex:1;color:#cbd5e1">{d.get("theme","")} / {d.get("subtheme","")}</span><span style="color:#64748b;font-size:.72rem">{d.get("next_review","")}</span></div>'
        for d in due[:15]
    )

    rec_rows = "".join(
        f'<tr><td>{r.get("date","")}</td><td>{r.get("subject","")}</td><td>{r.get("theme","")}</td><td style="color:#94a3b8">{r.get("subtheme","")[:20]}</td><td>{badge(r.get("result",""))}</td><td style="color:#64748b">{r.get("next_review","")}</td><td style="color:#94a3b8;font-size:.72rem">{r.get("memo","")[:20]}</td></tr>'
        for r in recent
    )
    rec_html = f'''<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.78rem">
<thead><tr>
<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #1f2d42;color:#64748b;font-size:.7rem">\u65e5\u4ed8</th>
<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #1f2d42;color:#64748b;font-size:.7rem">\u79d1\u76ee</th>
<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #1f2d42;color:#64748b;font-size:.7rem">\u30c6\u30fc\u30de</th>
<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #1f2d42;color:#64748b;font-size:.7rem">\u30b5\u30d6\u30c6\u30fc\u30da</th>
<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #1f2d42;color:#64748b;font-size:.7rem">\u7d50\u679c</th>
<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #1f2d42;color:#64748b;font-size:.7rem">\u6b21\u56de</th>
<th style="text-align:left;padding:8px 12px;border-bottom:1px solid #1f2d42;color:#64748b;font-size:.7rem">\u30e1\u30e2</th>
</tr></thead><tbody>{rec_rows}</tbody></table></div>'''

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>&#x26a1; \u30c6\u30b9\u30c8\u8a18\u9332 \u30c0\u30c3\u30b7\u30e5\u30dc\u30fc\u30c9</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0f1e;color:#cbd5e1;min-height:100vh}}
.hdr{{background:linear-gradient(135deg,#0d1b3e,#0a0f1e);border-bottom:1px solid #1e3a5f;padding:20px 32px;display:flex;align-items:center;justify-content:space-between}}
.hdr h1{{font-size:1.4rem;font-weight:700;color:#60a5fa}}
.hdr .sub{{font-size:.78rem;color:#64748b;margin-top:2px}}
.hdr-r{{font-size:.72rem;color:#475569;text-align:right}}
.wrap{{max-width:1440px;margin:0 auto;padding:24px 32py}}
.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}}
.kpi{{background:#111827;border:1px solid #1f2d42;border-radius:12px;padding:18px 20px}}
.kpi .lbl{{font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:#64748b}}
.kpi .val{{font-size:2.2rem;font-weight:800;line-height:1.1;margin:8px 0 4px}}
.kpi .sub{{font-size:.75rem;color:#475569}}
.card{{background:#111827;border:1px solid #1f2d42;border-radius:12px;padding:20px;margin-bottom:18px}}
.card h2{{font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;color:#64748b;margin-bottom:14px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px}}
.g3{{display:grid;grid-template-columns:2fr 1fr;gap:18px;margin-bottom:18px}}
canvas{{max-height:200px!important}}
@media(max-width:900px){{.kpi-row{{grid-template-columns:repeat(2,1fr)}}.g2,.g3{{grid-template-columns:1fr}}.wrap{{padding:16px}}}}
</style>
</head>
<body>
<header class="hdr">
  <div><h1>&#x26a1; \u30c6\u30b9\u30c8\u8a18\u9332 \u30c0\u30c3\u30b7\u30e5\u30dc\u30fc\u30c9</h1><div class="sub">Bug Map &amp; \u7fd2\u719f\u5ea6\u8ffd\u8de1 | denken3-study</div></div>
  <div class="hdr-r">\u6700\u7d42\u66f4\u65b0: {today.isoformat()}<br>\u7dcf\u8a18\u9332: {total} \u4ef6 &nbsp;|&nbsp; <a href="index.html" style="color:#60a5fa">\u2190 \u5b66\u7fd2\u9032\u6357\u3078</a></div>
</header>
<div class="wrap">

  <div class="kpi-row">
    <div class="kpi"><div class="lbl">\u7dcf\u8a18\u9332\u6570</div><div class="val" style="color:#60a5fa">{total}</div><div class="sub">\u7d2f\u8a08\u30c6\u30b9\u30c8\u554f\u984c</div></div>
    <div class="kpi"><div class="lbl">\u7406\u89e3\u6e08 OK</div><div class="val" style="color:#22c55e">{ok_n}</div><div class="sub">\u9054\u6210\u7387 {ok_rate}%</div></div>
    <div class="kpi"><div class="lbl">\u8981\u6ce8\u610f Risky</div><div class="val" style="color:#f59e0b">{risky_n}</div><div class="sub">\u6416\u3089\u304e\u3042\u308a</div></div>
    <div class="kpi"><div class="lbl">\u672c\u65e5\u30ec\u30d3\u30e5\u30fc</div><div class="val" style="color:#ef4444">{len(due)}</div><div class="sub">\u30b9\u30da\u30fc\u30b7\u30f3\u30b0\u5bfe\u8c61</div></div>
  </div>

  <div class="card"><h2>\U0001f4c5 \u76f4\u8fd130\u65e5\u306e\u5b66\u7fd2\u6d3b\u52d5</h2><canvas id="ac"></canvas></div>

  <div class="g3">
    <div class="card"><h2>\U0001f534 \u30d0\u30b4\u30de\u30c3\u30d7\uff08\u79d1\u76ee \xd7 \u30c6\u30fc\u30da\uff09</h2>{bugmap_html}</div>
    <div class="card"><h2>\U0001f4ca \u30d5\u30a7\u30fc\u30ba\u5225\u9032\u6357</h2>{phase_html if phase_html else '<p style="color:#64748b">\u30c7\u30fc\u30bf\u304c\u3042\u308a\u307e\u305b\u3093</p>'}</div>
  </div>

  <div class="g2">
    <div class="card"><h2>\U0001f501 \u672c\u65e5\u306e\u30ec\u30d3\u30e5\u30fc\u5bfe\u8c61</h2>{due_html}</div>
    <div class="card"><h2>\U0001f4c8 \u7d50\u679c\u5206\u5e03</h2><canvas id="rc"></canvas></div>
  </div>

  <div class="card"><h2>\U0001f4dd \u6700\u8fd1\u306e\u8a18\u9332\uff08\u76f4\u8fd110\u4ef6\uff09</h2>{rec_html}</div>

</div>
<script>
new Chart(document.getElementById('ac'),{{type:'bar',data:{{labels:{json.dumps(act_labels,ensure_ascii=False)},datasets:[{{label:'\u8a18\u9332\u6570',data:{json.dumps(act_data)},backgroundColor:'rgba(96,165,250,.55)',borderColor:'#60a5fa',borderWidth:1,borderRadius:4}}]}},options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{color:'#64748b',stepSize:1}},grid:{{color:'#1a2535'}}}},x:{{ticks:{{color:'#64748b',maxRotation:45,font:{{size:10}}}},grid:{{display:false}}}}}}}}}}}});
new Chart(document.getElementById('rc'),{{type:'doughnut',data:{{labels:['OK','Risky','NG'],datasets:[{{data:[{ok_n},{risky_n},{ng_n}],backgroundColor:['#22c55e','#f59e0b','#ef4444'],borderColor:'#111827',borderWidth:4}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{color:'#94a3b8',font:{{size:12}}}}}}}}}}}}}});
</script>
</body></html>"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard generated -> {OUTPUT_PATH} ({total} records)")

if __name__ == "__main__":
    generate()
