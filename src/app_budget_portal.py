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

# 깔끔하고 직관적인 오피스 테마 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
    }

    /* 상단 미니멀 헤더 */
    .search-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #0f766e 100%);
        padding: 20px 28px;
        border-radius: 12px;
        color: #ffffff;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.15);
    }
    
    .search-title {
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 6px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .search-subtitle {
        font-size: 13px;
        opacity: 0.9;
        margin: 0;
    }

    /* 요약 메트릭 카드 */
    .metric-badge {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-label {
        font-size: 12px;
        color: #64748b;
        font-weight: 500;
    }
    .metric-value {
        font-size: 20px;
        font-weight: 700;
        color: #1e3a8a;
    }

    /* 산출근거 수식 카드 */
    .detail-box {
        background: #ffffff;
        border-left: 4px solid #0d9488;
        padding: 16px;
        border-radius: 8px;
        margin-top: 12px;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
    }
    
    .formula-tag {
        background-color: #f0fdf4;
        color: #166534;
        border: 1px solid #bbf7d0;
        padding: 4px 10px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 14px;
        font-weight: 600;
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
    st.caption("예산편성 후 최종 합본예산서 CSV 파일을 업로드하시면 0.5초 만에 연도별로 자동 정제·적용됩니다.")
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
    <div class="search-subtitle">부서명, 세부사업명, 통계목, 산출근거 수식을 입력하여 예산 내역과 단가 수식을 1초 만에 확인하세요.</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 3. 드롭다운 필터 바 (회계구분 / 소관부서)
# ==========================================
# 회계명 정제: '회계'로 끝나는 정제된 명칭을 예산 규모 내림차순으로 정렬
valid_acct_df = df_year[df_year['회계명'].str.endswith('회계', na=False)]
acct_order = valid_acct_df.groupby('회계명')['예산액_억원'].sum().sort_values(ascending=False).index.tolist()
all_accts = ["전체"] + acct_order

# 소관 부서 정제: CSV 데이터 원본 부서 순서 그대로 유지 (이상치 '0', '-', 'nan', 'N/A', 숫자코드 제외)
csv_dept_list = []
for d in df_year['부서명'].dropna().unique():
    d_str = str(d).strip()
    if d_str and d_str not in ['0', '-', 'nan', 'N/A'] and not re.match(r'^\d', d_str):
        if d_str not in csv_dept_list:
            csv_dept_list.append(d_str)

all_depts = ["전체"] + csv_dept_list

# 예산구분 정제: 본예산, 추경1회, 추경2회 등 목록 추출
raw_type_list = [str(t).strip() for t in df_year['예산구분'].dropna().unique() if str(t).strip() not in ['-', 'nan', 'N/A', '']]
all_budget_types = ["전체"] + raw_type_list

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    sel_acct = st.selectbox("🏛️ 회계구분 선택 (예산 규모순)", all_accts, index=0)

with col_f2:
    sel_dept = st.selectbox("🏢 소관 부서 선택 (CSV 원본 부서 순서)", all_depts, index=0)

with col_f3:
    sel_budget_type = st.selectbox("📑 예산구분 선택 (본예산/추경1회...)", all_budget_types, index=0)

# 필터 적용
filtered_df = df_year.copy()
if sel_acct != "전체":
    filtered_df = filtered_df[filtered_df['회계명'] == sel_acct]
if sel_dept != "전체":
    filtered_df = filtered_df[filtered_df['부서명'] == sel_dept]
if sel_budget_type != "전체":
    filtered_df = filtered_df[filtered_df['예산구분'] == sel_budget_type]

# ==========================================
# 4. 실시간 통합 키워드 검색창
# ==========================================
st.markdown("---")
search_keyword = st.text_input(
    "🔎 예산 통합 검색어 입력", 
    placeholder="검색할 단어를 입력하세요 (예: 시민소통, 주차장, 수당, 마스크, 연수, 용역, 자치행정과...)"
)

search_df = filtered_df.copy()
if search_keyword.strip():
    kw = search_keyword.strip()
    mask = (
        search_df['부서명'].str.contains(kw, case=False, na=False) |
        search_df['세부사업명'].str.contains(kw, case=False, na=False) |
        search_df['정책사업명'].str.contains(kw, case=False, na=False) |
        search_df['통계목명'].str.contains(kw, case=False, na=False) |
        search_df['산출근거명'].str.contains(kw, case=False, na=False) |
        search_df['산출근거식'].str.contains(kw, case=False, na=False)
    )
    search_df = search_df[mask]

# 검색 결과 요약 메트릭 바
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.markdown(f"""
    <div class="metric-badge">
        <div class="metric-label">검색된 예산 항목 수</div>
        <div class="metric-value">{len(search_df):,} 건</div>
    </div>
    """, unsafe_allow_html=True)

with col_m2:
    total_search_eok = search_df['예산액_억원'].sum()
    st.markdown(f"""
    <div class="metric-badge">
        <div class="metric-label">검색 항목 예산 합계</div>
        <div class="metric-value">{total_search_eok:,.2f} 억 원</div>
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
# 5. 검색 결과 테이블 및 엑셀 다운로드
# ==========================================
display_cols = ['예산구분', '부서명', '회계명', '세부사업명', '편성목명', '통계목명', '산출근거명', '산출근거식', '예산액', '의무/재량구분']

col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.markdown(f"📋 **검색 결과 목록** (총 {len(search_df):,}건)")
with col_t2:
    csv_data = search_df[display_cols].to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 엑셀/CSV 다운로드",
        data=csv_data,
        file_name=f"예산검색결과_{selected_year}_{search_keyword}.csv",
        mime="text/csv",
        use_container_width=True
    )

# 테이블 표출 (검색어가 없을 때는 쾌속 표출용 300건 표출)
show_table_df = search_df[display_cols]
if not search_keyword.strip() and len(show_table_df) > 300:
    st.caption("💡 검색어를 입력하시면 전체 예산서 데이터에서 즉시 검색됩니다.")
    show_table_df = show_table_df.head(300)

st.dataframe(
    show_table_df,
    use_container_width=True,
    height=450,
    column_config={
        "예산액": st.column_config.NumberColumn("예산액 (천원)", format="%d"),
        "산출근거식": st.column_config.TextColumn("산출근거 수식 (단가*수량)", width="medium")
    }
)

# ==========================================
# 6. 개별 항목 세부 산출근거 수식 팝업 카드
# ==========================================
if not search_df.empty:
    st.markdown("---")
    st.markdown("### 📄 세부 산출근거 수식 확인 카드")
    
    sample_indices = search_df.index[:100]
    selected_idx = st.selectbox(
        "상세 산출근거식을 확인하실 항목을 선택하세요",
        options=sample_indices,
        format_func=lambda idx: f"[{search_df.loc[idx, '부서명']}] {search_df.loc[idx, '세부사업명']} - {search_df.loc[idx, '산출근거명']} ({data_manager.clean_num(search_df.loc[idx, '예산액']):,.0f} 천원)"
    )
    
    item = search_df.loc[selected_idx]
    budget_num = data_manager.clean_num(item['예산액'])
    
    st.markdown(f"""
    <div class="detail-box">
        <h4 style="margin-top:0; color:#1e3a8a;">[{item['부서명']}] {item['세부사업명']}</h4>
        <p><b>• 정책사업:</b> {item['정책사업명']} &nbsp;|&nbsp; <b>• 단위사업:</b> {item['단위사업명']}</p>
        <p><b>• 회계구분:</b> {item['회계명']} &nbsp;|&nbsp; <b>• 목/통계목:</b> {item['편성목명']} ({item['통계목명']})</p>
        <p><b>• 의무/재량:</b> {item['의무/재량구분']} &nbsp;|&nbsp; <b>• 산출근거 항목:</b> {item['산출근거명']}</p>
        <p><b>• 산출근거 수식:</b> <span class="formula-tag">{item['산출근거식']}</span></p>
        <p style="margin-bottom:0;"><b>• 예산 반영액:</b> <span style="font-size:18px; font-weight:700; color:#0f766e;">{budget_num:,.0f} 천원</span> ({budget_num/100000:,.2f} 억 원)</p>
    </div>
    """, unsafe_allow_html=True)
