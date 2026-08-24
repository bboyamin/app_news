import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))
import scratch.test_portal_target_exact as pte
import scratch.test_exact_zero_diff as ez

df_res = pte.load_portal_target_exact()
inc = df_res[df_res['정산 상태'] == '✅ 정산 포함']

dept_sums = inc.groupby('부서명')['예산액_num'].sum().to_dict()
clean_map = {str(d).replace(' ', ''): d for d in dept_sums.keys()}

for pdf_d, t_val in ez.pdf_targets.items():
    clean_p = pdf_d.replace(' ', '')
    matched = clean_map.get(clean_p)
    if matched:
        val = dept_sums[matched]
        if abs(val - t_val) > 0.01:
            print(f"DISCREPANCY DEPT [{pdf_d}]: sys={val:12,.0f} | target={t_val:12,.0f} | diff={val - t_val:+12,.0f}")
