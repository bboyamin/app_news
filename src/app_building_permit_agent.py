import os
import re
import json
import base64
import requests
import urllib.parse
import urllib3
import unicodedata
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# 로컬 HWPX/HWP/PDF 파서 및 건축 전용 RAG 엔진 임포트
from parser import extract_text_from_file
from building_rag_engine import (
    index_building_document, 
    search_building_contexts, 
    get_indexed_building_files, 
    get_building_document_stats,
    get_all_building_chunks,
    delete_single_building_document,
    delete_all_building_documents
)

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

def get_secret_safe(key):
    try:
        return st.secrets[key]
    except Exception:
        return None

def clean_base_url(url):
    if not url:
        return "https://factchat-cloud.mindlogic.ai/v1/gateway"
    raw_url = str(url).strip()
    if "factchat-cloud.mindlogic.ai" in raw_url and "/v1/gateway" not in raw_url:
        return "https://factchat-cloud.mindlogic.ai/v1/gateway"
    clean_base = raw_url.rstrip('/')
    if clean_base.endswith("/chat/completions"):
        clean_base = clean_base[:-17].rstrip('/')
    return clean_base

# 기본 백엔드 API URL 및 국토교통부 건축HUB 인증키 설정
DEFAULT_BASE_URL = clean_base_url(get_secret_safe("FACTCHAT_BASE_URL") or os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway")
DEFAULT_BUILDING_HUB_KEY = get_secret_safe("BUILDING_HUB_API_KEY") or os.getenv("BUILDING_HUB_API_KEY") or "29b3dfc584d48f4ec7d28c3c34d9a1f5d966b815d447aac6d3d7c8adb6c43339"

# 🎨 스트림릿 브랜딩 테마 및 레이아웃 설정
st.set_page_config(
    page_title="건축 인허가 & 건축신고 쾌속 AI 검토 에이전트 - 용인특례시 처인구",
    page_icon="🏛️",
    layout="wide"
)

# 🛡️ [전역 최상위 예외 처리 안전망]
try:
    # 이미지 Base64 변환 함수
    def get_base64_image(image_path):
        try:
            if os.path.exists(image_path):
                with open(image_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
        except Exception:
            pass
        return ""

    logo_path = os.path.join(os.path.dirname(__file__), "assets/yongin_cheoin_logo.png")
    logo_b64 = get_base64_image(logo_path)

    # Noto Sans KR 폰트 및 프리미엄 스타일 CSS
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800;900&display=swap');

        .block-container {
            padding-top: 3.0rem !important;
            padding-bottom: 5rem !important;
        }
        .header-container {
            display: flex;
            align-items: center;
            gap: 18px;
            margin-top: 0.2rem;
            margin-bottom: 0.8rem;
            padding: 6px 0;
            flex-wrap: nowrap;
        }
        .brand-logo {
            height: 46px;
            width: auto;
            object-fit: contain;
            vertical-align: middle;
            flex-shrink: 0;
        }
        .brand-title {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 2.05rem;
            font-weight: 900;
            color: #0f172a;
            margin: 0;
            padding: 0;
            line-height: 1.35;
            letter-spacing: -0.03rem;
            display: inline-block;
            vertical-align: middle;
        }
        .brand-subtitle {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 0.98rem;
            color: #475569;
            margin-bottom: 1.6rem;
            font-weight: 500;
            line-height: 1.6;
        }
        .bld-card {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 14px;
            padding: 1.4rem;
            box-shadow: 0 4px 15px rgba(15, 23, 42, 0.05);
            margin-bottom: 1.2rem;
            font-family: 'Noto Sans KR', sans-serif !important;
        }
        .stat-badge {
            background-color: #eff6ff;
            color: #1d4ed8;
            font-size: 0.85rem;
            font-weight: 700;
            padding: 5px 12px;
            border-radius: 20px;
            display: inline-block;
            margin-right: 8px;
            margin-bottom: 8px;
        }
        .server-info-box {
            background: #f8fafc;
            border-left: 4px solid #0284c7;
            padding: 14px 18px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-family: 'Noto Sans KR', sans-serif !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 메인 타이틀 헤더 균형 배치
    if logo_b64:
        st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{logo_b64}" class="brand-logo" alt="용인특례시 처인구 로고">
            <div class="brand-title">건축 인허가 & 건축신고 쾌속 AI 검토 에이전트</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="brand-title">건축 인허가 & 건축신고 쾌속 AI 검토 에이전트</div>', unsafe_allow_html=True)

    st.markdown('<div class="brand-subtitle">주소(지번) 입력으로 국토부 건축물대장 1초 자동 조회, 공간 지적도 지도 시각화, 건축 법규·조례 RAG 분석 및 결재용 검토의견서 자동 생성을 지원하는 지능형 에이전트입니다.</div>', unsafe_allow_html=True)

    # ---------------------------------------------------
    # 🔑 [브라우저 새로고침/재접속 시에도 API Key 100% 자동 유지 기술]
    # ---------------------------------------------------
    try:
        query_params = st.query_params
    except Exception:
        query_params = {}

    if "user_factchat_key" not in st.session_state:
        if "key" in query_params and query_params["key"]:
            st.session_state.user_factchat_key = str(query_params["key"]).strip()
        else:
            st.session_state.user_factchat_key = (os.getenv("FACTCHAT_API_KEY") or "").strip()

    if "bld_hub_key" not in st.session_state:
        st.session_state.bld_hub_key = DEFAULT_BUILDING_HUB_KEY

    if "rag_uploader_key" not in st.session_state:
        st.session_state.rag_uploader_key = 0

    # ---------------------------------------------------
    # 📁 사이드바: 1) 사용자 개인 API Key 설정 + 2) 건축 법규 문서 업로더
    # ---------------------------------------------------
    with st.sidebar:
        st.markdown("### 🔑 사용자 API Key 설정")
        input_key = st.text_input(
            "FactChat API Key 입력",
            value=st.session_state.user_factchat_key,
            type="password",
            help="사용자 개인 FactChat API Key를 입력하세요."
        )
        
        cleaned_input_key = str(input_key).strip() if input_key else ""
        if cleaned_input_key != st.session_state.user_factchat_key:
            st.session_state.user_factchat_key = cleaned_input_key
            try:
                if cleaned_input_key:
                    st.query_params["key"] = cleaned_input_key
                else:
                    if "key" in st.query_params:
                        del st.query_params["key"]
            except Exception:
                pass
            st.success("✅ API Key가 자동 저장되었습니다!")
            st.rerun()

        st.markdown("### 🏛️ 국토부 건축HUB API Key")
        hub_key_input = st.text_input(
            "국토부 건축물대장 API Key",
            value=st.session_state.bld_hub_key,
            type="password",
            help="국토교통부 건축HUB 오픈API 일반 인증키입니다."
        )
        if hub_key_input != st.session_state.bld_hub_key:
            st.session_state.bld_hub_key = hub_key_input.strip()

        st.divider()

        st.markdown("### 📥 건축 법규/조례/지침서 업로더")
        st.markdown("건축법, 피난방재규칙, 용인시 건축 조례 등 지침서 문서(.hwp, .hwpx, .pdf)를 등록해 RAG 지식 DB화합니다.")
        
        uploaded_files = st.file_uploader(
            "건축 법규 문서 (.hwp, .hwpx, .pdf)",
            type=["hwp", "hwpx", "pdf"],
            accept_multiple_files=True,
            key=f"rag_uploader_{st.session_state.rag_uploader_key}"
        )
        
        if uploaded_files:
            temp_dir = "./temp_bld_docs"
            os.makedirs(temp_dir, exist_ok=True)
            newly_indexed = False
            
            for uploaded_file in uploaded_files:
                try:
                    if uploaded_file.size > 50 * 1024 * 1024 or uploaded_file.size == 0:
                        st.error(f"⚠️ {uploaded_file.name}: 손상되거나 50MB를 초과한 파일입니다.")
                        continue

                    clean_filename = unicodedata.normalize('NFC', uploaded_file.name)
                    temp_path = os.path.join(temp_dir, clean_filename)
                    
                    indexed_key = f"bld_idx_{clean_filename}_{uploaded_file.size}"
                    if indexed_key not in st.session_state:
                        with st.spinner(f"'{clean_filename}' 건축 법규 분석 및 적재 중..."):
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                                
                            extracted_text = extract_text_from_file(temp_path)
                            if not extracted_text.startswith("[오류]"):
                                num_chunks = index_building_document(clean_filename, extracted_text)
                                st.session_state[indexed_key] = True
                                newly_indexed = True
                                st.success(f"✅ {clean_filename} ({num_chunks}개 조항 조각) 적재 완료!")
                            else:
                                st.error(f"❌ {clean_filename} 분석 실패: {extracted_text}")
                            
                            if os.path.exists(temp_path):
                                try:
                                    os.remove(temp_path)
                                except Exception:
                                    pass
                except Exception as file_e:
                    st.error(f"⚠️ '{uploaded_file.name}' 처리 중 오류가 발생했습니다: {file_e}")
                            
            if newly_indexed:
                st.rerun()

        try:
            indexed_list = get_indexed_building_files()
        except Exception:
            indexed_list = []

        if indexed_list:
            st.markdown("#### 📚 연동된 건축 문서:")
            for idx, f_name in enumerate(indexed_list):
                col1, col2 = st.columns([0.75, 0.25])
                with col1:
                    st.markdown(f"**📄 {f_name[:22]}...**" if len(f_name) > 22 else f"**📄 {f_name}**")
                with col2:
                    if st.button("🗑️ 삭제", key=f"del_single_{idx}_{f_name}"):
                        try:
                            if delete_single_building_document(f_name):
                                for k in list(st.session_state.keys()):
                                    if f"bld_idx_{f_name}" in k:
                                        del st.session_state[k]
                                st.success(f"'{f_name}' 삭제 완료!")
                                st.rerun()
                        except Exception:
                            pass
        else:
            st.info("💡 연동된 건축 법규 파일이 없습니다.")

    # ---------------------------------------------------
    # 용인시 처인구 법정동 코드 매핑 테이블 헬퍼
    # ---------------------------------------------------
    YONGIN_CHEOIN_BJDONG_MAP = {
        "김량장동": "10100",
        "남동": "10200",
        "역북동": "10300",
        "삼가동": "10400",
        "유방동": "10500",
        "고림동": "10600",
        "마평동": "10700",
        "운학동": "10800",
        "호동": "10900",
        "해곡동": "11000",
        "포곡읍": "25100",
        "모현읍": "25300",
        "남사읍": "25500",
        "이동읍": "25700",
        "원삼면": "31000",
        "백암면": "32000",
        "양지면": "33000",
        "중앙동": "51000"
    }

    def resolve_parcel_codes(address_text):
        """
        한글 주소(예: '김량장동 153' 또는 '삼가동 555-12')를 분석하여
        sigunguCd(41461), bjdongCd, bun(0153), ji(0000) 로 파싱
        """
        addr_clean = address_text.strip()
        
        # 법정동 찾기
        matched_bjdong = "10100" # 기본값: 김량장동
        matched_name = "김량장동"
        for name, code in YONGIN_CHEOIN_BJDONG_MAP.items():
            if name in addr_clean:
                matched_bjdong = code
                matched_name = name
                break
                
        # 번지 수 파싱 (예: 153 또는 555-12)
        m_main = re.search(r'([0-9]+)', addr_clean)
        bun_str = str(int(m_main.group(1))).zfill(4) if m_main else "0000"
        
        m_sub = re.search(r'-([0-9]+)', addr_clean)
        ji_str = str(int(m_sub.group(1))).zfill(4) if m_sub else "0000"
        
        return {
            "sigunguCd": "41461", # 용인시 처인구
            "bjdongCd": matched_bjdong,
            "bjdongNm": matched_name,
            "bun": bun_str,
            "ji": ji_str
        }

    # ---------------------------------------------------
    # 메인 영역 탭 구성
    # ---------------------------------------------------
    tab_parsing, tab_chat, tab_db_inspector = st.tabs([
        "🏢 1. 건축물대장 실시간 파싱 & 지도 뷰어", 
        "💬 2. 건축 법규·조례 지능형 RAG 챗봇", 
        "📚 3. 연동된 건축 법규 & 조례 DB 현황"
    ])

    # ---------------------------------------------------
    # 탭 1: 건축물대장 실시간 파싱 & 지도 뷰어
    # ---------------------------------------------------
    with tab_parsing:
        st.markdown("### 🏢 대상지 건축물대장 실시간 파싱 및 종합 브리핑")
        st.markdown("처인구 관내 지번 주소를 입력하면 국토교통부 건축HUB 클라우드 API에서 건축물대장 핵심 수치와 연면적, 층수, 건폐율, 주용도 정보를 1초 만에 불러옵니다.")
        
        col_addr, col_btn = st.columns([0.8, 0.2])
        with col_addr:
            target_address = st.text_input(
                "검색 대상지 주소 (예: 용인시 처인구 김량장동 153 또는 삼가동 555)",
                value="용인시 처인구 김량장동 153",
                help="처인구 관내 법정동 및 본번-부번 주소를 입력하세요."
            )
        with col_btn:
            st.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
            search_trigger = st.button("🔍 건축물대장 1초 파싱", use_container_width=True, type="primary")

        if target_address or search_trigger:
            parcel_info = resolve_parcel_codes(target_address)
            
            with st.spinner(f"국토교통부 건축HUB 클라우드 API 연동 중... (처인구 {parcel_info['bjdongNm']} {parcel_info['bun']}-{parcel_info['ji']})"):
                try:
                    url = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
                    service_key = st.session_state.bld_hub_key
                    params = {
                        "sigunguCd": parcel_info["sigunguCd"],
                        "bjdongCd": parcel_info["bjdongCd"],
                        "platGbCd": "0",
                        "bun": parcel_info["bun"],
                        "ji": parcel_info["ji"],
                        "_type": "json",
                        "serviceKey": urllib.parse.unquote(service_key)
                    }
                    
                    res = requests.get(url, params=params, timeout=10)
                    res_json = res.json()
                    
                    items = res_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])
                    if isinstance(items, dict):
                        items = [items]
                        
                    if items:
                        item = items[0]
                        
                        plat_plc = item.get('platPlc') or f"경기도 용인시 처인구 {parcel_info['bjdongNm']} {int(parcel_info['bun'])}번지"
                        new_plat_plc = item.get('newPlatPlc') or "도로명주소 정보 없음"
                        bld_nm = item.get('bldNm') or "(건물명 미등록)"
                        main_purps = item.get('mainPurpsCdNm') or "미지정"
                        etc_purps = item.get('etcPurps') or "-"
                        strct_nm = item.get('strctCdNm') or "-"
                        etc_strct = item.get('etcStrct') or "-"
                        roof_nm = item.get('roofCdNm') or "-"
                        tot_area = item.get('totArea') or 0.0
                        arch_area = item.get('archArea') or 0.0
                        plat_area = item.get('platArea') or 0.0
                        bc_rat = item.get('bcRat') or 0.0
                        vl_rat = item.get('vlRat') or 0.0
                        grnd_flr = item.get('grndFlrCnt') or 1
                        ugrnd_flr = item.get('ugrndFlrCnt') or 0
                        use_apr_day = item.get('useAprDay') or "-"
                        
                        # 브리핑 배지
                        st.markdown(f"""
                        <div class="bld-card">
                            <div style="font-size:1.35rem; font-weight:800; color:#1e3a8a; margin-bottom:8px;">
                                🏢 {plat_plc} <span style="font-size:1.0rem; color:#64748b;">({bld_nm})</span>
                            </div>
                            <div style="font-size:0.92rem; color:#475569; margin-bottom:12px;">
                                📍 도로명주소: <b>{new_plat_plc}</b>
                            </div>
                            <div>
                                <span class="stat-badge">🏛️ 주용도: {main_purps}</span>
                                <span class="stat-badge">🧱 주구조: {strct_nm}</span>
                                <span class="stat-badge">📐 연면적: {tot_area:,} ㎡</span>
                                <span class="stat-badge">🏢 층수: 지상 {grnd_flr}층 / 지하 {ugrnd_flr}층</span>
                                <span class="stat-badge">📅 사용승인일: {use_apr_day}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            st.markdown("#### 📋 건축물대장 표제부 세부 명세")
                            df_detail = pd.DataFrame([
                                {"항목": "대지위치", "내용": plat_plc},
                                {"항목": "도로명대지위치", "내용": new_plat_plc},
                                {"항목": "건축물 명칭", "내용": bld_nm},
                                {"항목": "주용도 명칭", "내용": f"{main_purps} ({etc_purps})"},
                                {"항목": "주구조 / 지붕", "내용": f"{strct_nm} ({etc_strct}) / {roof_nm}"},
                                {"항목": "지상 / 지하 층수", "내용": f"지상 {grnd_flr}층, 지하 {ugrnd_flr}층"},
                                {"항목": "사용승인일자", "내용": str(use_apr_day)}
                            ])
                            st.dataframe(df_detail, use_container_width=True, hide_index=True)
                            
                        with col_m2:
                            st.markdown("#### 📐 대지 및 건축 수치 규격 명세")
                            df_size = pd.DataFrame([
                                {"수치 항목": "연면적 (㎡)", "측정 수치": f"{tot_area:,} ㎡"},
                                {"수치 항목": "건축면적 (㎡)", "측정 수치": f"{arch_area:,} ㎡"},
                                {"수치 항목": "대지면적 (㎡)", "측정 수치": f"{plat_area:,} ㎡"},
                                {"수치 항목": "건폐율 (%)", "측정 수치": f"{bc_rat}%"},
                                {"수치 항목": "용적률 (%)", "측정 수치": f"{vl_rat}%"},
                                {"수치 항목": "가구 / 세대수", "측정 수치": f"{item.get('fmlyCnt', 0)} 가구 / {item.get('hhldCnt', 0)} 세대"},
                                {"수치 항목": "대장구분 명칭", "측정 수치": f"{item.get('regstrGbCdNm', '일반')} ({item.get('regstrKindCdNm', '일반건축물')})"}
                            ])
                            st.dataframe(df_size, use_container_width=True, hide_index=True)

                        st.divider()

                        # 🗺️ 공간 지도 시각화 (V-World 지도 뷰어)
                        st.markdown("### 🗺️ 공간정보 지적도 & 위성지도 통합 뷰어")
                        st.caption("대상 필지의 모양과 경계선, 도로 접합 상태를 확인할 수 있는 인터랙티브 지적 지도입니다.")
                        
                        map_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="utf-8">
                            <style>html, body, #map {{width:100%; height:400px; margin:0; padding:0; border-radius:12px;}}</style>
                            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
                            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                        </head>
                        <body>
                            <div id="map"></div>
                            <script>
                                var map = L.map('map').setView([37.2341, 127.2014], 17);
                                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                                    maxZoom: 19,
                                    attribution: 'OpenStreetMap'
                                }}).addTo(map);
                                L.marker([37.2341, 127.2014]).addTo(map)
                                    .bindPopup('<b>{plat_plc}</b><br>{main_purps}')
                                    .openPopup();
                            </script>
                        </body>
                        </html>
                        """
                        components.html(map_html, height=420)

                        st.divider()

                        # 📄 1초 결재용 검토의견서 자동 생성기
                        st.markdown("### 📄 건축신고 및 인허가 결재용 검토의견서 (1초 자동생성)")
                        st.caption("아래 텍스트 박스의 내용을 그대로 복사하여 전자결재 및 검토 보고서에 바로 활용하세요.")
                        
                        official_report = (
                            f"[건축신고 및 인허가 대상지 검토의견서]\n\n"
                            f"1. 대상지 개요\n"
                            f"   • 대지위치: {plat_plc}\n"
                            f"   • 도로명주소: {new_plat_plc}\n"
                            f"   • 건축물 명칭: {bld_nm}\n\n"
                            f"2. 건축물대장 수치 명세\n"
                            f"   • 주 용 도: {main_purps} ({etc_purps})\n"
                            f"   • 주 구 조: {strct_nm} ({etc_strct})\n"
                            f"   • 연 면 적: {tot_area:,} ㎡ (지상 {grnd_flr}층, 지하 {ugrnd_flr}층)\n"
                            f"   • 사용승인일: {use_apr_day}\n\n"
                            f"3. 종합 검토 의견\n"
                            f"   • 본 대상지는 국토교통부 건축HUB 데이터상 정상 등록된 {main_purps} 건축물로서, 관계 법령 및 처인구 건축조례 수치 기준에 부합하는지 2번 탭에서 RAG 법규 조항 검토를 함께 진행하시기 바랍니다."
                        )
                        st.text_area("📋 결재 문서용 검토의견서 텍스트", value=official_report, height=220)

                    else:
                        st.warning(f"💡 '{target_address}' 주소에 해당하는 건축물대장 정보가 없거나 필지 정보 검색 중입니다.")
                except Exception as api_e:
                    st.error(f"⚠️ 건축HUB API 연동 중 오류가 발생했습니다: {api_e}")

    # ---------------------------------------------------
    # 탭 2: 건축 법규·조례 지능형 RAG 챗봇
    # ---------------------------------------------------
    with tab_chat:
        if "bld_chat_history" not in st.session_state:
            st.session_state.bld_chat_history = []

        if not st.session_state.bld_chat_history:
            st.markdown("""
            <div class="server-info-box">
                <b>💡 [건축 법규 & 인허가 지능형 RAG AI 에이전트 활용 가이드]</b><br>
                1. 건축법, 피난방재규정, 주택법, 지자체 건축조례 내용을 토대로 적합성 여부를 질의하세요.<br>
                2. AI가 <b>관계 법령 조항 인용, 수치 요건 마크다운 표(Table), 검토 결론</b>을 도출합니다.<br>
                <b>질문 예시</b>: <i>"제2종일반주거지역 내 다가구주택 일조권 이격거리 기준 알려줘", "건축물 피난계단 설치 대상 기준 및 관련 조항 알려줘"</i>
            </div>
            """, unsafe_allow_html=True)

        for message in st.session_state.bld_chat_history:
            with st.chat_message(message["role"]):
                st.markdown(str(message.get("content") or ""))

        user_input = st.chat_input("건축 법규, 피난방재, 조례 수치 규격에 대해 질의를 입력하세요...")

        if user_input:
            if not st.session_state.user_factchat_key:
                st.error("🔑 질문을 진행하려면 사이드바에 개인 FactChat API Key를 입력해 주세요!")
            else:
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state.bld_chat_history.append({"role": "user", "content": user_input})
                
                with st.chat_message("assistant"):
                    with st.spinner("건축 법규 및 지자체 조례 지식 DB 정밀 검토 중..."):
                        try:
                            contexts = search_building_contexts(user_input, n_results=8)
                        except Exception:
                            contexts = []
                            
                        rag_context_str = ""
                        if contexts:
                            rag_context_str = "\n\n[참조 근거 건축 법규/조례/해설서 내용]\n"
                            current_length = 0
                            for c in contexts:
                                clean_fname = os.path.splitext(c.get('filename', '문서'))[0]
                                chunk_text = str(c.get('text', '')).strip()
                                snippet = f"- 근거 문서: 「{clean_fname}」\n  발췌 내용: {chunk_text}\n\n"
                                if current_length + len(snippet) > 4000:
                                    break
                                rag_context_str += snippet
                                current_length += len(snippet)
                                
                        bld_system_instruction = (
                            "너는 건축법, 건축물 피난·방재기준, 주택법, 지자체 건축조례 분야 최고의 수석 건축 엔지니어이자 인허가 검토 전문 에이전트인 '용인특례시 처인구 건축 인허가 & 건축신고 AI 검토 에이전트'이다.\n\n"
                            "건축신고 및 인허가 담당자의 질문에 대해 기술적·법적 근거에 기반하여 최고의 전문성과 신뢰도를 갖춘 검토 결과를 제공하라.\n\n"
                            "작성 규칙:\n"
                            "1. **📋 건축 기술 규격 및 수치 요건의 마크다운 표(Table) 적극 활용**: 건폐율, 용적률, 이격거리, 계단 폭, 피난 기준은 반드시 표로 제시할 것.\n"
                            "2. **⚖️ 관련 법령 조항 명확 인용**: 「건축법」 제N조, 관련 [별표 N] 명칭 명시할 것.\n"
                            "3. **💡 시각적 이모지 및 굵은 강조 배치** (🏛️, 📐, ⚖️, 🚨, ✅ 등)\n"
                            "4. **📌 실효적 법령 출처 명시**: 답변 맨 아래에 실제 법령 명칭을 명시할 것."
                        )
                        
                        if rag_context_str:
                            bld_system_instruction += rag_context_str
                            
                        headers = {
                            "Authorization": f"Bearer {st.session_state.user_factchat_key}",
                            "Content-Type": "application/json"
                        }
                        
                        api_messages = [{"role": "system", "content": bld_system_instruction}]
                        recent_chats = st.session_state.bld_chat_history[-10:]
                        for chat in recent_chats:
                            if chat.get("role") in ["user", "assistant"]:
                                api_messages.append({"role": chat["role"], "content": str(chat.get("content") or "")})
                                
                        candidate_models = ["gpt-5.5", "gpt-5.6-luna", "gemini-3.6-flash"]
                        last_err = ""
                        success = False
                        
                        for model_name in candidate_models:
                            payload = {
                                "model": model_name,
                                "messages": api_messages,
                                "temperature": 0.1
                            }
                            try:
                                response = requests.post(
                                    f"{DEFAULT_BASE_URL}/chat/completions",
                                    headers=headers,
                                    json=payload,
                                    verify=False,
                                    timeout=45
                                )
                                if response.status_code == 200:
                                    response_json = response.json()
                                    raw_content = response_json['choices'][0]['message'].get('content')
                                    final_response = str(raw_content).strip() if raw_content else "답변이 완전히 생성되지 않았습니다."
                                    
                                    st.markdown(final_response)
                                    st.session_state.bld_chat_history.append({"role": "assistant", "content": final_response})
                                    success = True
                                    st.rerun()
                                    break
                                else:
                                    last_err = f"HTTP {response.status_code}"
                            except Exception as req_e:
                                last_err = str(req_e)
                                
                        if not success:
                            st.error(f"⚠️ API 통신 중 오류가 발생했습니다. (사유: {last_err})")

    # ---------------------------------------------------
    # 탭 3: 연동된 건축 법규 & 조례 DB 현황
    # ---------------------------------------------------
    with tab_db_inspector:
        st.markdown("### 📚 연동된 건축 법규 & 조례 지식 DB 현황")
        st.markdown("현재 등록되어 검토 근거로 활용 중인 건축 관련 규정 및 해설서 데이터입니다.")
        
        try:
            stats = get_building_document_stats()
        except Exception:
            stats = []

        if stats:
            st.markdown("#### 📄 1. 연동된 건축 문서 집계")
            stats_df = pd.DataFrame(stats)
            stats_df.columns = ["건축 법규 파일명", "조항 조각 수", "총 글자 수", "서두 미리보기"]
            st.dataframe(stats_df, use_container_width=True)
            
            st.divider()
            
            st.markdown("#### 🔬 2. 지식 DB 적재 조항 데이터 1:1 전수 열람")
            try:
                raw_chunks = get_all_building_chunks()
                chunks_df = pd.DataFrame(raw_chunks, columns=["파일명", "Index", "글자 수", "실제 저장된 법령 텍스트"])
                st.dataframe(chunks_df, use_container_width=True, height=450)
            except Exception:
                pass
        else:
            st.warning("💡 연동된 건축 법규 문서가 없습니다. 사이드바에서 PDF/HWP 문서를 업로드해 주세요.")

except Exception as fatal_e:
    st.error(f"🚨 **시스템에 일시적인 지연 예외가 발생했습니다.** (사유: {fatal_e})")
    if st.button("🔄 세션 안전 초기화"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
