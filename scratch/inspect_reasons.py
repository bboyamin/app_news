import sys, os, pandas as pd, numpy as np, re
sys.path.append('src')
import app_budget_portal

pdf_targets = {
    '민생경제과': 33194563,
    '노인복지과': 439467167,
    '환경정책과': 37588939,
    '회계과': 254781010,
    '처인구 교통과': 5127532,
    '체육진흥과': 56997912,
    '생태하천과': 16283938,
    '자원순환과': 158362190,
    '자원육성과': 2553826,
    '복지정책과': 233240218,
    '처인구 건설과': 8836030,
    '수지구 세무1과': 553254,
    '인사관리과': 74604888,
    '처인구 자치행정과': 8032997,
    '의정담당관': 4791400,
    '의사입법담당관': 810867,
    '남사읍': 2415532
}

df_prep = app_budget_portal.load_and_prepare_year_data(2026)

out_lines = []
for dept, target_val in pdf_targets.items():
    dept_df = df_prep[df_prep['부서명'] == dept]
    inc_df = dept_df[dept_df['정산 상태'] == '✅ 정산 포함']
    sys_sum = inc_df['예산액_num'].sum()
    diff = sys_sum - target_val
    out_lines.append(f"=== [{dept}] 시스템: {sys_sum:,}천원 | PDF목표: {target_val:,}천원 | 차액: {diff:+,}천원 ===")
    
    # Show items that are included (✅ 정산 포함) across multiple budget types (e.g. 본예산 & 추경) in the same 세부사업명/통계목명
    grouped = dept_df.groupby(['세부사업명', '통계목명'])
    for (biz, tong), group in grouped:
        types = group['예산구분'].unique()
        if len(types) > 1:
            inc_in_grp = group[group['정산 상태'] == '✅ 정산 포함']
            if len(inc_in_grp['예산구분'].unique()) > 1:
                out_lines.append(f"  [중복 정산 포함 발생] 세부사업: {biz} | 통계목: {tong} | 예산구분들: {types}")
                for idx, row in group.iterrows():
                    out_lines.append(f"    - {row['예산구분']} | {row['산출근거명']} | {row['산출근거식']} | {row['예산액_num']:,}천원 | {row['정산 상태']}")
    out_lines.append("\n")

with open('scratch/17_depts_reasons.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))

print('Wrote scratch/17_depts_reasons.txt successfully!')
