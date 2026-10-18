# -*- coding: utf-8 -*-
import json, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import salary as S
rows = json.load(open(here / "_calc_js.json", encoding="utf-8"))
bad = 0
for man, fam, kids, meal, net, it, pen in rows:
    r = S.calc(man * 10000, meal=meal, family=fam, children=kids)
    if (r["net"], r["income_tax"], r["pension"]) != (net, it, pen):
        bad += 1
        if bad < 5: print("불일치", man, fam, kids, meal, (r["net"], r["income_tax"], r["pension"]), (net, it, pen))
print("py vs js 불일치", bad, "/", len(rows))
