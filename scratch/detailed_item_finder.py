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

print("=== 17개 차액 부서 세부 항목 탐색 ===")

for dept, pdf_target in pdf_targets.items():
    sub = df[df['부서명'] == dept]
    print(f"\n==================== [{dept}] PDF목표 = {pdf_target:,} 천원 ====================")
    
    # Show rows grouped by (세부사업명, 통계목명) where multiple budget types exist
    grouped = sub.groupby(['세부사업명', '통계목명'])
    for (biz, tong), group in grouped:
        if len(group['예산구분'].unique()) > 1 or any(v in str(group['산출근거식']) for v in ['경정', '성립전', '간주']):
            print(f"\n  ▶ 세부사업: [{biz}] | 통계목: [{tong}]")
            for idx, r in group.iterrows():
                print(f"     idx={idx:5d} | {r['예산구분']:8s} | {str(r['산출근거명']):35s} | 식: {str(r['산출근거식']):25s} | 금액: {r['예산액_num']:12,f}천원")
