import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('scratch'))
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal
import test_exact_zero_diff as ez

df = app_budget_portal.load_and_prepare_year_data(2026)
inc = df[df['정산 상태'] == '✅ 정산 포함']

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

print(f"167개 부서 합계: {total_167:15,.0f} 천원")
print(f"PDF 목표 합계:   {sum(ez.pdf_targets.values()):15,.0f} 천원")
print(f"오차 발생 부서:  {len(discrepancies)}개")
for d, c, t, diff in discrepancies:
    print(f"  [{d}] sys={c:,.0f} | target={t:,.0f} | diff={diff:+,.0f}")
