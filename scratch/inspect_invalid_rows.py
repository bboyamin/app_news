import pandas as pd
df_raw = pd.read_csv('data/budget_2026.csv', low_memory=False)
df_raw['amt_num'] = pd.to_numeric(df_raw['예산액'].astype(str).str.replace(',', '').str.replace('원', '').str.strip(), errors='coerce').fillna(0.0)

invalid = df_raw[(df_raw['부서명'].isna() | (df_raw['부서명'].astype(str).str.strip().isin(['-', '0', 'N/A', '']))) & (df_raw['세부사업명'].isna() | (df_raw['세부사업명'].astype(str).str.strip().isin(['-', '0', 'N/A', ''])))]

print(f"Total invalid rows: {len(invalid)}")
for idx, r in invalid.iterrows():
    print(f"Row {idx}: 예산구분={r.get('예산구분')} | 부서명={r.get('부서명')} | 사업={r.get('세부사업명')} | 통계={r.get('통계목명')} | 근거={r.get('산출근거명')} | 금액={r.get('amt_num'):,f}천원")
