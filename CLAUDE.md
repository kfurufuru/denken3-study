# denken3-study — エージェント向け作業ルール

電験三種の学習資産リポジトリ。GitHub Pages で `*.html` をそのまま公開している。
ここに書くルールは、過去に**同じ修正を繰り返した履歴**から抜き出したもの。
機械で検出できるものは `scripts/check_site.py`・`scripts/check_concept_questions.py` に寄せてあり、
このファイルには「機械で検出できないもの」だけを書く。

## push 前に必ず走らせる

```
python scripts/check_site.py
python scripts/check_concept_questions.py
```

どちらも CI（check-site.yml / check-data.yml）でも走る。ローカルで落ちるものを push しない。

## 書き込みの持ち主（誰がどこを書くか）

- `data/records.json` の writer はローカルの `sr-record.py` だけ。手編集・workflow からの追記はしない。
- `index.html` の一部は生成物で、手で直しても翌朝戻る。
  - `update_dashboard.py`（毎朝 update.yml）: `// ===== DATA =====` ブロック、達成率リング、`EXAM_DATE` の JS 行など
  - `scripts/generate_quiz_dashboard.py`（build-quiz.yml 手動）: QUIZ_MAIN / QUIZ_CHART セクション
  - 生成領域の値を直すときは**生成スクリプト側**を直す。手書き領域だけを直接編集する。

## 過去に繰り返したミスと、その予防

1. **直し漏れ**（#22→#27, #23→#24）: 1か所直したら、同じ文字列・同じ値をリポジトリ全体で `grep` して全件直す。
   PR 本文に「修正後、旧値は 0 件」と grep 結果を書く。
2. **定数の二重定義**（#23）: 同じ値を2か所に書かない。試験日は `update_dashboard.py` の `EXAM_DATE` だけが正本。
3. **退役した URL の復活**（#22, #27）: URL を退役させたら `scripts/check_site.py` の `DENYLIST` に理由付きで足す。
4. **画面は出るのに中身が違う**（#26）: fetch 失敗時に固定値へ落ちる作りがある。表示を変えたら、
   実ブラウザで開いて console のエラーと表示内容を確認する（「エラーが出ない」は検証にならない）。
5. **学習内容の誤り**（#15, #30, #32）: 合格点・数値・条文の値を書く／直すときは、出典（試験センター公式・電技解釈）を
   確認する。1か所で誤りを見つけたら、`notes/` `mistakes/` `data/` `docs/` の同じ記述を grep して全件直す。
   `wiki_anchor` は実在するページ id であることを確認する（CI は外部 Wiki を見ないので検出しない）。

## このファイルの更新ルール

同じ種類の修正が2回起きたら、まず `scripts/check_*.py` で機械的に検出できないか考える。
できないものだけをここに1行で足す。反映したら、次の同種作業で効いたかを確認する。
