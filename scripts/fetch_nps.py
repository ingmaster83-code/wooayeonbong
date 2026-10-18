# -*- coding: utf-8 -*-
"""국민연금 가입 사업장 내역(15083277) 월별 CSV 다운로드. 사용: python scripts/fetch_nps.py [--latest] [--from 202501]"""
import argparse, re, sys
from pathlib import Path
import requests
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "wooaingu" / "scripts"))
import fetch_files as FF
PK = "15083277"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="start", default="202501"); ap.add_argument("--latest", action="store_true")
a = ap.parse_args()
cur, vs = FF.versions(PK)
print("현재 버전", cur, "history", [v[0] for v in vs][:6])
if a.latest: vs = vs[:1]
for ym, uddi, name in vs:
    if ym < a.start: continue
    out = RAW / (ym + ".csv")
    if out.exists(): print("skip", ym); continue
    data, fname = FF.download(PK, uddi, out)
    out.write_bytes(data); print(ym, name, len(data) // 1024, "KB", fname)
