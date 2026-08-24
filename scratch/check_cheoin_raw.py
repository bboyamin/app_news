import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))
import pandas as pd

filepath = os.path.join("data", "budget_2026.csv")
df_raw = pd.read_csv(filepath, low_memory=False)
cheoin = df_raw[df_raw['부서명'] == '처인구 자치행정과'].copy()

amt_str = cheoin['예산액'].astype(str).str.replace(',', '', regex=False).str.replace('원', '', regex=False).str.strip()
cheoin['amt_num'] = pd.to_numeric(amt_str, errors='coerce').fillna(0.0)

print(f"Raw total of 처인구 자치행정과: {cheoin['amt_num'].sum():,.0f} 천원")
for biz, grp in cheoin.groupby('세부사업명'):
    print(f"  [{biz:30s}] sum={grp['amt_num'].sum():12,.0f} | count={len(grp)}")
