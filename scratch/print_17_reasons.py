import pandas as pd, numpy as np, re

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

df_raw = pd.read_csv('data/budget_2026.csv', low_memory=False)
df = df_raw.copy()
df['예산액_num'] = pd.to_numeric(df['예산액'].astype(str).str.replace(',', '').str.replace('원', '').str.strip(), errors='coerce').fillna(0.0)

print("=== 17개 오차 발생 부서 차액 및 요인 분석 ===")

for dept, pdf_target in pdf_targets.items():
    sub = df[df['부서명'] == dept]
    raw_sum = sub['예산액_num'].sum()
    diff = raw_sum - pdf_target
    print(f"\n[{dept}] raw_sum={raw_sum:12,f}천원 | pdf_target={pdf_target:12,d}천원 | raw_diff={diff:+12,f}천원")
    
    # Group by budget type
    btypes = sub.groupby('예산구분')['예산액_num'].sum().to_dict()
    print(f"  예산구분별 합계: {btypes}")
    
    # Check for rows with 경정 / 소계 / 대체 / 성립전 / 간주
    for btype in sub['예산구분'].unique():
        b_sub = sub[sub['예산구분'] == btype]
        print(f"   * [{btype}] {len(b_sub)}개 행 | 합계: {b_sub['예산액_num'].sum():,f}천원")
