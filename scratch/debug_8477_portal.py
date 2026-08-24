import sys, os
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal

df_year = app_budget_portal.load_and_prepare_year_data(2026, cache_version="v15.0")
r8477 = df_year.iloc[8477]
print(f"Row 8477 dept: {r8477.get('부서명')}")
print(f"Row 8477 biz: {r8477.get('세부사업명')}")
print(f"Row 8477 name: {r8477.get('산출근거명')}")
print(f"Row 8477 status: {r8477.get('정산 상태')}")
print(f"Row 8477 amt_num: {r8477.get('예산액_num')}")

inc = df_year[df_year['정산 상태'] == '✅ 정산 포함']
print(f"Included sum: {inc['예산액_num'].sum():,.0f} 천원")
