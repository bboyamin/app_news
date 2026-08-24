import sys, os
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal
import pandas as pd

df_year = app_budget_portal.load_and_prepare_year_data(2026, cache_version="v11.0")

included_df = df_year[df_year['정산 상태'] == '✅ 정산 포함']
total_budget_thousand = float(included_df['예산액_num'].sum())
total_budget_billion = total_budget_thousand / 100000.0

print(f"============================================================")
print(f"=== 포털 메인 카드 최종 표출 금액 검증 ===")
print(f"============================================================")
print(f"포털 메인 카드 천원 단위: {total_budget_thousand:15,.0f} 천원")
print(f"포털 메인 카드 억원 단위: {total_budget_billion:15.2f} 억 원")
print(f"목표 예산액 천원 단위:   {3463154010:15,.0f} 천원")
print(f"최종 차액:                 {total_budget_thousand - 3463154010:+15,.0f} 천원")

if abs(total_budget_thousand - 3463154010) < 1.0:
    print("\n🎉🎉🎉 포털 메인 화면의 총 예산 합계가 목표액 3,463,154,010 천원 (3조 4,631억 5,401만 원, 오차 0원)으로 완벽하게 표출됩니다!")
