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

# ===== 定数定義 =====

# 試験日・残日数
EXAM_DATE = datetime.date(2026, 8, 23)

# スロット割り当てルール: 分野カテゴリ → スロット
THEORY_CATEGORIES = {"電気回路", "電磁気学", "電子理論", "電気計測", "電気・電子計測", "電気及び電子計測"}

# Bugコード → 日本語説明
BUG_TO_DESC = {
    "ANCHOR": "思い込み",
    "CONF":   "自信過剰",
    "RUSH":   "焦り",
    "MODEL":  "モデル誤り",
    "TRACK":  "計算追跡ミス",
    "READ":   "読み飛ばし",
    "ASSUME": "前提見落とし",
}

# Bugコード → 対策文
BUG_TO_THEME = {
    "ANCHOR": "ANCHOR対策: 既知パターンを疑う問題を重点的に演習する",
    "CONF":   "CONF対策: 自信ある分野の検算問題を追加する",
    "RUSH":   "RUSH対策: 時間制限ありのスロー演習を計画する",
    "MODEL":  "MODEL対策: 物理モデルの図解演習を計画する",
    "TRACK":  "TRACK対策: 多ステップ計算の追跡訓練を計画する",
    "READ":   "READ対策: 問題文の精読・マーキング練習を計画する",
    "ASSUME": "ASSUME対策: 前提条件の明示化訓練を計画する",
}

# 優先度ランク
RANK = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}


# ===== Notion API =====

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


# ===== 統計計算（既存） =====

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


# ===== records.json 読み込み =====

def load_records():
    """data/records.json を読み込む。ファイルが無ければ空リスト返却。"""
    path = os.path.join(os.path.dirname(__file__), "data", "records.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️  data/records.json 読み込み失敗: {e}")
        return []


# ===== PAST_ERRORS 計算 =====

def compute_past_errors(records_list):
    """records.jsonからNG/Riskyの未解決誤答を抽出してリスト返却"""
    errors = []
    for r in records_list:
        result = r.get("result", "")
        nr = r.get("next_review", "")
        if result in ("ng", "risky") and nr != "done":
            errors.append({
                "question_id": r.get("theme", r.get("q", "")),
                "category":    r.get("category", r.get("theme", "")),
                "subject":     r.get("subject", "理論"),
                "result":      result,
                "date":        r.get("date", ""),
                "memo":        r.get("memo", ""),
                "next_review": nr,
            })
    # 日付の新しい順にソート
    errors.sort(key=lambda x: x.get("date", ""), reverse=True)
    return errors


# ===== TODAY_SESSIONS 計算 =====

def compute_today_sessions(notion_records, records_list):
    """
    Tab1「今日の学習」用データを生成する。

    スロット割り当て:
        morning  → 理論科目（電気回路/電磁気学/電子理論/電気計測 系）
        noon     → 法規科目
        evening  → 法規科目

    選出優先度:
        1. records.json で next_review が SR1〜SR5 かつ date が今日以前のもの → type:"review"
        2. 不足分を Notion の priority 順（S→A→B→C）で補充 → type:"weak"
    """
    today_str = datetime.date.today().isoformat()
    days_left = (EXAM_DATE - datetime.date.today()).days

    # --- SR復習候補を抽出 ---
    sr_candidates = []
    for rec in records_list:
        nr = rec.get("next_review", "")
        rec_date = rec.get("date", "")
        if nr in ("SR1", "SR2", "SR3", "SR4", "SR5") and rec_date <= today_str:
            sr_candidates.append(rec)

    # --- Notion弱点候補を抽出（未達成・重要度順）---
    notion_weak = []
    for r in notion_records:
        done = get_prop(r, "達成") or (
            get_prop(r, "1回目") == "×" and get_prop(r, "2回目") == "〇"
        )
        if get_prop(r, "1回目") == "×" and not done:
            notion_weak.append({
                "question_id":    get_prop(r, "問題ID"),
                "category":       get_prop(r, "分野"),
                "priority":       (get_prop(r, "重要度ランク") or "C")[:1],
                "last_result":    None,
            })
    notion_weak.sort(key=lambda x: RANK.get(x["priority"], 9))

    def _pick_for_slot(slot_name):
        """スロットに最適な問題を1件選んでSessionオブジェクトを返す"""
        is_theory = (slot_name == "morning")
        slot_meta = {
            "morning":  {"label": "朝", "emoji": "🌅",  "subject_label": "理論"},
            "noon":     {"label": "昼", "emoji": "☀️", "subject_label": "法規"},
            "evening":  {"label": "夜", "emoji": "🌙",  "subject_label": "法規"},
        }[slot_name]

        # SR復習から探す
        for i, rec in enumerate(sr_candidates):
            cat = rec.get("category", "") or rec.get("subject", "") or ""
            cat_is_theory = any(
                c in cat for c in ("理論", "電気回路", "電磁気", "電子", "計測")
            )
            if (is_theory and cat_is_theory) or (not is_theory and not cat_is_theory):
                sr_candidates.pop(i)
                last_res = rec.get("last_result", "ng")
                return {
                    "slot":          slot_name,
                    "label":         slot_meta["label"],
                    "emoji":         slot_meta["emoji"],
                    "subject_label": slot_meta["subject_label"],
                    "question_id":   rec.get("question_id", ""),
                    "category":      rec.get("category", ""),
                    "priority":      rec.get("priority", "B"),
                    "type":          "review",
                    "last_result":   last_res if last_res in ("ok", "risky", "ng") else "ng",
                }

        # Notion弱点から探す
        for i, rec in enumerate(notion_weak):
            cat = rec.get("category", "") or ""
            cat_is_theory = cat in THEORY_CATEGORIES or any(
                c in cat for c in ("理論", "電気回路", "電磁気", "電子", "計測")
            )
            if (is_theory and cat_is_theory) or (not is_theory and not cat_is_theory):
                notion_weak.pop(i)
                return {
                    "slot":          slot_name,
                    "label":         slot_meta["label"],
                    "emoji":         slot_meta["emoji"],
                    "subject_label": slot_meta["subject_label"],
                    "question_id":   rec.get("question_id", ""),
                    "category":      cat,
                    "priority":      rec.get("priority", "C"),
                    "type":          "weak",
                }

        # 候補なし → プレースホルダー
        return {
            "slot":          slot_name,
            "label":         slot_meta["label"],
            "emoji":         slot_meta["emoji"],
            "subject_label": slot_meta["subject_label"],
            "question_id":   "",
            "category":      "",
            "priority":      "C",
            "type":          "weak",
        }

    sessions = [
        _pick_for_slot("morning"),
        _pick_for_slot("noon"),
        _pick_for_slot("evening"),
    ]

    return {
        "date":      today_str,
        "days_left": days_left,
        "sessions":  sessions,
    }


# ===== PDCA_DATA 計算 =====

def compute_pdca_data(records_list):
    """
    Tab2「PDCA」用データを生成する。

    - do_logs  : 直近10件の学習記録
    - check_pending : next_review が SR2〜SR5 で直近7件
    - act_bugs : error_sub フィールドの集計（上位5件）
    - act_countermeasures : bug上位コードの対策文
    """
    today = datetime.date.today()

    # 今週の情報
    iso_week = today.isocalendar()[1]
    week_label = f"W{iso_week:02d}"
    # 今週の月曜〜日曜
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6)
    period_label = f"{monday.month}/{monday.day}–{sunday.month}/{sunday.day}"

    # --- do_logs: dateの降順で直近10件 ---
    sorted_recs = sorted(
        [r for r in records_list if r.get("date")],
        key=lambda x: x["date"],
        reverse=True
    )
    do_logs = []
    for rec in sorted_recs[:10]:
        rec_date = rec.get("date", "")
        try:
            d = datetime.date.fromisoformat(rec_date)
            date_label = f"{d.month}/{d.day}"
        except Exception:
            date_label = rec_date

        score_raw = rec.get("score")
        try:
            score = int(score_raw)
        except (TypeError, ValueError):
            score = 0

        do_logs.append({
            "date":   date_label,
            "theme":  rec.get("question_id", rec.get("theme", "")),
            "source": rec.get("source", "問題演習"),
            "score":  score,
            "result": rec.get("last_result", rec.get("result", "ok")),
        })

    # --- check_pending: SR2〜SR5 で直近7件（dateの降順）---
    pending_recs = [
        r for r in records_list
        if r.get("next_review", "") in ("SR2", "SR3", "SR4", "SR5")
    ]
    pending_recs.sort(key=lambda x: x.get("date", ""), reverse=True)
    check_pending = []
    for rec in pending_recs[:7]:
        rec_date = rec.get("date", "")
        try:
            d = datetime.date.fromisoformat(rec_date)
            days_ago = (today - d).days
        except Exception:
            days_ago = 0

        check_pending.append({
            "theme":    rec.get("question_id", rec.get("theme", "")),
            "result":   rec.get("last_result", rec.get("result", "risky")),
            "category": rec.get("category", ""),
            "days_ago": days_ago,
        })

    # --- act_bugs: error_sub フィールドを集計（上位5件）---
    bug_counter = {}
    for rec in records_list:
        error_sub = rec.get("error_sub", "")
        if not error_sub:
            continue
        # カンマ区切りで複数コードが入っている場合も考慮
        for code in str(error_sub).split(","):
            code = code.strip().upper()
            if code:
                bug_counter[code] = bug_counter.get(code, 0) + 1

    sorted_bugs = sorted(bug_counter.items(), key=lambda x: x[1], reverse=True)
    act_bugs = []
    for code, count in sorted_bugs[:5]:
        act_bugs.append({
            "code":  code,
            "desc":  BUG_TO_DESC.get(code, code),
            "count": count,
        })

    # --- act_countermeasures: 上位バグの対策文 ---
    act_countermeasures = []
    for bug in act_bugs:
        code = bug["code"]
        if code in BUG_TO_THEME:
            act_countermeasures.append(BUG_TO_THEME[code])

    return {
        "week":               week_label,
        "period":             period_label,
        "do_logs":            do_logs,
        "check_pending":      check_pending,
        "act_bugs":           act_bugs,
        "act_countermeasures": act_countermeasures,
    }


# ===== HTML注入（TODAY_SESSIONS / PDCA_DATA / PAST_ERRORS）=====

def inject_today_pdca(html, today_data, pdca_data, past_errors):
    """TODAY_SESSIONS と PDCA_DATA と PAST_ERRORS を HTML に注入する"""

    # TODAY_SESSIONS 置換
    today_js = json.dumps(today_data, ensure_ascii=False, indent=2)
    html = re.sub(
        r'// ===== TODAY_SESSIONS =====\s*\nconst TODAY_SESSIONS = \{.*?\};',
        f'// ===== TODAY_SESSIONS =====\nconst TODAY_SESSIONS = {today_js};',
        html,
        flags=re.DOTALL
    )

    # PDCA_DATA 置換
    pdca_js = json.dumps(pdca_data, ensure_ascii=False, indent=2)
    html = re.sub(
        r'// ===== PDCA_DATA =====\s*\nconst PDCA_DATA = \{.*?\};',
        f'// ===== PDCA_DATA =====\nconst PDCA_DATA = {pdca_js};',
        html,
        flags=re.DOTALL
    )

    # PAST_ERRORS 置換
    past_js = json.dumps(past_errors, ensure_ascii=False)
    html = re.sub(
        r'// ===== PAST_ERRORS =====\s*\nconst PAST_ERRORS = \[.*?\];',
        f'// ===== PAST_ERRORS =====\nconst PAST_ERRORS = {past_js};',
        html, flags=re.DOTALL
    )

    return html


# ===== 既存 inject_data（stats 注入）=====

def inject_data(stats, today_data, pdca_data, past_errors):
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

    # ===== DATE display (footer) =====
    html = re.sub(
        r"new Date\('[^']*'\)\.toLocaleDateString\('ja-JP'",
        f"new Date('{stats['updated']}').toLocaleDateString('ja-JP'",
        html
    )

    # ===== Category progress (bunya-pct) =====
    # Notion category names → HTML display order: 電気回路, 電気・電子計測, 電磁気学, 電子理論
    cat_map = [
        ("green",  ["電気回路"]),
        ("accent", ["電気・電子計測", "電気及び電子計測"]),
        ("orange", ["電磁気学", "電磁気"]),
        ("purple", ["電子理論"]),
    ]
    bar_ids = ["b1", "b2", "b3", "b4"]
    bar_pcts = []
    for color_var, aliases in cat_map:
        d = {"total": 0, "achieved": 0}
        for alias in aliases:
            if alias in cat:
                d = cat[alias]
                break
        c_pct = round(d["achieved"] / d["total"] * 100) if d["total"] else 0
        c_ach = d["achieved"]
        c_tot = d["total"] or "?"
        bar_pcts.append(c_pct)
        html = re.sub(
            rf'(<div class="bunya-pct" style="color:var\(--{color_var}\)">)\d+%'
            rf' <span[^>]*>[^<]*</span>',
            rf'\g<1>{c_pct}% <span style="color:var(--muted);font-weight:400;font-size:.7rem">≈ {c_ach}/{c_tot}問</span>',
            html
        )

    # ===== Bar widths (JS animation) =====
    for i, (bid, bp) in enumerate(zip(bar_ids, bar_pcts)):
        html = re.sub(
            rf"document\.getElementById\('{bid}'\)\.style\.width='[^']*'",
            f"document.getElementById('{bid}').style.width='{bp}%'",
            html
        )

    # ===== TODAY_SESSIONS / PDCA_DATA / PAST_ERRORS 注入 =====
    html = inject_today_pdca(html, today_data, pdca_data, past_errors)

    with open("index.html","w",encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 更新完了: {stats['updated']}")
    print(f"   達成: {achieved}/{total} ({pct}%)")
    print(f"   うち 2回目〇 新規: {stats['new_achieved']}問")
    print(f"   弱点: {len(stats['weak'])}問")
    for k,v in stats["by_cat"].items():
        p = round(v["achieved"]/v["total"]*100) if v["total"] else 0
        print(f"   {k}: {v['achieved']}/{v['total']} ({p}%)")
    print(f"   今日のセッション: {len(today_data.get('sessions', []))}スロット")
    print(f"   PDCAログ: do={len(pdca_data.get('do_logs',[]))}件 / pending={len(pdca_data.get('check_pending',[]))}件 / bugs={len(pdca_data.get('act_bugs',[]))}件")
    print(f"   記憶チェック(PAST_ERRORS): {len(past_errors)}件")


if __name__ == "__main__":
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN が設定されていません")
        print("   export NOTION_TOKEN=your_token")
        exit(1)
    print("📡 Notion からデータ取得中...")
    notion_records = query_all(DB_ID)
    print(f"   {len(notion_records)}件 取得完了")
    stats = compute_stats(notion_records)

    print("📂 data/records.json 読み込み中...")
    records = load_records()
    print(f"   {len(records)}件 ローカルレコード読み込み完了")

    today_data  = compute_today_sessions(notion_records, records)
    pdca_data   = compute_pdca_data(records)
    past_errors = compute_past_errors(records)

    inject_data(stats, today_data, pdca_data, past_errors)
