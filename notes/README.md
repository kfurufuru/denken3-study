# notes/ — 何をどこに書くか

**迷う時間をゼロにするための1枚ルール。書く前にここを3秒見る。**

## 判定フロー

```
その知識は「物理法則・原理」か？
  ├─ YES → clusters/<クラスタ名>.md      ← 科目をまたぐ。ここが正本
  └─ NO（機器の扱い・条文・設備知識）
        ├─ 法規 → 書かない。denken-wiki へ
        └─ それ以外 → <科目>.md
```

## 置き場一覧

| 内容 | 置き場 | 理由 |
|---|---|---|
| 物理法則・原理（Φ→e、ローレンツ力、磁気回路 …） | `notes/clusters/*.md` | 理論と機械で同じ穴を2回掘らないため |
| 機器の扱い方（巻数比・効率・%Z・制御） | `notes/machine.md` ほか科目別 | 法則ではなく運用知識 |
| 法規の条文・過去問クロスリファレンス | [denken-wiki](https://kfurufuru.github.io/denken-wiki/) | Wiki は条文×過去問の構造に最適化済み |
| 理論の科目別まとめ | [denken-wiki](https://kfurufuru.github.io/denken-wiki/) の theory/ | 既に整備済み。重複させない |
| 間違えた記録 | `mistakes/weak_points.md` | 弱点は資産 |
| テスト記録（数値） | `data/records.json`（`sr-record.py` が唯一の writer） | **手で編集しない** |
| 機械・電力の**進捗** | `machine-checklist.md` / `power-checklist.md` のチェックボックス | ここが達成率の SoT。`portal-summary.json` はこれを集計する |

## 進捗チェックリスト（下期受験科目）

チェックボックスを付けることが**進捗計測そのもの**。別途どこかへ転記しない。
`update_dashboard.py` が `- [x]` / `- [ ]` を数えて `data/portal-summary.json` の達成率を出す。

| 科目 | ファイル | 項目数 |
|---|---|---:|
| 機械 | [`machine-checklist.md`](machine-checklist.md) | 68 |
| 電力 | [`power-checklist.md`](power-checklist.md) | 61 |

---

## クラスタ一覧

| クラスタ | ファイル | 現在の弱点件数 |
|---|---|---|
| 磁気（Φ→e の一本道） | [`clusters/magnetism.md`](clusters/magnetism.md) | **16 / 25** |

> クラスタは**弱点が溜まってから作る**。空ファイルを先に並べない。
> 目安：同じ物理法則の ng/risky が3件を超えたら1本作る。

## 二重管理の禁止

同じ式・同じ説明を2箇所に書かない。片方は必ずリンクにする。
Wiki に既にあるものは Wiki へリンクし、**Wiki に無いものだけ**をここに書く。
