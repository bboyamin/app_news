import sys, os
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal

df = app_budget_portal.load_and_prepare_year_data(2026)
inc = df[(df['부서명'] == '처인구 자치행정과') & (df['정산 상태'] == '✅ 정산 포함')]
print("처인구 자치행정과 included sum:", inc['예산액_num'].sum())
print("Item details:")
for idx, r in inc.iterrows():
    print(f"  {r['orig_idx'] if 'orig_idx' in r else idx}: {r['세부사업명']} | {r['산출근거명']} | {r['예산액_num']}")
