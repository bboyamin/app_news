import pandas as pd, numpy as np, re

pdf_targets = {
    '민생경제과': 33194563,
    '노인복지과': 439467167,
    '환경정책과': 37588939,
    '회계과': 254781010,
    '처인구 교통과': 5127532,
    '체육진흥과': 56997912,
    '생태하천과': 16283938,
    '자원순환과': 158362190,
    '자원육성과': 2553826,
    '복지정책과': 233240218,
    '처인구 건설과': 8836030,
    '수지구 세무1과': 553254,
    '인사관리과': 74604888,
    '처인구 자치행정과': 8032997,
    '의정담당관': 4791400,
    '의사입법담당관': 810867,
    '남사읍': 2415532
}

df = pd.read_csv('data/budget_2026.csv', low_memory=False)

big_circle_pattern = re.compile(r'^[○Ο●◎◆■□]')

def get_symbol_level(name):
    s = str(name).strip()
    if big_circle_pattern.match(s): return 1
    return 4

def normalize_item_name(name):
    s = re.sub(r'^[○Ο●◎◆■□οo\-▪ㆍ･\s]+', '', str(name).strip())
    s = re.sub(r'\((성립전\d*차?|간주\d*차?)\)', '', s).strip()
    s_clean = s.replace(' ', '')
    return s_clean if len(s_clean) >= 2 else s.replace(' ', '')

def get_budget_type_sort_key(t_str):
    s = str(t_str).strip()
    if '본예산' in s or '당초' in s or s == '본': return (1, 0, 0, s)
    chugyeong_num = 0
    m_chu = re.search(r'추경(\d+)회', s)
    if m_chu: chugyeong_num = int(m_chu.group(1))
    elif '추경' in s: chugyeong_num = 50
    return (2, chugyeong_num, 0, s)

df_copy = df.copy()
df_copy['정산 상태'] = '✅ 정산 포함'

circle_excluded = set()
for (dept, biz, tong, btype), group in df_copy.groupby(['부서명', '세부사업명', '통계목명', '예산구분'], sort=False):
    names = group['산출근거명'].tolist()
    indices = group.index.tolist()
    n = len(names)
    i = 0
    while i < n:
        if get_symbol_level(names[i]) == 1:
            j = i + 1
            while j < n:
                if get_symbol_level(names[j]) == 1: break
                circle_excluded.add(indices[j])
                j += 1
            i = j - 1
        i += 1

for idx in circle_excluded:
    df_copy.loc[idx, '정산 상태'] = '🔻 소계 중복 제외'

non_circle_df = df_copy[df_copy['정산 상태'] == '✅ 정산 포함'].copy()
non_circle_df['norm_name'] = non_circle_df['산출근거명'].apply(normalize_item_name)
non_circle_df['sort_key'] = non_circle_df['예산구분'].apply(get_budget_type_sort_key)

superseded_indices = set()
for (dept, biz, tong, norm_val), group in non_circle_df.groupby(['부서명', '세부사업명', '통계목명', 'norm_name'], sort=False):
    if len(group['sort_key'].unique()) > 1:
        max_sort = group['sort_key'].max()
        chu_items = group[group['sort_key'] == max_sort]
        has_gyeongjeong = any('경정' in str(r['산출근거식']) for _, r in chu_items.iterrows())
        if has_gyeongjeong:
            replaced = group[group['sort_key'] < max_sort]
            superseded_indices.update(replaced.index)

for (dept, biz, tong), group in non_circle_df.groupby(['부서명', '세부사업명', '통계목명'], sort=False):
    u_types = group['sort_key'].unique()
    if len(u_types) > 1:
        u_max_type = max(u_types)
        chu_items = group[group['sort_key'] == u_max_type]
        prev_items = group[group['sort_key'] < u_max_type]
        for c_idx, c_row in chu_items.iterrows():
            c_norm = c_row['norm_name']
            f = str(c_row['산출근거식']).strip()
            name = str(c_row['산출근거명']).strip()
            exact_m = prev_items[prev_items['norm_name'] == c_norm]
            if not exact_m.empty:
                if '경정' in f or len(chu_items) == len(prev_items):
                    superseded_indices.update(exact_m.index)
            elif '경정' in f or '성립전' in f or '성립전' in name or '간주' in f or '간주' in name:
                if len(chu_items) == 1 and len(prev_items) == 1 and ('경정' in f or f in ['-', '']):
                    superseded_indices.update(prev_items.index)

for idx in superseded_indices:
    df_copy.loc[idx, '정산 상태'] = '🔄 경정 대체 제외'

print('=== 17개 오차 부서 세부 항목 파악 ===')
for dept, target_val in pdf_targets.items():
    sub = df_copy[df_copy['부서명'] == dept]
    inc_sub = sub[sub['정산 상태'] == '✅ 정산 포함']
    c_sum = inc_sub['예산액_num'].sum()
    diff = c_sum - target_val
    print(f'\n--- [{dept}] 시스템={c_sum:,}천원 | PDF={target_val:,}천원 | 차액={diff:+,}천원 ---')
    
    # Check groups in sub where multiple budget types exist
    grouped = sub.groupby(['세부사업명', '통계목명'])
    for (biz, tong), g in grouped:
        inc_g = g[g['정산 상태'] == '✅ 정산 포함']
        if len(inc_g['예산구분'].unique()) > 1:
            print(f'  ▶ [다중 예산구분 정산포함 발생] 세부사업: {biz} | 통계목: {tong}')
            for idx, r in g.iterrows():
                print(f'     - {r["예산구분"]:8s} | {r["산출근거명"]:30s} | 수식: {r["산출근거식"]:25s} | {r["예산액_num"]:10,f}천원 | {r["정산 상태"]}')
