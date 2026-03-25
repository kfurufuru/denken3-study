"""
電験3種 理論 ダッシュボード 自動更新スクリプト
=============================================
使い方:
  1. 環境変数を設定:
       NOTION_TOKEN = your_notion_integration_token
       DB_ID        = ff4fcb73cc14408caedf87c904ae2fd9
  2. 実行:
       python update_dashboard.py
  3. index.html が最新データで更新されます
"""

import os, json, re, datetime, requests

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DB_ID        = os.environ.get("DB_ID", "ff4fcb73cc14408caedf87c904ae2fd9")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def query_all(db_id):
    """全レコードを取得"""
    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=HEADERS, json=body
        )
        r.raise_for_status()
        data = r.json()
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
    return results

def get_prop(page, name):
    props = page.get("properties", {})
    p = props.get(name, {})
    t = p.get("type")
    if t == "checkbox":  return p.get("checkbox", False)
    if t == "select":    return (p.get("select") or {}).get("name", "")
    if t == "title":
        items = p.get("title", [])
        return "".join(i.get("plain_text","") for i in items)
    if t == "date":
        d = p.get("date") or {}
        return d.get("start", "")
    return ""

def compute_stats(records):
    total = len(records)
    achieved_orig = sum(1 for r in records if get_prop(r,"達成"))

    # 新ルール: 1回目=× かつ 2回目=〇 → 達成とみなす
    new_achieved = 0
    for r in records:
        if not get_prop(r,"達成"):
            if get_prop(r,"1回目") == "×" and get_prop(r,"2回目") == "〇":
                new_achieved += 1
    achieved = achieved_orig + new_achieved

    maru1   = sum(1 for r in records if get_prop(r,"1回目") == "〇")
    batu1   = sum(1 for r in records if get_prop(r,"1回目") == "×")

    by_cat = {}
    for r in records:
        cat = get_prop(r,"分野")
        if not cat: continue
        if cat not in by_cat:
            by_cat[cat] = {"total":0,"achieved":0}
        by_cat[cat]["total"] += 1
        done = get_prop(r,"達成") or (get_prop(r,"1回目")=="×" and get_prop(r,"2回目")=="〇")
        if done:
            by_cat[cat]["achieved"] += 1

    # 弱点リスト: 1回目=× かつ 未達成
    weak = []
    for r in records:
        done = get_prop(r,"達成") or (get_prop(r,"1回目")=="×" and get_prop(r,"2回目")=="〇")
        if get_prop(r,"1回目") == "×" and not done:
            weak.append({
                "q":    get_prop(r,"問題ID"),
                "topic":get_prop(r,"論点")[:28] if get_prop(r,"論点") else "",
                "cat":  get_prop(r,"分野"),
                "p":    (get_prop(r,"重要度ランク") or "")[:1],
                "date": get_prop(r,"最終実施日") or "未実施",
            })
    # S>A>B>C順
    rank = {"S":0,"A":1,"B":2,"C":3,"D":4}
    weak.sort(key=lambda x: (rank.get(x["p"],9), x["date"] == "未実施", x["date"]))

    return {
        "total": total, "achieved": achieved, "new_achieved": new_achieved,
        "maru1": maru1, "batu1": batu1,
        "by_cat": by_cat, "weak": weak[:20],
        "updated": datetime.date.today().isoformat()
    }

def inject_data(stats):
    """index.html の DATA セクションを更新"""
    with open("index.html","r",encoding="utf-8") as f:
        html = f.read()

    total = stats["total"]
    achieved = stats["achieved"]
    pct = round(achieved / total * 100, 1) if total else 0

    cat = stats["by_cat"]
    def cpct(name):
        d = cat.get(name, {"total":1,"achieved":0})
        return round(d["achieved"]/d["total"]*100) if d["total"] else 0

    # JavaScript data block
    weak_js = json.dumps(stats["weak"], ensure_ascii=False)

    new_block = f"""// ===== DATA =====
const ACHIEVED = {achieved}, TOTAL = {total};
const FIRST_MARU = {stats['maru1']}, FIRST_BATU = {stats['batu1']};
const STREAK = 3;
const EXAM_DATE = new Date('2026-08-23');
const STUDY_START = new Date('2025-09-01');
const TODAY = new Date('{stats['updated']}');

const WEAK_DATA = {weak_js};"""

    html = re.sub(r"// ===== DATA =====.*?const WEAK_DATA = \[.*?\];",
                  new_block, html, flags=re.DOTALL)

    # overall pct in ring label
    html = re.sub(r'<div class="ring-pct">[^<]*</div>',
                  f'<div class="ring-pct">{pct}%</div>', html)
    html = re.sub(r'<div class="ring-lbl">達成率</div>',
                  '<div class="ring-lbl">達成率</div>', html)

    # stat values
    html = re.sub(r'(<div[^>]*class="stat-val"[^>]*style="color:var\(--green\)"[^>]*>)[^<]*(</div>)',
                  f'\\g<1>{achieved}\\g<2>', html, count=1)

    with open("index.html","w",encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 更新完了: {stats['updated']}")
    print(f"   達成: {achieved}/{total} ({pct}%)")
    print(f"   うち 2回目〇 新規: {stats['new_achieved']}問")
    print(f"   弱点: {len(stats['weak'])}問")
    for k,v in stats["by_cat"].items():
        p = round(v["achieved"]/v["total"]*100) if v["total"] else 0
        print(f"   {k}: {v['achieved']}/{v['total']} ({p}%)")

if __name__ == "__main__":
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN が設定されていません")
        print("   export NOTION_TOKEN=your_token")
        exit(1)
    print("📡 Notion からデータ取得中...")
    records = query_all(DB_ID)
    print(f"   {len(records)}件 取得完了")
    stats = compute_stats(records)
    inject_data(stats)
