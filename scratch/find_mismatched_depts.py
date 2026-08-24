import sys, os
sys.path.insert(0, os.path.abspath('scratch'))
import test_exact_zero_diff
import test_exact_portal_display

df_prep = test_exact_portal_display.load_and_prepare_year_data_display(2026)
inc = df_prep[df_prep['정산 상태'] == '✅ 정산 포함']

dept_sums = inc.groupby('부서명')['예산액_num'].sum().to_dict()
clean_map = {str(d).replace(' ', ''): d for d in dept_sums.keys()}

official_167_sum = 0
unmatched_depts = []

for pdf_d, t_val in test_exact_zero_diff.pdf_targets.items():
    clean_p = pdf_d.replace(' ', '')
    matched_dept = clean_map.get(clean_p)
    if matched_dept:
        val = dept_sums[matched_dept]
        official_167_sum += val
        if abs(val - t_val) > 0.01:
            print(f"Mismatch in 167 dept [{pdf_d}]: sys={val:12,.0f} | target={t_val:12,.0f} | diff={val - t_val:+12,.0f}")
    else:
        print(f"NOT MATCHED DEPT: {pdf_d}")

print(f"\nOfficial 167 departments sum: {official_167_sum:15,.0f} 천원")
print(f"Target PDF 167 departments sum: {sum(test_exact_zero_diff.pdf_targets.values()):15,.0f} 천원")
