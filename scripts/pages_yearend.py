# -*- coding: utf-8 -*-
"""우아연봉 확장: 연말정산 환급(연봉별 절세 효과) 페이지. build_site.main() 에서 호출.
현행 세법(2026년 귀속 안내 기준) 일반 규정으로 계산한 참고용 추정이다. 세법은 개정될 수 있다."""
from common import *
import salary as S

YE_STEPS = list(range(2000, 10001, 100)) + list(range(10500, 20001, 500))

def table(heads, rows, num_cols=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num_cols else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num_cols else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)

def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)
def k(x): return "{:,}".format(x)

def total_pay(annual):
    """과세 대상 총급여 = 연봉 − 비과세 식대(월 20만원)"""
    pay = annual / 12
    return (pay - min(S.MEAL, pay)) * 12

def tax_due(annual, family=1, children=0, extra_ded=0, extra_credit=0):
    """연말정산 결정세액(소득세, 원) 근사. 지방소득세 별도."""
    r = S.calc(annual)
    s = total_pay(annual)
    tb = max(0, s - S.earned_income_deduction(s) - 1_500_000 * family - r["pension"] * 12 - (r["health"] + r["ltc"] + r["emp"]) * 12 - extra_ded)
    t = S.income_tax_base(tb)
    t = max(0, t - S.earned_tax_credit(t, s) - S.child_credit(children) - extra_credit)
    return t, tb

def marginal(tb):
    for lim, r, d in S.BRACKETS:
        if tb <= lim: return r

def card_limit(s):
    return 3_000_000 if s <= 70_000_000 else 2_500_000 if s <= 120_000_000 else 2_000_000

def pension_cap(s): return 9_000_000 if s <= 120_000_000 else 6_000_000
def pension_rate(s): return 0.165 if s <= 55_000_000 else 0.132
def rent_rate(s): return 0.17 if s <= 55_000_000 else 0.15
def rent_ok(s): return s <= 80_000_000

def r10(x): return int(round(x / 10.0)) * 10

def effect(annual, **kw):
    """공제 추가 시 줄어드는 세금(소득세+지방소득세, 원)"""
    t0, _ = tax_due(annual)
    t1, _ = tax_due(annual, **kw)
    return r10((t0 - t1) * 1.1)

def info(man):
    annual = man * 10_000
    s = total_pay(annual)
    t0, tb = tax_due(annual)
    r = marginal(tb)
    cl = card_limit(s); thr = s * 0.25
    pen = pension_cap(s) * pension_rate(s)
    rent_eff = {}
    for m in (30, 50, 70):
        rent_eff[m] = effect(annual, extra_credit=min(m * 120_000, 10_000_000) * rent_rate(s)) if rent_ok(s) else 0
    med_eff = {sp: r10(max(0, sp * 10_000 - s * 0.03) * 0.15 * 1.1) for sp in (200, 300, 500, 1000)}
    return dict(man=man, annual=annual, s=s, t0=t0, tb=tb, r=r, cl=cl, thr=thr, need_credit=thr + cl / 0.15, need_debit=thr + cl / 0.30,
                card_eff=effect(annual, extra_ded=cl), pen=pen, pen_eff=effect(annual, extra_credit=pen), rent_eff=rent_eff,
                rent_max=effect(annual, extra_credit=10_000_000 * rent_rate(s)) if rent_ok(s) else 0, dep_eff=effect(annual, family=2),
                child={n: r10(S.child_credit(n) * 1.1) for n in (1, 2, 3)}, both=effect(annual, extra_ded=cl, extra_credit=pen), med_eff=med_eff)

def mw(x): return k(int(round(x / 10_000)))
def pct(x): return "%g" % round(x * 100, 1)

def page_yearend(man):
    d = info(man); path = "/yearend/%d/" % man
    s = d["s"]
    rent_line = ("월세 세액공제(총급여 8천만원 이하, 연 한도 1,000만원)를 받으면 월세 50만원 기준 연 %s원, 한도(연 1,000만원)까지 내면 %s원 줄어듭니다." % (k(d["rent_eff"][50]), k(d["rent_max"]))) if rent_ok(s) \
        else "총급여가 8천만원을 넘어 월세 세액공제는 받을 수 없습니다."
    lead = ("<p class=\"lead\">연봉 <b>%s만원</b>(총급여 약 %s만원)의 연말정산 결정세액은 약 <b>%s원</b>(지방소득세 별도), 한계세율은 <b>%d%%</b>입니다. "
            "카드 소득공제를 한도까지 채우면 세금이 약 <b>%s원</b>, 연금저축·IRP를 %s만원 넣으면 약 <b>%s원</b> 줄어듭니다. 둘을 함께 하면 최대 약 <b>%s원</b>입니다. %s</p>") % (
        k(man), mw(s), k(r10(d["t0"])), round(d["r"] * 100), k(d["card_eff"]), mw(pension_cap(s)), k(d["pen_eff"]), k(d["both"]), rent_line)
    rows = [["신용카드 등 소득공제", "총급여의 25%%(%s만원) 초과분 × 15~40%%, 한도 %s만원" % (mw(d["thr"]), mw(d["cl"])), k(d["card_eff"]) + "원"],
            ["연금저축·IRP 세액공제", "연 %s만원 × %s%%" % (mw(pension_cap(s)), pct(pension_rate(s))), k(d["pen_eff"]) + "원"],
            ["월세 세액공제(월 50만원)", ("연 600만원 × %d%%" % round(rent_rate(s) * 100)) if rent_ok(s) else "총급여 8천만원 초과로 해당 없음", (k(d["rent_eff"][50]) + "원") if rent_ok(s) else "-"],
            ["부양가족 1명 추가(기본공제 150만원)", "소득공제 150만원 × 세율", k(d["dep_eff"]) + "원"],
            ["자녀 1명 / 2명 / 3명 세액공제", "25만 / 55만 / 95만원", "%s / %s / %s원" % (k(d["child"][1]), k(d["child"][2]), k(d["child"][3]))]]
    t1 = table(["항목", "공제 방식", "줄어드는 세금(지방소득세 포함)"], rows, (2,))
    t2 = table(["연간 의료비 지출(본인·부양가족)", "줄어드는 세금"], [[k(sp) + "만원", k(d["med_eff"][sp]) + "원"] for sp in (200, 300, 500, 1000)], (1,))
    i = YE_STEPS.index(man); near = YE_STEPS[max(0, i - 5): i + 6]
    nrows = []
    for v in near:
        e = info(v)
        nrows.append([('<a href="/yearend/%d/">%s만원</a>' % (v, k(v))) if v != man else "<b>%s만원</b>" % k(v), k(r10(e["t0"])) + "원", k(e["card_eff"]) + "원", k(e["pen_eff"]) + "원"])
    t3 = table(["연봉", "결정세액(소득세)", "카드 한도 공제 효과", "연금·IRP 효과"], nrows, (1, 2, 3))
    capped = d["pen_eff"] >= r10(d["t0"] * 1.1) - 10
    cap_note = "<p class=\"note\">이 연봉은 결정세액이 작아 세액공제를 한도까지 받아도 낸 세금(약 %s원, 지방소득세 포함) 이상은 줄어들지 않습니다. 공제는 세금을 0원으로 만들 수 있을 뿐 환급액을 더 늘리지는 못합니다.</p>" % k(r10(d["t0"] * 1.1)) if capped else ""
    sal_link = min(range(1500, 30001, 100), key=lambda v: abs(v - man))
    body = """
<div class="page-head"><h1>연봉 %(m)s만원 연말정산 — 카드·연금저축·월세 절세 효과</h1><p>총급여 약 %(s)s만원 · 한계세율 %(r)d%% · 결정세액 약 %(t0)s원</p></div>
%(lead)s
<div class="stat-row"><div class="stat"><small>결정세액(소득세)</small><b>%(t0)s원</b></div><div class="stat"><small>한계세율</small><b>%(r)d%%</b></div><div class="stat"><small>카드 한도 공제 시</small><b>-%(ce)s원</b></div><div class="stat"><small>연금·IRP 시</small><b>-%(pe)s원</b></div></div>
%(ad)s
<h2 class="group-title">📋 항목별 절세 효과</h2>
%(t1)s
%(cap_note)s
<h2 class="group-title">🏥 의료비 세액공제 (총급여 3%% 초과분 × 15%%)</h2>
<p class="lead">총급여의 3%%(%(med3)s만원)를 넘는 의료비만 공제됩니다.</p>
%(t2)s
<h2 class="group-title">🔁 비슷한 연봉</h2>
%(t3)s
<h2 class="group-title">📌 신용카드 공제를 한도까지 받으려면</h2>
<ul class="lead" style="margin-left:20px"><li>총급여의 25%%인 %(thr)s만원은 공제 없이 먼저 써야 합니다.</li><li>신용카드(공제율 15%%)만 쓴다면 약 %(nc)s만원, 체크카드·현금영수증(30%%)만 쓴다면 약 %(nd)s만원을 쓰면 한도 %(cl)s만원이 찹니다.</li><li>전통시장·대중교통(40%%)은 별도 추가 한도가 있어 한도 초과분을 더 받을 수 있습니다.</li></ul>
<p class="note">2026년 현행 세법의 일반 규정으로 계산한 참고용 추정입니다. 연봉은 세전 연봉(식대 월 20만원 비과세 가정), 부양가족 없음(본인만)을 기준으로 하며 보험료·교육비·기부금·주택자금 등 다른 공제와 중복·한도 적용에 따라 실제 환급액은 달라집니다. 정확한 금액은 국세청 홈택스 연말정산 간소화 서비스에서 확인하세요.</p>
%(ch)s
""" % dict(m=k(man), s=mw(s), r=round(d["r"] * 100), t0=k(r10(d["t0"])), lead=lead, ce=k(d["card_eff"]), pe=k(d["pen_eff"]), ad=ad(), t1=t1, t2=t2, t3=t3, cap_note=cap_note,
           med3=mw(s * 0.03), thr=mw(d["thr"]), nc=mw(d["need_credit"]), nd=mw(d["need_debit"]), cl=mw(d["cl"]),
           ch=chips([("연봉 %s만원 실수령액" % k(sal_link), "/salary/%d/" % sal_link), ("연말정산 전체 보기", "/yearend/"), ("신용카드 공제", "/yearend/card/"), ("연금저축·IRP", "/yearend/pension/"), ("월세 세액공제", "/yearend/rent/")]))
    faq = [("연봉 %s만원이면 연말정산 환급이 얼마나 되나요?" % k(man), "환급액은 한 해 동안 낸 원천징수세와 결정세액의 차이로 정해져 사람마다 다릅니다. 연봉 %s만원의 결정세액은 약 %s원이며 카드 공제 한도를 채우면 약 %s원, 연금저축·IRP를 채우면 약 %s원 세금이 줄어듭니다." % (k(man), k(r10(d["t0"])), k(d["card_eff"]), k(d["pen_eff"]))),
           ("신용카드는 얼마를 써야 공제받나요?", "총급여의 25%%(%s만원)를 넘게 쓴 금액부터 공제됩니다. 한도 %s만원을 채우려면 신용카드만 쓸 경우 약 %s만원이 필요합니다." % (mw(d["thr"]), mw(d["cl"]), mw(d["need_credit"])) ),
           ("연금저축·IRP는 얼마까지 세액공제되나요?", "연금저축 연 600만원을 포함해 IRP까지 합쳐 연 %s만원 한도로 %s%%를 세액공제받습니다(총급여 5,500만원 이하 16.5%%, 초과 13.2%%)." % (mw(pension_cap(s)), pct(pension_rate(s))))]
    faq[1] = (faq[1][0], faq[1][1].replace("%%", "%"))
    faq[2] = (faq[2][0], faq[2][1].replace("%%", "%"))
    write(path, layout(path, "연봉 %s만원 연말정산 환급 — 카드·연금저축 절세 효과" % k(man),
        "연봉 %s만원 연말정산 결정세액 약 %s원, 카드 한도 공제 시 -%s원, 연금저축·IRP 시 -%s원. 월세·의료비·자녀 세액공제 효과 정리." % (k(man), k(r10(d["t0"])), k(d["card_eff"]), k(d["pen_eff"])),
        body, faq, [("홈", "/"), ("연말정산", "/yearend/"), ("연봉 %s만원" % k(man), path)]), "0.6" if man % 500 == 0 else "0.5")

HUB_STEPS = [2400, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 7000, 8000, 9000, 10000, 12000, 15000, 20000]

def hub():
    rows = []
    for v in HUB_STEPS:
        e = info(v)
        rows.append(['<a href="/yearend/%d/">%s만원</a>' % (v, k(v)), k(r10(e["t0"])) + "원", "%d%%" % round(e["r"] * 100), k(e["card_eff"]) + "원", k(e["pen_eff"]) + "원", k(e["both"]) + "원"])
    t = table(["연봉", "결정세액", "한계세율", "카드 한도", "연금·IRP", "둘 다"], rows, (1, 2, 3, 4, 5))
    body = """
<div class="page-head"><h1>연말정산 환급 — 연봉별 절세 효과 (2026 귀속)</h1><p>신용카드·연금저축·IRP·월세·의료비·자녀</p></div>
<p class="lead">연말정산에서 세금을 줄이는 대표 항목인 <b>신용카드 등 소득공제</b>, <b>연금저축·IRP 세액공제</b>, <b>월세 세액공제</b>, 의료비, 부양가족·자녀 공제가 연봉별로 얼마나 효과가 있는지 정리했습니다. 연봉을 눌러 세부 금액을 확인하세요. 소득공제는 한계세율을 곱한 만큼, 세액공제는 공제액 그대로 세금이 줄어듭니다.</p>
%(ad)s
%(t)s
<h2 class="group-title">🔎 주제별 보기</h2>
%(ch)s
<p class="note">2026년 현행 세법 일반 규정으로 계산한 참고용 추정이며 지방소득세(10%%)를 포함한 절감액입니다. 세법 개정이나 개인 상황에 따라 실제와 다를 수 있습니다.</p>
""" % dict(ad=ad(), t=t, ch=chips([("신용카드 소득공제", "/yearend/card/"), ("연금저축·IRP", "/yearend/pension/"), ("월세 세액공제", "/yearend/rent/"), ("의료비 공제", "/yearend/medical/")]))
    faq = [("연말정산 환급은 어떻게 정해지나요?", "1년간 월급에서 미리 낸 원천징수세액과 연말정산으로 확정한 결정세액을 비교해 많이 냈으면 환급, 적게 냈으면 추가 납부합니다."),
           ("소득공제와 세액공제는 무엇이 다른가요?", "소득공제는 과세표준을 줄여 한계세율만큼 세금이 줄고, 세액공제는 계산된 세금에서 공제액을 직접 뺍니다. 같은 100만원이라도 세액공제가 훨씬 큰 효과를 냅니다.")]
    write("/yearend/", layout("/yearend/", "연말정산 환급 — 연봉별 절세 효과 (카드·연금저축·월세)", "연봉별 연말정산 결정세액과 신용카드·연금저축·IRP·월세·의료비·자녀 공제 효과를 한눈에 비교.", body, faq, [("홈", "/"), ("연말정산", "/yearend/")], coupang=True), "0.9")

TOPIC_STEPS = [2400, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 7000, 8000, 9000, 10000, 12000, 15000]

def topic(slug, title, h1, lead, heads, rowfn, faq, desc):
    rows = []
    for v in TOPIC_STEPS:
        e = info(v); rows.append(['<a href="/yearend/%d/">%s만원</a>' % (v, k(v))] + rowfn(e))
    t = table(heads, rows, tuple(range(1, len(heads))))
    body = '<div class="page-head"><h1>%s</h1><p>연봉별 · 2026 귀속 · 참고용 추정</p></div>\n<p class="lead">%s</p>\n%s\n%s\n%s\n<p class="note">현행 세법 일반 규정으로 계산한 참고용 추정이며 지방소득세 포함 절감액입니다. 개인 상황에 따라 실제와 다를 수 있습니다.</p>' % (
        h1, lead, ad(), t, chips([("연말정산 전체", "/yearend/"), ("신용카드", "/yearend/card/"), ("연금저축·IRP", "/yearend/pension/"), ("월세", "/yearend/rent/"), ("의료비", "/yearend/medical/")]))
    p = "/yearend/%s/" % slug
    write(p, layout(p, title, desc, body, faq, [("홈", "/"), ("연말정산", "/yearend/"), (h1, p)]), "0.8")

def all_pages():
    n0 = len(WRITTEN)
    for m in YE_STEPS: page_yearend(m)
    hub()
    topic("card", "신용카드 소득공제 — 연봉별 얼마 써야 공제? 한도·절세 효과", "신용카드 소득공제 연봉별 기준",
          "신용카드·체크카드·현금영수증 사용액은 <b>총급여의 25%를 넘는 금액</b>부터 소득공제됩니다. 공제율은 신용카드 15%, 체크카드·현금영수증 30%, 전통시장·대중교통 40%이고 총급여 7천만원 이하는 300만원, 7천만~1.2억원은 250만원, 1.2억원 초과는 200만원까지 공제됩니다.",
          ["연봉", "25% 문턱", "공제 한도", "신용카드만 쓸 때 필요액", "체크카드만 쓸 때 필요액", "한도 공제 시 절세"],
          lambda e: [mw(e["thr"]) + "만원", mw(e["cl"]) + "만원", mw(e["need_credit"]) + "만원", mw(e["need_debit"]) + "만원", k(e["card_eff"]) + "원"],
          [("카드 공제는 얼마를 써야 받나요?", "총급여의 25%를 초과한 사용분부터 공제됩니다."), ("체크카드가 더 유리한가요?", "공제율이 30%로 신용카드 15%의 두 배라서, 문턱을 넘은 뒤에는 체크카드·현금영수증이 같은 금액으로 공제액이 큽니다.")],
          "연봉별 신용카드·체크카드 소득공제 문턱(총급여 25%)·한도·필요 사용액과 절세 효과를 표로 정리했습니다.")
    topic("pension", "연금저축·IRP 세액공제 — 연봉별 환급액 (900만원 한도)", "연금저축·IRP 세액공제 연봉별 환급",
          "연금저축은 연 600만원, IRP를 합치면 연 <b>900만원</b>까지 세액공제됩니다(총급여 1.2억원 초과 시 합산 600만원으로 낮아질 수 있음). 총급여 5,500만원 이하는 <b>16.5%</b>, 초과는 <b>13.2%</b>를 공제해 세금에서 바로 뺍니다.",
          ["연봉", "납입 한도", "공제율", "세액공제액", "줄어드는 세금(지방세 포함)"],
          lambda e: [mw(pension_cap(e["s"])) + "만원", pct(pension_rate(e["s"])) + "%", k(int(pension_cap(e["s"]) * pension_rate(e["s"]))) + "원", k(e["pen_eff"]) + "원"],
          [("연금저축과 IRP를 같이 넣을 수 있나요?", "네. 연금저축 연 600만원을 포함해 합산 연 900만원까지 세액공제를 받습니다."), ("세액공제율은 몇 %인가요?", "총급여 5,500만원 이하는 16.5%, 초과는 13.2%입니다.")],
          "연봉별 연금저축·IRP 납입 한도와 세액공제 환급액(16.5%·13.2%)을 정리했습니다.")
    topic("rent", "월세 세액공제 — 연봉 8천만원 이하 환급액 (월 30~70만원)", "월세 세액공제 연봉별 환급",
          "무주택 세대주가 국민주택규모 이하(또는 기준시가 4억원 이하) 주택에 월세로 살면 <b>총급여 8천만원 이하</b>일 때 연 최대 1,000만원 한도로 월세의 <b>15~17%</b>를 세액공제받습니다. 총급여 5,500만원 이하는 17%, 초과는 15%입니다.",
          ["연봉", "공제율", "월세 30만원", "월세 50만원", "월세 70만원"],
          lambda e: [("%d%%" % round(rent_rate(e["s"]) * 100)) if rent_ok(e["s"]) else "해당 없음"] + ([k(e["rent_eff"][m]) + "원" for m in (30, 50, 70)] if rent_ok(e["s"]) else ["-", "-", "-"]),
          [("월세 세액공제 요건은?", "총급여 8천만원 이하 무주택 세대주(세대원 포함 가능)이고 임대차계약서 주소지에 전입신고가 되어 있어야 합니다."), ("월세 공제 한도는?", "연 월세 지급액 1,000만원까지 인정되며 공제율은 15~17%입니다.")],
          "연봉별 월세 세액공제율과 월세 30·50·70만원일 때 줄어드는 세금을 표로 정리했습니다.")
    topic("medical", "의료비 세액공제 — 연봉별 문턱(총급여 3%)과 환급액", "의료비 세액공제 연봉별 기준",
          "의료비는 <b>총급여의 3%를 초과한 금액</b>의 15%를 세액공제합니다. 본인·65세 이상·장애인·난임시술비는 한도가 없고, 그 밖의 부양가족은 연 700만원까지입니다. 문턱을 넘지 못하면 공제받을 수 없습니다.",
          ["연봉", "3% 문턱", "의료비 300만원", "의료비 500만원", "의료비 1,000만원"],
          lambda e: [mw(e["s"] * 0.03) + "만원"] + [k(e["med_eff"][sp]) + "원" for sp in (300, 500, 1000)],
          [("의료비는 얼마부터 공제되나요?", "총급여의 3%를 넘는 금액부터 공제되며 초과분의 15%를 세액공제합니다."), ("미용·성형 비용도 공제되나요?", "미용·성형 목적 진료비와 건강기능식품 구입비 등은 공제 대상이 아닙니다.")],
          "연봉별 의료비 세액공제 문턱(총급여 3%)과 의료비 지출별 환급액을 정리했습니다.")
    return len(WRITTEN) - n0
