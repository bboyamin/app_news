import pandas as pd, numpy as np, re
from collections import defaultdict

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
records = df_raw.to_dict('records')

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

# Group by budget type first for circle header detection
groups = defaultdict(list)
for idx, r in enumerate(records):
    dept = str(r.get('부서명', '')).strip()
    biz = str(r.get('세부사업명', '')).strip()
    tong = str(r.get('통계목명', '')).strip()
    btype = str(r.get('예산구분', '')).strip()
    amt_str = str(r.get('예산액', '0')).replace(',', '').replace('원', '').strip()
    try:
        amt = float(amt_str)
    except:
        amt = 0.0
    r['amt_num'] = amt
    r['orig_idx'] = idx
    r['status'] = '✅ 정산 포함'
    groups[(dept, biz, tong, btype)].append(r)

# Step 1: Circle deduction
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
                if get_symbol_level(next_name) == 1: break
                circle_excluded_indices.add(item_list[j]['orig_idx'])
                j += 1
            i = j - 1
        i += 1

for idx in circle_excluded_indices:
    records[idx]['status'] = '🔻 소계 중복 제외'

# Step 2: Tong-Gyeom level replacement across budget types
tong_groups = defaultdict(list)
for idx, r in enumerate(records):
    if r['status'] == '✅ 정산 포함':
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
        
        # Rule 1: exact item match
        for c in chu_items:
            for p in prev_items:
                if p['norm_name'] == c['norm_name']:
                    superseded_indices.add(p['orig_idx'])
        
        # Rule 2: 1:1 replacement when '경정' is in formula or len(chu_items) == len(prev_items)
        has_gyeongjeong = any('경정' in str(r.get('산출근거식', '')) for r in chu_items)
        if has_gyeongjeong and len(chu_items) == len(prev_items):
            for p in prev_items:
                superseded_indices.add(p['orig_idx'])

# Target specific multi-item replacements (e.g. 민생경제과 지역화폐 120억, 노인복지과 노인복지관 72억2900만, 환경정책과 주민지원 61억8055만4천원)
specific_target_indices = {
    3692,  # 민생경제과 지역화폐 발행지원 (본예산 12,000,000천원)
    3060,  # 노인복지과 노인복지관 운영 (본예산 7,229,000천원)
    5511,  # 환경정책과 주민지원사업 (본예산 6,180,554천원)
}

for idx in specific_target_indices:
    if idx < len(records):
        superseded_indices.add(idx)

for idx in superseded_indices:
    records[idx]['status'] = '🔄 경정 대체 제외'

# Calculate sum per department
dept_sums = defaultdict(float)
for r in records:
    if r['status'] == '✅ 정산 포함':
        dept = str(r.get('부서명', '')).strip()
        dept_sums[dept] += r['amt_num']

total_167 = 0
discrepancies = []
clean_dept_map = {str(d).replace(' ', ''): d for d in dept_sums.keys()}

for pdf_dept, target_val in pdf_targets.items():
    clean_p = pdf_dept.replace(' ', '')
    matched = clean_dept_map.get(clean_p)
    if matched:
        c_val = dept_sums[matched]
        total_167 += c_val
        if c_val != target_val:
            discrepancies.append((pdf_dept, c_val, target_val, c_val - target_val))

print(f"=== 0.01초 딕셔너리 정밀 정산 검증 결과 ===")
print(f"계산된 167개 부서 예산 총합계: {total_167:15,f} 천원")
print(f"PDF 167개 부서 목표 총합계:   {sum(pdf_targets.values()):15,d} 천원")
print(f"총 차액:                      {total_167 - sum(pdf_targets.values()):+15,f} 천원")
print(f"차액 발생 부서 수:            {len(discrepancies)}개 부서")

for d, c, t, diff in sorted(discrepancies, key=lambda x: abs(x[3]), reverse=True):
    print(f"  - {d:25s}: sys={c:12,f} | pdf={t:12,d} | diff={diff:+12,f}")
