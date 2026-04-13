#!/usr/bin/env python3
"""
テスト記録を data/records.json に追記するスクリプト
GitHub Actions の repository_dispatch イベントから呼び出される

v2: theme_id 自動解決 + attempt 自動付番
"""
import json, os, re, sys
from datetime import datetime

RECORDS_PATH = "data/records.json"

# theme表示名 → theme_id 変換テーブル（既知テーマ）
THEME_ID_MAP = {
    "三相交流": "sansou-kouryu",
    "電磁誘導": "denji-yudou",
    "静電容量": "seiden-youryou",
    "電位・電界・磁界": "deni-denkai-jikai",
    "電界・磁界・電位": "denkai-jikai-deni",
    "磁界": "jikai",
    "不等率": "futouritsu",
    "過去問演習": "kakomon-enshu",
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


def to_slug(text):
    """theme表示名からtheme_idスラッグを生成（フォールバック用）"""
    text = text.strip().lower()
    # 日付サフィックスを除去 (e.g. "_2026-03-27")
    text = re.sub(r'_\d{4}-\d{2}-\d{2}$', '', text)
    # 英数字とハイフン以外をハイフンに
    text = re.sub(r'[^a-z0-9\u3040-\u9fff]+', '-', text)
    return text.strip('-') or "unknown"


def resolve_theme_id(record):
    """レコードの theme_id を解決する"""
    # 既に theme_id があればそのまま
    if record.get("theme_id"):
        return record["theme_id"]

    theme = record.get("theme", "")
    # 日付サフィックスを除去して検索
    base_theme = re.sub(r'_\d{4}-\d{2}-\d{2}$', '', theme)

    # 変換テーブルから検索
    if base_theme in THEME_ID_MAP:
        return THEME_ID_MAP[base_theme]

    # フォールバック: スラッグ化
    return to_slug(theme)


def calc_attempt(records, theme_id, subject):
    """同一 theme_id + subject の既存レコード数 + 1 を返す"""
    count = sum(
        1 for r in records
        if r.get("theme_id") == theme_id and r.get("subject") == subject
    )
    return count + 1


def main():
    record_json = os.environ.get("RECORD", "")
    if not record_json:
        print("❌ RECORD 環境変数が空です")
        sys.exit(1)

    try:
        record = json.loads(record_json)
    except json.JSONDecodeError as e:
        print(f"❌ JSON パースエラー: {e}")
        sys.exit(1)

    # 必須フィールドの検証
    required = ["subject", "theme", "result"]
    for field in required:
        if not record.get(field):
            print(f"⚠️  必須フィールド '{field}' が空です")

    # date が無い場合は今日の日付を補完
    if not record.get("date"):
        record["date"] = datetime.now().strftime("%Y-%m-%d")

    # 既存レコードを読み込む
    os.makedirs("data", exist_ok=True)
    try:
        with open(RECORDS_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        records = []

    # theme_id 自動解決
    record["theme_id"] = resolve_theme_id(record)

    # theme表示名を正規化（日付サフィックス除去）
    base_theme = re.sub(r'_\d{4}-\d{2}-\d{2}$', '', record.get("theme", ""))
    if base_theme != record.get("theme"):
        record["theme"] = base_theme

    # attempt 自動付番
    record["attempt"] = calc_attempt(records, record["theme_id"], record.get("subject", ""))

    # 不要フィールドの除去
    record.pop("consecutive_ok", None)

    # 新しいレコードを追加
    records.append(record)

    # 書き戻す
    with open(RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"✅ レコード追記完了")
    print(f"   日付: {record.get('date')}")
    print(f"   科目: {record.get('subject')} / {record.get('theme')} (id: {record.get('theme_id')})")
    print(f"   結果: {record.get('result')} → 次回: {record.get('next_review')}")
    print(f"   試行: {record.get('attempt')}回目")
    print(f"   総件数: {len(records)} 件")

if __name__ == "__main__":
    main()
