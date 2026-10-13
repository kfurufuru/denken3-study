#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""retro_open.py — docs/retro.md の「効果未確認」をセッション開始時に表示する。

置いた理由: CLAUDE.md の「反映したら、次の同種作業で効いたかを確認する」は、
エージェントが覚えていないと実行されない。SessionStart hook でこの一覧を毎回
コンテキストに入れ、ユーザーに言われなくても確認が回るようにする。

使い方（.claude/settings.json の SessionStart hook から呼ぶ）:
    python3 scripts/retro_open.py
未確認が無ければ何も出力しない。終了コードは常に 0（hook でセッションを止めない）。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp932 crash 回避
except Exception:
    pass

RETRO = Path(__file__).resolve().parent.parent / "docs" / "retro.md"


def open_items(text):
    m = re.search(r"^## 効果未確認\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return []
    return re.findall(r"^### (.+?)\n(.*?)(?=^### |\Z)", m.group(1), re.M | re.S)


def main():
    try:
        items = open_items(RETRO.read_text(encoding="utf-8"))
    except OSError:
        return
    if not items:
        return
    print(f"[docs/retro.md] 効果未確認の振り返り {len(items)} 件。"
          "今回の作業が確認条件に当たれば結果を書き、確認済みへ移すこと（CLAUDE.md「振り返り」）。")
    for title, body in items:
        cond = re.search(r"^- 確認条件: (.+)$", body, re.M)
        print(f"- {title}" + (f" — 確認条件: {cond.group(1)}" if cond else ""))


if __name__ == "__main__":
    main()
