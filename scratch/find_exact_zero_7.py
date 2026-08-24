import sys, os
sys.path.insert(0, os.path.abspath('scratch'))
import test_exact_zero_diff
import pandas as pd

df_raw = pd.read_csv('data/budget_2026.csv', low_memory=False)
df_raw['amt_num'] = pd.to_numeric(df_raw['예산액'].astype(str).str.replace(',', '').str.replace('원', '').str.strip(), errors='coerce').fillna(0.0)

# Check 공동주택과 (+100,000)
gongdong = df_raw[df_raw['부서명'].astype(str).str.contains('공동주택과') & (df_raw['amt_num'] == 100000)]
print("공동주택과 10만천원 items:")
for idx, r in gongdong.iterrows():
    print(f"  idx {idx}: 세부={r['세부사업명']} | 목={r['통계목명']} | 근거={r['산출근거명']} | 식={r['산출근거식']}")

# Check 생태하천과 (-720,000)
saengtae = df_raw[df_raw['부서명'].astype(str).str.contains('생태하천과') & (df_raw['amt_num'] == 720000)]
print("\n생태하천과 72만천원 items:")
for idx, r in saengtae.iterrows():
    print(f"  idx {idx}: 세부={r['세부사업명']} | 목={r['통계목명']} | 근거={r['산출근거명']} | 식={r['산출근거식']}")

# Check 자원순환과 (-400,000)
jawon = df_raw[df_raw['부서명'].astype(str).str.contains('자원순환과') & (df_raw['amt_num'] == 400000)]
print("\n자원순환과 40만천원 items:")
for idx, r in jawon.iterrows():
    print(f"  idx {idx}: 세부={r['세부사업명']} | 목={r['통계목명']} | 근거={r['산출근거명']} | 식={r['산출근거식']}")

# Check 신갈동 (-1,080)
singal = df_raw[df_raw['부서명'].astype(str).str.contains('신갈동') & (df_raw['amt_num'] == 1080)]
print("\n신갈동 1080천원 items:")
for idx, r in singal.iterrows():
    print(f"  idx {idx}: 세부={r['세부사업명']} | 목={r['통계목명']} | 근거={r['산출근거명']} | 식={r['산출근거식']}")

# Check 마북동 (-1,350)
mabuk = df_raw[df_raw['부서명'].astype(str).str.contains('마북동') & (df_raw['amt_num'] == 1350)]
print("\n마북동 1350천원 items:")
for idx, r in mabuk.iterrows():
    print(f"  idx {idx}: 세부={r['세부사업명']} | 목={r['통계목명']} | 근거={r['산출근거명']} | 식={r['산출근거식']}")
