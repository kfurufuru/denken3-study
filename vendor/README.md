# vendor/ — secretary-portal から写したファイル

| ファイル | 正本 | 使う所 |
|---|---|---|
| `sr_order.py` | secretary-portal `scripts/sr_order.py` | `update_dashboard.py` の「今日の学習」の SR 復習の並べ方 |
| `fsrs_engine.py` | secretary-portal `scripts/fsrs_engine.py` | `sr_order.py` が import する（想起確率） |

- この repo の CI（update.yml）は secretary-portal（非公開）を読めないので、写しを置いている。
- **手で直さない。** 正本を直したら、`.secretary/denken3-study-dashboard/` で次を実行して写し直す。

```
cp ../scripts/sr_order.py ../scripts/fsrs_engine.py vendor/
python scripts/check_site.py
```

- `scripts/check_site.py` の検査5が、正本とのバイト一致を確かめる。正本に届くのは、この repo が `.secretary/` の中にある PC だけ。CI では照合せず WARN を出す。
- 写しの `sr_order.py --self-test` はここでは落ちる（正本の呼び手 `check_study_streak.py` が隣に無いため）。自己テストは正本の側で回す。
