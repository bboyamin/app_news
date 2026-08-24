import pandas as pd
df = pd.read_csv('data/budget_2026.csv', low_memory=False)
for idx in range(8470, 8485):
    r = df.iloc[idx]
    dept = r.get('부서명')
    biz = r.get('세부사업명')
    amt = r.get('예산액')
    name = r.get('산출근거명')
    print(f"Index {idx}: [{dept}] {biz} | {name} | {amt}")
