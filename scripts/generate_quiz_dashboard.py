#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/records.json を読み込み、index.html の QUIZ_MAIN / QUIZ_CHART セクションを更新する。
quiz.html は生成しない（index.html のタブとして統合済み）。
"""
import json, os, re
from datetime import date, timedelta
from collections import defaultdict, Counter

RECORDS_PATH = "data/records.json"
INDEX_PATH   = "index.html"

SUBJECT_ORDER = ["理論", "電力", "機械", "法規"]
REVIEW_DAYS   = {"SR1": 1, "SR2": 3, "SR3": 7, "SR4": 14, "SR5": 30, "done": 9999}

WIKI_BASE = "https://kfurufuru.github.io/denken-wiki-riron/themes/"
WIKI_MAP = {
    "三相交流": "sansou-kouryu",
    "電磁誘導": "denjiryoku",
    "コンデンサ": "condenser",
    "磁気回路": "jiki-kairo",
    "過渡現象": "kato-gensho",
    "直流回路": "chokuryu-kairo",
    "交流基礎": "kouryu-kiso",
    "RLC回路": "rlc-kairo",
    "交流電力": "kouryu-denryoku",
    "静電気": "seidenki",
    "インダクタンス": "inductance",
    "半導体": "handotai",
    "トランジスタ": "transistor",
    "オペアンプ": "opamp",
    "電気計測": "keiki",
    "ブリッジ回路": "bridge",
}

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
    labels = {"ok":"OL","risky":"Risky","ng":"NG"}
    bg, fg = cell_style(result)
    lbl = labels.get(result, result.upper())
    return f'<span class="q-badge-{"ok" if result=="ok" else "risky" if result=="risky" else "ng"}">{lbl}</span>'

def generate():
    records = load()
    today = date.today()

    total  = len(records)
    rc     = Counter(r.get("result","") for r in records)
    ok_n, risky_n, ng_n = rc["ok"], rc["risky"], rc["ng"]
    ok_pct = round(ok_n / total * 100) if total else 0

    # 本日レビュー対象
    due = []
    for r in records:
        d, nr = r.get("date",""), r.get("next_review","")
        if not d or not nr or nr == "done": continue
        try:
            due_date = date.fromisoformat(d) + timedelta(days=REVIEW_DAYS.get(nr, 7))
            if due_date <= today: due.append({**r, "due_date": due_date.isoformat()})
        except: pass
    due.sort(key=lambda x: x.get("date",""))

    # バグマップ
    bmap = defaultdict(lambda: defaultdict(list))
    subjects, themes = set(), set()
    for r in records:
        s, t, res = r.get("subject","?"), r.get("theme","?"), r.get("result","")
        subjects.add(s); themes.add(t); bmap[t][s].append(res)
    subjects = [s for s in SUBJECT_ORDER if s in subjects] + sorted(s for s in subjects if s not in SUBJECT_ORDER)
    themes   = sorted(themes)

    th = "".join(f"<th>{s}</th>" for s in subjects)
    rows = ""
    for t in themes:
        cells = ""
        for s in subjects:
            rs = bmap[t][s]
            if not rs:
                cells += '<td class="q-status-none">－</td>'
            else:
                dom = dominant(rs); bg, fg = cell_style(dom)
                cnt = Counter(rs)
                tip = f"OK:{cnt['ok']} Risky:{cnt['risky']} NG:{cnt['ng']}"
                lbl = {"ok":"OK","risky":"Risky","ng":"NG"}.get(dom, dom)
                css = "q-status-ok" if dom=="ok" else "q-status-risky" if dom=="risky" else "q-status-ng"
                wiki_slug = WIKI_MAP.get(t)
                if wiki_slug:
                    wiki_url = f"{WIKI_BASE}{wiki_slug}/"
                    cells += f'<td class="{css}" title="{tip}"><a href="{wiki_url}" target="_blank" style="color:inherit;text-decoration:none;display:block">{lbl} <span style="font-size:.6rem;opacity:.8">📖</span></a></td>'
                else:
                    cells += f'<td class="{css}" title="{tip}">{lbl}</td>'
        rows += f'<tr><td style="color:var(--muted2);font-size:.72rem;padding:5px 10px;text-align:left;white-space:nowrap">{t}</td>{cells}</tr>'
    bugmap_html = f'<div style="overflow-x:auto"><table class="q-bug-tbl"><thead><tr><th style="text-align:left">テーマ＼科目</th>{th}</tr></thead><tbody>{rows}</tbody></table></div>'

    # フェーズ別進捗
    phase_stats = defaultdict(Counter)
    for r in records:
        phase_stats[r.get("phase","?")][r.get("result","")] += 1
    phase_html = ""
    for ph, cnt in sorted(phase_stats.items()):
        tot = sum(cnt.values())
        if not tot: continue
        bars = "".join(
            f'<div style="width:{round(cnt.get(r,0)/tot*100)}%;background:{"#22c55e" if r=="ok" else "#f59e0b" if r=="risky" else "#ef4444"};height:100%"></div>'
            for r in ["ok","risky","ng"]
        )
        phase_html += f'''<div class="q-phase-bar">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
            <span style="color:var(--text);font-weight:600;font-size:.85rem">Phase {ph}</span>
            <span style="color:var(--muted);font-size:.72rem">{tot}問</span>
          </div>
          <div style="height:10px;background:var(--bg);border-radius:5px;overflow:hidden;display:flex">{bars}</div>
          <div style="font-size:.7rem;margin-top:4px;display:flex;gap:12px">
            <span style="color:#4ade80">✓ {cnt.get("ok",0)}</span>
            <span style="color:#fbbf24">⚠ {cnt.get("risky",0)}</span>
            <span style="color:#f87171">✗ {cnt.get("ng",0)}</span>
          </div>
        </div>'''
    if not phase_html:
        phase_html = '<p style="color:var(--muted)">データがありません</p>'

    # レビューリスト
    if not due:
        due_html = '<p style="color:#22c55e;padding:16px 0">🎉 本日のレビュー対象はありません！</p>'
    else:
        due_html = "".join(
            f'<div class="q-review-item">{badge(d.get("result",""))}'
            f'<span style="color:#60a5fa;font-weight:600">[{d.get("subject","")}]</span>'
            f'<span style="flex:1;color:var(--text)">{d.get("theme","")} {("/ " + d.get("subtheme","")) if d.get("subtheme") else ""}</span>'
            f'<span style="color:var(--muted);font-size:.72rem">{d.get("next_review","")}</span></div>'
            for d in due[:15]
        )

    # 最近の記録
    recent = sorted(records, key=lambda x: x.get("date",""), reverse=True)[:10]
    rec_rows = "".join(
        f'<tr><td>{r.get("date","")}</td><td>{r.get("subject","")}</td>'
        f'<td>{r.get("theme","")}</td><td>{badge(r.get("result",""))}</td>'
        f'<td style="color:var(--muted)">{r.get("next_review","")}</td>'
        f'<td style="color:var(--muted2);font-size:.72rem">{(r.get("memo","") or "")[:25]}</td></tr>'
        for r in recent
    )

    # 活動データ（直近30日）
    dcounts    = Counter(r.get("date","") for r in records)
    act_labels = [(today - timedelta(days=i)).strftime("%-m/%-d") for i in range(29, -1, -1)]
    act_data   = [dcounts.get((today - timedelta(days=i)).isoformat(), 0) for i in range(29, -1, -1)]

    # ---- HTML セクション生成 ----
    main_html = f'''
<main class="main">

  <!-- KPI -->
  <div class="section">
    <div class="sec-title">📊 テスト記録サマリ</div>
    <div class="q-kpi-row">
      <div class="q-kpi"><div class="lbl">総記録数</div><div class="val" style="color:#60a5fa">{total}</div><div class="sub">累計テスト問題</div></div>
      <div class="q-kpi"><div class="lbl">理解済 OK</div><div class="val" style="color:#22c55e">{ok_n}</div><div class="sub">達成率 {ok_pct}%</div></div>
      <div class="q-kpi"><div class="lbl">要注意 Risky</div><div class="val" style="color:#f59e0b">{risky_n}</div><div class="sub">揺らぎあり</div></div>
      <div class="q-kpi"><div class="lbl">本日レビュー</div><div class="val" style="color:#ef4444">{len(due)}</div><div class="sub">スペーシング対象</div></div>
    </div>
  </div>

  <!-- 活動チャート -->
  <div class="section">
    <div class="card"><div class="card-header">📅 直近30日の学習活動</div><canvas id="q-ac" class="q-chart"></canvas></div>
  </div>

  <!-- バグマップ + フェーズ別 -->
  <div class="section">
    <div class="g21">
      <div class="card">
        <div class="card-header">🔴 バグマップ（科目 × テーマ）</div>
        {bugmap_html}
      </div>
      <div class="card">
        <div class="card-header">📊 フェーズ別進捗</div>
        {phase_html}
      </div>
    </div>
  </div>

  <!-- レビュー対象 + 結果分布 -->
  <div class="section">
    <div class="g2">
      <div class="card">
        <div class="card-header">🔁 本日のレビュー対象</div>
        {due_html}
      </div>
      <div class="card">
        <div class="card-header">📈 結果分布</div>
        <canvas id="q-rc" class="q-chart" style="display:block;margin:0 auto"></canvas>
      </div>
    </div>
  </div>

  <!-- 最近の記録 -->
  <div class="section">
    <div class="card">
      <div class="card-header">📝 最近の記録（直近10件）</div>
      <div style="overflow-x:auto">
        <table class="q-rec-tbl">
          <thead><tr><th>日付</th><th>科目</th><th>テーマ</th><th>結果</th><th>次回</th><th>メモ</th></tr></thead>
          <tbody>{rec_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- 更新ボタン -->
  <div class="section" style="text-align:right">
    <button id="q-refresh-btn" onclick="quizRefresh()" style="background:linear-gradient(135deg,#065f46,#047857);color:#6ee7b7;border:1px solid #10b981;padding:10px 20px;border-radius:10px;font-size:.85rem;font-weight:700;cursor:pointer;font-family:inherit;transition:all .3s">🔄 Make.com更新トリガー</button>
  </div>

  <div class="footer">⚡ テスト記録 ダッシュボード ｜ 最終更新: {today.isoformat()}</div>
</main>'''

    # ---- チャートJS生成 ----
    chart_js = f'''// QUIZ_CHART_START
function initQuizCharts() {{
  // 活動チャート
  new Chart(document.getElementById('q-ac'), {{
    type: 'bar',
    data: {{
      labels: {json.dumps(act_labels, ensure_ascii=False)},
      datasets: [{{
        label: '記録数',
        data: {json.dumps(act_data)},
        backgroundColor: 'rgba(96,165,250,.55)',
        borderColor: '#60a5fa',
        borderWidth: 1,
        borderRadius: 4
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{ beginAtZero: true, ticks: {{ color: '#64748b', stepSize: 1 }}, grid: {{ color: '#1a2535' }} }},
        x: {{ ticks: {{ color: '#64748b', maxRotation: 45, font: {{ size: 10 }} }}, grid: {{ display: false }} }}
      }}
    }}
  }});

  // 結果分布ドーナツ
  new Chart(document.getElementById('q-rc'), {{
    type: 'doughnut',
    data: {{
      labels: ['OK','Risky','NG'],
      datasets: [{{
        data: [{ok_n}, {risky_n}, {ng_n}],
        backgroundColor: ['#22c55e','#f59e0b','#ef4444'],
        borderColor: '#0d1117',
        borderWidth: 4
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 12 }} }} }} }}
    }}
  }});
}}
// QUIZ_CHART_END'''

    # ---- index.html を書き換え ----
    with open(INDEX_PATH, encoding="utf-8") as f:
        html = f.read()

    # QUIZ_MAIN セクションを置換
    html = re.sub(
        r'<!-- QUIZ_MAIN_START -->.*?<!-- QUIZ_MAIN_END -->',
        f'<!-- QUIZ_MAIN_START -->\n{main_html}\n<!-- QUIZ_MAIN_END -->',
        html, flags=re.DOTALL
    )

    # QUIZ_CHART セクションを置換
    html = re.sub(
        r'// QUIZ_CHART_START.*?// QUIZ_CHART_END',
        chart_js,
        html, flags=re.DOTALL
    )

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ index.html 更新完了 ({total} records, {len(due)} due today)")

if __name__ == "__main__":
    generate()
