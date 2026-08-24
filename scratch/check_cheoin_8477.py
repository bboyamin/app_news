import sys, os
sys.path.insert(0, os.path.abspath('src'))
import data_manager
import pandas as pd

df = pd.read_csv('data/budget_2026.csv', low_memory=False)
amt_str = df['예산액'].astype(str).str.replace(',', '', regex=False).str.replace('원', '', regex=False).str.strip()
df['amt_num'] = pd.to_numeric(amt_str, errors='coerce').fillna(0.0)

cheoin = df[df['부서명'] == '처인구 자치행정과']
print(f"Total raw sum for 처인구 자치행정과: {cheoin['amt_num'].sum():,.0f} 천원")

import test_exact_zero_diff
records = test_exact_zero_diff.records
cheoin_inc = [r for r in records if r.get('부서명') == '처인구 자치행정과' and r.get('status') == '✅ 정산 포함']
cheoin_sum = sum(r['amt_num'] for r in cheoin_inc)
print(f"test_exact_zero_diff sum for 처인구 자치행정과: {cheoin_sum:,.0f} 천원")
print(f"Target PDF for 처인구 자치행정과: {test_exact_zero_diff.pdf_targets['처인구 자치행정과']:,.0f} 천원")
