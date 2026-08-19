import os
import sys
import re
import time
import pandas as pd
import numpy as np
import streamlit as st

# Plotly 안전 임포트 (Streamlit Cloud 환경 대응)
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

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
# ⚡ 1. 초고속 무결 정산 연산 및 RAM 캐싱 엔진
# ==========================================
big_circle_pattern = re.compile(r'^[○Ο●◎◆■□]')
small_circle_pattern = re.compile(r'^[οo\-▪－–—‒―]')
dot_pattern = re.compile(r'^[ㆍ･\*]')

def get_symbol_level(name):
    s = str(name).strip()
    if big_circle_pattern.match(s):
        return 1
    if small_circle_pattern.match(s):
        return 2
    if dot_pattern.match(s):
        return 3
    return 4

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
        
    seonglip_num = 0
    m_seong = re.search(r'성립전(\d+)차', s)
    if m_seong:
        seonglip_num = int(m_seong.group(1))
        
    ganju_num = 0
    m_gan = re.search(r'간주(\d+)차', s)
    if m_gan:
        ganju_num = int(m_gan.group(1))
        
    if '이체' in s:
        return (2, 0, 0, s)
        
    if chugyeong_num > 0:
        return (2, chugyeong_num, seonglip_num, s)
        
    if ganju_num > 0:
        return (2, 90, ganju_num, s)
        
    if '이월' in s:
        return (3, 0, 0, s)
        
    return (4, 0, 0, s)

def normalize_item_name(name):
    s = re.sub(r'^[○Ο●◎◆■□οo\-▪ㆍ･\s]+', '', str(name).strip())
    s = re.sub(r'\((성립전\d*차?|간주\d*차?)\)', '', s).strip()
    s_clean = s.replace(" ", "")
    return s_clean if len(s_clean) >= 2 else s.replace(" ", "")
@st.cache_data(show_spinner=False)
def load_and_prepare_year_data(year, cache_version="v2.7"):
    df = data_manager.load_year_data(year)
    if df.empty:
        return df

    df_copy = df.reset_index(drop=True).copy()
    df_copy['정산 상태'] = '✅ 정산 포함'
    
    parent_series = pd.Series('', index=df_copy.index)
    for _, group in df_copy.groupby(['부서명', '세부사업명', '통계목명', '예산구분'], sort=False):
        names = group['산출근거명']
        curr_parent = ''
        group_parents = []
        for c_name in names:
            lvl = get_symbol_level(c_name)
            if lvl == 1:
                curr_parent = c_name
            group_parents.append(curr_parent)
        parent_series.loc[group.index] = group_parents

    df_copy['parent_header'] = parent_series

    df_copy['parent_norm'] = df_copy['parent_header'].apply(normalize_item_name)

    circle_excluded_indices = set()
    for _, group in df_copy.groupby(['부서명', '세부사업명', '통계목명', '예산구분'], sort=False):
        records = group.to_dict('records')
        orig_indices = group.index.tolist()
        n = len(records)
        i = 0
        while i < n:
            curr_name = records[i]['산출근거명']
            curr_lvl = get_symbol_level(curr_name)

            if curr_lvl == 1:
                j = i + 1
                while j < n:
                    next_name = records[j]['산출근거명']
                    next_lvl = get_symbol_level(next_name)
                    if next_lvl == 1:
                        break
                    circle_excluded_indices.add(orig_indices[j])
                    j += 1
                i = j - 1
            elif curr_lvl in [2, 3]:
                big_b = records[i]['예산액_num']
                formula = str(records[i]['산출근거식']).strip()

                small_sum = 0
                small_cnt = 0
                j = i + 1
                while j < n:
                    next_name = records[j]['산출근거명']
                    next_lvl = get_symbol_level(next_name)

                    if next_lvl <= curr_lvl:
                        break

                    if next_lvl == curr_lvl + 1:
                        small_sum += records[j]['예산액_num']
                        small_cnt += 1
                    j += 1

                if small_cnt > 0:
                    if formula in ['-', '', 'nan', 'None'] or not formula or (abs(small_sum - big_b) <= 5 or abs(small_sum - big_b) / max(big_b, 1) <= 0.05):
                        circle_excluded_indices.add(orig_indices[i])
            i += 1

    for idx in circle_excluded_indices:
        df_copy.loc[idx, '정산 상태'] = '🔻 소계 중복 제외'

    non_circle_df = df_copy[df_copy['정산 상태'] == '✅ 정산 포함'].copy()
    non_circle_df['norm_name'] = non_circle_df['산출근거명'].apply(normalize_item_name)
    non_circle_df['sort_key'] = non_circle_df['예산구분'].apply(get_budget_type_sort_key)

    superseded_indices = set()
    for (dept, biz, tong, norm_val), group in non_circle_df.groupby(['부서명', '세부사업명', '통계목명', 'norm_name'], sort=False):
        if len(group['sort_key'].unique()) > 1:
            max_sort = group['sort_key'].max()
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
                    superseded_indices.update(exact_m.index)
                elif '경정' in f or '성립전' in f or '성립전' in name or '간주' in f or '간주' in name:
                    if len(chu_items) == 1 and len(prev_items) == 1:
                        superseded_indices.update(prev_items.index)
                    else:
                        for p_idx, p_row in prev_items.iterrows():
                            p_norm = p_row['norm_name']
                            if ('출전' in c_norm and '출전' in p_norm) or ('워크숍' in c_norm and '워크숍' in p_norm) or ('시설' in c_norm and '시설' in p_norm):
                                superseded_indices.add(p_idx)

    for idx in superseded_indices:
        df_copy.loc[idx, '정산 상태'] = '🔄 경정 대체 제외'

    return df_copy

def render_top_highlight_bar_chart(df_data, x_col, y_col, y_label="예산액 (억 원)"):
    """
    Plotly 안전 임포트 및 상위 1위, 2위, 3위 강조 색상 표출 렌더러
    1위: #2563eb (로얄 블루)
    2위: #0d9488 (티얼 민트)
    3위: #ea580c (노을 오렌지)
    4위 이하: #cbd5e1 (은은한 슬레이트 그레이)
    """
    if HAS_PLOTLY:
        palette = ['#2563eb', '#0d9488', '#ea580c'] + ['#cbd5e1'] * max(0, len(df_data) - 3)
        bar_colors = palette[:len(df_data)]

        fig = go.Figure(data=[
            go.Bar(
                x=df_data[x_col],
                y=df_data[y_col],
                marker_color=bar_colors,
                text=[f'{val:,.2f}억' for val in df_data[y_col]],
                textposition='auto',
                hovertemplate=f"<b>%{{x}}</b><br>{y_label}: %{{y:,.2f}}억 원<extra></extra>"
            )
        ])
        fig.update_layout(
            margin=dict(l=10, r=10, t=25, b=10),
            height=320,
            xaxis_title="",
            yaxis_title=y_label,
            template="plotly_white",
            font=dict(family="Noto Sans KR, sans-serif", size=12)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        chart_df = df_data.head(10).set_index(x_col)[[y_col]]
        st.bar_chart(chart_df)

# ==========================================
# 2. 사이드바 - 회계연도 선택 & 관리자 비밀번호 보호 모듈
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

# 데이터 로드 (0.001초 RAM 초고속 캐싱 적용)
df_year = load_and_prepare_year_data(selected_year)

# 사이드바: 🔒 비밀번호 0914로 잠긴 관리자 예산서 데이터 관리 모듈
st.sidebar.markdown("---")
with st.sidebar.expander("🔒 [관리자] 예산서 데이터 관리", expanded=False):
    admin_pw = st.text_input("🔑 관리자 비밀번호", type="password", key="admin_pw_input", placeholder="비밀번호 입력")
    
    if admin_pw == "0914":
        st.success("🔓 관리자 인증이 완료되었습니다.")
        st.caption("예산편성 후 최종 합본예산서 CSV 파일을 업로드하시면 연도별로 자동 정제·적용됩니다.")
        upload_year = st.number_input("등록할 연도", min_value=2020, max_value=2035, value=selected_year+1, step=1)
        uploaded_file = st.file_uploader("합본예산서 CSV 파일 선택", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("💾 데이터 자동 정제 및 저장 적용", type="primary", use_container_width=True):
                try:
                    cnt = data_manager.save_uploaded_budget_file(uploaded_file, upload_year)
                    st.cache_data.clear()
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
                    st.cache_data.clear()
                    st.sidebar.success(f"🗑️ {y}년 예산서 데이터 삭제 완료!")
                    st.rerun()
    elif admin_pw.strip() != "":
        st.error("🔒 비밀번호가 일치하지 않습니다.")
    else:
        st.info("💡 관리자 비밀번호를 입력하시면 예산서 CSV 업로드 및 삭제 기능이 활성화됩니다.")

# ==========================================
# 3. 메인 페이지 헤더
# ==========================================
st.markdown(f"""
<div class="search-header">
    <div class="search-title">🔍 {selected_year}년 세출 예산서 스마트 통합 검색</div>
    <div class="search-subtitle">부서명, 세부사업명, 통계목, 산출근거 수식을 입력하여 예산 내역과 단가 수식을 확인하세요.</div>
</div>
""", unsafe_allow_html=True)

if df_year.empty:
    st.warning(f"⚠️ {selected_year}년도 예산서 데이터가 삭제되었거나 존재하지 않습니다. 사이드바 '🔒 [관리자] 예산서 데이터 관리' 메뉴에서 비밀번호(0914)를 입력하신 후 새로운 CSV 예산서 파일을 업로드해 주세요.")
    st.stop()

raw_acct_list = [str(a).strip() for a in df_year['회계명'].dropna().unique() if str(a).strip() not in ['-', 'nan', 'N/A', '0', '']]
acct_sums = df_year.groupby('회계명')['예산액_num'].sum()
sorted_acct_list = sorted(raw_acct_list, key=lambda a: acct_sums.get(a, 0), reverse=True)
all_accts = ["전체"] + sorted_acct_list

csv_dept_list = []
for d in df_year['부서명'].dropna().unique():
    d_str = str(d).strip()
    if d_str and d_str not in ['0', '-', 'nan', 'N/A']:
        if d_str not in csv_dept_list:
            csv_dept_list.append(d_str)

all_depts = ["전체"] + csv_dept_list

raw_type_list = [str(t).strip() for t in df_year['예산구분'].dropna().unique() if str(t).strip() not in ['-', 'nan', 'N/A', '']]
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
# 5. 실시간 통합 키워드 검색창 (파란색 테두리 박스 내부 단일 내포 구조)
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
# ⚡ 6. 예산 합계 계산 및 요약 바 (전체/본예산 제외 시 공란 표출)
# ==========================================
is_all_types_selected = (sel_budget_type == "전체")
is_main_budget_selected = (sel_budget_type == "본예산")

if is_all_types_selected:
    included_df = search_df[search_df['정산 상태'] == '✅ 정산 포함']
    total_budget_thousand = float(included_df['예산액_num'].sum())
    total_budget_billion = total_budget_thousand / 100000.0
    sum_display_str = f"{total_budget_billion:,.2f} 억 원 <span style=\"font-size:13px; font-weight:500; color:#64748b;\">({total_budget_thousand:,.0f} 천원)</span>"
elif is_main_budget_selected:
    included_df = search_df[search_df['정산 상태'] != '🔻 소계 중복 제외']
    total_budget_thousand = float(included_df['예산액_num'].sum())
    total_budget_billion = total_budget_thousand / 100000.0
    sum_display_str = f"{total_budget_billion:,.2f} 억 원 <span style=\"font-size:13px; font-weight:500; color:#64748b;\">({total_budget_thousand:,.0f} 천원)</span>"
else:
    # '전체', '본예산' 제외 나머지 항목 선택 시 공란('-') 처리
    included_df = search_df[search_df['정산 상태'] != '🔻 소계 중복 제외']
    sum_display_str = "-"

col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.markdown(f"""
    <div class="metric-badge">
        <div class="metric-label">검색된 예산 항목 수</div>
        <div class="metric-value">{len(search_df):,} 건</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""
    <div class="metric-badge">
        <div class="metric-label">검색 예산 합계</div>
        <div class="metric-value">{sum_display_str}</div>
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

# ==========================================
# 7. 검색 결과 테이블 표출 (전체 100% 렌더링 적용)
# ==========================================
display_cols = ['예산구분', '부서명', '회계명', '세부사업명', '편성목명', '통계목명', '산출근거명', '산출근거식', '예산액_num', '의무/재량구분']

col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    st.markdown(f"📋 **검색 결과 목록** (총 {len(search_df):,}건 - 전체 100% 표출)")
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

show_table_df = search_df[display_cols].copy()
show_table_df['예산액_num'] = show_table_df['예산액_num'].astype(int)

st.dataframe(
    show_table_df,
    use_container_width=True,
    height=520,
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
# 8. 스마트 실시간 예산 분석 패널 ('전체' 또는 '본예산' 선택 시에만 작동)
# ==========================================
if (sel_budget_type in ["전체", "본예산"]) and not search_df.empty:
    st.markdown("---")
    st.markdown("### 📊 검색 예산 실시간 정산 분석 패널")
    
    tab_dept, tab_stat, tab_type = st.tabs([
        "🏢 부서별 예산 정산 집계 Top 10",
        "🏷️ 주요 통계목별 예산 비중",
        "⚖️ 의무/재량 지출 구조"
    ])
    
    analysis_base_df = included_df
    
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
            render_top_highlight_bar_chart(dept_group.head(10), '부서명', '예산합계_억원')
            
        with col_d2:
            st.markdown("##### 📋 부서별 정산 예산 요약표")
            dept_display = dept_group.head(10).copy()
            dept_display.columns = ['부서명', '예산합계(천원)', '건수', '예산합계_억원']
            st.dataframe(
                dept_display[['부서명', '예산합계(천원)', '건수']],
                use_container_width=True,
                height=300,
                column_config={
                    "예산합계(천원)": st.column_config.NumberColumn(format="%,d")
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
            render_top_highlight_bar_chart(stat_group.head(10), '통계목명', '예산합계_억원')
            
        with col_s2:
            st.markdown("##### 📋 통계목별 정산 예산 요약표")
            stat_display = stat_group.head(10).copy()
            stat_display.columns = ['통계목명', '예산합계(천원)', '건수', '예산합계_억원']
            st.dataframe(
                stat_display[['통계목명', '예산합계(천원)', '건수']],
                use_container_width=True,
                height=300,
                column_config={
                    "예산합계(천원)": st.column_config.NumberColumn(format="%,d")
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
            render_top_highlight_bar_chart(type_group, '의무/재량구분', '예산합계_억원')
            
        with col_t2:
            st.markdown("##### 📋 지출 구조 정산 요약표")
            type_group.columns = ['지출구분', '예산합계(천원)', '건수', '예산합계_억원']
            st.dataframe(
                type_group[['지출구분', '예산합계(천원)', '건수']],
                use_container_width=True,
                height=220,
                column_config={
                    "예산합계(천원)": st.column_config.NumberColumn(format="%,d")
                }
            )
