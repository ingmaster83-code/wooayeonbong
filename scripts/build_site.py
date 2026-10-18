# -*- coding: utf-8 -*-
"""우아연봉 정적 사이트 생성기. 사용: python scripts/build_site.py [최소가입자수=30]  → _site/"""
import sys, json, gzip, re, shutil, statistics, unicodedata, collections, time
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *
import salary as S

SITE_MIN_N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
MIN_WAGE_2026 = 10_320
CAP_NOW = 6_590_000
RATE_NOW = 0.095

# ───────────────────────── 데이터 준비 ─────────────────────────
def slugify(name):
    s = unicodedata.normalize("NFKC", name)
    s = re.sub(r'주식회사|유한회사|유한책임회사|사단법인|재단법인|학교법인|사회복지법인|의료법인', "", s)
    s = re.sub(r'\([^)]{0,6}\)', "", s)
    s = re.sub(r'[\\/?#%&"<>|:*\'`~!@$^+=,;\[\]{}]', "", s)
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"\s+", "-", s.strip()).strip(".-")
    return s or "회사"

def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None

def load():
    d = json.load(gzip.open(ROOT / "_data" / "companies.json.gz", "rt", encoding="utf-8"))
    meta, cs = d["meta"], d["companies"]
    cs = [c for c in cs if c["n"] >= SITE_MIN_N]
    dm = meta["latest_data"]
    rate = 0.095 if dm >= "2026-01" else 0.09
    cap = 6_590_000 if dm >= "2026-07" else 6_370_000
    used = {}
    for c in cs:
        c["name"] = unicodedata.normalize("NFKC", c["name"])
        sl = slugify(c["name"])
        if sl in used:
            sl = sl + "-" + c["biz"]
        used[sl] = 1
        c["slug"] = sl
        c["est_m"] = c["bill"] / (c["n"] * rate) if c["n"] else 0
        c["ratio"] = c["est_m"] / cap
        c["annual"] = c["est_m"] * 12
        hs = [h for h in c["hist"] if h is not None]
        c["avg_n"] = sum(hs) / len(hs) if hs else c["n"]
        c["first_n"] = hs[0] if hs else c["n"]
        c["chg"] = c["n"] - c["first_n"]
        c["chg_pct"] = (c["chg"] / c["first_n"] * 100) if c["first_n"] else 0
        full = c["nm"] >= 12
        c["turn"] = (c["lost12"] / c["avg_n"] * 100) if full and c["avg_n"] else None
        c["hire"] = (c["new12"] / c["avg_n"] * 100) if full and c["avg_n"] else None
        c["iname"] = (c["iname"] or "").strip()
        if c["iname"] in ("", "해당없음"): c["iname"] = "업종 미분류"
        c["ikey"] = c["icode"]
        c["rkey"] = (c["sido"], c["sgg"])
    return meta, cs, rate, cap

def salary_txt(c, cap):
    if c["ratio"] >= 0.97: return "%s만원 이상" % man(cap * 12), True
    return "약 %s만원" % man(c["annual"]), False

# ───────────────────────── 부품 ─────────────────────────
def table(heads, rows, num_cols=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num_cols else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num_cols else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)

def bars(vals, labels):
    vals2 = [v for v in vals if v is not None]
    if not vals2: return ""
    lo, hi = min(vals2), max(vals2)
    span = max(hi - lo, 1)
    # 변화가 작아도 보이도록 최소 높이 25% + 비례
    h = "".join('<div title="%s: %s명" style="height:%d%%"></div>' % (l, "{:,}".format(v), 25 + 75 * (v - lo) / span) if v is not None else '<div style="height:2%"></div>'
                for v, l in zip(vals, labels))
    lb = "".join("<span>%s</span>" % l[5:].lstrip("0") for l in labels)
    return '<div class="bars">%s</div><div class="bars-lbl">%s</div>' % (h, lb)

def chips(items, cls=""):
    return '<div class="chips">%s</div>' % "".join('<a class="chip%s" href="%s">%s</a>' % (" " + cls if cls else "", u, esc(t)) for t, u in items)

def ym_txt(dm):
    y, m = dm.split("-")
    return "%s년 %d월" % (y, int(m))

def comp_link(c): return '<a href="/company/%s/">%s</a>' % (c["slug"], esc(c["name"]))

# ───────────────────────── 실수령액 페이지 ─────────────────────────
ANNUAL_STEPS = sorted(set(list(range(1500, 30001, 100)) + list(range(2050, 8000, 100))))
MONTHLY_STEPS = sorted(set(list(range(150, 1001, 10)) + list(range(1050, 3001, 50))))

def near_steps(steps, v, k=5):
    i = steps.index(v)
    return steps[max(0, i - k): i + k + 1]

def fam_rows(annual):
    rows = []
    for fam in (1, 2, 3, 4):
        r = S.calc(annual, family=fam)
        rows.append(["본인 포함 %d명" % fam, won(r["income_tax"]) + "원", won(r["net"]) + "원", won(r["net_year"]) + "원"])
    return rows

def page_salary(man_won, cs_by_est):
    annual = man_won * 10000
    r = S.calc(annual)
    r0 = S.calc(annual, meal=0)
    path = "/salary/%d/" % man_won
    mon = r["net"]
    hourly = annual / 12 / 209
    mw_ratio = hourly / MIN_WAGE_2026
    rows = [["세전 월급", won(r["pay"]) + "원", "연봉 ÷ 12"], ["비과세 식대", won(r["meal"]) + "원", "월 20만원까지 비과세(가정)"],
            ["국민연금", "-" + won(r["pension"]) + "원", "4.75%"], ["건강보험", "-" + won(r["health"]) + "원", "3.595%"],
            ["장기요양보험", "-" + won(r["ltc"]) + "원", "건강보험료의 13.14%"], ["고용보험", "-" + won(r["emp"]) + "원", "0.9%"],
            ["소득세", "-" + won(r["income_tax"]) + "원", "연말정산식 근사(본인만 공제)"], ["지방소득세", "-" + won(r["local_tax"]) + "원", "소득세의 10%"],
            ["<b>월 실수령액</b>", "<b>%s원</b>" % won(r["net"]), "공제율 %.1f%%" % (r["rate"] * 100)]]
    t1 = table(["항목", "금액(월)", "산정"], rows, (1,))
    t2 = table(["공제대상 가족", "월 소득세", "월 실수령액", "연 실수령액"], fam_rows(annual), (1, 2, 3))
    t3 = table(["", "월 실수령액", "연 실수령액"], [["식대 20만원 비과세", won(r["net"]) + "원", won(r["net_year"]) + "원"], ["비과세 없음(전액 과세)", won(r0["net"]) + "원", won(r0["net_year"]) + "원"]], (1, 2))
    nb = []
    for v in near_steps(ANNUAL_STEPS, man_won):
        rv = S.calc(v * 10000)
        nb.append(['<a href="/salary/%d/">연봉 %s만원</a>' % (v, "{:,}".format(v)) if v != man_won else "<b>연봉 %s만원</b>" % "{:,}".format(v), won(rv["net"]) + "원", won(rv["net"] * 12) + "원"])
    t4 = table(["연봉", "월 실수령액", "연 실수령액"], nb, (1, 2))
    # 같은 수준 평균연봉 회사
    lo, hi = annual * 0.97, annual * 1.03
    import bisect
    keys = [c["annual"] for c in cs_by_est]
    a, b = bisect.bisect_left(keys, lo), bisect.bisect_right(keys, hi)
    near = sorted([c for c in cs_by_est[a:b] if c["ratio"] < 0.95], key=lambda c: -c["n"])[:10]
    comp = ""
    if near:
        comp = '<h2 class="group-title">🏢 추정 평균연봉이 비슷한 회사 <small>국민연금 신고 소득 기준</small></h2>' + table(
            ["회사", "업종", "직원 수", "추정 평균연봉"], [[comp_link(c), esc(c["iname"]), "{:,}명".format(c["n"]), "약 %s만원" % man(c["annual"])] for c in near], (2, 3))
    k = "{:,}".format(man_won)
    lead = ("<p class=\"lead\"><b>연봉 %s만원</b>이면 2026년 기준 <b>월 실수령액은 약 %s원</b>입니다(식대 20만원 비과세, 본인만 공제 가정). 세전 월급 %s원에서 국민연금·건강보험·장기요양·고용보험 %s원, 소득세·지방소득세 %s원을 제하고 남는 금액입니다. "
            "연 실수령액은 약 %s원이며, 환산 시급은 약 %s원으로 2026년 최저임금(%s원)의 %.1f배입니다.</p>") % (
        k, won(mon), won(r["pay"]), won(r["insurance"]), won(r["income_tax"] + r["local_tax"]), won(r["net_year"]), won(hourly), won(MIN_WAGE_2026), mw_ratio)
    body = """
<div class="page-head"><h1>연봉 %(k)s만원 실수령액 — 월 %(mon)s원 (2026년)</h1><p>4대보험·소득세 공제 내역 · 부양가족별 · 비슷한 연봉 비교</p></div>
%(lead)s
%(ad)s
<h2 class="group-title">🧾 월급 명세 (공제 내역)</h2>
%(t1)s
<h2 class="group-title">👨‍👩‍👧 부양가족 수에 따른 실수령액</h2>
%(t2)s
<h2 class="group-title">🍚 비과세 식대에 따른 차이</h2>
%(t3)s
<p class="note">식대 비과세는 월 20만원까지 적용되며 4대보험료와 소득세 계산에서 빠집니다. 회사가 식대를 따로 지급하지 않으면 아래 줄(전액 과세)에 가깝습니다.</p>
%(comp)s
<h2 class="group-title">📈 비슷한 연봉의 실수령액</h2>
%(t4)s
<div class="chips"><a class="chip" href="/calculator/">내 조건으로 계산하기</a><a class="chip" href="/salary/">연봉 실수령액 표 전체</a><a class="chip" href="/monthly/">월급 실수령액</a></div>
<div class="note-box">실수령액은 2026년 요율(국민연금 4.75%%, 건강보험 3.595%%, 장기요양 13.14%%, 고용보험 0.9%%)과 소득세법상 공제를 적용한 근사 계산입니다. 실제 급여명세서는 상여·수당·비과세 항목, 원천징수 비율 선택, 연말정산 결과에 따라 달라질 수 있습니다.</div>
""" % dict(k=k, mon=won(mon), lead=lead, ad=ad(), t1=t1, t2=t2, t3=t3, t4=t4, comp=comp)
    faq = [("연봉 %s만원이면 월급은 얼마인가요?" % k, "연봉 %s만원의 세전 월급은 %s원이고, 4대보험과 세금을 뗀 월 실수령액은 약 %s원입니다." % (k, won(r["pay"]), won(mon))),
           ("연봉 %s만원의 공제율은 얼마인가요?" % k, "4대보험 %s원과 소득세·지방소득세 %s원을 합쳐 월 %s원, 세전 월급의 약 %.1f%%가 공제됩니다." % (won(r["insurance"]), won(r["income_tax"] + r["local_tax"]), won(r["deduction"]), r["rate"] * 100)),
           ("연봉에 퇴직금이 포함돼 있으면 어떻게 계산하나요?", "퇴직금이 연봉에 포함된 경우 실제 월급은 연봉÷13(또는 14)에 가깝습니다. 이때는 '월급 실수령액' 페이지에서 실제 세전 월급을 직접 찾아 확인하세요.")]
    write(path, layout(path, "연봉 %s만원 실수령액 — 월 %s원 (2026년)" % (k, won(mon)),
        "연봉 %s만원의 2026년 월 실수령액은 약 %s원. 국민연금·건강보험·장기요양·고용보험·소득세 공제 내역과 부양가족별 실수령액, 비슷한 연봉 비교." % (k, won(mon)),
        body, faq, [("홈", "/"), ("연봉 실수령액", "/salary/"), ("%s만원" % k, path)], coupang=(man_won % 500 == 0)), "0.8" if man_won % 500 == 0 else "0.6")

def page_monthly(m):
    annual = m * 12 * 10000
    r = S.calc(annual)
    path = "/monthly/%d/" % m
    mon = r["net"]
    rows = [["세전 월급", won(r["pay"]) + "원"], ["비과세 식대", won(r["meal"]) + "원"], ["국민연금", "-" + won(r["pension"]) + "원"], ["건강보험", "-" + won(r["health"]) + "원"],
            ["장기요양보험", "-" + won(r["ltc"]) + "원"], ["고용보험", "-" + won(r["emp"]) + "원"], ["소득세", "-" + won(r["income_tax"]) + "원"], ["지방소득세", "-" + won(r["local_tax"]) + "원"],
            ["<b>월 실수령액</b>", "<b>%s원</b>" % won(mon)]]
    t1 = table(["항목", "금액(월)"], rows, (1,))
    nb = []
    for v in near_steps(MONTHLY_STEPS, m):
        rv = S.calc(v * 12 * 10000)
        nb.append(['<a href="/monthly/%d/">월급 %s만원</a>' % (v, "{:,}".format(v)) if v != m else "<b>월급 %s만원</b>" % "{:,}".format(v), won(rv["net"]) + "원", "{:,}만원".format(round(v * 12))])
    t4 = table(["세전 월급", "월 실수령액", "연봉 환산"], nb, (1, 2))
    k = "{:,}".format(m)
    lead = ("<p class=\"lead\">세전 <b>월급 %s만원</b>(연봉 %s만원)을 받으면 2026년 기준 <b>월 실수령액은 약 %s원</b>입니다. 공제 합계는 월 %s원(%.1f%%)이며 4대보험이 %s원, 소득세·지방소득세가 %s원입니다. 비과세 식대 20만원, 본인만 공제 가정입니다.</p>") % (
        k, "{:,}".format(m * 12), won(mon), won(r["deduction"]), r["rate"] * 100, won(r["insurance"]), won(r["income_tax"] + r["local_tax"]))
    body = """
<div class="page-head"><h1>월급 %(k)s만원 실수령액 — 세전 월급 기준 (2026년)</h1><p>공제 내역 · 연봉 환산 · 비슷한 월급 비교</p></div>
%(lead)s
%(ad)s
<h2 class="group-title">🧾 공제 내역</h2>
%(t1)s
<h2 class="group-title">📈 비슷한 월급의 실수령액</h2>
%(t4)s
<div class="chips"><a class="chip" href="/salary/%(ann)s/">연봉 %(annk)s만원 실수령액</a><a class="chip" href="/calculator/">내 조건으로 계산하기</a><a class="chip" href="/monthly/">월급 실수령액 표</a></div>
<div class="note-box">2026년 요율 기준 근사 계산입니다. 실제 급여명세서는 상여·수당·비과세 항목과 부양가족에 따라 달라질 수 있습니다.</div>
""" % dict(k=k, lead=lead, ad=ad(), t1=t1, t4=t4, ann=nearest(ANNUAL_STEPS, m * 12), annk="{:,}".format(nearest(ANNUAL_STEPS, m * 12)))
    faq = [("월급 %s만원의 실수령액은 얼마인가요?" % k, "세전 월급 %s만원이면 4대보험과 세금을 뗀 월 실수령액은 약 %s원입니다." % (k, won(mon))),
           ("월급 %s만원이면 연봉은 얼마인가요?" % k, "연봉으로 환산하면 %s만원입니다(상여·퇴직금 별도 없음 가정)." % "{:,}".format(m * 12))]
    write(path, layout(path, "월급 %s만원 실수령액 — 월 %s원 (2026년)" % (k, won(mon)),
        "세전 월급 %s만원의 2026년 월 실수령액은 약 %s원. 4대보험·소득세 공제 내역과 연봉 환산, 비슷한 월급 비교." % (k, won(mon)),
        body, faq, [("홈", "/"), ("월급 실수령액", "/monthly/"), ("%s만원" % k, path)]), "0.6")

def nearest(steps, v):
    return min(steps, key=lambda s: abs(s - v))

def hub_pages():
    def s(v): return won(S.calc(v * 10000)["net"])
    body = """
<div class="page-head"><h1>연봉별 월 실수령액 표 (2026년)</h1><p>연봉 1,500만원 ~ 3억원 · 4대보험과 소득세 반영</p></div>
<p class="lead">2026년 요율로 계산한 연봉별 월 실수령액 표입니다. 비과세 식대 20만원, 본인만 공제 기준이며 금액을 누르면 공제 내역과 부양가족별 실수령액을 볼 수 있습니다. 연봉 4,000만원은 월 약 %s원, 5,000만원은 약 %s원, 1억원은 약 %s원이 실수령액입니다.</p>
%s
%s
<div class="chips"><a class="chip" href="/monthly/">월급 실수령액 표</a><a class="chip" href="/calculator/">직접 계산하기</a></div>
"""
    rows = []
    for v in ANNUAL_STEPS:
        if v > 15000 and v % 500: continue
        r = S.calc(v * 10000)
        rows.append(['<a href="/salary/%d/">%s만원</a>' % (v, "{:,}".format(v)), won(r["pay"]) + "원", won(r["net"]) + "원", won(r["income_tax"] + r["local_tax"]) + "원", "%.1f%%" % (r["rate"] * 100)])
    t = table(["연봉", "세전 월급", "월 실수령액", "월 소득세(지방세 포함)", "공제율"], rows, (1, 2, 3, 4))
    write("/salary/", layout("/salary/", "연봉별 월 실수령액 표 (2026년) — 연봉 1,500만~3억",
        "2026년 연봉별 월 실수령액 표. 연봉 3,000만·4,000만·5,000만·1억원의 4대보험·소득세 공제 후 실수령액을 한눈에 비교합니다.",
        body % (s(4000), s(5000), s(10000), ad(), t), [("연봉 4,000만원이면 월 실수령액은?", "2026년 기준 월 약 %s원입니다." % s(4000)), ("연봉 5,000만원이면 월 실수령액은?", "2026년 기준 월 약 %s원입니다." % s(5000)),
        ("표의 기준은 무엇인가요?", "비과세 식대 월 20만원, 본인만 공제(부양가족 없음), 2026년 4대보험 요율과 소득세법 공제를 적용한 근사 계산입니다.")], [("홈", "/"), ("연봉 실수령액", "/salary/")], coupang=True), "0.9")
    rows = []
    for m in MONTHLY_STEPS:
        r = S.calc(m * 12 * 10000)
        rows.append(['<a href="/monthly/%d/">%s만원</a>' % (m, "{:,}".format(m)), won(r["net"]) + "원", won(r["deduction"]) + "원", "{:,}만원".format(m * 12)])
    t = table(["세전 월급", "월 실수령액", "월 공제액", "연봉 환산"], rows, (1, 2, 3))
    body2 = """
<div class="page-head"><h1>월급별 실수령액 표 (2026년) — 세전 월급 기준</h1><p>세전 월급 150만원 ~ 3,000만원</p></div>
<p class="lead">세전 월급에서 4대보험과 소득세를 뗀 월 실수령액을 2026년 요율로 계산했습니다. 월급 200만원은 약 %s원, 300만원은 약 %s원, 500만원은 약 %s원이 실수령액입니다. 금액을 누르면 공제 내역을 볼 수 있습니다.</p>
%s
%s
<div class="chips"><a class="chip" href="/salary/">연봉 실수령액 표</a><a class="chip" href="/calculator/">직접 계산하기</a></div>
""" % (won(S.calc(200 * 120000)["net"]), won(S.calc(300 * 120000)["net"]), won(S.calc(500 * 120000)["net"]), ad(), t)
    write("/monthly/", layout("/monthly/", "월급별 월 실수령액 표 (2026년) — 세전 월급 150만~3,000만",
        "2026년 세전 월급별 월 실수령액 표. 월급 200만·300만·400만·500만원의 4대보험·소득세 공제 후 금액을 비교합니다.", body2,
        [("월급 300만원이면 실수령액은?", "2026년 기준 월 약 %s원입니다(식대 20만원 비과세, 본인만 공제)." % won(S.calc(300 * 120000)["net"]))], [("홈", "/"), ("월급 실수령액", "/monthly/")], coupang=True), "0.9")

# ───────────────────────── 회사 페이지 ─────────────────────────
def build_groups(cs):
    ind = collections.defaultdict(list); reg = collections.defaultdict(list); sido = collections.defaultdict(list)
    for c in cs:
        ind[c["ikey"]].append(c); reg[c["rkey"]].append(c); sido[c["sido"]].append(c)
    return ind, reg, sido

def page_company(c, meta, cap, ind_stats, ind, reg, cs_est_sorted):
    dm = meta["latest_data"]
    path = "/company/%s/" % c["slug"]
    st, capped = salary_txt(c, cap)
    est_m = min(c["est_m"], cap)
    sal_man = man(c["annual"]) if not capped else man(cap * 12)
    # 추이
    labels = meta["data_months"]
    chart = bars(c["hist"], labels)
    nm_info = ""
    if c["nm"] < 12: nm_info = "<p class=\"note\">이 사업장은 최근 12개월 중 %d개월분 자료만 있어 입사·퇴사 통계가 집계 기간 부족으로 표시됩니다(신규 가입 또는 사업장 변경).</p>" % c["nm"]
    it = ind_stats.get(c["ikey"])
    ind_txt = ""
    if it and it["count"] >= 8:
        rank = sum(1 for x in ind[c["ikey"]] if x["annual"] < c["annual"])
        pct = 100 - rank * 100.0 / it["count"]
        ind_txt = ("<p class=\"lead\">같은 업종(%s)의 %d개 법인 가운데 이 회사의 추정 평균연봉은 <b>상위 %d%%</b> 수준입니다(업종 중앙값 약 %s만원%s).</p>") % (
            esc(c["iname"]), it["count"], max(1, round(pct)), man(it["med_annual"]), (", 업종 평균 퇴사율 %.0f%%" % it["med_turn"]) if it["med_turn"] is not None else "")
    # 계산 연동
    nv = nearest(ANNUAL_STEPS, round(min(c["annual"], cap * 12) / 10000))
    rr = S.calc(nv * 10000)
    calc_txt = ("<p class=\"lead\">추정 평균연봉 수준인 연봉 %s만원을 받으면 2026년 기준 월 실수령액은 약 <b>%s원</b>입니다. 자세한 공제 내역은 <a href=\"/salary/%d/\">연봉 %s만원 실수령액</a>에서 확인하세요.</p>") % (
        "{:,}".format(nv), won(rr["net"]), nv, "{:,}".format(nv))
    # 요약 문단
    trend = ("최근 1년간 %s명(%+.1f%%) %s했습니다" % ("{:,}".format(abs(c["chg"])), c["chg_pct"], "증가" if c["chg"] > 0 else "감소")) if abs(c["chg_pct"]) >= 1 else "최근 1년간 인원 변동이 거의 없었습니다"
    flow = ""
    if c["turn"] is not None:
        flow = " 최근 12개월 동안 새로 가입한 직원은 %s명, 가입을 상실한 직원은 %s명으로 연 퇴사율 추정치는 약 %.0f%%입니다." % ("{:,}".format(c["new12"]), "{:,}".format(c["lost12"]), c["turn"])
    cap_note = ""
    if capped:
        cap_note = "<div class=\"note-box\">이 회사의 평균 소득이 국민연금 기준소득월액 상한(월 %s원)에 도달해 실제 평균연봉은 위 금액보다 높을 수 있습니다. 상한 때문에 정확한 값을 알 수 없어 ‘이상’으로 표시했습니다.</div>" % won(cap)
    elif c["ratio"] >= 0.85:
        cap_note = "<div class=\"note-box\">평균 소득이 기준소득월액 상한에 가까워 고소득 직원의 소득이 일부 잘려 반영됐을 수 있습니다. 실제 평균연봉은 위 금액보다 높을 수 있습니다.</div>"
    elif c["est_m"] < 1_200_000:
        cap_note = "<div class=\"note-box\">평균 소득이 낮게 나타났습니다. 단시간·단기 근로자 비중이 높거나 가입 직후 사업장일 수 있어 추정 연봉이 실제보다 낮을 수 있습니다.</div>"
    lead = ("<p class=\"lead\"><b>%s</b>은(는) %s %s %s에 있는 법인으로, 국민연금 가입자(직원) 수는 <b>%s명</b>(%s 기준)입니다. 업종은 ‘%s’이고 가입 사업장은 %d곳입니다. "
            "국민연금 신고 소득으로 추정한 평균연봉은 <b>%s</b>(월 평균 %s원)이며 %s.%s</p>") % (
        esc(c["name"]), esc(c["sido"]), esc(c["sgg"]), esc(c["dong"]), "{:,}".format(c["n"]), ym_txt(dm), esc(c["iname"]), c["br"], st, won(est_m), trend, flow)
    stats = '<div class="stat-row"><div class="stat"><small>직원 수(가입자)</small><b>%s명</b></div><div class="stat"><small>추정 평균연봉</small><b>%s</b></div><div class="stat"><small>1년 인원 증감</small><b>%+d명</b></div>%s%s</div>' % (
        "{:,}".format(c["n"]), st.replace("약 ", "~"), c["chg"],
        ('<div class="stat"><small>연 퇴사율(추정)</small><b>%.0f%%</b></div>' % c["turn"]) if c["turn"] is not None else "",
        ('<div class="stat"><small>연 입사율(추정)</small><b>%.0f%%</b></div>' % c["hire"]) if c["hire"] is not None else "")
    hist_rows = [[labels[i][:4] + "년 " + str(int(labels[i][5:])) + "월", "{:,}명".format(c["hist"][i]) if c["hist"][i] is not None else "-"] for i in range(len(labels) - 1, -1, -1)]
    # 관련 회사
    rel = [x for x in ind[c["ikey"]] if x is not c and x["sido"] == c["sido"]]
    rel.sort(key=lambda x: abs(x["n"] - c["n"]))
    rel = rel[:5]
    if len(rel) < 5:
        extra = [x for x in reg[c["rkey"]] if x is not c and x not in rel]
        extra.sort(key=lambda x: -x["n"])
        rel += extra[:5 - len(rel)]
    rel_html = ""
    if rel:
        rel_html = '<h2 class="group-title">🔗 같은 업종·지역 회사</h2>' + table(["회사", "업종", "직원 수", "추정 평균연봉"], [
            [comp_link(x), esc(x["iname"]), "{:,}명".format(x["n"]), salary_txt(x, cap)[0]] for x in rel], (2, 3))
    body = """
<div class="page-head"><h1>%(nm)s 평균연봉·직원수·퇴사율</h1><p>%(sido)s %(sgg)s · %(ind)s · 국민연금 가입 기준 %(ym)s</p></div>
%(lead)s
%(stats)s
%(cap)s
%(ad)s
<h2 class="group-title">📊 직원 수 추이 <small>최근 12개월 국민연금 가입자</small></h2>
%(chart)s
%(nm_info)s
<details><summary>월별 직원 수 표 보기</summary>%(histt)s</details>
%(ind_txt)s
<h2 class="group-title">💰 연봉으로 보는 실수령액</h2>
%(calc)s
%(rel)s
<h2 class="group-title">ℹ️ 이 숫자는 어떻게 계산했나요?</h2>
<p class="lead">국민연금공단이 공개한 가입 사업장 내역의 <b>당월 고지금액 ÷ (가입자 수 × 보험료율 %(rate).1f%%)</b>로 1인당 월 평균 기준소득월액을 구하고 12를 곱했습니다. 기준소득월액은 비과세 소득을 뺀 신고 소득이며 월 %(capv)s원이 상한이라 고소득자의 소득은 일부 잘립니다. 60세 이상·단시간 근로자 등 가입 대상이 아닌 직원은 빠지고, 신고는 실제 급여보다 늦게 반영될 수 있어 실제 평균연봉과 차이가 있습니다. 자세한 기준은 <a href="/about/">산정 기준</a> 페이지를 참고하세요.</p>
""" % dict(nm=esc(c["name"]), sido=esc(c["sido"]), sgg=esc(c["sgg"]), ind=esc(c["iname"]), ym=ym_txt(dm), lead=lead, stats=stats, cap=cap_note, ad=ad(), chart=chart, nm_info=nm_info,
           histt=table(["기준월", "가입자 수"], hist_rows, (1,)), ind_txt=ind_txt, calc=calc_txt, rel=rel_html, rate=RATE_NOW * 100, capv="{:,}".format(cap))
    faq = [("%s 평균연봉은 얼마인가요?" % c["name"], "국민연금 가입 사업장 데이터로 추정한 %s 평균연봉은 %s입니다(월 평균 약 %s원). 실제 급여와 다를 수 있으며 상한·비과세·상여 반영 방식에 따라 오차가 있습니다." % (c["name"], st, won(est_m))),
           ("%s 직원은 몇 명인가요?" % c["name"], "%s 기준 국민연금 가입자는 %s명이며 가입 사업장은 %d곳입니다. %s" % (ym_txt(dm), "{:,}".format(c["n"]), c["br"], trend + ".")),
           ("%s 퇴사율은 어떻게 보나요?" % c["name"], ("최근 12개월 상실 가입자 %s명을 평균 가입자 %s명으로 나눈 값은 약 %.0f%%입니다. 상실에는 정년·계약 만료·전출 등이 포함돼 자발적 퇴사율과는 다릅니다." % ("{:,}".format(c["lost12"]), "{:,}".format(round(c["avg_n"])), c["turn"])) if c["turn"] is not None else "집계 기간이 12개월에 못 미쳐 퇴사율을 계산하지 않았습니다.")]
    ld = [{"@context": "https://schema.org", "@type": "Organization", "name": c["name"], "address": {"@type": "PostalAddress", "addressRegion": c["sido"], "addressLocality": c["sgg"], "addressCountry": "KR"},
           "numberOfEmployees": {"@type": "QuantitativeValue", "value": c["n"]}}]
    title = "%s 평균연봉·직원수·퇴사율 (%s)" % (c["name"], ym_txt(dm))
    desc = "%s(%s %s, %s) 직원 %s명, 추정 평균연봉 %s%s. 최근 1년 인원 %+d명. 국민연금 가입 사업장 데이터 기반." % (
        c["name"], c["sido"], c["sgg"], c["iname"], "{:,}".format(c["n"]), st, (", 연 퇴사율 약 %.0f%%" % c["turn"]) if c["turn"] is not None else "", c["chg"])
    write(path, layout(path, title, desc, body, faq, [("홈", "/"), ("회사 연봉", "/rank/"), (c["name"], path)], extra_ld=ld, coupang=(c["n"] >= 100)), "0.5" if c["n"] < 100 else "0.7")

# ───────────────────────── 업종·지역·순위 ─────────────────────────
def company_table(lst, cap, limit=200):
    rows = []
    for c in lst[:limit]:
        t, capped = salary_txt(c, cap)
        rows.append([comp_link(c), esc(c["iname"]), "%s %s" % (esc(c["sido"]), esc(c["sgg"])), "{:,}명".format(c["n"]), t,
                     ("%.0f%%" % c["turn"]) if c["turn"] is not None else "-"])
    return table(["회사", "업종", "지역", "직원 수", "추정 평균연봉", "퇴사율"], rows, (3, 4, 5))

def page_industry(ik, lst, meta, cap):
    name = lst[0]["iname"]
    lst = sorted(lst, key=lambda c: -c["n"])
    ms = med([c["annual"] for c in lst]); mt = med([c["turn"] for c in lst])
    tot = sum(c["n"] for c in lst)
    path = "/industry/%s/" % ik
    body = """
<div class="page-head"><h1>%(nm)s 회사 평균연봉·직원수 순위</h1><p>업종코드 %(ik)s · 국민연금 가입 법인 %(cnt)s곳 · %(ym)s 기준</p></div>
<p class="lead">‘%(nm)s’ 업종의 국민연금 가입 법인(직원 %(minn)s명 이상) %(cnt)s곳을 직원 수 순으로 정리했습니다. 이 업종 회사들의 추정 평균연봉 중앙값은 <b>약 %(ms)s만원</b>이고 직원은 모두 %(tot)s명입니다%(mt)s.</p>
%(ad)s
%(tbl)s
<div class="chips"><a class="chip" href="/industry/">업종 전체</a><a class="chip" href="/rank/">회사 순위</a></div>
""" % dict(nm=esc(name), ik=ik, cnt="{:,}".format(len(lst)), ym=ym_txt(meta["latest_data"]), minn=SITE_MIN_N, ms=man(ms), tot="{:,}".format(tot),
           mt=(", 평균 퇴사율은 약 %.0f%%" % mt) if mt is not None else "", ad=ad(), tbl=company_table(lst, cap))
    faq = [("%s 회사 평균연봉은 얼마인가요?" % name, "국민연금 가입 데이터로 추정한 이 업종 회사들의 평균연봉 중앙값은 약 %s만원입니다. 회사별 차이가 크고 상한·비과세 때문에 실제와 다를 수 있습니다." % man(ms)),
           ("이 업종에서 직원이 가장 많은 회사는?", "%s(직원 %s명)입니다." % (lst[0]["name"], "{:,}".format(lst[0]["n"])))]
    write(path, layout(path, "%s 회사 평균연봉·직원수 순위 (%s)" % (name, ym_txt(meta["latest_data"])),
        "%s 업종 법인 %s곳의 직원 수와 추정 평균연봉 순위. 평균연봉 중앙값 약 %s만원, 직원 합계 %s명." % (name, "{:,}".format(len(lst)), man(ms), "{:,}".format(tot)),
        body, faq, [("홈", "/"), ("업종", "/industry/"), (name, path)]), "0.6")
    return dict(ik=ik, name=name, cnt=len(lst), med=ms, tot=tot)

def page_industry_index(items):
    items = sorted(items, key=lambda x: -x["cnt"])
    rows = [['<a href="/industry/%s/">%s</a>' % (i["ik"], esc(i["name"])), "{:,}곳".format(i["cnt"]), "{:,}명".format(i["tot"]), "약 %s만원" % man(i["med"])] for i in items]
    body = """
<div class="page-head"><h1>업종별 회사 평균연봉</h1><p>국민연금 가입 법인 기준 · 회사 %(n)s곳 이상 업종</p></div>
<p class="lead">업종을 골라 해당 업종 회사들의 직원 수와 추정 평균연봉을 비교하세요. 값은 국민연금 가입 사업장 데이터로 추정한 것입니다.</p>
%(ad)s
%(t)s
""" % dict(n=15, ad=ad(), t=table(["업종", "회사 수", "직원 합계", "평균연봉 중앙값"], rows, (1, 2, 3)))
    write("/industry/", layout("/industry/", "업종별 회사 평균연봉 비교", "업종별 법인 수와 직원 수, 추정 평균연봉 중앙값 비교. 국민연금 가입 사업장 데이터 기반.", body, None, [("홈", "/"), ("업종", "/industry/")]), "0.7")

def page_region(sido, sgg, lst, meta, cap):
    lst = sorted(lst, key=lambda c: -c["n"])
    ms = med([c["annual"] for c in lst]); tot = sum(c["n"] for c in lst)
    place = "%s %s" % (sido, sgg)
    path = "/region/%s/%s/" % (sido, sgg)
    top_ind = collections.Counter(c["iname"] for c in lst).most_common(3)
    body = """
<div class="page-head"><h1>%(pl)s 회사 평균연봉·직원수 순위</h1><p>국민연금 가입 법인 %(cnt)s곳 · %(ym)s 기준</p></div>
<p class="lead">%(pl)s에 사업장이 있는 국민연금 가입 법인(직원 %(minn)s명 이상) %(cnt)s곳의 직원 수와 추정 평균연봉입니다. 이 지역 회사들의 평균연봉 중앙값은 <b>약 %(ms)s만원</b>, 직원은 모두 %(tot)s명이며 업종은 %(ti)s 순으로 많습니다.</p>
%(ad)s
%(tbl)s
<div class="chips"><a class="chip" href="/region/%(sido)s/">%(sido)s 전체</a><a class="chip" href="/region/">지역 전체</a></div>
""" % dict(pl=esc(place), cnt="{:,}".format(len(lst)), ym=ym_txt(meta["latest_data"]), minn=SITE_MIN_N, ms=man(ms), tot="{:,}".format(tot),
           ti=" · ".join("%s(%d곳)" % (esc(n), k) for n, k in top_ind), ad=ad(), tbl=company_table(lst, cap), sido=esc(sido))
    faq = [("%s에서 직원이 가장 많은 회사는?" % place, "%s(직원 %s명)입니다." % (lst[0]["name"], "{:,}".format(lst[0]["n"]))),
           ("%s 회사 평균연봉은 얼마인가요?" % place, "국민연금 가입 데이터로 추정한 이 지역 회사들의 평균연봉 중앙값은 약 %s만원입니다." % man(ms))]
    write(path, layout(path, "%s 회사 평균연봉·직원수 순위 (%s)" % (place, ym_txt(meta["latest_data"])),
        "%s 국민연금 가입 법인 %s곳의 직원 수와 추정 평균연봉 순위. 평균연봉 중앙값 약 %s만원." % (place, "{:,}".format(len(lst)), man(ms)),
        body, faq, [("홈", "/"), ("지역", "/region/"), (sido, "/region/%s/" % sido), (sgg, path)]), "0.6")
    return dict(sido=sido, sgg=sgg, cnt=len(lst), med=ms, tot=tot)

def page_sido(sido, lst, subs, meta):
    rows = [['<a href="/region/%s/%s/">%s</a>' % (sido, s["sgg"], esc(s["sgg"])), "{:,}곳".format(s["cnt"]), "{:,}명".format(s["tot"]), "약 %s만원" % man(s["med"])] for s in sorted(subs, key=lambda x: -x["cnt"])]
    ms = med([c["annual"] for c in lst])
    path = "/region/%s/" % sido
    body = """
<div class="page-head"><h1>%(s)s 시군구별 회사 평균연봉</h1><p>국민연금 가입 법인 %(cnt)s곳 · %(ym)s 기준</p></div>
<p class="lead">%(s)s의 국민연금 가입 법인 %(cnt)s곳을 시군구별로 정리했습니다. 전체 평균연봉 중앙값은 약 %(ms)s만원입니다.</p>
%(ad)s
%(t)s
""" % dict(s=esc(sido), cnt="{:,}".format(len(lst)), ym=ym_txt(meta["latest_data"]), ms=man(ms), ad=ad(), t=table(["시군구", "회사 수", "직원 합계", "평균연봉 중앙값"], rows, (1, 2, 3)))
    write(path, layout(path, "%s 시군구별 회사 평균연봉·직원수" % sido, "%s 시군구별 국민연금 가입 법인 수, 직원 합계, 추정 평균연봉 중앙값." % sido, body, None, [("홈", "/"), ("지역", "/region/"), (sido, path)]), "0.6")

def page_region_index(sidos):
    rows = [['<a href="/region/%s/">%s</a>' % (s, esc(s)), "{:,}곳".format(n), "{:,}명".format(t), "약 %s만원" % man(m)] for s, n, t, m in sidos]
    body = """
<div class="page-head"><h1>지역별 회사 평균연봉</h1><p>시도 · 시군구별 국민연금 가입 법인</p></div>
<p class="lead">시도를 골라 시군구별 회사 수와 추정 평균연봉을 확인하세요.</p>
%s
%s
""" % (ad(), table(["시도", "회사 수", "직원 합계", "평균연봉 중앙값"], rows, (1, 2, 3)))
    write("/region/", layout("/region/", "지역별 회사 평균연봉 — 시도·시군구", "시도별 국민연금 가입 법인 수와 직원 합계, 추정 평균연봉 중앙값.", body, None, [("홈", "/"), ("지역", "/region/")]), "0.7")

def page_rank(key, title, h1, lead, lst, cap, meta, extra_cols=None, path=None):
    rows = []
    for i, c in enumerate(lst[:300], 1):
        t, capped = salary_txt(c, cap)
        rows.append([str(i), comp_link(c), esc(c["iname"]), "{:,}명".format(c["n"]), t, "%+.1f%%" % c["chg_pct"], ("%.0f%%" % c["turn"]) if c["turn"] is not None else "-"])
    path = path or "/rank/%s/" % key
    body = """
<div class="page-head"><h1>%s</h1><p>국민연금 가입 법인 · %s 기준</p></div>
<p class="lead">%s</p>
%s
%s
<div class="chips"><a class="chip" href="/rank/">순위 전체</a><a class="chip" href="/industry/">업종별</a><a class="chip" href="/region/">지역별</a></div>
""" % (h1, ym_txt(meta["latest_data"]), lead, ad(), table(["순위", "회사", "업종", "직원 수", "추정 평균연봉", "1년 증감률", "퇴사율"], rows, (0, 3, 4, 5, 6)))
    write(path, layout(path, title, lead[:110], body, None, [("홈", "/"), ("순위", "/rank/"), (h1, path)]), "0.8")

def page_rank_index(meta):
    cards = [("employees", "직원 수 많은 회사 TOP 300", "국민연금 가입자 수 기준 대기업 순위"), ("salary", "추정 평균연봉 높은 회사", "소득이 상한에 도달한 회사부터"),
             ("hiring", "인원이 늘고 있는 회사", "최근 1년 직원 증가율 상위(직원 200명 이상)"), ("stable", "퇴사율이 낮은 회사", "근속이 안정적인 회사(직원 200명 이상)")]
    body = """
<div class="page-head"><h1>회사 연봉·직원수 순위</h1><p>국민연금 가입 법인 · %s 기준</p></div>
<p class="lead">국민연금 가입 사업장 데이터로 만든 회사 순위입니다. 회사 이름을 검색하거나 순위·업종·지역에서 찾아보세요.</p>
%s
<div class="card-grid">%s</div>
<div class="chips"><a class="chip" href="/industry/">업종별 평균연봉</a><a class="chip" href="/region/">지역별 평균연봉</a></div>
""" % (ym_txt(meta["latest_data"]), ad(), "".join('<a class="card" href="/rank/%s/"><b>%s</b><span>%s</span></a>' % (k, t, d) for k, t, d in cards))
    write("/rank/", layout("/rank/", "회사 평균연봉·직원수 순위", "직원 수, 추정 평균연봉, 인원 증가, 퇴사율로 보는 회사 순위. 국민연금 가입 사업장 데이터 기반.", body, None, [("홈", "/"), ("순위", "/rank/")]), "0.8")

# ───────────────────────── 기타 페이지 ─────────────────────────
def page_home(meta, cs, cap):
    dm = meta["latest_data"]
    top = sorted(cs, key=lambda c: -c["n"])[:10]
    pop = [(v, S.calc(v * 10000)["net"]) for v in (3000, 3500, 4000, 5000, 6000, 8000, 10000)]
    body = """
<div class="hero"><h1>💼 회사 평균연봉 · 연봉 실수령액</h1><p>국민연금 가입 데이터로 추정한 회사별 평균연봉·직원수·퇴사율과 2026년 연봉별 실수령액을 한곳에서.</p>
<div class="search-box"><input id="q" type="search" placeholder="회사 이름을 입력하세요 (예: 삼성전자, 쿠팡, 우아한형제들)" autocomplete="off"><div class="sr-list" id="sr"></div></div></div>
%(ad)s
<h2 class="group-title">💰 연봉별 월 실수령액 (2026년)</h2>
%(sal)s
<h2 class="group-title">🏢 직원 수 많은 회사</h2>
%(top)s
<h2 class="group-title">🔎 둘러보기</h2>
<div class="card-grid">
<a class="card" href="/rank/"><b>회사 순위</b><span>직원 수·연봉·인원 증가·퇴사율</span></a>
<a class="card" href="/industry/"><b>업종별 평균연봉</b><span>%(ni)s개 업종 비교</span></a>
<a class="card" href="/region/"><b>지역별 평균연봉</b><span>시도·시군구별 회사</span></a>
<a class="card" href="/calculator/"><b>실수령액 계산기</b><span>연봉·월급·부양가족 직접 입력</span></a>
</div>
<p class="lead">우아연봉은 국민연금공단의 가입 사업장 내역(%(ym)s 기준)을 이용해 직원 %(minn)s명 이상 법인 %(nc)s곳의 직원 수, 추정 평균연봉, 최근 1년 입사·퇴사 규모를 보여 드립니다. 추정 방식과 한계는 <a href="/about/">산정 기준</a>에서 공개합니다.</p>
<script src="/assets/js/search.js"></script>
""" % dict(ad=ad(), sal=table(["연봉", "월 실수령액"], [['<a href="/salary/%d/">%s만원</a>' % (v, "{:,}".format(v)), won(n) + "원"] for v, n in pop], (1,)),
           top=company_table(top, cap, 10), ni=0, ym=ym_txt(dm), minn=SITE_MIN_N, nc="{:,}".format(len(cs)))
    return body

def page_about(meta, cap):
    body = """
<div class="page-head"><h1>산정 기준과 데이터 출처</h1><p>회사 연봉·실수령액을 어떻게 계산하는지 공개합니다</p></div>
<h2 class="group-title">🏢 회사별 추정 평균연봉</h2>
<p class="lead"><b>데이터</b>: 공공데이터포털 국민연금공단 「국민연금 가입 사업장 내역」(월별 CSV, 이용허락범위 제한 없음). 법인(법인 사업장) 중 최근월 가입 상태인 사업장을 사업장명과 사업자등록번호 앞 6자리로 묶어 한 회사로 봅니다. 개인사업장은 대표자 개인 이름이 상호인 경우가 많아 제외했습니다.</p>
<p class="lead"><b>계산</b>: 1인당 월 평균 기준소득월액 = 당월 고지금액 ÷ (가입자 수 × 보험료율). 보험료율은 2026년 1월부터 9.5%, 그 이전은 9%입니다. 여기에 12를 곱해 추정 평균연봉으로 표시합니다.</p>
<p class="lead"><b>한계</b>: ① 기준소득월액에는 상한({CAP}원, 2026년 7월~)이 있어 고소득자 소득이 잘려 반영됩니다. 평균이 상한에 닿은 회사는 ‘이상’으로 표시합니다. ② 비과세 소득은 빠지고 상여·성과급은 신고 방식에 따라 일부만 반영됩니다. ③ 신고는 실제 급여 변동보다 늦게 반영될 수 있습니다. ④ 만 60세 이상과 단시간 근로자 등 가입 대상이 아닌 직원은 포함되지 않습니다. ⑤ 지점별 사업장명이 다른 회사는 한 회사로 묶이지 않을 수 있습니다. 그래서 이 값은 ‘국민연금 신고 소득 기준 추정치’이며 회사가 공개한 평균 급여나 실제 급여와 다릅니다.</p>
<p class="lead"><b>입사·퇴사</b>: 최근 12개월 월별 ‘신규취득자수’와 ‘상실가입자수’를 합산합니다. 상실에는 정년·계약 만료·전출 등이 포함되므로 자발적 퇴사율과 같지 않습니다. 자료가 12개월에 못 미치는 사업장은 표시하지 않습니다.</p>
<h2 class="group-title">🧮 실수령액</h2>
<p class="lead">2026년 근로자 부담 요율을 적용합니다: 국민연금 4.75%(기준소득월액 상한 월 {CAP}원), 건강보험 3.595%, 장기요양보험 건강보험료의 13.14%, 고용보험 0.9%. 소득세는 연말정산 방식(근로소득공제 → 인적공제 → 4대보험료 공제 → 세율표 → 근로소득세액공제)으로 연 세액을 계산해 12로 나눈 근사값이고 지방소득세는 소득세의 10%입니다. 비과세 식대 월 20만원과 공제대상 가족 수를 가정으로 두며 상여·수당·연말정산 환급은 반영하지 않습니다. 실제 원천징수액(간이세액표)과 차이가 있을 수 있습니다.</p>
<h2 class="group-title">📬 문의·정정</h2>
<p class="lead">회사명 삭제·정정 요청이나 오류 제보는 <a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a> 으로 보내 주세요. 사업장 정보는 모두 공공데이터이며 개인을 식별할 수 있는 정보는 다루지 않습니다.</p>
""".replace("{CAP}", won(cap))
    write("/about/", layout("/about/", "산정 기준과 데이터 출처", "우아연봉의 회사별 추정 평균연봉, 입사·퇴사 통계, 실수령액 계산 기준과 한계를 공개합니다.", body, None, [("홈", "/"), ("산정 기준", "/about/")]), "0.5")

def page_privacy():
    body = """
<div class="page-head"><h1>개인정보처리방침</h1></div>
<p class="lead">우아연봉(wooayeonbong.wooahouse.com, 이하 “서비스”)은 회원가입이나 로그인을 요구하지 않으며 이용자의 개인정보를 직접 수집하지 않습니다. 계산기에 입력한 값은 브라우저 안에서만 처리되고 서버로 전송되지 않습니다.</p>
<h3>자동 수집 정보</h3><p class="lead">서비스 개선을 위해 Google Analytics로 방문자 수·페이지뷰 등 익명 통계를 수집하며, Google AdSense와 쿠팡 파트너스는 맞춤 광고를 위해 쿠키를 사용할 수 있습니다. 쿠키는 브라우저 설정에서 비활성화할 수 있습니다. (<a href="https://policies.google.com/privacy">Google 개인정보처리방침</a>, <a href="https://policies.google.com/technologies/ads">Google 광고 정책</a>)</p>
<h3>공공데이터</h3><p class="lead">서비스는 국민연금공단이 공개한 가입 사업장 내역(법인 사업장의 집계 수치)만 사용하며 개인을 식별할 수 있는 정보는 포함하지 않습니다.</p>
<h3>쿠팡 파트너스</h3><p class="lead">일부 페이지에는 쿠팡 파트너스 활동의 일환으로 광고가 포함되어 있으며 이에 따른 수수료를 제공받을 수 있습니다.</p>
<h3>문의</h3><p class="lead"><a href="mailto:ingmaster83@gmail.com">ingmaster83@gmail.com</a></p>
<p class="note">최종 수정일: 2026년 10월 18일</p>
"""
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아연봉 개인정보처리방침", body, None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)

def page_calculator():
    body = """
<div class="page-head"><h1>연봉·월급 실수령액 계산기 (2026년)</h1><p>4대보험 + 소득세 · 부양가족 · 비과세 식대 반영</p></div>
<p class="lead">연봉(또는 세전 월급)을 입력하면 2026년 요율로 국민연금·건강보험·장기요양·고용보험과 소득세·지방소득세를 계산해 월 실수령액을 알려 줍니다. 입력한 값은 서버로 전송되지 않습니다.</p>
<div class="tool-box">
<div class="tool-row">
<div><label for="c-mode">입력 기준</label><select id="c-mode"><option value="y">연봉(만원)</option><option value="m">세전 월급(만원)</option></select></div>
<div><label for="c-amt">금액(만원)</label><input id="c-amt" type="number" min="0" value="4000" style="width:130px"></div>
<div><label for="c-meal">비과세 식대(월, 원)</label><input id="c-meal" type="number" min="0" step="10000" value="200000" style="width:130px"></div>
<div><label for="c-fam">공제대상 가족(본인 포함)</label><select id="c-fam"><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option></select></div>
<div><label for="c-kid">8세 이상 자녀 수</label><select id="c-kid"><option>0</option><option>1</option><option>2</option><option>3</option></select></div>
<button class="btn-p" id="c-go">계산하기</button></div>
<div class="tool-out" id="c-out">금액을 입력하고 계산하기를 눌러 주세요.</div></div>
%(ad)s
<div class="chips"><a class="chip" href="/salary/">연봉별 실수령액 표</a><a class="chip" href="/monthly/">월급별 실수령액 표</a></div>
<div class="note-box">2026년 요율(국민연금 4.75%%, 건강보험 3.595%%, 장기요양 13.14%%, 고용보험 0.9%%)과 소득세법 공제를 적용한 근사 계산입니다. 실제 급여명세서와 차이가 있을 수 있습니다. 자세한 기준은 <a href="/about/">산정 기준</a>을 참고하세요.</div>
<script src="/assets/js/calc.js"></script>
""" % dict(ad=ad())
    faq = [("실수령액은 어떻게 계산하나요?", "세전 월급에서 비과세 식대를 뺀 금액을 기준으로 4대보험을 계산하고, 연말정산식으로 구한 연 소득세를 12로 나눠 월 소득세와 지방소득세를 구합니다."),
           ("부양가족을 늘리면 실수령액이 늘어나나요?", "공제대상 가족이 늘면 인적공제가 늘어 소득세가 줄어듭니다. 8세 이상 자녀는 자녀세액공제가 추가로 적용됩니다.")]
    write("/calculator/", layout("/calculator/", "연봉·월급 실수령액 계산기 (2026년)", "연봉이나 세전 월급을 입력해 2026년 월 실수령액을 계산합니다. 4대보험, 소득세, 부양가족, 비과세 식대 반영.", body, faq, [("홈", "/"), ("계산기", "/calculator/")]), "0.8")

def write_assets(cs, cap):
    a = OUT / "assets"
    shutil.copytree(ROOT / "assets", a, dirs_exist_ok=True)
    (a / "data").mkdir(exist_ok=True)
    idx = [[c["name"], c["slug"], c["n"], c["sido"], c["sgg"], round(c["annual"] / 10000) if c["ratio"] < 0.97 else -round(cap * 12 / 10000)] for c in cs]
    (a / "data" / "search.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def make_og():
    f = ROOT / "assets" / "og-image.png"
    if f.exists(): return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return
    im = Image.new("RGB", (1200, 630), (29, 78, 216))
    dr = ImageDraw.Draw(im)
    def font(sz):
        for n in ("malgunbd.ttf", "malgun.ttf", "NanumGothicBold.ttf"):
            try: return ImageFont.truetype(n, sz)
            except Exception: pass
        return ImageFont.load_default()
    dr.rounded_rectangle((90, 90, 1110, 540), 40, fill=(255, 255, 255))
    dr.text((150, 150), "우아연봉", font=font(110), fill=(30, 58, 138))
    dr.text((150, 300), "회사 평균연봉 · 직원수 · 퇴사율", font=font(54), fill=(31, 41, 55))
    dr.text((150, 380), "연봉 실수령액 계산 (2026)", font=font(54), fill=(31, 41, 55))
    dr.text((150, 470), "wooayeonbong.wooahouse.com", font=font(34), fill=(107, 114, 128))
    im.save(f)

# ───────────────────────── 실행 ─────────────────────────
def main():
    t0 = time.time()
    make_og()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    meta, cs, rate, cap = load()
    print("회사", len(cs), "최신", meta["latest_data"], "rate", rate, "cap", cap)
    write_assets(cs, cap)
    ind, reg, sido = build_groups(cs)
    ind_stats = {}
    for k, lst in ind.items():
        ind_stats[k] = dict(count=len(lst), med_annual=med([c["annual"] for c in lst]), med_turn=med([c["turn"] for c in lst]))
    cs_est = sorted(cs, key=lambda c: c["annual"])
    # 회사
    for i, c in enumerate(cs):
        page_company(c, meta, cap, ind_stats, ind, reg, cs_est)
        if i % 10000 == 0: print(" company", i, round(time.time() - t0), "s")
    # 실수령액
    for v in ANNUAL_STEPS: page_salary(v, cs_est)
    for m in MONTHLY_STEPS: page_monthly(m)
    hub_pages(); page_calculator()
    # 업종
    inds = [page_industry(k, lst, meta, cap) for k, lst in ind.items() if len(lst) >= 15 and k not in ("000000", "")]
    page_industry_index(inds)
    # 지역
    subs_by_sido = collections.defaultdict(list)
    for (sd, sg), lst in reg.items():
        if len(lst) >= 5 and sd and sg:
            subs_by_sido[sd].append(page_region(sd, sg, lst, meta, cap))
    sidos = []
    for sd, lst in sido.items():
        if sd in subs_by_sido:
            page_sido(sd, lst, subs_by_sido[sd], meta)
            sidos.append((sd, len(lst), sum(c["n"] for c in lst), med([c["annual"] for c in lst])))
    page_region_index(sorted(sidos, key=lambda x: -x[1]))
    # 순위
    page_rank_index(meta)
    page_rank("employees", "직원 수 많은 회사 TOP 300 (국민연금 가입 기준)", "직원 수 많은 회사 TOP 300", "국민연금 가입자 수가 많은 법인 300곳입니다. 직원 수와 추정 평균연봉, 최근 1년 인원 증감을 함께 보여 드립니다.",
              sorted(cs, key=lambda c: -c["n"]), cap, meta)
    page_rank("salary", "추정 평균연봉 높은 회사 순위 (국민연금 신고 소득 기준)", "추정 평균연봉 높은 회사", "국민연금 신고 소득으로 추정한 평균연봉이 높은 회사입니다. 기준소득월액 상한에 닿은 회사는 같은 값(이상)으로 표시되며 이 경우 직원 수 순으로 정렬했습니다.",
              sorted([c for c in cs if c["n"] >= 100], key=lambda c: (-min(c["annual"], cap * 12 * 0.999 if c["ratio"] >= 0.97 else c["annual"]), -c["n"])), cap, meta)
    page_rank("hiring", "인원이 늘고 있는 회사 순위 (최근 1년 직원 증가율)", "인원이 늘고 있는 회사", "최근 1년간 국민연금 가입자(직원) 수가 가장 많이 늘어난 회사입니다. 직원 200명 이상 회사 기준입니다.",
              sorted([c for c in cs if c["n"] >= 200 and c["nm"] >= 12], key=lambda c: -c["chg_pct"]), cap, meta)
    page_rank("stable", "퇴사율 낮은 회사 순위 (근속 안정 회사)", "퇴사율 낮은 회사", "최근 12개월 가입 상실 비율(퇴사율 추정치)이 낮은 회사입니다. 직원 200명 이상, 12개월 자료가 있는 법인 기준이며 정년·계약 만료 등도 포함된 수치입니다.",
              sorted([c for c in cs if c["n"] >= 200 and c["turn"] is not None], key=lambda c: c["turn"]), cap, meta)
    # 홈 / 기타
    body = page_home(meta, cs, cap).replace("0개 업종", "%d개 업종" % len(inds))
    write("/", layout("/", "우아연봉 — 회사 평균연봉·직원수·퇴사율, 연봉 실수령액", "국민연금 가입 데이터로 추정한 회사별 평균연봉·직원수·퇴사율과 2026년 연봉·월급별 실수령액을 확인하세요.", body,
                      [("회사 평균연봉은 어떻게 알 수 있나요?", "국민연금공단이 공개한 가입 사업장의 가입자 수와 당월 고지금액으로 1인당 평균 기준소득월액을 추정합니다. 상한·비과세 때문에 실제와 차이가 있습니다."),
                       ("연봉 실수령액은 어떻게 계산하나요?", "2026년 4대보험 요율과 소득세법 공제를 적용한 근사 계산입니다. 연봉별 표와 계산기를 이용하세요.")]), "1.0")
    page_about(meta, cap); page_privacy()
    # 사이트맵·robots·404
    today = time.strftime("%Y-%m-%d")
    chunks = [WRITTEN[i:i + 40000] for i in range(0, len(WRITTEN), 40000)]
    for n, ch in enumerate(chunks, 1):
        urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr) for p, pr in ch)
        (OUT / ("sitemap-%d.xml" % n)).write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    idx = "".join("<sitemap><loc>%s/sitemap-%d.xml</loc><lastmod>%s</lastmod></sitemap>" % (BASE, n, today) for n in range(1, len(chunks) + 1))
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</sitemapindex>\n' % idx, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooayeonbong.wooahouse.com\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1><p>주소가 바뀌었거나 데이터 기준 변경으로 사라진 회사일 수 있어요.</p></div><div class="chips"><a class="chip" href="/">홈에서 회사 검색</a><a class="chip" href="/salary/">연봉 실수령액</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("pages:", len(WRITTEN), "elapsed", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
