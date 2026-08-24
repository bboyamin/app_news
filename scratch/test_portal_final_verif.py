import sys, os
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal

df = app_budget_portal.load_and_prepare_year_data(2026)
inc = df[df['정산 상태'] == '✅ 정산 포함']
total_thousand = inc['예산액_num'].sum()

print("==================================================")
print(f"포털 최종 계산 금액 (천원): {total_thousand:15,.0f} 천원")
print(f"목표 예산 금액 (천원):      3,463,154,010 천원")
print(f"최종 차액 (천원):           {total_thousand - 3463154010:+15,.0f} 천원")
print(f"첫 번째 행 부서명:         {df.iloc[0]['부서명']}")
print("==================================================")
