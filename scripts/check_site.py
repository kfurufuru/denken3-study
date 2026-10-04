#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_site.py — 公開 HTML の回帰検査（リンク・試験日・onclick）。

置いた理由: 同じ種類の修正が繰り返されていた。
  - #22 → #27: 404 のポータルリンクを index.html だけ直し、denken-map.html と
    stats.html に直し漏れた（「前回の直し漏れ」）
  - #23 → #24: 試験日を直したが、手書きラベル2件が旧値のまま残った
  - #30: 定義のない関数（quizRefresh）を呼ぶ更新ボタンが残っていた
人の注意では再発を防げなかったので、機械で落とす。

**射程**: オフラインで決まることだけを見る。
  1. 退役済み URL（DENYLIST）が *.html / 生成スクリプトに残っていないか
  2. リポジトリ内への相対リンク（href / src）の先が実在するか
  3. 試験日が update_dashboard.py の EXAM_DATE 1か所と一致しているか
     （index.html の JS 定数・手書きラベルの日付と試験回「R08下」の両方）
  4. onclick="f(...)" の f が同じファイル内で定義されているか
外部 URL の生死（HTTP 200 か）は見ない。ネットワーク依存で CI が不安定になるため。
内容の正しさ（合格点・数値・解説）も見ない。

使い方:
    python scripts/check_site.py
終了コード: 0=PASS / 1=違反あり
"""
import ast
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp932 crash 回避
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# 退役済みで、二度と戻ってはいけない URL。直したら理由付きでここに足す。
DENYLIST = {
    "kfurufuru.github.io/secretary-portal/": "404。secretary-portal-public/ を使う（#22, #27）",
    "kfurufuru.github.io/denken-wiki-riron/": "更新停止の旧理論Wiki（#22）",
    "kfurufuru.github.io/denken-wiki-denryoku/": "更新停止の旧電力Wiki（#22）",
}
# DENYLIST を検査する対象。コメントで旧 URL に言及するのは可なので、
# .py は「文字列リテラル内」だけを見る。
HTML_GLOB = "*.html"
PY_FILES = ["update_dashboard.py", "scripts/generate_quiz_dashboard.py"]

LINK = re.compile(r'\b(?:href|src)\s*=\s*"([^"]*)"')
ONCLICK = re.compile(r'\bonclick\s*=\s*"\s*([A-Za-z_$][\w$]*)\s*\(')
JS_DEF = r'(?:function\s+{0}\s*\(|\b(?:const|let|var)\s+{0}\s*=|\bwindow\.{0}\s*=|\b{0}\s*:\s*function)'
JS_EXAM = re.compile(r"const\s+EXAM_DATE\s*=\s*new Date\('(\d{4}-\d{2}-\d{2})")
LABEL_EXAM = re.compile(r"CBT初日\s*\((\d{4}-\d{2}-\d{2})\)")
# 試験回ラベル（「R08上 (2026年8月下旬)」「R08下 CBT初日」など）。過去問番号「R04下-問8」は対象外。
LABEL_SESSION = re.compile(r"R(\d{2})([上下])\s*(?=試験|CBT|\()")


def session_of(iso):
    """試験日から「R08下」のような試験回を出す。年度は4月始まり、上期=4〜9月。"""
    y, m = int(iso[:4]), int(iso[5:7])
    nendo = y if m >= 4 else y - 1
    return f"R{nendo - 2018:02d}", ("上" if 4 <= m <= 9 else "下")


def lineno(text, pos):
    return text.count("\n", 0, pos) + 1


def py_string_literals(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value


def exam_date_from_py():
    """update_dashboard.py の EXAM_DATE = datetime.date(Y, M, D) を読む。複数定義は違反。"""
    path = ROOT / "update_dashboard.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "EXAM_DATE" for t in node.targets
        ):
            call = node.value
            if isinstance(call, ast.Call) and len(call.args) == 3 and all(
                isinstance(a, ast.Constant) for a in call.args
            ):
                y, m, d = (a.value for a in call.args)
                found.append((node.lineno, f"{y:04d}-{m:02d}-{d:02d}"))
            else:
                found.append((node.lineno, None))
    return found


def main():
    errors, warns = [], []
    htmls = sorted(ROOT.glob(HTML_GLOB))

    # 1. 退役済み URL
    for path in htmls:
        text = path.read_text(encoding="utf-8")
        for bad, why in DENYLIST.items():
            for m in re.finditer(re.escape(bad), text):
                errors.append(f"{path.name}:{lineno(text, m.start())}: 退役済み URL {bad} — {why}")
    for rel in PY_FILES:
        path = ROOT / rel
        for ln, s in py_string_literals(path):
            for bad, why in DENYLIST.items():
                if bad in s:
                    errors.append(f"{rel}:{ln}: 退役済み URL {bad} — {why}")

    # 2. 相対リンクの実在
    for path in htmls:
        text = path.read_text(encoding="utf-8")
        for m in LINK.finditer(text):
            url = m.group(1).strip()
            where = f"{path.name}:{lineno(text, m.start())}"
            if not url or url.startswith(("#", "http://", "https://", "mailto:", "javascript:", "data:", "{", "$")):
                continue
            if url.startswith("file:"):
                errors.append(f"{where}: file:// リンクは公開ページから開けない（#33 で撤去）: {url}")
                continue
            target = (path.parent / url.split("#")[0].split("?")[0]).resolve()
            if ROOT not in target.parents and target != ROOT:
                warns.append(f"{where}: リポジトリ外を指すので実在を検査できない: {url}")
                continue
            if not target.exists():
                errors.append(f"{where}: リンク先が無い: {url}")

    # 3. 試験日の一元化
    defs = exam_date_from_py()
    if len(defs) != 1 or defs[0][1] is None:
        errors.append(f"update_dashboard.py: EXAM_DATE は datetime.date(Y, M, D) で1か所だけ定義する（検出: {defs}）")
    else:
        exam = defs[0][1]
        index = ROOT / "index.html"
        text = index.read_text(encoding="utf-8")
        js = [(lineno(text, m.start()), m.group(1)) for m in JS_EXAM.finditer(text)]
        if len(js) != 1:
            errors.append(f"index.html: const EXAM_DATE が1件でない（{len(js)}件）")
        for ln, v in js:
            if v != exam:
                errors.append(f"index.html:{ln}: JS の EXAM_DATE {v} ≠ update_dashboard.py の {exam}")
        for m in LABEL_EXAM.finditer(text):
            if m.group(1) != exam:
                errors.append(f"index.html:{lineno(text, m.start())}: 手書きラベルの試験日 {m.group(1)} ≠ {exam}")
        want = "".join(session_of(exam))
        for m in LABEL_SESSION.finditer(text):
            got = f"R{m.group(1)}{m.group(2)}"
            if got != want:
                errors.append(f"index.html:{lineno(text, m.start())}: 試験回ラベル {got} ≠ EXAM_DATE から出る {want}")

    # 4. onclick の関数が定義されているか
    for path in htmls:
        text = path.read_text(encoding="utf-8")
        for m in ONCLICK.finditer(text):
            name = m.group(1)
            if not re.search(JS_DEF.format(re.escape(name)), text):
                errors.append(f"{path.name}:{lineno(text, m.start())}: onclick の {name}() が定義されていない")

    for w in warns:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[ERROR] {e}")
    if errors:
        print(f"FAIL: {len(errors)} 件")
        return 1
    print(f"PASS（HTML {len(htmls)} ファイル, WARN {len(warns)} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
