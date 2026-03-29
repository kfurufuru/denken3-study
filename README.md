# denken3-study

電験三種（第三種電気主任技術者）合格に向けた学習資産リポジトリ。ノート・弱点・テンプレート・プロンプトを蓄積する場所。

---

## ⚡ テスト記録 ダッシュボード

[![テスト記録ダッシュボード](https://img.shields.io/badge/⚡_テスト記録-ダッシュボード-blue?style=for-the-badge)](https://kfurufuru.github.io/denken3-study/quiz.html)
[![学習進捗ページ](https://img.shields.io/badge/📚_学習進捗-ページ-brightgreen?style=for-the-badge)](https://kfurufuru.github.io/denken3-study/)
[![法規Wiki](https://img.shields.io/badge/📖_法規Wiki-条文×過去問-teal?style=for-the-badge)](https://kfurufuru.github.io/denken-wiki/)

| ダッシュボード | 内容 |
|---|---|
| [⚡ テスト記録 ダッシュボード](https://kfurufuru.github.io/denken3-study/quiz.html) | Bugマップ・レビュー予定・達成率 → **メイン利用先** |
| [📚 学習進捗ページ](https://kfurufuru.github.io/denken3-study/) | ノート・テンプレートインデックス |
| [📖 法規 知識Wiki](https://kfurufuru.github.io/denken-wiki/) | 条文×過去問クロスリファレンス → **法規の理解用** |

> 🤖 ChatGPTで「記録して」→ Make.com経由 → GitHub Actionsが自動で記録追記・ダッシュボード更新

---

## 🗺️ 学習システム全体マップ

```
Layer 1: 知識ベース（denken-wiki）     ← 「何を理解すべきか」
  └→ 条文解説・過去問クロスリファレンス・技術翻訳表
     🌐 https://kfurufuru.github.io/denken-wiki/

Layer 2: 進捗管理（denken3-study）     ← 「やったか / できたか」 ★ここ
  └→ 達成率ダッシュボード・テスト記録・弱点マップ
     🌐 https://kfurufuru.github.io/denken3-study/

Layer 3: 内省・分析（.secretary）      ← 「なぜ間違えたか」
  └→ e-log・フェインマンセッション・知識代謝（非公開）
```

---

## 🗂️ Notion 学習管理システム

| ページ | 役割 |
|---|---|
| [📚 電験3種 学習ダッシュボード](https://www.notion.so/af4180a0286e4c76b153fe6071cacf0a) | 全体の入口・進捗確認 |
| [📊 理論 学習マスターDB（95項目）](https://www.notion.so/6413af86a82e4bb390c4dc399b6f98cd) | ステータス・理解度・次回復習日の管理 |
| [📘 理論 合格ガイド](https://www.notion.so/e072dab8d7cc452f94e2bc5149354658) | 優先順位設計・8週間学習モデル |
| [🏢 Fカンパニー（AI知識チーム）](https://www.notion.so/32b6ccc20ddf81d39febf1d07dcb0789) | AI社員による学習サポート体制 |

> **役割分担**：Notion = 項目管理（数字・状態）、GitHub = ノート本体（公式・解説）・テスト記録ダッシュボード、ChatGPT = 問題出題・記録

---

## 📁 フォルダ構成

| フォルダ| 内容 |
|---|---|
| docs/ | 学習方針・ロードマップ・試験戦略 |
| notes/ | 科目別ノート（理論・電力・機械・法規） |
| mistakes/ | 弱点集・ミス記録 |
| templates/ | 週次レビュー・ノート・ミス分析テンプレ |
| logs/ | 週次レビュー記録 |
| data/ | テスト記録JSON（自動更新） |
| scripts/ | ダッシュボード生成スクリプト |

---

## 📖 法規科目について

法規の学習は **[denken-wiki](https://kfurufuru.github.io/denken-wiki/)** で条文理解→過去問演習のサイクルを回す。

| 法規リソース | リンク |
|---|---|
| テーマ別（接地工事・絶縁性能 等16テーマ） | [テーマ一覧](https://kfurufuru.github.io/denken-wiki/themes/) |
| 過去問マッピング（H23〜R03 143問） | [過去問](https://kfurufuru.github.io/denken-wiki/kakomon/) |
| 出題頻度ランキング | [ランキング](https://kfurufuru.github.io/denken-wiki/kakomon/ranking/) |
| 頻出数値一覧 | [数値一覧](https://kfurufuru.github.io/denken-wiki/reference/numbers/) |
