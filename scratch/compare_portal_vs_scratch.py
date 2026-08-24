import sys, os
sys.path.insert(0, os.path.abspath('src'))
import app_budget_portal
import pandas as pd, numpy as np

# 1. Load via app_budget_portal
df_portal = app_budget_portal.load_and_prepare_year_data(2026)
portal_inc = df_portal[df_portal['정산 상태'] == '✅ 정산 포함']
portal_sums = portal_inc.groupby('부서명')['예산액_num'].sum().to_dict()

# 2. Load via raw csv
import test_exact_zero_diff

raw_sums = test_exact_zero_diff.dept_sums

clean_map = {str(d).replace(' ', ''): d for d in raw_sums.keys()}

for pdf_dept, target_val in test_exact_zero_diff.pdf_targets.items():
    clean_p = pdf_dept.replace(' ', '')
    m_raw = clean_map.get(clean_p)
    raw_val = raw_sums.get(m_raw, 0)
    
    m_port = clean_map.get(clean_p)
    port_val = portal_sums.get(m_port, 0) if m_port else 0
    
    if abs(port_val - raw_val) > 0.01:
        print(f"DIFF in [{pdf_dept}]: raw={raw_val:12,.0f} | portal={port_val:12,.0f} | diff={port_val - raw_val:+12,.0f}")
