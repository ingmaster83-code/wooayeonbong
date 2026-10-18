# -*- coding: utf-8 -*-
import sys, collections, pathlib
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
f = sorted((pathlib.Path(__file__).resolve().parent.parent / "data" / "raw").glob("*.csv"))[-1]
for enc in ("cp949", "utf-8-sig"):
    try:
        df = pd.read_csv(f, encoding=enc, dtype=str); break
    except Exception as e:
        print(enc, e)
print(f.name, df.shape)
print(df.columns.tolist())
print(df.head(5).to_string())
for c in df.columns:
    print(c, df[c].nunique(), df[c].isna().mean().round(3))
df["n"] = pd.to_numeric(df.iloc[:, df.columns.get_loc([c for c in df.columns if "가입자수" in c][0])], errors="coerce")
print(df["n"].describe())
print((df["n"] >= 10).sum(), (df["n"] >= 50).sum(), (df["n"] >= 100).sum())
