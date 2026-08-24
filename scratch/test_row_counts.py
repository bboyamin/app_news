import sys, os
sys.path.insert(0, os.path.abspath('src'))
import data_manager
import pandas as pd

df1 = pd.read_csv('data/budget_2026.csv', low_memory=False)
df2 = data_manager.read_csv_robust('data/budget_2026.csv')

print(f"pd.read_csv rows: {len(df1)}")
print(f"read_csv_robust rows: {len(df2)}")
