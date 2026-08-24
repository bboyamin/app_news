import pandas as pd, numpy as np
import sys, os
sys.path.insert(0, os.path.abspath('src'))
import data_manager

df_raw = pd.read_csv('data/budget_2026.csv', low_memory=False)
df_clean = data_manager.clean_budget_dataframe(df_raw)

print(f"Raw rows: {len(df_raw)}, Cleaned rows: {len(df_clean)}")

df_raw['예산액_num'] = pd.to_numeric(df_raw['예산액'].astype(str).str.replace(',', '').str.replace('원', '').str.strip(), errors='coerce').fillna(0.0)

diff_rows = set(df_raw.index) - set(df_clean.index)
print(f"Dropped row indices: {diff_rows}")

for idx in diff_rows:
    row = df_raw.loc[idx]
    print(f"  Dropped row {idx}: 부서={row.get('부서명')} | 세부사업={row.get('세부사업명')} | 통계목={row.get('통계목명')} | 근거={row.get('산출근거명')} | 금액={row.get('예산액_num'):12,f}천원")
