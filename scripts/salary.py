# -*- coding: utf-8 -*-
"""2026년 기준 연봉/월급 실수령액 계산 (4대보험 + 소득세·지방소득세 근사).

요율(근로자 부담, 2026): 국민연금 4.75%(기준소득월액 상한 6,590,000원, 2026-07~), 건강보험 3.595%,
장기요양 = 건강보험료 × 13.14%, 고용보험 0.9%.
소득세: 연말정산식(근로소득공제 → 인적공제 → 보험료공제 → 세율표 → 근로소득세액공제)을 12로 나눈 근사값.
실제 원천징수액(간이세액표)과 수십~수만 원 차이가 날 수 있다.
"""
RATES = dict(pension=0.0475, pension_cap=6_590_000, health=0.03595, ltc=0.1314, emp=0.009, local=0.10)
MEAL = 200_000   # 비과세 식대(월)

def f10(x): return int(x // 10 * 10)

def earned_income_deduction(s):
    if s <= 5_000_000: d = s * 0.70
    elif s <= 15_000_000: d = 3_500_000 + (s - 5_000_000) * 0.40
    elif s <= 45_000_000: d = 7_500_000 + (s - 15_000_000) * 0.15
    elif s <= 100_000_000: d = 12_000_000 + (s - 45_000_000) * 0.05
    else: d = 14_750_000 + (s - 100_000_000) * 0.02
    return min(d, 20_000_000)

BRACKETS = [(14_000_000, 0.06, 0), (50_000_000, 0.15, 1_260_000), (88_000_000, 0.24, 5_760_000),
            (150_000_000, 0.35, 15_440_000), (300_000_000, 0.38, 19_940_000), (500_000_000, 0.40, 25_940_000),
            (1_000_000_000, 0.42, 35_940_000), (float("inf"), 0.45, 65_940_000)]

def income_tax_base(tb):
    for lim, r, ded in BRACKETS:
        if tb <= lim: return max(0, tb * r - ded)

def earned_tax_credit(tax, s):
    c = tax * 0.55 if tax <= 1_300_000 else 715_000 + (tax - 1_300_000) * 0.30
    if s <= 33_000_000: lim = 740_000
    elif s <= 70_000_000: lim = max(660_000, 740_000 - (s - 33_000_000) * 0.008)
    else: lim = max(500_000, 660_000 - (s - 70_000_000) * 0.5)
    return min(c, lim)

def child_credit(n):
    if n <= 0: return 0
    if n == 1: return 250_000
    if n == 2: return 550_000
    return 550_000 + 400_000 * (n - 2)

def calc(annual, meal=MEAL, family=1, children=0):
    """annual: 세전 연봉(원). family: 본인 포함 공제대상 가족 수. 반환 dict(월 단위 원)."""
    pay = annual / 12
    meal = min(meal, pay)
    base = pay - meal                      # 4대보험·소득세 과세 기준 월 보수
    pension = f10(min(base, RATES["pension_cap"]) * RATES["pension"])
    health = f10(base * RATES["health"])
    ltc = f10(health * RATES["ltc"])
    emp = f10(base * RATES["emp"])
    s = base * 12
    ins_year = (pension + health + ltc + emp) * 12
    tb = max(0, s - earned_income_deduction(s) - 1_500_000 * family - pension * 12 - (health + ltc + emp) * 12)
    tax = income_tax_base(tb)
    tax = max(0, tax - earned_tax_credit(tax, s) - child_credit(children))
    income_tax = f10(tax / 12)
    local_tax = f10(income_tax * RATES["local"])
    ded = pension + health + ltc + emp + income_tax + local_tax
    return dict(annual=annual, pay=round(pay), meal=meal, pension=pension, health=health, ltc=ltc, emp=emp,
                income_tax=income_tax, local_tax=local_tax, deduction=ded, net=round(pay) - ded,
                insurance=pension + health + ltc + emp, net_year=(round(pay) - ded) * 12,
                rate=ded / pay if pay else 0)

def from_monthly(monthly, **kw):
    return calc(monthly * 12, **kw)

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for a in (24_000_000, 30_000_000, 40_000_000, 50_000_000, 60_000_000, 80_000_000, 100_000_000, 150_000_000):
        r = calc(a)
        print(a // 10000, r["net"], r["pension"], r["health"], r["ltc"], r["emp"], r["income_tax"], r["local_tax"], "%.1f%%" % (r["rate"] * 100))
