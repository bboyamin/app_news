import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))
import src.app_budget_portal as app_budget_portal
import scratch.test_exact_zero_diff as ez

df_portal = app_budget_portal.load_and_prepare_year_data(2026, cache_version="v9.0")
inc = df_portal[df_portal['정산 상태'] == '✅ 정산 포함']

dept_sums = inc.groupby('부서명')['예산액_num'].sum().to_dict()
clean_map = {str(d).replace(' ', ''): d for d in dept_sums.keys()}

total_167 = 0
discrepancies = []

for pdf_d, t_val in ez.pdf_targets.items():
    clean_p = pdf_d.replace(' ', '')
    matched = clean_map.get(clean_p)
    if matched:
        val = dept_sums[matched]
        total_167 += val
        if abs(val - t_val) > 0.01:
            discrepancies.append((pdf_d, val, t_val, val - t_val))
    else:
        discrepancies.append((pdf_d, 0, t_val, -t_val))

print(f"============================================================")
print(f"=== 포털 모듈 167개 소관부서 100.00% 오차 0원 검증 결과 ===")
print(f"============================================================")
print(f"포털 모듈 계산 167개 부서 총액: {total_167:15,.0f} 천원")
print(f"PDF 167개 소관부서 목표 총액:   {sum(ez.pdf_targets.values()):15,.0f} 천원")
print(f"최종 차액:                      {total_167 - sum(ez.pdf_targets.values()):+15,.0f} 천원")
print(f"차액 발생 부서 수:              {len(discrepancies)}개 부서")

if abs(total_167 - sum(ez.pdf_targets.values())) < 1.0 and len(discrepancies) == 0:
    print("\n🎉🎉🎉 167개 모든 부서 및 전체 예산액 합계가 100.00% 오차 0원으로 완벽 일치합니다! (3,463,154,010천원)")
else:
    for d, c, t, diff in discrepancies:
        print(f"  [{d:25s}] sys={c:12,.0f} | target={t:12,.0f} | diff={diff:+12,.0f}")
