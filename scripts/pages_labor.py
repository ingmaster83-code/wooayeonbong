# -*- coding: utf-8 -*-
"""우아연봉 확장: 퇴직금(+퇴직소득세)·실업급여(구직급여)·주휴수당·최저임금 페이지. build_site.main() 에서 호출."""
from common import *
import salary as S

MW = {2026: 10_320, 2027: 10_700}      # 최저임금(시급)
MW_MONTH = {2026: 2_156_880, 2027: 2_236_300}
DAYS3M = 91.25                          # 퇴직 전 3개월 평균 일수 가정(365/4)

def table(heads, rows, num_cols=()):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i in num_cols else "", h) for i, h in enumerate(heads))
    body = "".join("<tr>%s</tr>" % "".join('<td%s>%s</td>' % (' class="num"' if i in num_cols else "", v) for i, v in enumerate(r)) for r in rows)
    return '<div class="tbl-wrap"><table class="tbl"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, body)

def chips(items): return '<div class="chips">%s</div>' % "".join('<a class="chip" href="%s">%s</a>' % (u, esc(t)) for t, u in items)
def k(x): return "{:,}".format(x)

# ───────────────────────── 퇴직금 ─────────────────────────
def severance_pay(monthly, years):
    """월 평균임금 → 퇴직금. 1일 평균임금 = 월×3/91.25, 퇴직금 = 1일평균임금 × 30 × 근속일(=연×365)/365"""
    return monthly * 3 / DAYS3M * 30 * years

def service_deduction(y):
    if y <= 5: return 1_000_000 * y
    if y <= 10: return 5_000_000 + 2_000_000 * (y - 5)
    if y <= 20: return 15_000_000 + 2_500_000 * (y - 10)
    return 40_000_000 + 3_000_000 * (y - 20)

def converted_deduction(c):
    if c <= 8_000_000: return c
    if c <= 70_000_000: return 8_000_000 + (c - 8_000_000) * 0.60
    if c <= 100_000_000: return 45_200_000 + (c - 70_000_000) * 0.55
    if c <= 300_000_000: return 61_700_000 + (c - 100_000_000) * 0.45
    return 151_700_000 + (c - 300_000_000) * 0.35

def severance_tax(pay, years):
    """퇴직소득세(지방소득세 별도). 연분연승법. 반환 (소득세, 지방소득세)"""
    base = pay - service_deduction(years)
    if base <= 0: return 0, 0
    conv = base * 12 / years
    tb = max(0, conv - converted_deduction(conv))
    tax = S.income_tax_base(tb) * years / 12
    it = int(tax // 10 * 10)
    return it, int(it * 0.1 // 10 * 10)

SEV_STEPS = sorted(set(list(range(150, 1001, 10)) + list(range(1050, 2001, 50))))
SEV_YEARS = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30]

def sev_row(m_man, y):
    pay = round(severance_pay(m_man * 10000, y))
    it, lt = severance_tax(pay, y)
    return pay, it + lt, pay - it - lt

def page_severance(m):
    path = "/severance/%d/" % m
    rows = []
    for y in SEV_YEARS:
        pay, tax, net = sev_row(m, y)
        rows.append(['<a href="/severance/years/%d/">근속 %d년</a>' % (y, y), won(pay) + "원", won(tax) + "원", won(net) + "원"])
    t = table(["근속기간", "퇴직금(세전)", "퇴직소득세(지방세 포함)", "세후 퇴직금"], rows, (1, 2, 3))
    p3, t3, n3 = sev_row(m, 3); p5, t5, n5 = sev_row(m, 5); p10, t10, n10 = sev_row(m, 10)
    near = [v for v in SEV_STEPS if abs(v - m) <= 50][:9]
    nb = table(["월 평균임금", "3년", "5년", "10년"], [[('<a href="/severance/%d/">%s만원</a>' % (v, k(v))) if v != m else "<b>%s만원</b>" % k(v)] + [won(sev_row(v, y)[0]) + "원" for y in (3, 5, 10)] for v in near], (1, 2, 3))
    kk = k(m)
    lead = ("<p class=\"lead\"><b>월 평균임금 %s만원</b>인 직원의 퇴직금은 근속 3년 약 <b>%s원</b>, 5년 약 <b>%s원</b>, 10년 약 <b>%s원</b>입니다(세전). 10년 근속이면 퇴직소득세와 지방소득세로 약 %s원이 빠져 세후 약 %s원을 받습니다. "
            "계산은 1일 평균임금(월 평균임금×3÷91.25일)의 30일분에 근속연수를 곱하는 법정 방식이며, 상여금·연차수당이 평균임금에 들어가면 더 늘어납니다.</p>") % (kk, won(p3), won(p5), won(p10), won(t10), won(n10))
    body = """
<div class="page-head"><h1>월급 %(kk)s만원 퇴직금 — 근속 3년·5년·10년 (2026)</h1><p>근속기간별 퇴직금과 퇴직소득세 · 세후 수령액</p></div>
%(lead)s
%(ad)s
<h2 class="group-title">💼 근속기간별 퇴직금</h2>
%(t)s
<p class="note">퇴직금은 계속 근로기간 1년 이상, 주 15시간 이상 근무한 근로자에게 지급됩니다. 퇴직소득세는 연분연승법(근속연수공제·환산급여공제)으로 계산한 근사값이며, 퇴직연금(IRP)으로 받으면 세금이 이연됩니다.</p>
<h2 class="group-title">📈 비슷한 월급의 퇴직금</h2>
%(nb)s
%(ch)s
<div class="note-box">월급은 퇴직 전 3개월 평균임금(세전, 상여·수당 포함)을 가정합니다. 실제 퇴직금은 평균임금에 포함되는 항목과 재직일수에 따라 달라지며, 법정 퇴직금보다 많이 주는 회사도 있습니다.</div>
""" % dict(kk=kk, lead=lead, ad=ad(), t=t, nb=nb, ch=chips([("퇴직금 계산 표", "/severance/"), ("실수령액 계산기", "/calculator/"), ("실업급여", "/unemployment/")]))
    faq = [("월급 %s만원이면 퇴직금은 얼마인가요?" % kk, "근속 1년이면 약 %s원, 3년이면 약 %s원, 5년이면 약 %s원, 10년이면 약 %s원입니다(세전)." % (won(sev_row(m, 1)[0]), won(p3), won(p5), won(p10))),
           ("퇴직금에도 세금이 붙나요?", "네. 퇴직소득세와 지방소득세가 붙습니다. 근속이 길수록 공제가 커 세율이 낮고, 월급 %s만원 10년 근속이면 세금은 퇴직금의 약 %.1f%%입니다." % (kk, t10 / p10 * 100)),
           ("1년 미만 근무하면 퇴직금이 없나요?", "계속 근로기간이 1년 미만이거나 주 평균 15시간 미만이면 법정 퇴직금 대상이 아닙니다.")]
    write(path, layout(path, "월급 %s만원 퇴직금 — 근속 5년 %s원, 10년 %s원 (2026)" % (kk, won(p5), won(p10)),
        "월 평균임금 %s만원의 퇴직금. 근속 3년 %s원, 5년 %s원, 10년 %s원과 퇴직소득세·세후 수령액을 근속기간별로 계산했습니다." % (kk, won(p3), won(p5), won(p10)),
        body, faq, [("홈", "/"), ("퇴직금", "/severance/"), ("월급 %s만원" % kk, path)]), "0.6")

def page_severance_years(y):
    path = "/severance/years/%d/" % y
    ms = [150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 1000, 1500, 2000]
    rows = []
    for m in ms:
        pay, tax, net = sev_row(m, y)
        rows.append(['<a href="/severance/%d/">%s만원</a>' % (m, k(m)) if m in SEV_STEPS else "%s만원" % k(m), won(pay) + "원", won(tax) + "원", won(net) + "원"])
    t = table(["월 평균임금", "퇴직금(세전)", "퇴직소득세(지방세 포함)", "세후 퇴직금"], rows, (1, 2, 3))
    p300, t300, n300 = sev_row(300, y)
    sd = service_deduction(y)
    lead = ("<p class=\"lead\"><b>근속 %d년</b>이면 퇴직금은 월 평균임금의 약 %.2f배입니다. 월 평균임금 300만원이면 약 <b>%s원</b>(세후 약 %s원)이고, 500만원이면 약 %s원입니다. 근속연수공제는 %s원이 적용됩니다.</p>") % (
        y, severance_pay(1, y), won(p300), won(n300), won(sev_row(500, y)[0]), won(sd))
    body = """
<div class="page-head"><h1>근속 %(y)d년 퇴직금 — 월급별 계산 (2026)</h1><p>월 평균임금별 퇴직금과 퇴직소득세</p></div>
%(lead)s
%(ad)s
%(t)s
%(ch)s
<div class="note-box">퇴직금 = 1일 평균임금(월 평균임금×3÷91.25) × 30일 × 근속연수. 퇴직소득세는 연분연승법 근사값입니다.</div>
""" % dict(y=y, lead=lead, ad=ad(), t=t, ch=chips([("%d년" % yy, "/severance/years/%d/" % yy) for yy in (1, 2, 3, 5, 7, 10, 15, 20, 25, 30) if yy != y] + [("퇴직금 표", "/severance/")]))
    faq = [("근속 %d년 퇴직금은 얼마인가요?" % y, "월 평균임금의 약 %.2f배입니다. 월급 300만원이면 약 %s원입니다." % (severance_pay(1, y), won(p300))),
           ("근속 %d년 퇴직소득세는 얼마인가요?" % y, "월 평균임금 300만원 기준 약 %s원(지방소득세 포함)입니다." % won(t300))]
    write(path, layout(path, "근속 %d년 퇴직금 — 월급 300만원이면 %s원 (2026)" % (y, won(p300)),
        "근속 %d년 퇴직금을 월 평균임금별로 계산했습니다. 월급 300만원 %s원, 500만원 %s원, 세후 금액과 퇴직소득세 포함." % (y, won(p300), won(sev_row(500, y)[0])),
        body, faq, [("홈", "/"), ("퇴직금", "/severance/"), ("근속 %d년" % y, path)]), "0.6")

def page_severance_hub():
    rows = []
    for m in SEV_STEPS:
        if m > 1000 and m % 100: continue
        if m < 1000 and m % 50: continue
        rows.append(['<a href="/severance/%d/">%s만원</a>' % (m, k(m))] + [won(sev_row(m, y)[0]) + "원" for y in (1, 3, 5, 10)])
    t = table(["월 평균임금", "1년", "3년", "5년", "10년"], rows, (1, 2, 3, 4))
    body = """
<div class="page-head"><h1>퇴직금 계산 — 월급·근속기간별 표 (2026)</h1><p>퇴직금 산식 · 퇴직소득세 · 지급 기준</p></div>
<p class="lead"><b>퇴직금</b>은 계속 근로기간 1년 이상, 주 평균 15시간 이상 일한 근로자에게 <b>1일 평균임금의 30일분 × 근속연수</b>로 지급합니다. 1일 평균임금은 퇴직 전 3개월 임금 총액을 그 기간의 일수로 나눈 값이고, 월급이 일정하면 월 평균임금 × 3 ÷ 91일 안팎입니다. 결과적으로 월 평균임금에 근속연수를 곱한 값의 약 98.6%%입니다. 월급을 눌러 근속기간별 퇴직금과 퇴직소득세를 확인하세요.</p>
%(ad)s
%(t)s
%(ch)s
""" % dict(ad=ad(), t=t, ch=chips([("근속 %d년" % y, "/severance/years/%d/" % y) for y in SEV_YEARS]))
    faq = [("퇴직금 계산식은 무엇인가요?", "퇴직금 = 1일 평균임금 × 30일 × (재직일수 ÷ 365). 1일 평균임금은 퇴직 전 3개월 임금 총액 ÷ 그 기간 일수입니다."),
           ("퇴직금은 언제까지 받아야 하나요?", "퇴직한 날부터 14일 이내에 지급해야 하며 당사자 합의로 연장할 수 있습니다."),
           ("퇴직연금(DC·IRP)이면 어떻게 다른가요?", "DC형은 회사가 매년 연봉의 1/12 이상을 계좌에 넣어 운용하고, 퇴직급여는 계좌 잔액입니다. 이 표는 확정급여(DB)·법정 퇴직금 기준 근사치입니다.")]
    write("/severance/", layout("/severance/", "퇴직금 계산 — 월급·근속기간별 표 (2026)", "월 평균임금과 근속기간별 퇴직금 표와 퇴직소득세 계산. 월급 300만원 근속 5년 퇴직금은 얼마인지 바로 확인하세요.",
        body, faq, [("홈", "/"), ("퇴직금", "/severance/")], coupang=True), "0.9")

# ───────────────────────── 실업급여(구직급여) ─────────────────────────
UI_MIN = round(MW[2026] * 0.8 * 8)    # 66,048
UI_MAX = 68_100
UI_DAYS = [("under-1y", "1년 미만", 120, 120), ("1-3y", "1년 이상 3년 미만", 150, 180), ("3-5y", "3년 이상 5년 미만", 180, 210),
           ("5-10y", "5년 이상 10년 미만", 210, 240), ("10y-plus", "10년 이상", 240, 270)]

def page_unemp(age, slug, label, d_u50, d_o50):
    days = d_u50 if age == "under50" else d_o50
    agel = "50세 미만" if age == "under50" else "50세 이상(장애인 포함)"
    path = "/unemployment/%s/%s/" % (age, slug)
    lo, hi = UI_MIN * days, UI_MAX * days
    other = "over50" if age == "under50" else "under50"
    od = d_o50 if age == "under50" else d_u50
    body = """
<div class="page-head"><h1>실업급여 %(al)s·가입기간 %(lb)s — %(d)d일, 총 %(lo)s~%(hi)s원</h1><p>2026년 구직급여 · 소정급여일수와 총 수령액</p></div>
<p class="lead">%(al)s이면서 고용보험 가입기간이 <b>%(lb)s</b>이면 실업급여(구직급여)를 받을 수 있는 기간(소정급여일수)은 <b>%(d)d일</b>입니다. 2026년 1일 구직급여는 하한 %(mn)s원~상한 %(mx)s원이라 총 수령액은 약 <b>%(lo)s~%(hi)s원</b>이고, 월 환산(30일)으로 약 %(m1)s~%(m2)s원입니다. 같은 가입기간에 %(ol)s이면 %(od)d일입니다.</p>
%(ad)s
<h2 class="group-title">📋 조건별 소정급여일수와 총액</h2>
%(t)s
<div class="note-box">2026년에는 최저임금 인상으로 하한액(최저임금의 80%%×8시간 = %(mn)s원)이 높아져 대부분의 수급자가 하한~상한(%(mx)s원) 사이의 금액을 받습니다. 1일 구직급여 = 퇴직 전 평균임금의 60%%(하한·상한 적용). 상한액·산정 방식은 2027년 개편이 논의되고 있어 고용노동부 공지를 확인하세요.</div>
%(ch)s
""" % dict(al=agel, lb=label, d=days, lo=won(lo), hi=won(hi), mn=won(UI_MIN), mx=won(UI_MAX), m1=won(UI_MIN * 30), m2=won(UI_MAX * 30), ol="50세 이상" if age == "under50" else "50세 미만", od=od, ad=ad(),
           t=unemp_table(), ch=chips([("실업급여 전체", "/unemployment/"), ("퇴직금", "/severance/"), ("연봉 실수령액", "/salary/")]))
    faq = [("%s 가입기간 %s이면 실업급여는 며칠 받나요?" % (agel, label), "%d일입니다. 이직 후 구직급여를 받을 수 있는 소정급여일수는 연령과 고용보험 가입기간에 따라 120~270일입니다." % days),
           ("1일 실업급여는 얼마인가요?", "2026년 기준 하한 %s원, 상한 %s원이며 평균임금의 60%%를 이 범위로 보정합니다." % (won(UI_MIN), won(UI_MAX))),
           ("실업급여를 받으려면 어떤 조건이 필요한가요?", "이직 전 18개월 중 피보험단위기간이 180일 이상이고, 회사 사정 등 비자발적 사유로 이직했으며, 근로 의사와 능력이 있어 적극적으로 재취업 활동을 해야 합니다.")]
    write(path, layout(path, "실업급여 %s 가입 %s — %d일 총 %s~%s원 (2026)" % (agel, label, days, won(lo), won(hi)),
        "%s·고용보험 가입기간 %s 실업급여는 %d일, 총 %s~%s원(2026년 구직급여 하한 %s원~상한 %s원 기준)." % (agel, label, days, won(lo), won(hi), won(UI_MIN), won(UI_MAX)),
        body, faq, [("홈", "/"), ("실업급여", "/unemployment/"), ("%s %s" % (agel, label), path)]), "0.6")

def unemp_table():
    rows = []
    for slug, label, d1, d2 in UI_DAYS:
        rows.append(['<a href="/unemployment/under50/%s/">%s</a>' % (slug, label), "%d일 (%s~%s원)" % (d1, won(UI_MIN * d1), won(UI_MAX * d1)), '<a href="/unemployment/over50/%s/">%d일 (%s~%s원)</a>' % (slug, d2, won(UI_MIN * d2), won(UI_MAX * d2))])
    return table(["고용보험 가입기간", "50세 미만", "50세 이상·장애인"], rows)

def page_unemp_hub():
    hrows = []
    for h in (8, 7, 6, 5, 4):
        mn = round(MW[2026] * 0.8 * h)
        hrows.append(["%d시간" % h, won(mn) + "원", won(mn * 30) + "원"])
    body = """
<div class="page-head"><h1>실업급여(구직급여) 2026 — 금액·기간·조건 총정리</h1><p>하한 %(mn)s원 · 상한 %(mx)s원 · 소정급여일수 120~270일</p></div>
<p class="lead"><b>실업급여(구직급여)</b>는 회사 사정 등으로 비자발적으로 일을 그만둔 고용보험 가입자가 재취업할 때까지 받는 급여입니다. 1일 금액은 퇴직 전 평균임금의 60%%이고 2026년에는 <b>하한 %(mn)s원, 상한 %(mx)s원</b>입니다. 최저임금 인상으로 하한액이 이전 상한액(66,000원)을 넘어서 상한을 올렸고, 그 결과 월급 수준과 상관없이 하루 %(mn)s~%(mx)s원, 월 환산 약 %(m1)s~%(m2)s원을 받게 됩니다. 받을 수 있는 기간은 나이와 가입기간에 따라 다릅니다.</p>
%(ad)s
<h2 class="group-title">📅 가입기간·연령별 소정급여일수와 총액</h2>
%(t)s
<h2 class="group-title">⏰ 1일 소정근로시간이 짧으면 하한액이 달라요</h2>
%(ht)s
<h2 class="group-title">✅ 받으려면</h2>
<p class="lead">① 이직일 이전 18개월 중 피보험단위기간 180일 이상 ② 비자발적 이직(권고사직·계약만료·폐업 등. 자발적 퇴사도 임금체불·괴롭힘 등 정당한 사유가 있으면 가능) ③ 근로 의사와 능력이 있으나 취업하지 못한 상태 ④ 적극적인 재취업 활동. 신청은 이직 후 고용센터에서 수급자격 인정을 받고 실업 인정을 정기적으로 받아야 합니다.</p>
<div class="note-box">금액과 기준은 고용노동부 발표를 토대로 한 참고 정보이며 2027년에 상한 연동·지급 기준 개편이 논의되고 있습니다. 실제 수급액은 고용센터에서 확정됩니다.</div>
""" % dict(mn=won(UI_MIN), mx=won(UI_MAX), m1=won(UI_MIN * 30), m2=won(UI_MAX * 30), ad=ad(), t=unemp_table(),
           ht=table(["1일 소정근로시간", "하한액(최저임금 80%)", "월 환산(30일)"], hrows, (1, 2)))
    faq = [("2026년 실업급여 하한액은 얼마인가요?", "최저임금 10,320원의 80%%×8시간으로 하루 %s원, 월 환산 약 %s원입니다." % (won(UI_MIN), won(UI_MIN * 30))),
           ("2026년 실업급여 상한액은 얼마인가요?", "하루 %s원입니다. 하한액이 이전 상한(66,000원)을 넘어서면서 2026년에 상한이 인상됐습니다." % won(UI_MAX)),
           ("실업급여는 세금을 내나요?", "구직급여는 소득세가 없는 비과세 소득입니다.")]
    write("/unemployment/", layout("/unemployment/", "실업급여(구직급여) 2026 금액·기간·조건 — 하한 66,048원 상한 68,100원", "2026년 실업급여 하한·상한액, 가입기간·연령별 소정급여일수와 총 수령액, 신청 조건을 정리했습니다.",
        body, faq, [("홈", "/"), ("실업급여", "/unemployment/")], coupang=True), "0.9")

# ───────────────────────── 주휴수당·최저임금 ─────────────────────────
HOURS = [15, 20, 25, 30, 35, 40]
WAGE_STEPS = [10_320, 10_700] + list(range(10_400, 20_001, 100)) + list(range(20_500, 30_001, 500))

def month_hours(h):  # 주 h시간 + 주휴 → 월 환산 시간
    return round((h + h / 40 * 8) * 365 / 7 / 12) if h < 40 else 209

def weekly(wage, h):
    hol = round(wage * min(h, 40) / 40 * 8)
    return hol, wage * h + hol, wage * month_hours(h)

def page_weekly(w):
    path = "/weekly-holiday/%d/" % w
    rows = []
    for h in HOURS:
        hol, wk, mo = weekly(w, h)
        rows.append(["주 %d시간" % h, won(hol) + "원", won(wk) + "원", won(mo) + "원", "%d시간" % month_hours(h)])
    t = table(["근무시간", "주휴수당(주)", "주급(주휴 포함)", "월급(세전)", "월 환산시간"], rows, (1, 2, 3, 4))
    hol40, wk40, mo40 = weekly(w, 40)
    hol20, wk20, mo20 = weekly(w, 20)
    r = S.calc(mo40 * 12, meal=0)
    mw_note = ""
    if w in (10_320, 10_700):
        mw_note = "<p class=\"lead\">%s원은 %d년 적용 최저임금입니다.</p>" % (k(w), 2026 if w == 10_320 else 2027)
    elif w < MW[2027]:
        mw_note = "<p class=\"lead\">2027년 최저임금(%s원)보다 낮은 시급입니다. 최저임금 미만으로는 계약할 수 없습니다.</p>" % won(MW[2027])
    body = """
<div class="page-head"><h1>시급 %(w)s원 주휴수당·월급 — 주 15~40시간 (세전)</h1><p>주휴수당 · 주급 · 월 환산 · 4대보험 후 실수령</p></div>
<p class="lead"><b>시급 %(w)s원</b>으로 주 40시간(하루 8시간×5일) 일하면 주휴수당은 주당 <b>%(h40)s원</b>, 월급은 월 209시간 기준 <b>%(m40)s원</b>(세전)입니다. 주 20시간이면 주휴수당 %(h20)s원, 월급 %(m20)s원입니다. 주 40시간 월급에서 4대보험과 세금을 빼면 월 실수령액은 약 %(net)s원입니다(식대 비과세 없음, 본인만 공제).</p>
%(mw)s
%(ad)s
<h2 class="group-title">⏱️ 근무시간별 주휴수당과 월급</h2>
%(t)s
<p class="note">주휴수당은 1주 소정근로시간이 15시간 이상이고 소정 근로일을 개근했을 때 하루분 임금을 더 주는 제도입니다. 주 40시간 이하는 시급 × (주 근로시간 ÷ 40 × 8시간), 주 40시간 이상은 시급×8시간입니다. 월 환산시간은 (주 근로 + 주휴시간)×365÷7÷12입니다.</p>
%(ch)s
""" % dict(w=k(w), h40=won(hol40), m40=won(mo40), h20=won(hol20), m20=won(mo20), net=won(r["net"]), mw=mw_note, ad=ad(), t=t,
           ch=chips([("최저임금", "/minimum-wage/"), ("주휴수당 전체", "/weekly-holiday/"), ("월급 %s만원 실수령액" % k(nearest_m(mo40 / 10000)), "/monthly/%d/" % nearest_m(mo40 / 10000)), ("연봉 실수령액", "/salary/")]))
    faq = [("시급 %s원 주휴수당은 얼마인가요?" % k(w), "주 40시간 근무 시 주당 %s원, 주 20시간 근무 시 주당 %s원입니다." % (won(hol40), won(hol20))),
           ("시급 %s원이면 월급은 얼마인가요?" % k(w), "주 40시간 기준 월 209시간으로 %s원(세전)입니다. 주휴수당이 이미 포함된 금액입니다." % won(mo40)),
           ("주 15시간 미만이면 주휴수당이 없나요?", "네. 1주 소정근로시간이 15시간 미만이면 주휴수당 지급 대상이 아닙니다(초단시간 근로자).")]
    write(path, layout(path, "시급 %s원 주휴수당·월급 — 주 40시간 월 %s원 (세전)" % (k(w), won(mo40)),
        "시급 %s원의 주휴수당과 월급. 주 40시간 월 %s원, 주 20시간 월 %s원(세전)과 4대보험 후 실수령액." % (k(w), won(mo40), won(mo20)),
        body, faq, [("홈", "/"), ("주휴수당", "/weekly-holiday/"), ("시급 %s원" % k(w), path)]), "0.6")

def nearest_m(v):
    steps = [x for x in range(150, 1001, 10)]
    return min(steps, key=lambda s: abs(s - v))

def page_weekly_hub():
    rows = []
    for w in WAGE_STEPS:
        if w > 20_000 or w % 500 == 0 or w in (10_320, 10_700):
            hol, wk, mo = weekly(w, 40)
            rows.append(['<a href="/weekly-holiday/%d/">%s원</a>' % (w, k(w)), won(hol) + "원", won(mo) + "원", won(weekly(w, 20)[2]) + "원"])
    t = table(["시급", "주휴수당(주 40시간)", "월급(주 40시간)", "월급(주 20시간)"], rows, (1, 2, 3))
    body = """
<div class="page-head"><h1>주휴수당 계산 — 시급별 월급 표 (2026·2027)</h1><p>주 15~40시간 · 최저임금 · 월 209시간 환산</p></div>
<p class="lead"><b>주휴수당</b>은 주 15시간 이상 일하고 개근한 근로자에게 하루치 임금(주 40시간이면 8시간분)을 더 주는 수당입니다. 시급 10,320원(2026년 최저임금)으로 주 40시간 일하면 주휴수당은 주 %(h)s원이고 월급은 %(m)s원입니다. 2027년 최저임금은 10,700원으로 월 환산액이 %(m2)s원입니다. 시급을 눌러 근무시간별 계산을 확인하세요.</p>
%(ad)s
%(t)s
%(ch)s
""" % dict(h=won(weekly(10_320, 40)[0]), m=won(MW_MONTH[2026]), m2=won(MW_MONTH[2027]), ad=ad(), t=t, ch=chips([("최저임금", "/minimum-wage/"), ("연봉 실수령액", "/salary/")]))
    faq = [("주휴수당 계산식은?", "1주 소정근로시간이 40시간 이하일 때 시급 × (주 근로시간 ÷ 40) × 8시간입니다. 40시간 이상이면 시급 × 8시간입니다."),
           ("월 209시간은 어떻게 나오나요?", "주 40시간 근무에 주휴 8시간을 더한 48시간에 365÷7÷12를 곱한 약 208.6시간을 209시간으로 올림한 값입니다.")]
    write("/weekly-holiday/", layout("/weekly-holiday/", "주휴수당 계산 — 시급별 월급 표 (2026·2027)", "시급별 주휴수당과 월급 표. 최저임금 10,320원(2026)·10,700원(2027) 주 40시간 월급과 근무시간별 계산.",
        body, faq, [("홈", "/"), ("주휴수당", "/weekly-holiday/")], coupang=True), "0.9")

def page_minwage():
    rows = []
    for y in (2026, 2027):
        w = MW[y]
        r = S.calc(MW_MONTH[y] * 12, meal=0)
        rows.append(["%d년" % y, won(w) + "원", won(weekly(w, 40)[0]) + "원", won(MW_MONTH[y]) + "원", won(MW_MONTH[y] * 12) + "원", won(r["net"]) + "원"])
    t = table(["적용 연도", "시급", "주휴수당(주 40h)", "월 환산액", "연 환산액", "월 실수령(근사)"], rows, (1, 2, 3, 4, 5))
    body = """
<div class="page-head"><h1>최저임금 2026·2027 — 시급·월급·연봉 환산</h1><p>2026년 10,320원 · 2027년 10,700원(3.7%% 인상)</p></div>
<p class="lead">2026년 최저임금은 시간당 <b>10,320원</b>(월 209시간 환산 %(m26)s원), 2027년은 <b>10,700원</b>(월 %(m27)s원)입니다. 월 환산액은 주 40시간 근무에 주휴수당을 포함한 금액이며 세전입니다. 실수령액은 4대보험과 소득세를 제하면 2026년 기준 약 %(n26)s원입니다.</p>
%(ad)s
%(t)s
<div class="chips"><a class="chip" href="/weekly-holiday/10320/">시급 10,320원 상세</a><a class="chip" href="/weekly-holiday/10700/">시급 10,700원 상세</a><a class="chip" href="/weekly-holiday/">주휴수당 표</a><a class="chip" href="/monthly/220/">월급 220만원 실수령액</a><a class="chip" href="/unemployment/">실업급여 하한액</a></div>
<div class="note-box">최저임금은 매년 1월 1일부터 12월 31일까지 적용됩니다. 월 환산액과 실수령액은 주 40시간·월 209시간 기준 근사값입니다.</div>
""" % dict(m26=won(MW_MONTH[2026]), m27=won(MW_MONTH[2027]), n26=won(S.calc(MW_MONTH[2026] * 12, meal=0)["net"]), ad=ad(), t=t)
    faq = [("2026년 최저임금은 얼마인가요?", "시간당 10,320원이며 주 40시간(월 209시간) 기준 월 환산액은 2,156,880원입니다."),
           ("2027년 최저임금은 얼마인가요?", "시간당 10,700원으로 2026년보다 380원(3.7%) 올랐고 월 환산액은 2,236,300원입니다.")]
    write("/minimum-wage/", layout("/minimum-wage/", "최저임금 2026·2027 — 시급 10,320원·10,700원, 월급 환산", "2026년 최저임금 10,320원(월 2,156,880원)과 2027년 10,700원(월 2,236,300원) 환산 월급·연봉·실수령액과 주휴수당.",
        body, faq, [("홈", "/"), ("최저임금", "/minimum-wage/")], coupang=True), "0.9")

def all_pages():
    n0 = len(WRITTEN)
    for m in SEV_STEPS: page_severance(m)
    for y in range(1, 31): page_severance_years(y)
    page_severance_hub()
    for age in ("under50", "over50"):
        for slug, label, d1, d2 in UI_DAYS: page_unemp(age, slug, label, d1, d2)
    page_unemp_hub()
    for w in WAGE_STEPS: page_weekly(w)
    page_weekly_hub(); page_minwage()
    return len(WRITTEN) - n0
