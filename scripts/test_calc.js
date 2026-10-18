// calc.js(브라우저 계산기)와 salary.py 결과 대조용 덤프: node scripts/test_calc.js → scripts/_calc_js.json
const fs = require('fs'), path = require('path');
const YB = require(path.join(__dirname, '..', 'assets', 'js', 'calc.js'));
const out = [];
for (let man = 1200; man <= 40000; man += 370) {
  for (const fam of [1, 3]) for (const kids of [0, 2]) for (const meal of [0, 200000]) {
    const r = YB.calc(man * 10000, meal, fam, kids);
    out.push([man, fam, kids, meal, r.net, r.it, r.pension]);
  }
}
fs.writeFileSync(path.join(__dirname, '_calc_js.json'), JSON.stringify(out));
console.log('cases', out.length);
