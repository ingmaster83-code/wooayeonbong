/* 연봉/월급 실수령액 계산기 — scripts/salary.py 와 같은 식 (2026년 요율) */
var YB = (function () {
  var RATES = { pension: 0.0475, cap: 6590000, health: 0.03595, ltc: 0.1314, emp: 0.009, local: 0.10 };
  function f10(x) { return Math.floor(x / 10) * 10; }
  function eid(s) {
    var d;
    if (s <= 5000000) d = s * 0.70;
    else if (s <= 15000000) d = 3500000 + (s - 5000000) * 0.40;
    else if (s <= 45000000) d = 7500000 + (s - 15000000) * 0.15;
    else if (s <= 100000000) d = 12000000 + (s - 45000000) * 0.05;
    else d = 14750000 + (s - 100000000) * 0.02;
    return Math.min(d, 20000000);
  }
  var BR = [[14000000, 0.06, 0], [50000000, 0.15, 1260000], [88000000, 0.24, 5760000], [150000000, 0.35, 15440000],
    [300000000, 0.38, 19940000], [500000000, 0.40, 25940000], [1000000000, 0.42, 35940000], [Infinity, 0.45, 65940000]];
  function taxBase(tb) { for (var i = 0; i < BR.length; i++) if (tb <= BR[i][0]) return Math.max(0, tb * BR[i][1] - BR[i][2]); }
  function credit(tax, s) {
    var c = tax <= 1300000 ? tax * 0.55 : 715000 + (tax - 1300000) * 0.30, lim;
    if (s <= 33000000) lim = 740000;
    else if (s <= 70000000) lim = Math.max(660000, 740000 - (s - 33000000) * 0.008);
    else lim = Math.max(500000, 660000 - (s - 70000000) * 0.5);
    return Math.min(c, lim);
  }
  function child(n) { return n <= 0 ? 0 : n === 1 ? 250000 : n === 2 ? 550000 : 550000 + 400000 * (n - 2); }
  function calc(annual, meal, family, kids) {
    var pay = annual / 12;
    meal = Math.min(meal, pay);
    var base = pay - meal;
    var pension = f10(Math.min(base, RATES.cap) * RATES.pension);
    var health = f10(base * RATES.health), ltc = f10(health * RATES.ltc), emp = f10(base * RATES.emp);
    var s = base * 12;
    var tb = Math.max(0, s - eid(s) - 1500000 * family - pension * 12 - (health + ltc + emp) * 12);
    var tax = taxBase(tb);
    tax = Math.max(0, tax - credit(tax, s) - child(kids));
    var it = f10(tax / 12), lt = f10(it * RATES.local);
    var ded = pension + health + ltc + emp + it + lt;
    var p = Math.round(pay);
    return { pay: p, meal: meal, pension: pension, health: health, ltc: ltc, emp: emp, it: it, lt: lt, ded: ded, net: p - ded, rate: pay ? ded / pay : 0 };
  }
  return { calc: calc };
})();

(function () {
  if (typeof document === 'undefined' || !document.getElementById('c-go')) return;
  function w(x) { return Math.round(x).toLocaleString('ko-KR'); }
  document.getElementById('c-go').onclick = function () {
    var mode = document.getElementById('c-mode').value;
    var amt = +document.getElementById('c-amt').value * 10000;
    var meal = +document.getElementById('c-meal').value || 0;
    var fam = +document.getElementById('c-fam').value, kids = +document.getElementById('c-kid').value;
    var out = document.getElementById('c-out');
    if (!(amt > 0)) { out.textContent = '금액을 입력해 주세요.'; return; }
    var annual = mode === 'm' ? amt * 12 : amt;
    var r = YB.calc(annual, meal, fam, kids);
    out.innerHTML = '<b>월 실수령액 약 ' + w(r.net) + '원</b> (연 ' + w(r.net * 12) + '원)<br>' +
      '세전 월급 ' + w(r.pay) + '원 − 공제 ' + w(r.ded) + '원 (' + (r.rate * 100).toFixed(1) + '%)<br>' +
      '국민연금 ' + w(r.pension) + ' · 건강보험 ' + w(r.health) + ' · 장기요양 ' + w(r.ltc) + ' · 고용보험 ' + w(r.emp) +
      ' · 소득세 ' + w(r.it) + ' · 지방소득세 ' + w(r.lt) + ' (원)';
  };
})();
if (typeof module !== 'undefined') module.exports = YB;
