import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('src'))
import data_manager
import pandas as pd
from collections import defaultdict
import re

import scratch.test_exact_zero_diff as ez

big_circle_pattern = re.compile(r'^[○Ο●◎◆■□]')
def get_symbol_level(name):
    return 1 if big_circle_pattern.match(str(name).strip()) else 4

def normalize_item_name_improved(name):
    s = re.sub(r'^[○Ο●◎◆■□οo\-▪ㆍ･\s]+', '', str(name).strip())
    # Strip (성립전...), (간주...), - 성립전, (자체), (국비), (도비) etc.
    s = re.sub(r'[\(\[\-].*?(성립전|간주|자체|국비|도비|시비|경정).*?[\)\]]?', '', s).strip()
    s_clean = s.replace(" ", "")
    return s_clean if len(s_clean) >= 2 else s.replace(" ", "")

def get_budget_type_sort_key(t_str):
    s = str(t_str).strip()
    if '본예산' in s or '당초' in s or s == '본':
        return (1, 0, 0, s)
    chugyeong_num = 0
    m_chu = re.search(r'추경(\d+)회', s)
    if m_chu:
        chugyeong_num = int(m_chu.group(1))
    elif '추경' in s:
        chugyeong_num = 50
    return (2, chugyeong_num, 0, s)

def load_pure_algorithmic():
    filepath = os.path.join("data", "budget_2026.csv")
    df_raw = pd.read_csv(filepath, low_memory=False)
    
    amt_str = df_raw['예산액'].astype(str).str.replace(',', '', regex=False).str.replace('원', '', regex=False).str.strip()
    df_raw['예산액_num'] = pd.to_numeric(amt_str, errors='coerce').fillna(0.0)
    df_raw['예산액_원'] = df_raw['예산액_num'] * 1000.0
    df_raw['예산액_억원'] = df_raw['예산액_num'] / 100000.0

    records = df_raw.to_dict('records')

    groups = defaultdict(list)
    for idx, r in enumerate(records):
        dept = str(r.get('부서명', '')).strip()
        biz = str(r.get('세부사업명', '')).strip()
        tong = str(r.get('통계목명', '')).strip()
        btype = str(r.get('예산구분', '')).strip()
        r['orig_idx'] = idx
        r['정산 상태'] = '✅ 정산 포함'
        groups[(dept, biz, tong, btype)].append(r)

    circle_excluded_indices = set()
    for key, item_list in groups.items():
        n = len(item_list)
        i = 0
        while i < n:
            name = item_list[i].get('산출근거명', '')
            if name and get_symbol_level(name) == 1:
                j = i + 1
                while j < n:
                    next_name = item_list[j].get('산출근거명', '')
                    if get_symbol_level(next_name) == 1:
                        break
                    circle_excluded_indices.add(item_list[j]['orig_idx'])
                    j += 1
                i = j - 1
            i += 1

    for idx in circle_excluded_indices:
        records[idx]['정산 상태'] = '🔻 소계 중복 제외'

    tong_groups = defaultdict(list)
    for idx, r in enumerate(records):
        if r['정산 상태'] == '✅ 정산 포함':
            dept = str(r.get('부서명', '')).strip()
            biz = str(r.get('세부사업명', '')).strip()
            tong = str(r.get('통계목명', '')).strip()
            r['norm_name'] = normalize_item_name_improved(r.get('산출근거명', ''))
            r['sort_key'] = get_budget_type_sort_key(r.get('예산구분', ''))
            tong_groups[(dept, biz, tong)].append(r)

    superseded_indices = set()
    for (dept, biz, tong), item_list in tong_groups.items():
        types = set(r['sort_key'] for r in item_list)
        if len(types) > 1:
            max_k = max(types)
            chu_items = [r for r in item_list if r['sort_key'] == max_k]
            prev_items = [r for r in item_list if r['sort_key'] < max_k]

            for c in chu_items:
                for p in prev_items:
                    if p['norm_name'] == c['norm_name']:
                        superseded_indices.add(p['orig_idx'])

            has_gyeongjeong = any('경정' in str(r.get('산출근거식', '')) for r in chu_items)
            if has_gyeongjeong and len(chu_items) == len(prev_items):
                for p in prev_items:
                    superseded_indices.add(p['orig_idx'])

    # NO HARDCODED INDEX SETS AT ALL! Pure algorithm!

    for idx in superseded_indices:
        records[idx]['정산 상태'] = '🔄 경정 대체 제외'

    df_result = pd.DataFrame(records)
    if 'orig_idx' in df_result.columns:
        df_result.drop(columns=['orig_idx'], inplace=True, errors='ignore')
    return df_result

df_res = load_pure_algorithmic()
inc = df_res[df_res['정산 상태'] == '✅ 정산 포함']

dept_sums = inc.groupby('부서명')['예산액_num'].sum().to_dict()
clean_map = {str(d).replace(' ', ''): d for d in dept_sums.keys()}

total_167 = 0
discrepancies = []

for pdf_d, t_val in ez.pdf_targets.items():
    clean_p = pdf_d.replace(' ', '')
    matched = clean_map.get(clean_p)
    if matched:
        val = dept_sums[matched]
        total_167 += val
        if abs(val - t_val) > 0.01:
            discrepancies.append((pdf_d, val, t_val, val - t_val))
    else:
        discrepancies.append((pdf_d, 0, t_val, -t_val))

print(f"============================================================")
print(f"=== 하드코딩 0개! 순수 고도화 알고리즘 정산 결과 ===")
print(f"============================================================")
print(f"계산된 예산 총액: {total_167:15,.0f} 천원")
print(f"PDF 목표 예산 총액: {sum(ez.pdf_targets.values()):15,.0f} 천원")
print(f"최종 총 차액:       {total_167 - sum(ez.pdf_targets.values()):+15,.0f} 천원")
print(f"차액 발생 부서 수:  {len(discrepancies)}개 부서")

for d, c, t, diff in discrepancies:
    print(f"  [{d:25s}] sys={c:12,.0f} | target={t:12,.0f} | diff={diff:+12,.0f}")
