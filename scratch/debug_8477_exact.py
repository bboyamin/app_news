import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))
import scratch.test_exact_zero_diff as ez

records = ez.records
cheoin_inc = [r for r in records if r.get('부서명') == '처인구 자치행정과' and r.get('status') == '✅ 정산 포함']
cheoin_sum = sum(r['amt_num'] for r in cheoin_inc)

print(f"cheoin_sum: {cheoin_sum}")
print(f"pdf_target: {ez.pdf_targets['처인구 자치행정과']}")
print(f"diff: {cheoin_sum - ez.pdf_targets['처인구 자치행정과']}")

for r in cheoin_inc:
    if '업무추진' in str(r.get('산출근거명', '')):
        print(f"  [{r['orig_idx']}] {r['세부사업명']} | {r['산출근거명']} | {r['amt_num']}")
