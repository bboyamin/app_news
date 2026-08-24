import sys, os
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal

df = app_budget_portal.load_and_prepare_year_data(2026)
print("=== First 5 rows ===")
print(df[['예산구분', '부서명', '회계명', '세부사업명', '산출근거명', '예산액_num']].head(5))
