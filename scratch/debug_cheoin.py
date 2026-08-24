import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))
import scratch.test_verify_perfect_zero as tvp

df_res = tvp.load_portal_verified()
inc = df_res[(df_res['정산 상태'] == '✅ 정산 포함') & (df_res['부서명'] == '처인구 자치행정과')]

print("=== 처인구 자치행정과 포함 항목 목록 ===")
for idx, r in inc.iterrows():
    print(f"[{idx}] {r.get('세부사업명')} | {r.get('산출근거명')} | {r.get('예산액_num')}")

print(f"Total Sum: {inc['예산액_num'].sum():,.0f} 천원")
