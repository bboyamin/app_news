import pandas as pd

df = pd.read_csv('data/budget_2026.csv', low_memory=False)
df['예산액_num'] = pd.to_numeric(df['예산액'].astype(str).str.replace(',', '').str.replace('원', '').str.strip(), errors='coerce').fillna(0.0)

depts = ['생태하천과', '자원순환과', '공동주택과', '복지정책과', '처인구 자치행정과', '의사입법담당관', '마북동', '신갈동']

for d in depts:
    sub = df[df['부서명'] == d]
    print(f"\n==================== [{d}] (총 {len(sub)}개 행) ====================")
    for idx, r in sub.iterrows():
        print(f"  idx={idx:5d} | {str(r['예산구분']):8s} | 세부: {str(r['세부사업명']):25s} | 목: {str(r['통계목명']):15s} | 근거: {str(r['산출근거명']):30s} | 식: {str(r['산출근거식']):25s} | {r['예산액_num']:12,f}천원")
