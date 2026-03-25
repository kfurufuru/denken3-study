#!/usr/bin/env python3
"""
テスト記録を data/records.json に追記するスクリプト
GitHub Actions の repository_dispatch イベントから呼び出される
"""
import json, os, sys
from datetime import datetime

RECORDS_PATH = "data/records.json"

def main():
    # GitHub Actions から渡されるペイロードを取得
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

    # 新しいレコードを追加
    records.append(record)

    # 書き戻す
    with open(RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"✅ レコード追記完了")
    print(f"   日付: {record.get('date')}")
    print(f"   科目: {record.get('subject')} / {record.get('theme')}")
    print(f"   結果: {record.get('result')} → 次回: {record.get('next_review')}")
    print(f"   総件数: {len(records)} 件")

if __name__ == "__main__":
    main()
