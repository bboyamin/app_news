import sys, os
sys.path.insert(0, os.path.abspath('scratch'))
import test_exact_zero_diff

dept_sums = test_exact_zero_diff.dept_sums
pdf_targets = test_exact_zero_diff.pdf_targets

clean_dept_map = {str(d).replace(' ', ''): d for d in dept_sums.keys()}

real_total = 0
discrepancies = []

for pdf_d, t_val in pdf_targets.items():
    clean_p = pdf_d.replace(' ', '')
    matched = clean_dept_map.get(clean_p)
    if matched:
        c_val = dept_sums[matched]
        real_total += c_val
        if abs(c_val - t_val) > 0.01:
            discrepancies.append((pdf_d, c_val, t_val, c_val - t_val))
    else:
        discrepancies.append((pdf_d, 0, t_val, -t_val))

print(f"REAL calculated total across 167 departments: {real_total:15,.0f} 천원")
print(f"Target PDF total:                            {sum(pdf_targets.values()):15,.0f} 천원")
print(f"REAL Total difference:                        {real_total - sum(pdf_targets.values()):+15,.0f} 천원")
print(f"Number of discrepancy departments:            {len(discrepancies)}개 부서")

for d, c, t, diff in discrepancies:
    print(f"  [{d:25s}] sys={c:12,.0f} | target={t:12,.0f} | diff={diff:+12,.0f}")
