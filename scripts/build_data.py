# -*- coding: utf-8 -*-
"""data/raw/{YYYYMM}.csv(국민연금 가입 사업장 내역) → _data/companies.json.gz (+ meta).
회사 = (사업장명, 사업자등록번호 앞6자리) 로 지점을 합산한다. 법인만, 최근월 등록 상태, 가입자 MIN_N 이상."""
import sys, json, gzip, re, pathlib, collections
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "_data"
OUT.mkdir(exist_ok=True)
MIN_N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
COLS = {"자료생성년월": "ym", "사업장명": "name", "사업자등록번호": "biz", "사업장가입상태코드 1 등록 2 탈퇴": "st", "사업장지번상세주소": "addr",
        "사업장형태구분코드 1 법인 2 개인": "typ", "사업장업종코드": "icode", "사업장업종코드명": "iname", "적용일자": "since",
        "가입자수": "n", "당월고지금액": "bill", "신규취득자수": "new", "상실가입자수": "lost"}
SIDO = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산",
        "세종특별자치시": "세종", "경기도": "경기", "강원도": "강원", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전라북도": "전북",
        "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주", "제주도": "제주"}

def clean_name(s):
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s

def main():
    files = sorted(RAW.glob("*.csv"))
    months = [f.stem for f in files]
    print("months", months)
    comp = {}  # key -> dict
    latest = months[-1]
    for f in files:
        ym = f.stem
        df = pd.read_csv(f, encoding="cp949", dtype=str, usecols=list(COLS), na_filter=False).rename(columns=COLS)
        for c in ("n", "bill", "new", "lost"):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int64")
        df = df[(df["st"] == "1") & (df["typ"] == "1") & (df["iname"] != "BIZ_NO미존재사업장")]
        df["name"] = df["name"].map(clean_name)
        g = df.groupby(["name", "biz"], sort=False)
        agg = g.agg(n=("n", "sum"), bill=("bill", "sum"), new=("new", "sum"), lost=("lost", "sum"), br=("n", "size")).reset_index()
        # 대표 지점(가입자 최다)의 주소·업종·적용일자
        top = df.sort_values("n", ascending=False).drop_duplicates(["name", "biz"])[["name", "biz", "addr", "icode", "iname", "since"]]
        agg = agg.merge(top, on=["name", "biz"], how="left")
        for r in agg.itertuples(index=False):
            k = (r.name, r.biz)
            d = comp.get(k)
            if d is None:
                d = comp[k] = dict(name=r.name, biz=r.biz, hist={}, new={}, lost={})
            d["hist"][ym] = int(r.n)
            d["new"][ym] = int(r.new); d["lost"][ym] = int(r.lost)
            if ym == latest:
                d.update(n=int(r.n), bill=int(r.bill), br=int(r.br), addr=r.addr, icode=r.icode, iname=r.iname, since=r.since)
        print(ym, len(df), "rows", len(agg), "companies")
    out = []
    for k, d in comp.items():
        if "n" not in d or d["n"] < MIN_N: continue
        toks = d["addr"].split()
        sido = SIDO.get(toks[0], toks[0]) if toks else ""
        sgg = toks[1] if len(toks) > 1 else ""
        dong = toks[2] if len(toks) > 2 else ""
        if len(toks) > 3 and toks[1].endswith("시") and toks[2].endswith("구"):
            dong = toks[3]
        hist = [d["hist"].get(m) for m in months]
        out.append(dict(name=d["name"], biz=d["biz"], n=d["n"], bill=d["bill"], br=d["br"], sido=sido, sgg=sgg, dong=dong,
                        icode=d["icode"], iname=d["iname"], since=d["since"][:7] if d["since"] else "",
                        hist=hist, new12=sum(d["new"].values()), lost12=sum(d["lost"].values()), nm=len(d["hist"])))
    out.sort(key=lambda x: -x["n"])
    print("companies >=", MIN_N, ":", len(out))
    def prev(m):  # 파일명(YYYYMM)의 자료는 전월 기준(자료생성년월)
        y, mo = int(m[:4]), int(m[4:])
        mo -= 1
        if mo == 0: y, mo = y - 1, 12
        return "%04d-%02d" % (y, mo)
    meta = dict(months=months, data_months=[prev(m) for m in months], latest=latest, latest_data=prev(latest), min_n=MIN_N, count=len(out))
    with gzip.open(OUT / "companies.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(dict(meta=meta, companies=out), fh, ensure_ascii=False, separators=(",", ":"))
    print("saved", (OUT / "companies.json.gz").stat().st_size // 1024, "KB")

if __name__ == "__main__":
    main()
