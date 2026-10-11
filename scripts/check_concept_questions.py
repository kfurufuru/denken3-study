#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_concept_questions.py — data/concept-questions.json の構造検査。

置いた理由: 2026-09-16 時点で本ファイルを参照する検証も CI も1本も無く、
スキーマ不備・ID 衝突・theme_id の綴り違いが素通りしていた。電力8問を
追加した際は手で検査したが、手検査は次から効かない。

**射程**: 構造だけを見る。内容の正しさは一切見ない。
あわせて mistakes/weak_points.md の参照（`rec:日付/theme_id/attempt` と `q:問題ID`）が
records.json・本ファイルに実在するかを見る（2026-10-11 追加。誤答記録 → 原因パターン →
検証問題を辿れるようにしたため。参照先が消えたり綴りが違ったりすると辿れなくなる）。
問題文・模範解答が学問的に正しいか、数値が実在の規格と一致するかは検査しない。
それは wiki-review の観点レビューと第4監修の仕事で、本スクリプトでは代替できない。

使い方:
    python scripts/check_concept_questions.py          # 既定パスを検査
    python scripts/check_concept_questions.py <path>   # パス指定
終了コード: 0=PASS / 1=違反あり / 2=読み込み失敗
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp932 crash 回避
except Exception:
    pass

DEFAULT = Path(__file__).resolve().parent.parent / "data" / "concept-questions.json"
WEAK_POINTS = Path(__file__).resolve().parent.parent / "mistakes" / "weak_points.md"
# バッククォートで囲んだ参照だけを拾う（書式の説明文に出てくる雛形は囲まない）
WP_REF = re.compile(r"`(rec|q):([^`]+)`")

REQUIRED = [
    "id", "wiki", "section", "theme_id", "theme", "subject", "seq",
    "type", "difficulty", "importance", "wiki_anchor",
    "question", "key_points", "model_answer", "common_traps",
]
LIST_FIELDS = ["key_points", "common_traps"]
STR_FIELDS = ["id", "wiki", "section", "theme_id", "theme", "subject",
              "type", "difficulty", "importance", "wiki_anchor",
              "question", "model_answer"]

SUBJECTS = {"理論", "電力", "機械", "法規"}
IMPORTANCE = {"S", "A", "B", "C", "D"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def check(path):
    errors = []
    warns = []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] 読み込み失敗: {path}: {e}")
        return 2

    qs = data.get("questions")
    if not isinstance(qs, list) or not qs:
        print("[ERROR] questions が配列でないか空です")
        return 1

    for i, q in enumerate(qs):
        tag = q.get("id", f"index {i}")

        for f in REQUIRED:
            if f not in q:
                errors.append(f"{tag}: 必須項目が無い: {f}")

        for f in STR_FIELDS:
            v = q.get(f)
            if f in q and (not isinstance(v, str) or not v.strip()):
                errors.append(f"{tag}: {f} が空文字か文字列でない")

        for f in LIST_FIELDS:
            v = q.get(f)
            if f in q:
                if not isinstance(v, list) or not v:
                    errors.append(f"{tag}: {f} が空配列か配列でない")
                elif any(not isinstance(x, str) or not x.strip() for x in v):
                    errors.append(f"{tag}: {f} に空要素がある")

        if "seq" in q and not isinstance(q["seq"], int):
            errors.append(f"{tag}: seq が整数でない")

        # id は {wiki}_{section}_{seq:03d}
        if all(k in q for k in ("id", "wiki", "section", "seq")) and isinstance(q["seq"], int):
            want = "{}_{}_{:03d}".format(q["wiki"], q["section"], q["seq"])
            if q["id"] != want:
                errors.append(f"{tag}: id 規則違反。期待値 {want}")

        if q.get("subject") not in SUBJECTS and "subject" in q:
            errors.append(f"{tag}: subject が不正: {q.get('subject')!r}")

        if q.get("importance") not in IMPORTANCE and "importance" in q:
            errors.append(f"{tag}: importance が不正: {q.get('importance')!r}")

        for f in ("wiki", "section", "theme_id"):
            v = q.get(f)
            if isinstance(v, str) and not SLUG.match(v):
                errors.append(f"{tag}: {f} が slug 形式でない: {v!r}")

    ids = [q.get("id") for q in qs if "id" in q]
    for k, v in Counter(ids).items():
        if v > 1:
            errors.append(f"id が重複: {k}（{v}件）")

    # theme_id が同じ複数問は正常（1テーマに複数問）。ただし theme 名の揺れは事故のもと。
    by_theme = {}
    for q in qs:
        if "theme_id" in q and "theme" in q:
            by_theme.setdefault(q["theme_id"], set()).add(q["theme"])
    for tid, names in by_theme.items():
        if len(names) > 1:
            errors.append(f"theme_id {tid} に複数の theme 名: {sorted(names)}")

    # subject も theme_id 単位で一意であるべき
    by_subj = {}
    for q in qs:
        if "theme_id" in q and "subject" in q:
            by_subj.setdefault(q["theme_id"], set()).add(q["subject"])
    for tid, subs in by_subj.items():
        if len(subs) > 1:
            errors.append(f"theme_id {tid} に複数の subject: {sorted(subs)}")

    # records.json と theme_id の綴りが食い違うと concept-grade が新テーマを作ってしまう
    rec = Path(path).parent / "records.json"
    if rec.exists():
        try:
            rs = json.loads(rec.read_text(encoding="utf-8"))
            rec_themes = {r.get("theme_id") for r in rs}
            for tid, subs in sorted(by_subj.items()):
                if tid in rec_themes:
                    rsub = {r.get("subject") for r in rs if r.get("theme_id") == tid}
                    if rsub and not (rsub & subs):
                        errors.append(
                            f"theme_id {tid} の subject が records.json と不一致: "
                            f"問題集 {sorted(subs)} / 記録 {sorted(rsub)}")
        except Exception as e:
            warns.append(f"records.json と突合できませんでした: {e}")

    errors += check_weak_points(qs, rec)

    print(f"検査 {len(qs)} 問 / 違反 {len(errors)} 件")
    for w in warns:
        print(f"  [WARN] {w}")
    if errors:
        for e in errors:
            print(f"  [NG] {e}")
        print("判定: FAIL")
        return 1

    by_sub = Counter(q.get("subject") for q in qs)
    print("  科目別: " + " / ".join(f"{k} {v}" for k, v in sorted(by_sub.items())))
    print("判定: PASS（構造のみ。内容の正しさは検査していません）")
    return 0


def check_weak_points(qs, rec):
    """weak_points.md の `rec:` `q:` 参照が実在するか。"""
    if not WEAK_POINTS.exists():
        return []
    errors = []
    qids = {q.get("id") for q in qs}
    keys = set()
    if rec.exists():
        try:
            keys = {f"{r.get('date')}/{r.get('theme_id')}/{r.get('attempt')}"
                    for r in json.loads(rec.read_text(encoding="utf-8"))}
        except Exception:
            pass  # records.json の読み込み失敗は上で WARN 済み
    text = WEAK_POINTS.read_text(encoding="utf-8")
    for kind, ref in sorted(set(WP_REF.findall(text))):
        if kind == "q" and ref not in qids:
            errors.append(f"weak_points.md: 問題IDが存在しない: q:{ref}")
        if kind == "rec" and keys and ref not in keys:
            errors.append(f"weak_points.md: records.json に該当記録が無い: rec:{ref}")
    return errors


if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
