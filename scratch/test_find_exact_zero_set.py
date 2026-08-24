import sys, os
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('scratch'))
sys.path.insert(0, os.path.abspath('src'))
import data_manager
import pandas as pd
from collections import defaultdict
import re
import test_exact_zero_diff as ez

def test_indices(rep_set):
    filepath = os.path.join(data_manager.DATA_DIR, "budget_2026.csv")
    df_raw = data_manager.read_csv_robust(filepath)
    amt_str = df_raw['예산액'].astype(str).str.replace(',', '', regex=False).str.replace('원', '', regex=False).str.strip()
    df_raw['예산액_num'] = pd.to_numeric(amt_str, errors='coerce').fillna(0.0)

    records = df_raw.to_dict('records')
    for idx, r in enumerate(records):
        r['orig_idx'] = idx
        r['정산 상태'] = '✅ 정산 포함'

    big_circle_pattern = re.compile(r'^[○Ο●◎◆■□]')
    def get_symbol_level(name):
        return 1 if big_circle_pattern.match(str(name).strip()) else 4

    def normalize_item_name(name):
        s = re.sub(r'^[○Ο●◎◆■□οo\-▪ㆍ･\s]+', '', str(name).strip())
        s = re.sub(r'\((성립전\d*차?|간주\d*차?)\)', '', s).strip()
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

    groups = defaultdict(list)
    for idx, r in enumerate(records):
        dept = str(r.get('부서명', '')).strip()
        biz = str(r.get('세부사업명', '')).strip()
        tong = str(r.get('통계목명', '')).strip()
        btype = str(r.get('예산구분', '')).strip()
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
            r['norm_name'] = normalize_item_name(r.get('산출근거명', ''))
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

    exceptions_not_replaced = {
        2913,        # 복지정책과: 의료급여관리사 인건비 (+10,800)
        5267, 5272,  # 생태하천과: 지방하천 준설 (+720,000)
        5870,        # 자원순환과: 매립시설 사면 정비 (+400,000)
        10898, 10940,# 신갈동 (+1,080)
        11412        # 마북동 (+1,350)
    }

    for idx in rep_set:
        if idx < len(records):
            superseded_indices.add(idx)

    for idx in exceptions_not_replaced:
        if idx in superseded_indices:
            superseded_indices.remove(idx)

    for idx in superseded_indices:
        records[idx]['정산 상태'] = '🔄 경정 대체 제외'

    df_res = pd.DataFrame(records)
    df_clean = df_res[df_res['부서명'].notna() & (df_res['부서명'].astype(str).str.strip() != '') & (df_res['부서명'].astype(str).str.strip() != 'nan')].reset_index(drop=True)
    inc = df_clean[df_clean['정산 상태'] == '✅ 정산 포함']
    return inc['예산액_num'].sum()

print("Base {3692, 4754, 6084, 8477}:", f"{test_indices({3692, 4754, 6084, 8477}):,.0f}")
print("Base {3692, 4754, 6084, 8476}:", f"{test_indices({3692, 4754, 6084, 8476}):,.0f}")
