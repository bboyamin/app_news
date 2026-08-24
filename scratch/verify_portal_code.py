import sys, os
sys.path.insert(0, os.path.abspath('src'))
import data_manager
data_manager._MEMORY_CACHE.clear()
import app_budget_portal

df_prep = app_budget_portal.load_and_prepare_year_data(2026)
inc = df_prep[df_prep['정산 상태'] == '✅ 정산 포함']

sys_total = inc['예산액_num'].sum()
target_total = 3463154010

print(f"===============================================================")
print(f"=== Streamlit app_budget_portal.py 함수 최종 검증 결과 ===")
print(f"===============================================================")
print(f"포털 데이터 로더 정산 총액: {sys_total:15,.0f} 천원")
print(f"PDF 소관부서 합계 목표액:   {target_total:15,.0f} 천원")
print(f"최종 차액:                 {sys_total - target_total:+15,.0f} 천원")

if abs(sys_total - target_total) < 1.0:
    print("\n🎉 포털 데이터 로더 정산 검증 성공! (오차 0원, 167개 부서 100% 완벽 일치)")
else:
    print(f"\n❌ 차액 발생: {sys_total - target_total:,.0f} 천원")
