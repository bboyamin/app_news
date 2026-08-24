import pandas as pd, numpy as np, re

pdf_targets = {
    '시민소통관': 130390, '감사관': 178348, '공보관': 4129755, '미디어담당관': 2378526, '안전정책관': 4611192,
    '재난대응담당관': 27585663, '도시기획단': 1570005, '정책기획과': 4737734, '예산과': 61324916, '법무과': 1964306,
    '정보통신과': 7526984, '행정과': 26821847, '자치분권과': 10352961, '인사관리과': 74604888, '민원여권과': 1563464,
    '회계과': 254781010, '재산관리과': 14050830, '세정과': 999709, '징수과': 1148095, '교육청소년과': 64508831,
    '평생교육과': 5855308, '청년정책과': 16409662, '여성가족과': 53266101, '문화예술과': 40538467, '체육진흥과': 56997912,
    '관광과': 1196174, '복지정책과': 233240218, '통합돌봄과': 12285536, '노인복지과': 439467167, '장애인복지과': 148765579,
    '아동보육과': 485956979, '일자리정책과': 10856174, '민생경제과': 33194563, '기업지원과': 12847670, '농업정책과': 79049688,
    '축산과': 13580837, '산림과': 19995918, '동물보호과': 2436164, '도시정책과': 636680, '도시개발과': 331150,
    '도시정비과': 11602367, '토지정보과': 2982850, '주택정책과': 2097290, '공동주택과': 4299643, '주택정비과': 42382,
    '건축과': 409687, '공공건축과': 24148434, '교통정책과': 60493257, '대중교통과': 136787846, '도시철도과': 151097095,
    '물류화물과': 28741417, '건설정책과': 3471432, '도로건설과': 76159443, '도로구조물과': 14688698, '생태하천과': 16283938,
    '반도체정책과': 1442860, '반도체국가산단과': 40708, '반도체일반산단과': 8854548, '미래성장전략과': 6647461, '미래도시과': 51822,
    '기업산단입지과': 3609746, '4차산업융합과': 6977763, '환경정책과': 37588939, '기후대기과': 51574589, '자원순환과': 158362190,
    '위생과': 2317396, '자원육성과': 2553826, '기술지원과': 4973565, '농촌테마과': 4637313, '처인구 보건소 보건정책과': 10048273,
    '처인구 보건소 건강증진과': 14279506, '기흥구 보건소 보건행정과': 13940405, '기흥구 보건소 건강증진과': 12651009, '수지구 보건소 보건행정과': 11709741,
    '수지구 보건소 건강증진과': 6076536, '의정담당관': 4791400, '의사입법담당관': 810867, '처인구 자치행정과': 8032997, '처인구 민원지적과': 612060,
    '처인구 세무1과': 511846, '처인구 세무2과': 331070, '처인구 사회복지과': 220342, '처인구 가정복지과': 5692858, '처인구 산업과': 725338,
    '처인구 환경위생과': 353808, '처인구 교통과': 5127532, '처인구 도시미관과': 10129122, '처인구 건설과': 8836030, '처인구 도로과': 36635364,
    '처인구 도시건축1과': 273650, '처인구 도시건축2과': 255960, '기흥구 자치행정과': 7940724, '기흥구 민원지적과': 558887, '기흥구 세무1과': 571366,
    '기흥구 세무2과': 295136, '기흥구 사회복지과': 106710, '기흥구 가정복지과': 3738236, '기흥구 산업환경과': 229734, '기흥구 교통과': 6748286,
    '기흥구 도시미관과': 7571865, '기흥구 건설과': 6154531, '기흥구 도로과': 30417378, '기흥구 도시건축1과': 98670, '기흥구 도시건축2과': 86190,
    '수지구 자치행정과': 6706458, '수지구 민원지적과': 307620, '수지구 세무1과': 553254, '수지구 세무2과': 217831, '수지구 사회복지과': 77682,
    '수지구 가정복지과': 2975362, '수지구 산업환경과': 131280, '수지구 교통과': 4338542, '수지구 도시미관과': 5175017, '수지구 건설도로과': 22456988,
    '수지구 도시건축과': 124450, '도서관정책과': 11301006, '동부도서관': 4057488, '중부도서관': 3863820, '서부도서관': 3750667, '공원조성과': 32821033,
    '동부공원관리과': 20311583, '서부공원관리과': 17037413, '수도행정과': 1639956, '수도시설과': 525538, '하수행정과': 2065569, '하수시설과': 13814856,
    '하수운영과': 4510859, '차량등록사업소': 1988292, '포곡읍': 1709467, '모현읍': 1856163, '이동읍': 2139200, '남사읍': 2415532, '양지읍': 1932382,
    '원삼면': 2319955, '백암면': 2238757, '중앙동': 592313, '역북동': 512270, '삼가동': 469578, '유림1동': 374674, '유림2동': 394943, '동부동': 489284,
    '신갈동': 703023, '영덕1동': 483146, '영덕2동': 291121, '구갈동': 707472, '상갈동': 390060, '보라동': 844584, '기흥동': 430179, '서농동': 466829,
    '구성동': 725666, '마북동': 498010, '동백1동': 387087, '동백2동': 507476, '동백3동': 809972, '상하동': 434825, '보정동': 531444, '풍덕천1동': 475055,
    '풍덕천2동': 485067, '신봉동': 482087, '죽전1동': 485117, '죽전2동': 446654, '죽전3동': 378680, '동천동': 779218, '상현1동': 387591, '상현2동': 507153,
    '상현3동': 380729, '성복동': 559350
}

df_raw = pd.read_csv('data/budget_2026.csv', low_memory=False)
df = df_raw.copy()
df['예산액_num'] = pd.to_numeric(df['예산액'].astype(str).str.replace(',', '').str.replace('원', '').str.strip(), errors='coerce').fillna(0.0)

big_circle_pattern = re.compile(r'^[○Ο●◎◆■□]')
def get_symbol_level(name): return 1 if big_circle_pattern.match(str(name).strip()) else 4

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

df_copy = df.reset_index(drop=True).copy()
df_copy['정산 상태'] = '✅ 정산 포함'

# 1. Circle deduction within budget types
circle_excluded = set()
for (dept, biz, tong, btype), group in df_copy.groupby(['부서명', '세부사업명', '통계목명', '예산구분'], sort=False):
    records = group[['산출근거명']].to_dict('records')
    orig_indices = group.index.tolist()
    n = len(records)
    i = 0
    while i < n:
        if records[i]['산출근거명'] and get_symbol_level(records[i]['산출근거명']) == 1:
            j = i + 1
            while j < n:
                if get_symbol_level(records[j]['산출근거명']) == 1: break
                circle_excluded.add(orig_indices[j])
                j += 1
            i = j - 1
        i += 1

for idx in circle_excluded:
    df_copy.loc[idx, '정산 상태'] = '🔻 소계 중복 제외'

non_circle = df_copy[df_copy['정산 상태'] == '✅ 정산 포함'].copy()
non_circle['norm_name'] = non_circle['산출근거명'].apply(normalize_item_name)
non_circle['sort_key'] = non_circle['예산구분'].apply(get_budget_type_sort_key)

superseded_indices = set()

for (dept, biz, tong), group in non_circle.groupby(['부서명', '세부사업명', '통계목명'], sort=False):
    u_types = group['sort_key'].unique()
    if len(u_types) > 1:
        u_max_type = max(u_types)
        chu_items = group[group['sort_key'] == u_max_type]
        prev_items = group[group['sort_key'] < u_max_type]
        
        has_gyeongjeong = any('경정' in str(r['산출근거식']) for _, r in chu_items.iterrows())
        if has_gyeongjeong:
            superseded_indices.update(prev_items.index)
        else:
            # Check 1:1 item match
            for c_idx, c_row in chu_items.iterrows():
                c_norm = c_row['norm_name']
                exact_m = prev_items[prev_items['norm_name'] == c_norm]
                if not exact_m.empty:
                    superseded_indices.update(exact_m.index)

for idx in superseded_indices:
    df_copy.loc[idx, '정산 상태'] = '🔄 경정 대체 제외'

inc = df_copy[df_copy['정산 상태'] == '✅ 정산 포함']
calc_sum_167 = 0

csv_dept_map = {str(d).replace(' ', ''): d for d in inc['부서명'].dropna().unique()}

discrepancies = []
for pdf_dept, target_val in pdf_targets.items():
    clean_p = pdf_dept.replace(' ', '')
    matched = csv_dept_map.get(clean_p)
    if matched:
        c_val = inc[inc['부서명'] == matched]['예산액_num'].sum()
        calc_sum_167 += c_val
        if c_val != target_val:
            discrepancies.append((pdf_dept, c_val, target_val, c_val - target_val))

print(f"=== 통계목 경정 대체 통합 규칙 적용 결과 ===")
print(f"CALCULATED SUM (167 DEPTS): {calc_sum_167:15,f} 천원")
print(f"TARGET SUM (167 DEPTS):     {sum(pdf_targets.values()):15,d} 천원")
print(f"TOTAL DIFFERENCE:           {calc_sum_167 - sum(pdf_targets.values()):+15,f} 천원")
print(f"DISCREPANCY DEPT COUNT:    {len(discrepancies)}개 부서")

for d, c, t, diff in sorted(discrepancies, key=lambda x: abs(x[3]), reverse=True):
    print(f"  - {d:25s}: sys={c:12,f} | pdf={t:12,d} | diff={diff:+12,f}")
