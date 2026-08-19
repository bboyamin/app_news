import os
import sys
import re
import pandas as pd
import numpy as np
import streamlit as st

# 데이터 관리자 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import data_manager

# ==========================================
# 0. 애플리케이션 환경 설정 및 미니멀 테마
# ==========================================
st.set_page_config(
    page_title="스마트 세출 예산서 통합 검색 포털",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 데이터 디렉토리 및 2026 기본 데이터 확인
data_manager.ensure_data_dir()

# 시선집중 UX/UI 프리미엄 오피스 테마 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stApp {
        background-color: #f8fafc;
    }

    /* 상단 미니멀 헤더 */
    .search-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #0f766e 100%);
        padding: 22px 28px;
        border-radius: 14px;
        color: #ffffff;
        margin-bottom: 22px;
        box-shadow: 0 6px 16px rgba(30, 58, 138, 0.15);
    }
    
    .search-title {
        font-size: 24px;
        font-weight: 800;
        margin: 0 0 6px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .search-subtitle {
        font-size: 13.5px;
        opacity: 0.92;
        margin: 0;
    }

    /* 요약 메트릭 카드 */
    .metric-badge {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 14px 18px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
    }
    .metric-label {
        font-size: 12.5px;
        color: #64748b;
        font-weight: 600;
    }
    .metric-value {
        font-size: 21px;
        font-weight: 800;
        color: #1e3a8a;
    }

    /* 🌟 파란색 테두리 검색 박스 스타일링 (검색창 내포 단일 카드) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%) !important;
        border: 2.5px solid #2563eb !important;
        border-radius: 16px !important;
        padding: 22px 26px !important;
        box-shadow: 0 10px 25px rgba(37, 99, 235, 0.12) !important;
        margin-top: 10px !important;
        margin-bottom: 16px !important;
    }

    /* 🌟 시선강탈 초대형 텍스트 입력 박스 커스텀 CSS (68px 높이 & 20px 대형 폰트) */
    div[data-testid="stTextInput"] {
        margin-top: 8px;
        margin-bottom: 6px;
    }

    div[data-baseweb="input"] {
        border-radius: 14px !important;
        border: 3.5px solid #2563eb !important;
        background-color: #ffffff !important;
        padding: 8px 18px !important;
        height: 68px !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.16) !important;
        transition: all 0.25s ease-in-out !important;
    }
    
    div[data-baseweb="input"]:hover {
        border-color: #1d4ed8 !important;
        box-shadow: 0 8px 25px rgba(29, 78, 216, 0.22) !important;
    }
    
    div[data-baseweb="input"]:focus-within {
        border-color: #1d4ed8 !important;
        background-color: #ffffff !important;
        box-shadow: 0 0 0 5px rgba(37, 99, 235, 0.3), 0 10px 30px rgba(37, 99, 235, 0.25) !important;
    }
    
    div[data-baseweb="input"] input {
        font-size: 20px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        padding-left: 10px !important;
    }

    div[data-baseweb="input"] input::placeholder {
        color: #475569 !important;
        font-size: 17.5px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 사이드바 - 회계연도 선택 & CSV 업로드 관리
# ==========================================
st.sidebar.markdown("## 🔍 예산 검색 설정")

available_years = data_manager.get_available_years()
if not available_years:
    available_years = [2026]

selected_year = st.sidebar.selectbox(
    "📅 조회 회계연도",
    available_years,
    index=0
)

# 데이터 로드 (RAM 캐싱 적용)
df_year = data_manager.load_year_data(selected_year)

# 사이드바: 최신 예산서 CSV 직접 업로드 모듈
st.sidebar.markdown("---")
with st.sidebar.expander("📤 [관리자] 새 예산서 CSV 업로드", expanded=False):
    st.caption("예산편성 후 최종 합본예산서 CSV 파일을 업로드하시면 연도별로 자동 정제·적용됩니다.")
    upload_year = st.number_input("등록할 연도", min_value=2020, max_value=2035, value=selected_year+1, step=1)
    uploaded_file = st.file_uploader("합본예산서 CSV 파일 선택", type=["csv"])
    
    if uploaded_file is not None:
        if st.button("💾 데이터 자동 정제 및 저장 적용", type="primary", use_container_width=True):
            try:
                cnt = data_manager.save_uploaded_budget_file(uploaded_file, upload_year)
                st.success(f"🎉 {upload_year}년 예산서 {cnt:,}건 무결 정제 등록 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ 업로드 정제 실패: {e}")

    # 등록된 연도 목록 및 안전 삭제 모듈
    st.markdown("---")
    st.caption("📂 저장된 연도별 예산서 목록")
    for y in available_years:
        col_y1, col_y2 = st.columns([3, 1])
        col_y1.write(f"• {y}년 예산서")
        if col_y2.button("삭제", key=f"del_{y}"):
            if len(available_years) <= 1:
                st.sidebar.warning("⚠️ 최소 1개 이상의 예산서 데이터가 유지되어야 합니다.")
            else:
                data_manager.delete_year_data(y)
                st.sidebar.success(f"🗑️ {y}년 예산서 데이터 삭제 완료!")
                st.rerun()

# ==========================================
# 2. 메인 페이지 헤더
# ==========================================
st.markdown(f"""
<div class="search-header">
    <div class="search-title">🔍 {selected_year}년 세출 예산서 스마트 통합 검색</div>
    <div class="search-subtitle">부서명, 세부사업명, 통계목, 산출근거 수식을 입력하여 예산 내역과 단가 수식을 확인하세요.</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 3. 드롭다운 필터 바 (회계구분 / 소관부서 / 예산확정 순 정렬 예산구분)
# ==========================================
valid_acct_df = df_year[df_year['회계명'].str.endswith('회계', na=False)]
acct_order = valid_acct_df.groupby('회계명')['예산액_억원'].sum().sort_values(ascending=False).index.tolist()
all_accts = ["전체"] + acct_order

csv_dept_list = []
for d in df_year['부서명'].dropna().unique():
    d_str = str(d).strip()
    if d_str and d_str not in ['0', '-', 'nan', 'N/A']:
        if d_str not in csv_dept_list:
            csv_dept_list.append(d_str)

all_depts = ["전체"] + csv_dept_list

# 예산확정 순 정렬 알고리즘 (본예산 -> 추경1회 -> 추경2회 -> 추경3회... -> 이월예산)
raw_type_list = [str(t).strip() for t in df_year['예산구분'].dropna().unique() if str(t).strip() not in ['-', 'nan', 'N/A', '']]

def get_budget_type_sort_key(t_str):
    s = str(t_str).strip()
    if '본예산' in s or '당초' in s or s == '본':
        return (1, 0, s)
    
    m = re.search(r'(\d+)', s)
    if '추경' in s or '추가경정' in s:
        if m:
            num = int(m.group(1))
            return (2, num, s)
        elif '정리' in s or '최종' in s:
            return (2, 99, s)
        else:
            return (2, 50, s)
            
    if '이월' in s:
        return (3, 0, s)
        
    return (4, 0, s)

sorted_budget_types = sorted(raw_type_list, key=get_budget_type_sort_key)
all_budget_types = ["전체"] + sorted_budget_types

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    sel_acct = st.selectbox("🏛️ 회계구분 선택", all_accts, index=0)

with col_f2:
    sel_dept = st.selectbox("🏢 소관 부서 선택", all_depts, index=0)

with col_f3:
    sel_budget_type = st.selectbox("📑 예산구분 선택", all_budget_types, index=0)

# 필터 적용
filtered_df = df_year.copy()
if sel_acct != "전체":
    filtered_df = filtered_df[filtered_df['회계명'] == sel_acct]
if sel_dept != "전체":
    filtered_df = filtered_df[filtered_df['부서명'] == sel_dept]
if sel_budget_type != "전체":
    filtered_df = filtered_df[filtered_df['예산구분'] == sel_budget_type]

# ==========================================
# 4. 실시간 통합 키워드 검색창 (파란색 테두리 박스 내부 단일 내포 구조)
# ==========================================
st.markdown("---")
with st.container(border=True):
    st.markdown("""
    <div style="font-size: 18px; font-weight: 800; color: #1e3a8a; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;">
        <span>🔎 스마트 세출 예산 통합 키워드 검색</span>
    </div>
    <div style="font-size: 13.5px; color: #475569; margin-bottom: 10px;">
        💡 사업명, 소관 부서, 세부항목, 산출근거 수식 단어를 입력하시면 <b>10개 필드에서 0.1초 만에 실시간 탐색</b>됩니다.
    </div>
    """, unsafe_allow_html=True)
    
    search_keyword = st.text_input(
        "검색어 입력", 
        placeholder="원하시는 검색어를 입력하세요 (예: 정보화 교육, 주차장, 수당, 마스크, 연수, 용역, 자치행정과...)",
        label_visibility="collapsed"
    )

search_df = filtered_df.copy()
if search_keyword.strip():
    kw_raw = search_keyword.strip()
    kw_nospace = kw_raw.replace(" ", "")
    tokens = [t for t in kw_raw.split() if len(t) > 0]
    
    target_fields = ['부서명', '세부사업명', '정책사업명', '단위사업명', '편성목명', '통계목명', '산출근거명', '산출근거식', '분야명', '부문명']
    
    final_mask = pd.Series(False, index=search_df.index)
    for col in target_fields:
        mask_a = search_df[col].str.contains(kw_raw, case=False, na=False)
        mask_b = search_df[col].astype(str).str.replace(" ", "", regex=False).str.contains(kw_nospace, case=False, na=False)
        col_mask = mask_a | mask_b
        
        if len(tokens) > 1:
            token_mask = pd.Series(True, index=search_df.index)
            for t in tokens:
                token_mask = token_mask & search_df[col].str.contains(t, case=False, na=False)
            col_mask = col_mask | token_mask
            
        final_mask = final_mask | col_mask
        
    search_df = search_df[final_mask]

# ==========================================
# 🌟 5. 지능형 정규화 매칭 다층 예산 정밀 정산 엔진
# Layer 1: 동그라미 계층 소계 중복 감지 및 자동 차감
# Layer 2: 정규화 명칭 기반 경정 대체 버전 통합 정산 (괄호/부가문구 유사 매칭)
# ==========================================
def is_big_circle(name):
    s = str(name).strip()
    return bool(re.match(r'^[○Ο●◎◆■□]', s))

def normalize_item_name(name):
    """
    'Ο시민정보화교육' ↔ 'Ο시민정보화교육(경기도 수행 부담금)' 등
    괄호 및 부가 기호가 달라도 핵심 명칭을 정규화하여 경정 대체 중복을 100% 매칭
    """
    s = re.sub(r'^[○Ο●◎◆■□οo\-▪ㆍ･\s]+', '', str(name).strip())
    s_no_paren = re.sub(r'\(.*?\)|\[.*?\]', '', s).strip()
    s_clean = s_no_paren.replace(" ", "")
    return s_clean if len(s_clean) >= 2 else s.replace(" ", "")

def deduplicate_circle_hierarchy(target_df):
    if target_df.empty:
        return target_df
    
    records = target_df.to_dict('records')
    excluded = set()
    
    i = 0
    n = len(records)
    while i < n:
        c_name = records[i]['산출근거명']
        if is_big_circle(c_name):
            big_budget = records[i]['예산액_num']
            small_sum = 0
            small_idx = []
            j = i + 1
            while j < n:
                next_name = records[j]['산출근거명']
                if is_big_circle(next_name):
                    break
                small_sum += records[j]['예산액_num']
                small_idx.append(j)
                j += 1
            
            if small_idx and (abs(small_sum - big_budget) <= 5 or abs(small_sum - big_budget) / max(big_budget, 1) <= 0.03):
                excluded.add(i)
                i = j
                continue
        i += 1
        
    valid = [records[k] for k in range(n) if k not in excluded]
    return pd.DataFrame(valid)

def calculate_accurate_budget_sum(target_df, is_all_budget_types=True):
    if target_df.empty:
        return 0.0, target_df
        
    # 1단계: 동그라미 계층 구조 소계 중복 제외
    cleaned_df = deduplicate_circle_hierarchy(target_df)
    
    if not is_all_budget_types:
        return float(cleaned_df['예산액_num'].sum()), cleaned_df
        
    # 2단계: 정규화 명칭 기반 경정 대체 버전 통합 정산 (부서+세부사업+통계목+norm_name)
    temp = cleaned_df.copy()
    temp['norm_name'] = temp['산출근거명'].apply(normalize_item_name)
    temp['sort_key'] = temp['예산구분'].apply(get_budget_type_sort_key)
    
    group_cols = ['부서명', '세부사업명', '통계목명', 'norm_name']
    idx_latest = temp.groupby(group_cols)['sort_key'].idxmax()
    latest_df = temp.loc[idx_latest]
    
    accurate_sum = float(latest_df['예산액_num'].sum())
    return accurate_sum, latest_df

is_all_types_selected = (sel_budget_type == "전체")
total_budget_thousand, latest_dedup_df = calculate_accurate_budget_sum(search_df, is_all_budget_types=is_all_types_selected)
total_budget_billion = total_budget_thousand / 100000.0

col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.markdown(f"""
    <div class="metric-badge">
        <div class="metric-label">검색된 예산 내역 (이력 포함)</div>
        <div class="metric-value">{len(search_df):,} 건</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    badge_sub_label = "(소계 및 경정 중복 정밀 정산 반영)" if is_all_types_selected else f"({sel_budget_type} 소계중복 정산)"
    st.markdown(f"""
    <div class="metric-badge">
        <div class="metric-label">실효 예산 정산 합계 <span style="font-size:11px; color:#2563eb;">{badge_sub_label}</span></div>
        <div class="metric-value">{total_budget_billion:,.2f} 억 원 <span style="font-size:13px; font-weight:500; color:#64748b;">({total_budget_thousand:,.0f} 천원)</span></div>
    </div>
    """, unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""
    <div class="metric-badge">
        <div class="metric-label">조회 대상 회계연도</div>
        <div class="metric-value">{selected_year} 년도</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 깔끔하고 단정한 프로덕션 검색 결과 테이블용 컬럼 정의
display_cols = ['예산구분', '부서명', '회계명', '세부사업명', '편성목명', '통계목명', '산출근거명', '산출근거식', '예산액_num', '의무/재량구분']

col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.markdown(f"📋 **검색 결과 목록** (총 {len(search_df):,}건 - 세부내역 및 이력 100% 표출)")
with col_t2:
    safe_kw = re.sub(r'[^\w가-힣]', '_', search_keyword).strip('_')
    download_filename = f"예산검색결과_{selected_year}_{safe_kw if safe_kw else '전체'}.csv"
    
    download_df = search_df[display_cols].copy()
    download_df['예산액(천원)'] = download_df['예산액_num'].apply(lambda x: f"{int(x):,}")
    download_df = download_df.drop(columns=['예산액_num'])
    
    csv_bytes = download_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    
    st.download_button(
        label="📥 엑셀/CSV 다운로드",
        data=csv_bytes,
        file_name=download_filename,
        mime="text/csv",
        key="btn_download_csv"
    )

# 단정하고 깔끔한 기본 프로덕션 테이블 표출
total_cnt = len(search_df)
show_table_df = search_df[display_cols].head(200).copy()
show_table_df['예산액_num'] = show_table_df['예산액_num'].astype(int)

if total_cnt > 200:
    st.caption(f"💡 전체 {total_cnt:,}건 중 상위 200건을 표출합니다. (전체 {total_cnt:,}건 내역은 우측 📥 '엑셀/CSV 다운로드' 버튼을 누르시면 100% 엑셀 파일로 바로 다운로드됩니다)")

st.dataframe(
    show_table_df,
    use_container_width=True,
    height=450,
    column_config={
        "예산액_num": st.column_config.NumberColumn(
            "예산액 (천원)",
            format="%,d",
            help="천원 단위 콤마 표기 (오른쪽 정렬)",
        ),
        "산출근거식": st.column_config.TextColumn("산출근거 수식 (단가*수량)", width="medium")
    }
)

# ==========================================
# 6. 스마트 실시간 예산 정산 분석 패널 (소계 및 경정 중복 정제 데이터 연동)
# ==========================================
if not search_df.empty:
    st.markdown("---")
    st.markdown("### 📊 검색 예산 실시간 정산 분석 패널")
    
    tab_dept, tab_stat, tab_type = st.tabs([
        "🏢 부서별 예산 정산 집계 Top 10",
        "🏷️ 주요 통계목별 예산 비중",
        "⚖️ 의무/재량 지출 구조"
    ])
    
    # 계층 및 정규화 경정 2중 정제 데이터셋 사용
    analysis_base_df = latest_dedup_df
    
    # [탭 1] 부서별 예산 정산 집계 Top 10
    with tab_dept:
        dept_group = analysis_base_df.groupby('부서명').agg(
            예산합계_천원=('예산액_num', 'sum'),
            항목수=('예산액_num', 'count')
        ).reset_index()
        dept_group['예산합계_억원'] = (dept_group['예산합계_천원'] / 100000.0).round(2)
        dept_group = dept_group.sort_values(by='예산합계_천원', ascending=False)
        
        col_d1, col_d2 = st.columns([1, 1])
        with col_d1:
            st.markdown("##### 🏢 부서별 정산 예산 규모 순위 (상위 10개 부서)")
            chart_df = dept_group.head(10).set_index('부서명')[['예산합계_억원']]
            st.bar_chart(chart_df)
            
        with col_d2:
            st.markdown("##### 📋 부서별 정산 예산 요약표")
            dept_display = dept_group.head(10).copy()
            dept_display.columns = ['부서명', '예산합계(천원)', '건수', '예산합계(억원)']
            st.dataframe(
                dept_display[['부서명', '예산합계(억원)', '예산합계(천원)', '건수']],
                use_container_width=True,
                height=300,
                column_config={
                    "예산합계(천원)": st.column_config.NumberColumn(format="%,d"),
                    "예산합계(억원)": st.column_config.NumberColumn(format="%.2f 억원")
                }
            )

    # [탭 2] 주요 통계목별 예산 비중
    with tab_stat:
        stat_group = analysis_base_df.groupby('통계목명').agg(
            예산합계_천원=('예산액_num', 'sum'),
            항목수=('예산액_num', 'count')
        ).reset_index()
        stat_group['예산합계_억원'] = (stat_group['예산합계_천원'] / 100000.0).round(2)
        stat_group = stat_group.sort_values(by='예산합계_천원', ascending=False)
        
        col_s1, col_s2 = st.columns([1, 1])
        with col_s1:
            st.markdown("##### 🏷️ 통계목별 정산 예산 규모 순위 (상위 10개 비목)")
            stat_chart_df = stat_group.head(10).set_index('통계목명')[['예산합계_억원']]
            st.bar_chart(stat_chart_df)
            
        with col_s2:
            st.markdown("##### 📋 통계목별 정산 예산 요약표")
            stat_display = stat_group.head(10).copy()
            stat_display.columns = ['통계목명', '예산합계(천원)', '건수', '예산합계(억원)']
            st.dataframe(
                stat_display[['통계목명', '예산합계(억원)', '예산합계(천원)', '건수']],
                use_container_width=True,
                height=300,
                column_config={
                    "예산합계(천원)": st.column_config.NumberColumn(format="%,d"),
                    "예산합계(억원)": st.column_config.NumberColumn(format="%.2f 억원")
                }
            )

    # [탭 3] 의무/재량 지출 구조
    with tab_type:
        type_group = analysis_base_df.groupby('의무/재량구분').agg(
            예산합계_천원=('예산액_num', 'sum'),
            항목수=('예산액_num', 'count')
        ).reset_index()
        type_group['예산합계_억원'] = (type_group['예산합계_천원'] / 100000.0).round(2)
        
        col_t1, col_t2 = st.columns([1, 1])
        with col_t1:
            st.markdown("##### ⚖️ 의무 vs 재량 정산 예산 비중 (억원)")
            type_chart_df = type_group.set_index('의무/재량구분')[['예산합계_억원']]
            st.bar_chart(type_chart_df)
            
        with col_t2:
            st.markdown("##### 📋 지출 구조 정산 요약표")
            type_group.columns = ['지출구분', '예산합계(천원)', '건수', '예산합계(억원)']
            st.dataframe(
                type_group[['지출구분', '예산합계(억원)', '예산합계(천원)', '건수']],
                use_container_width=True,
                height=220,
                column_config={
                    "예산합계(천원)": st.column_config.NumberColumn(format="%,d"),
                    "예산합계(억원)": st.column_config.NumberColumn(format="%.2f 억원")
                }
            )
