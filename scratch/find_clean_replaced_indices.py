import sys, os
sys.path.insert(0, os.path.abspath('src'))
import data_manager
import pandas as pd

df_raw = pd.read_csv('data/budget_2026.csv', low_memory=False)
df_clean = data_manager.load_year_data(2026)

target_raw_indices = [3692, 3060, 5511, 2913, 6084, 8477]

for r_idx in target_raw_indices:
    raw_row = df_raw.iloc[r_idx]
    dept = raw_row['부서명']
    biz = raw_row['세부사업명']
    tong = raw_row['통계목명']
    name = raw_row['산출근거명']
    amt = raw_row['예산액']
    
    # find matching row in df_clean
    m = df_clean[(df_clean['부서명'] == str(dept).strip()) & (df_clean['세부사업명'] == str(biz).strip()) & (df_clean['통계목명'] == str(tong).strip()) & (df_clean['산출근거명'] == str(name).strip())]
    if not m.empty:
        c_idx = m.index[0]
        print(f"RAW idx {r_idx:5d} -> CLEAN idx {c_idx:5d} | 부서={dept} | 세부={biz} | 목={tong} | 근거={name}")
    else:
        print(f"RAW idx {r_idx:5d} NOT FOUND IN CLEAN! 부서={dept} | 세부={biz}")
