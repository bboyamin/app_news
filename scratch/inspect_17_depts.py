import sys, pandas as pd, numpy as np, re
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

for dept, target_val in pdf_targets.items():
    dept_df = df_prep[df_prep['부서명'] == dept]
    inc_df = dept_df[dept_df['정산 상태'] == '✅ 정산 포함']
    sys_sum = inc_df['예산액_num'].sum()
    diff = sys_sum - target_val
    print(f'=== [{dept}] 시스템: {sys_sum:,}천원 | PDF목표: {target_val:,}천원 | 차액: {diff:+,}천원 ===')
    print(dept_df[['예산구분', '세부사업명', '통계목명', '산출근거명', '산출근거식', '예산액_num', '정산 상태']].to_string())
    print('\n' + '='*80 + '\n')
