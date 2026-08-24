import pandas as pd, numpy as np, re

df_raw = pd.read_csv('data/budget_2026.csv', low_memory=False)
df = df_raw.copy()
df['예산액_num'] = pd.to_numeric(df['예산액'].astype(str).str.replace(',', '').str.replace('원', '').str.strip(), errors='coerce').fillna(0.0)

target_depts = [
    '민생경제과', '노인복지과', '환경정책과', '회계과', '처인구 교통과',
    '체육진흥과', '생태하천과', '자원순환과', '자원육성과', '복지정책과',
    '처인구 건설과', '수지구 세무1과', '인사관리과', '처인구 자치행정과',
    '의정담당관', '의사입법담당관', '남사읍'
]

print("=== 17개 차액 부서 원본 데이터 항목 점검 ===")
for dept in target_depts:
    sub = df[df['부서명'] == dept]
    print(f"\n▶ 부서명: [{dept}] (총 {len(sub)}개 행)")
    btypes = sub.groupby('예산구분')['예산액_num'].sum().to_dict()
    for bt, val in btypes.items():
        print(f"   - {bt:10s}: {val:14,f} 천원")
    
    # Check for rows with 경정, 성립전, 간주
    chu_rows = sub[sub['산출근거식'].astype(str).str.contains('경정|성립전|간주') | sub['산출근거명'].astype(str).str.contains('경정|성립전|간주')]
    if not chu_rows.empty:
        print("   [추경/경정/성립전/간주 명시 항목]:")
        for _, r in chu_rows.iterrows():
            print(f"     * [{r['예산구분']}] 세부사업: {r['세부사업명']} | 통계목: {r['통계목명']} | 산출근거: {r['산출근거명']} | 식: {r['산출근거식']} | 금액: {r['예산액_num']:,}천원")
