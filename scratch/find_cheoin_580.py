import sys, os
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal

df = app_budget_portal.load_and_prepare_year_data(2026)
inc = df[(df['부서명'] == '처인구 자치행정과') & (df['정산 상태'] == '✅ 정산 포함')]

for idx, r in inc.iterrows():
    val = r['예산액_num']
    if val == 580.0 or val == 5800.0 or val == 8580.0 or val == 580 or '580' in str(val):
        print(f"Match 580: {r['orig_idx'] if 'orig_idx' in r else idx}: {r['세부사업명']} | {r['산출근거명']} | {val}")

print("Checking items around 8477:")
for idx, r in df[(df['부서명'] == '처인구 자치행정과')].iterrows():
    if 8470 <= r.get('orig_idx', idx) <= 8485:
        print(f"  {r.get('orig_idx', idx)}: {r['산출근거명']} | {r['예산액_num']} | {r['정산 상태']}")
