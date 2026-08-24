import sys, os
sys.path.insert(0, os.path.abspath('scratch'))
import test_exact_zero_diff

print("\n--- 167개 부서 중 PDF 목표액과 차이가 남은 부서 목록 ---")
for pdf_dept, target_val in test_exact_zero_diff.pdf_targets.items():
    clean_p = pdf_dept.replace(' ', '')
    matched = test_exact_zero_diff.clean_dept_map.get(clean_p)
    if matched:
        c_val = test_exact_zero_diff.dept_sums[matched]
        diff = c_val - target_val
        if abs(diff) > 0.01:
            print(f"[{pdf_dept:20s}] 시스템={c_val:13,.0f} | 목표={target_val:13,.0f} | 차액={diff:+13,.0f} 천원")
