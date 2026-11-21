"""
sr_order.py — records.json を読む装置の「次にやるテーマ」の順序の正本（R2）

設計: inbox/design-r2-pick-order-20261023.md（2026-10-23 決定）
規範: docs/shimoki-site-philosophy.md R2「同じ正本を読む装置は、同じ順序を出す」

呼ぶ側は scripts/sr-pick-next.py（skill sr-quick ほか）と scripts/check_study_streak.py
（セッション開始フック）。**並べ方・候補の選び方・期日はここにしか書かない。**
以前は2つが別々に書いていて、同じ records.json から逆の順序を出していた
（直ったテーマが残る・期日を見ない・期日前の ng を出す。設計書 1-1 で再現）。

順序: (未克服か, 想起確率 R の低い順, theme_id)
  - 候補はテーマの最新の記録で、期日が今日以前のものだけ（期日前の ng は出さない）
  - ng を risky より先にする段は置かない。ng は安定度が小さく R が早く下がるので、
    R の順で自然に前へ出る。段を置くと、長く放置した risky が ng の後ろに沈む
  - FSRS-6 では次の間隔は R が 0.9 に下がる日で、間隔≒安定度。だから R の低い順は
    機械Wiki の「経過日数÷間隔の大きい順」（kikai-tracker.jsx の overdueRatio）とほぼ同じ順になる

Usage:
  python scripts/sr_order.py --self-test
"""
import datetime as dt
import importlib.util
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fsrs_engine  # noqa: E402

UNMASTERED = {"ng", "risky"}
# next_review ラベル → 日数（interval_days を持たない v1 の記録用）
SR_LABEL_DAYS = {"SR1": 1, "SR2": 3, "SR3": 7}
MAX_DAYS = 36500  # 間隔・安定度の上限（これを超える値は壊れた記録として読まない）


def jst_today(now: dt.datetime | None = None) -> dt.date:
    """日本時間の今日。クラウドのコンテナは UTC なので date.today() は日本時間 0〜9 時に1日前になる。
    日本は夏時間が無いので固定の +9 時間でよい（zoneinfo は Windows で tzdata が要る）。now は self-test 用（aware）。"""
    jst = dt.timezone(dt.timedelta(hours=9))
    return (now.astimezone(jst) if now else dt.datetime.now(jst)).date()


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _date(v) -> dt.date | None:
    """'YYYY-MM-DD' だけを日付として読む（Python 3.11 以降の fromisoformat は '20261001' も受けるが、
    文字列で日付を比べる箇所と食い違うので受けない）。"""
    if not isinstance(v, str) or not _DATE_RE.match(v):
        return None
    try:
        return dt.date.fromisoformat(v)
    except ValueError:
        return None


def _num(v) -> float | None:
    """有限の数（数字の文字列を含む）。bool・NaN・無限大・数でないものは None。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return None
    if isinstance(v, (int, float)):
        try:
            f = float(v)
        except OverflowError:
            return None
        return f if math.isfinite(f) else None
    return None


def _days(v) -> int | None:
    """間隔の日数。0 以上の数（1.0・"1" も受ける）を整数に丸める。"""
    f = _num(v)
    if f is None or f < 0 or f > MAX_DAYS:
        return None
    return int(round(f))


def _plus(d: dt.date, days: int) -> dt.date | None:
    try:
        return d + dt.timedelta(days=days)
    except OverflowError:   # 9999-12-31 + 間隔 など
        return None


def theme_key(rec: dict):
    """テーマの鍵は theme_id だけ。sr-record.py は必ず theme_id を書く。

    theme だけの古い記録を theme で束ねると、同じテーマが theme_id の記録と2行に割れる（監査 #4）。
    文字列・整数でない theme_id（配列など）は鍵にしない（監査 #5: 辞書の鍵にできず例外で止まる）。
    """
    k = rec.get("theme_id")
    if isinstance(k, bool) or not isinstance(k, (str, int)) or k == "":
        return None
    return k


def is_test_record(rec: dict) -> bool:
    """theme_id が 'test-' で始まる試験用の記録（sr-pick-next.py の load_records と同じ判定）。
    正本の側で外すので、フックと sr-pick-next が同じテーマを数える（監査 #3）。"""
    return str(rec.get("theme_id", "")).lower().startswith("test-")


def _rank(r: dict, i: int, until: dt.date | None = None):
    """記録の順位（日付 → attempt → 追記した順）。日付が読めない・until より後なら None。

    「テーマの最新の記録」の定義はこの1か所。sr-record.py の「前回の記録」もこれを使う（R2 段階3）。
    """
    d = _date(r.get("date"))
    if d is None or (until is not None and d > until):
        return None
    att = _num(r.get("attempt"))
    return (d, att if att is not None else 0.0, i)


def latest_of_theme(records: list, theme_id, until: dt.date | None = None) -> dict | None:
    """1つのテーマの最新の記録（順位は _rank）。until を渡すと、その日以前の記録だけから選ぶ。

    試験用の theme_id でも数える（呼ぶ側がテーマを名指しするため。sr-record.py --allow-test-id）。
    """
    best = None
    for i, r in enumerate(records if isinstance(records, list) else []):
        if not isinstance(r, dict) or r.get("theme_id") != theme_id:
            continue
        rank = _rank(r, i, until)
        if rank is not None and (best is None or rank > best[0]):
            best = (rank, r)
    return best[1] if best else None


def latest_pairs(records: list, today: dt.date | None = None) -> list[tuple]:
    """テーマごとの (最新の記録, その1つ前の記録 または None)。順位は日付 → attempt → 追記した順。

    日付の読めない記録・テーマの無い記録・試験用の記録は数えない。
    today を渡すと、今日より後の日付の記録も数えない（sr-record.py の --date は日付を検査しないので、
    打ち間違えた未来日の ok がテーマの最新になり、本当の最新の ng を隠す。監査 #2）。
    """
    top: dict = {}
    for i, r in enumerate(records if isinstance(records, list) else []):
        if not isinstance(r, dict) or is_test_record(r):
            continue
        key, rank = theme_key(r), _rank(r, i, today)
        if key is None or rank is None:
            continue
        item = (rank, r)
        best, second = top.get(key, (None, None))
        if best is None or item[0] > best[0]:
            top[key] = (item, best)
        elif second is None or item[0] > second[0]:
            top[key] = (best, item)
    return [(b[1], s[1] if s else None) for b, s in top.values()]


def latest_per_theme(records: list, today: dt.date | None = None) -> list[dict]:
    """テーマごとの最新の記録（latest_pairs の最新だけ）。"""
    return [r for r, _ in latest_pairs(records, today)]


def recall_test_applies(rec: dict, prev: dict | None) -> bool:
    """recall_test_due（ok の3日後の再テスト）を効かせるか。

    効かせるのは「ng・risky の直後に付けた ok」だけ（2026-10-23 古舘さん決定・設計書 §11）。
    sr-record.py は ok のたびに recall_test_due を書くが、毎回効かせると FSRS の間隔が77日に伸びても
    3日ごとに戻る（監査 #1）。直後の確かめ（わかったつもりの検出）だけを残し、以後は FSRS に従う。
    書く側は変えない（すでに書かれた古い記録にも同じ規則が効くように、読む側の1か所で決める）。
    """
    return (rec.get("result") == "ok" and isinstance(prev, dict)
            and not is_mastered(prev))


def due_date(rec: dict, prev: dict | None = None) -> dt.date | None:
    """期日。date + interval_days。ng・risky の直後の ok だけは recall_test_due との早い方
    （recall_test_applies）。

    どちらも無い記録は next_review のラベルから求める。'done'・不明は None（出さない）。
    recall_test_due を優先しないのは、ok を付けたばかりのテーマは FSRS の間隔が2日になる
    ことがあり、recall_test_due（3日後）を優先すると FSRS の期日を過ぎてから出るため。
    """
    d = _date(rec.get("date"))
    if d is None:
        return None
    cands = []
    rtd = _date(rec.get("recall_test_due")) if recall_test_applies(rec, prev) else None
    if rtd is not None:
        cands.append(rtd)
    iv = _days(rec.get("interval_days"))
    if iv is not None and _plus(d, iv) is not None:
        cands.append(_plus(d, iv))
    if cands:
        return min(cands)
    label = rec.get("next_review")
    if isinstance(label, str) and label in SR_LABEL_DAYS:
        return _plus(d, SR_LABEL_DAYS[label])
    return None


def stability(rec: dict) -> float:
    """FSRS の安定度。無い古い記録は interval_days（FSRS-6 では間隔≒安定度）で代える。"""
    s = _num(rec.get("fsrs_stability"))
    if s is not None and s > 0:
        return min(s, float(MAX_DAYS))
    iv = _days(rec.get("interval_days"))
    if iv:
        return float(iv)
    label = rec.get("next_review")
    return float(SR_LABEL_DAYS.get(label, 1) if isinstance(label, str) else 1)


def retrievability(rec: dict, today: dt.date) -> float:
    d = _date(rec.get("date"))
    elapsed = (today - d).days if d else 0
    return fsrs_engine.retrievability(elapsed, stability(rec))


def is_mastered(rec: dict) -> bool:
    res = rec.get("result")
    return not (isinstance(res, str) and res in UNMASTERED)


def order_key(rec: dict, today: dt.date):
    return (1 if is_mastered(rec) else 0, retrievability(rec, today), str(theme_key(rec)))


def due_items(records: list, today: dt.date) -> list[tuple]:
    """期日が今日以前のテーマの (最新の記録, 期日) を、出す順に並べて返す。"""
    out = []
    for r, prev in latest_pairs(records, today):
        due = due_date(r, prev)
        if due is not None and due <= today:
            out.append((r, due))
    out.sort(key=lambda x: order_key(x[0], today))
    return out


def due_themes(records: list, today: dt.date) -> list[dict]:
    """期日が今日以前のテーマ（最新の記録）を、出す順に並べて返す。"""
    return [r for r, _ in due_items(records, today)]


def next_due(records: list, today: dt.date, unmastered_only: bool = False):
    """期日が明日以降のテーマで、いちばん早いもの。(期日, 記録) か None。

    unmastered_only=True なら未克服のテーマだけから選ぶ（「未克服は期日前」と言う文言の次の期日。監査 #10）。
    """
    future = []
    for r, prev in latest_pairs(records, today):
        if unmastered_only and is_mastered(r):
            continue
        due = due_date(r, prev)
        if due is not None and due > today:
            future.append((due, str(theme_key(r)), r))
    if not future:
        return None
    future.sort(key=lambda x: (x[0], x[1]))
    return future[0][0], future[0][2]


# ── 自己テスト ───────────────────────────────────────────────────

def _fixture():
    """設計書 1-1 の5件と境界。今日は 2026-10-23。"""
    def R(tid, d, res, iv, attempt=1, **kw):
        r = {"theme_id": tid, "theme": tid, "subject": "理論", "date": d,
             "result": res, "interval_days": iv, "attempt": attempt}
        r.update(kw)
        return r
    return [
        R("A_fixed", "2026-10-01", "ng", 1, 1), R("A_fixed", "2026-10-15", "ok", 6, 2, recall_test_due="2026-10-30"),
        R("B_old_risky", "2026-06-28", "risky", 3),
        R("C_ng_yday", "2026-10-22", "ng", 1),
        R("D_ng_today", "2026-10-23", "ng", 1),
    ]


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _self_test() -> int:
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append("%s: got %r want %r" % (name, got, want))

    today = dt.date(2026, 10, 23)
    recs = _fixture()
    ids = lambda rs: [theme_key(r) for r in rs]  # noqa: E731

    # G2: 設計書 1-1 は未克服の B → C が先。A（直った）は未克服としては出ず、克服済みの復習
    # （ok・間隔6日で FSRS の期日 10-21 を過ぎた）として最後に出る。D（期日は明日）は出ない
    check("1-1 の順", ids(due_themes(recs, today)), ["B_old_risky", "C_ng_yday", "A_fixed"])
    check("A は克服済みとして出る", [is_mastered(r) for r in due_themes(recs, today)], [False, False, True])
    check("期日前の次", (next_due(recs, today)[0].isoformat(), theme_key(next_due(recs, today)[1])),
          ("2026-10-24", "D_ng_today"))

    # 陽性対照: 旧来の並べ方（ng を先・新しい日付ほど先）なら C が B より前に来る＝検査が差を見分けられる
    legacy = sorted(due_themes(recs, today),
                    key=lambda r: ({"ng": 0, "risky": 1}.get(r["result"], 9), -dt.date.fromisoformat(r["date"]).toordinal()))
    check("陽性対照（旧順は C が先）", ids(legacy), ["C_ng_yday", "B_old_risky", "A_fixed"])

    # 期日ちょうどは出す・期日の翌日の前は出さない
    check("期日ちょうど", ids(due_themes([{"theme_id": "x", "date": "2026-10-20", "result": "ng", "interval_days": 3}], today)), ["x"])
    check("期日の前日", ids(due_themes([{"theme_id": "x", "date": "2026-10-21", "result": "ng", "interval_days": 3}], today)), [])
    # recall_test_due と interval の早い方
    check("早い方（interval）", due_date({"date": "2026-10-20", "interval_days": 2, "recall_test_due": "2026-10-23"}), dt.date(2026, 10, 22))
    okr = {"date": "2026-10-20", "result": "ok", "interval_days": 9, "recall_test_due": "2026-10-23"}
    check("ng の直後の ok は再テストの日（早い方）", due_date(okr, {"result": "ng"}), dt.date(2026, 10, 23))
    check("ok の直後の ok は FSRS の期日（監査 #1）", due_date(okr, {"result": "ok"}), dt.date(2026, 10, 29))
    check("初めての ok は FSRS の期日", due_date(okr, None), dt.date(2026, 10, 29))
    # 監査 #1 の場面: ok を続けると、2回目以降は FSRS の間隔どおりに伸びる（3日ごとに戻らない）
    chain = [{"theme_id": "c", "date": "2026-01-01", "result": "ng", "interval_days": 1, "attempt": 1},
             {"theme_id": "c", "date": "2026-01-02", "result": "ok", "interval_days": 2, "attempt": 2, "recall_test_due": "2026-01-05"},
             {"theme_id": "c", "date": "2026-01-04", "result": "ok", "interval_days": 23, "attempt": 3, "recall_test_due": "2026-01-07"}]
    check("ok が続くと FSRS の間隔（23日）", [d.isoformat() for _, d in due_items(chain, dt.date(2026, 1, 27))], ["2026-01-27"])
    check("ok が続くと3日後には出ない", due_items(chain, dt.date(2026, 1, 7)), [])
    check("ラベルだけ", due_date({"date": "2026-10-20", "next_review": "SR2"}), dt.date(2026, 10, 23))
    check("done は出さない", due_date({"date": "2026-10-20", "next_review": "done"}), None)
    check("bool の interval は数えない", due_date({"date": "2026-10-20", "interval_days": True}), None)
    # 最新の決め方: 日付 → attempt → 追記した順
    same_day = [{"theme_id": "y", "date": "2026-10-20", "result": "ok", "attempt": 3},
                {"theme_id": "y", "date": "2026-10-20", "result": "ng", "attempt": 2}]
    check("同じ日は attempt の大きい方", latest_per_theme(same_day)[0]["result"], "ok")
    back = [{"theme_id": "z", "date": "2026-10-20", "result": "ok"},
            {"theme_id": "z", "date": "2026-10-10", "result": "ng"}]
    check("後から古い日付を追記しても最新は日付で決まる", latest_per_theme(back)[0]["result"], "ok")
    # 克服済みは未克服の後ろ・未克服の中は R の低い順（安定度の無い古い記録は interval で代える）
    mix = [{"theme_id": "ok_old", "date": "2026-01-01", "result": "ok", "interval_days": 30},
           {"theme_id": "risky_s50", "date": "2026-09-01", "result": "risky", "fsrs_stability": 50.0, "interval_days": 30},
           {"theme_id": "ng_s1", "date": "2026-10-20", "result": "ng", "fsrs_stability": 1.0, "interval_days": 1}]
    check("未克服が先・R の低い順", ids(due_themes(mix, today)), ["ng_s1", "risky_s50", "ok_old"])

    # 2026-10-23 壊す側監査の再現入力（番号は監査表の #）
    ng = {"theme_id": "t", "date": "2026-10-20", "result": "ng", "interval_days": 1, "attempt": 2}
    check("#2 未来日の ok は ng を隠さない",
          ids(due_themes([ng, {"theme_id": "t", "date": "2027-10-20", "result": "ok", "interval_days": 9, "attempt": 3}], today)), ["t"])
    check("#3 試験用の記録は数えない", ids(due_themes([dict(ng, theme_id="test-q1"), ng], today)), ["t"])
    check("#4 theme だけの古い記録は数えない",
          ids(latest_per_theme([{"theme": "電磁誘導", "date": "2026-09-01", "result": "ng"}, ng])), ["t"])
    check("#5 配列の theme_id で止まらない", ids(latest_per_theme([dict(ng, theme_id=["bad"]), dict(ng, theme_id={"x": 1}), ng])), ["t"])
    for iv in (1.0, "1", 0):
        check("#7 interval_days=%r でも期日がある" % (iv,), due_date(dict(ng, interval_days=iv)) is not None, True)
    um = {"theme_id": "u", "date": "2026-10-23", "result": "ng", "interval_days": 5}
    mm = {"theme_id": "m", "date": "2026-10-20", "result": "ok", "interval_days": 4}
    check("#10 未克服だけの次の期日", theme_key(next_due([um, mm], today, unmastered_only=True)[1]), "u")
    check("#11 区切りの無い日付は読まない", latest_per_theme([dict(ng, date="20261001")]), [])
    same = [{"theme_id": "s", "date": "2026-10-20", "result": "ok", "attempt": "3"},
            {"theme_id": "s", "date": "2026-10-20", "result": "ng", "attempt": 2}]
    check("#12 文字列の attempt も数で比べる", latest_per_theme(same)[0]["result"], "ok")
    big = [{"theme_id": "o", "date": "9999-12-31", "result": "ng", "interval_days": 10_000_000},
           {"theme_id": "p", "date": "2026-10-01", "result": "ng", "interval_days": 10**400, "fsrs_stability": 10**400},
           {"theme_id": "q", "date": "2026-10-01", "result": ["ng"], "interval_days": 1}, ng]
    try:
        check("桁あふれ・型違いで止まらない", ids(due_themes(big, dt.date(9999, 12, 31))) is not None, True)
        check("桁あふれ・型違いで止まらない（今日）", "t" in ids(due_themes(big, today)), True)
    except Exception as e:  # noqa: BLE001
        fails.append("桁あふれ・型違いで例外: %s: %s" % (type(e).__name__, e))

    # R2 段階3: sr-record.py の「前回の記録」（テーマを名指し・その日以前で最新）
    hist = [{"theme_id": "h", "date": "2026-10-20", "result": "ok", "attempt": 2},
            {"theme_id": "h", "date": "2026-10-10", "result": "ng", "attempt": 3}]   # 後から古い日付を追記
    check("名指し: 追記の順でなく日付の順", latest_of_theme(hist, "h")["date"], "2026-10-20")
    check("名指し: その日以前だけ", latest_of_theme(hist, "h", dt.date(2026, 10, 15))["date"], "2026-10-10")
    check("名指し: それより前に記録が無い", latest_of_theme(hist, "h", dt.date(2026, 10, 1)), None)
    check("名指し: 試験用のテーマも数える", latest_of_theme([dict(ng, theme_id="test-q")], "test-q")["result"], "ng")

    # G1: 2つの装置が同じ順を出す（片方だけ並べ方を変えると落ちる）
    try:
        css = _load("check_study_streak", "check_study_streak.py")
        pick = _load("sr_pick_next", "sr-pick-next.py")
        for name, data in (("1-1", recs), ("混在", mix + recs)):
            hook = [d["theme_id"] for d in css.overdue_reviews(data, today)]
            picked = [theme_key(r) for r in pick.normal_candidates(data, today)]
            check("G1 フック＝sr-pick-next（%s）" % name, picked, hook)
            check("G1 正本と一致（%s）" % name, hook, ids(due_themes(data, today)))
    except Exception as e:  # 読み込めないこと自体を失敗にする（無音で通さない）
        fails.append("G1: 2つの装置を読み込めない（%s: %s）" % (type(e).__name__, e))

    for f in fails:
        print("  [FAIL] %s" % f)
    utc = dt.timezone.utc
    for when, want in [(dt.datetime(2026, 11, 15, 14, 59, tzinfo=utc), "2026-11-15"),   # JST 23:59
                       (dt.datetime(2026, 11, 15, 15, 0, tzinfo=utc), "2026-11-16"),    # JST 0:00 の境界
                       (dt.datetime(2026, 11, 15, 23, 30, tzinfo=utc), "2026-11-16"),   # JST 8:30（UTC はまだ前日）
                       (dt.datetime(2026, 12, 31, 15, 0, tzinfo=utc), "2027-01-01")]:   # 年越し
        check("jst_today(%s UTC)" % when.strftime("%m-%d %H:%M"), jst_today(when).isoformat(), want)
    print("self-test:", "ALL PASS" if not fails else "%d FAIL" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print(__doc__)
