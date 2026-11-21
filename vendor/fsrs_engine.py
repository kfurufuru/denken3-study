#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fsrs_engine.py — FSRS-6 スケジューラの自己完結実装（sr-record.py の計算エンジン）。

式・定数は py-fsrs（open-spaced-repetition/py-fsrs, MIT）fsrs/scheduler.py から
逐語移植（2026-07-30 取得・一次照合済み）。依存追加を避けるため vendored。
本システム向けの固定条件（py-fsrs の設定値に対応）:
  - learning_steps=() / relearning_steps=() … 分単位ステップは日粒度のチャット学習に不適合。
    全 rating が直接 next_interval へ（py-fsrs は steps 空のとき同じ経路を通る）
  - enable_fuzzing=False … 記録の決定性を優先（テスト可能性・再現性）
  - maximum_interval=365 … 試験対策文脈（py-fsrs 既定 36500 日は不適合）
  - desired_retention=0.9 … このとき next_interval == stability が厳密に成立

rating 対応（sr-record.py の result 3値 → FSRS 4値の部分集合）:
  ng → 1 (Again) / risky → 2 (Hard) / ok → 3 (Good)。4 (Easy) は未使用。

SM-2 履歴からの移行シード（seed_from_sm2）は FSRS 公式ではないヒューリスティック:
  - stability = 前回 interval_days（retention 0.9 で interval==stability のため自然に接続）
  - difficulty = clamp(11 - 3*ease_factor, 1, 10)（ease 2.5→3.5 / 1.3→7.1 / 3.0→2.0）

自己テスト: python scripts/fsrs_engine.py --self-test
"""
import math
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp932 crash 回避
except Exception:
    pass

# py-fsrs DEFAULT_PARAMETERS（FSRS-6・21個・逐語）
FSRS_DEFAULT_DECAY = 0.1542
DEFAULT_PARAMETERS = (
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722,
    0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425,
    0.0912, 0.0658, FSRS_DEFAULT_DECAY,
)
STABILITY_MIN = 0.001
MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0

DESIRED_RETENTION = 0.9
MAXIMUM_INTERVAL = 365

W = DEFAULT_PARAMETERS
_DECAY = -W[20]
_FACTOR = 0.9 ** (1 / _DECAY) - 1

RATING_AGAIN, RATING_HARD, RATING_GOOD, RATING_EASY = 1, 2, 3, 4
RESULT_TO_RATING = {"ng": RATING_AGAIN, "risky": RATING_HARD, "ok": RATING_GOOD}


def _clamp_difficulty(d):
    return min(max(d, MIN_DIFFICULTY), MAX_DIFFICULTY)


def _clamp_stability(s):
    return max(s, STABILITY_MIN)


def initial_stability(rating):
    return _clamp_stability(W[rating - 1])


def initial_difficulty(rating, clamp=True):
    d = W[4] - (math.e ** (W[5] * (rating - 1))) + 1
    return _clamp_difficulty(d) if clamp else d


def retrievability(elapsed_days, stability):
    """review後 elapsed_days 日時点の想起確率 R(t,S)。"""
    elapsed_days = max(0, elapsed_days)
    return (1 + _FACTOR * elapsed_days / stability) ** _DECAY


def next_difficulty(difficulty, rating):
    """linear damping + mean reversion（py-fsrs _next_difficulty 逐語）。"""
    arg_1 = initial_difficulty(RATING_EASY, clamp=False)
    delta_difficulty = -(W[6] * (rating - 3))
    linear_damping = (10.0 - difficulty) * delta_difficulty / 9.0
    arg_2 = difficulty + linear_damping
    return _clamp_difficulty(W[7] * arg_1 + (1 - W[7]) * arg_2)


def _next_recall_stability(difficulty, stability, r, rating):
    hard_penalty = W[15] if rating == RATING_HARD else 1
    easy_bonus = W[16] if rating == RATING_EASY else 1
    return stability * (
        1
        + (math.e ** W[8])
        * (11 - difficulty)
        * (stability ** -W[9])
        * ((math.e ** ((1 - r) * W[10])) - 1)
        * hard_penalty
        * easy_bonus
    )


def _next_forget_stability(difficulty, stability, r):
    long_term = (
        W[11]
        * (difficulty ** -W[12])
        * (((stability + 1) ** W[13]) - 1)
        * (math.e ** ((1 - r) * W[14]))
    )
    short_term = stability / (math.e ** (W[17] * W[18]))
    return min(long_term, short_term)


def _short_term_stability(stability, rating):
    inc = (math.e ** (W[17] * (rating - 3 + W[18]))) * (stability ** -W[19])
    if rating in (RATING_HARD, RATING_GOOD, RATING_EASY):
        inc = max(inc, 1.0)
    return _clamp_stability(stability * inc)


def review(stability, difficulty, rating, elapsed_days):
    """1回のレビューで (new_stability, new_difficulty) を返す。

    stability/difficulty が None なら新規カード（initial_*）。
    elapsed_days < 1 は同日再レビュー（short-term 経路・py-fsrs と同挙動）。
    """
    if stability is None or difficulty is None:
        return initial_stability(rating), initial_difficulty(rating)
    if elapsed_days < 1:
        return _short_term_stability(stability, rating), next_difficulty(difficulty, rating)
    r = retrievability(elapsed_days, stability)
    if rating == RATING_AGAIN:
        s = _next_forget_stability(difficulty, stability, r)
    else:
        s = _next_recall_stability(difficulty, stability, r, rating)
    return _clamp_stability(s), next_difficulty(difficulty, rating)


def next_interval(stability, desired_retention=DESIRED_RETENTION,
                  maximum_interval=MAXIMUM_INTERVAL):
    iv = (stability / _FACTOR) * ((desired_retention ** (1 / _DECAY)) - 1)
    return min(max(round(iv), 1), maximum_interval)


def next_review_label(interval_days):
    """interval_days -> next_review ラベル（v1 互換・旧 concept-grade Step 7c の対応表）。"""
    if interval_days <= 1:
        return "SR1"
    if interval_days <= 5:
        return "SR2"
    if interval_days <= 13:
        return "SR3"
    return "done"


def seed_from_sm2(interval_days, ease_factor):
    """SM-2 履歴しかない record から FSRS 状態を初期化する移行ヒューリスティック。

    FSRS 公式の手続きではない（公式は review log 全履歴の replay）。本システムは
    record 単位で状態を持ち回るため、直前 interval を stability に読み替える
    （retention 0.9 なら interval==stability）近似で接続する。
    """
    s = _clamp_stability(float(interval_days) if interval_days else 1.0)
    d = _clamp_difficulty(11.0 - 3.0 * float(ease_factor or 2.5))
    return s, d


def _self_test():
    failures = []

    def check(name, cond, detail=""):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
        if not cond:
            failures.append(name)

    # 1) 定数の内部整合: retention 0.9 で interval == stability（丸め前）
    for s in (1, 6, 30, 365):
        iv = (s / _FACTOR) * ((0.9 ** (1 / _DECAY)) - 1)
        check(f"interval==stability (S={s})", abs(iv - s) < 1e-9, f"iv={iv}")

    # 2) 新規カード: initial_* がパラメータ表と一致
    check("initial S(Good)==w[2]", initial_stability(RATING_GOOD) == W[2])
    check("initial D clamp [1,10]",
          all(1.0 <= initial_difficulty(r) <= 10.0 for r in (1, 2, 3, 4)))

    # 3) 移行シード → ok: interval が伸びる（SM-2 由来 S=6, ease=2.5, 6日後に ok）
    s0, d0 = seed_from_sm2(6, 2.5)
    s_ok, d_ok = review(s0, d0, RATING_GOOD, elapsed_days=6)
    check("ok で stability 増", s_ok > s0, f"{s0}->{round(s_ok, 2)}")
    check("ok 後 interval > 前回", next_interval(s_ok) > 6, f"iv={next_interval(s_ok)}")

    # 4) ng: stability が縮む・interval 短縮
    s_ng, d_ng = review(s0, d0, RATING_AGAIN, elapsed_days=6)
    check("ng で stability 減", s_ng < s0, f"{s0}->{round(s_ng, 2)}")
    check("ng で difficulty 増", d_ng > d0, f"{round(d0, 2)}->{round(d_ng, 2)}")

    # 5) 単調性: 同状態から ok > risky > ng の interval 順
    s_r, _ = review(s0, d0, RATING_HARD, elapsed_days=6)
    check("interval 単調 ok>risky>ng",
          next_interval(s_ok) > next_interval(s_r) > next_interval(s_ng)
          or next_interval(s_r) == next_interval(s_ng) == 1)

    # 6) adversarial: 同日再レビュー（elapsed=0）が short-term 経路で完走
    s_st, d_st = review(s0, d0, RATING_GOOD, elapsed_days=0)
    check("同日再レビュー完走・S非減", s_st >= s0, f"{s0}->{round(s_st, 2)}")

    # 7) adversarial: 大幅超過（117日・dead-man 実例）で発散しない
    s_over, _ = review(s0, d0, RATING_GOOD, elapsed_days=117)
    check("117日超過 ok で有限・上限内", s_over > 0 and next_interval(s_over) <= 365,
          f"S={round(s_over, 2)} iv={next_interval(s_over)}")

    # 8) adversarial: 極端値でも clamp が効く（S 極小・D 両端・負 elapsed）
    s_x, d_x = review(0.001, 10.0, RATING_AGAIN, elapsed_days=400)
    check("極小S+ng で S>=0.001", s_x >= STABILITY_MIN)
    check("D clamp 上限", next_difficulty(10.0, RATING_AGAIN) <= 10.0)
    check("負 elapsed は 0 扱い", retrievability(-5, 6.0) == 1.0)
    check("interval 下限 1", next_interval(0.001) == 1)

    # 9) next_review_label 境界（1/5/13 の以下・超過）
    check("label 境界", (next_review_label(1), next_review_label(2), next_review_label(5),
                        next_review_label(6), next_review_label(13), next_review_label(14))
          == ("SR1", "SR2", "SR2", "SR3", "SR3", "done"))

    # 10) seed_from_sm2 の写像点検（docstring の3点）
    for ease, d_exp in ((2.5, 3.5), (1.3, 7.1), (3.0, 2.0)):
        _, d = seed_from_sm2(6, ease)
        check(f"seed D(ease={ease})≈{d_exp}", abs(d - d_exp) < 1e-9, f"d={d}")

    print(f"\nself-test: {'ALL PASS' if not failures else 'FAIL: ' + ', '.join(failures)}")
    return 0 if not failures else 1


def _cli_next(argv):
    """concept-grade 等の呼び出し用 CLI。手計算（LLM の暗算）を排除する。

    使い方:
      新規テーマ:   python fsrs_engine.py --next --result ok
      既存(FSRS):   python fsrs_engine.py --next --result ng --stability 6.0 --difficulty 3.5 --elapsed 6
      既存(SM-2遺産): python fsrs_engine.py --next --result ok --interval 6 --ease 2.5 --elapsed 6
    出力: {"fsrs_stability":…,"fsrs_difficulty":…,"interval_days":…,"next_review":…} の JSON 1行
    """
    import argparse
    import json
    ap = argparse.ArgumentParser(description="FSRS-6 次回スケジュール計算")
    ap.add_argument("--result", required=True, choices=sorted(RESULT_TO_RATING))
    ap.add_argument("--stability", type=float, help="前回 fsrs_stability")
    ap.add_argument("--difficulty", type=float, help="前回 fsrs_difficulty")
    ap.add_argument("--interval", type=float, help="前回 interval_days（SM-2 遺産からの seed 用）")
    ap.add_argument("--ease", type=float, help="前回 ease_factor（同上）")
    ap.add_argument("--elapsed", type=float, default=None, help="前回レビューからの経過日数")
    a = ap.parse_args(argv)
    if a.stability is not None and a.difficulty is not None:
        s0, d0 = a.stability, a.difficulty
    elif a.interval is not None or a.ease is not None:
        s0, d0 = seed_from_sm2(a.interval or 1, a.ease or 2.5)
    else:
        s0 = d0 = None  # 新規テーマ
    elapsed = a.elapsed if a.elapsed is not None else (a.interval or 0)
    s, d = review(s0, d0, RESULT_TO_RATING[a.result], elapsed)
    iv = next_interval(s)
    print(json.dumps({
        "fsrs_stability": round(s, 4),
        "fsrs_difficulty": round(d, 4),
        "interval_days": iv,
        "next_review": next_review_label(iv),
    }))
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    if "--next" in sys.argv:
        argv = [x for x in sys.argv[1:] if x != "--next"]
        sys.exit(_cli_next(argv))
    print(__doc__)
