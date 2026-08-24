import os
import json
import base64
import requests
import urllib3
import unicodedata
import traceback
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# 로컬 HWPX/HWP/PDF 파서 및 정보통신 전용 RAG 엔진 임포트
from parser import extract_text_from_file
from ict_rag_engine import (
    index_ict_document, 
    search_ict_contexts, 
    get_indexed_ict_files, 
    get_ict_document_stats,
    get_all_ict_chunks,
    delete_single_ict_document,
    delete_all_ict_documents
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

# 기본 백엔드 API URL
DEFAULT_BASE_URL = clean_base_url(get_secret_safe("FACTCHAT_BASE_URL") or os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway")

# 🎨 스트림릿 브랜딩 테마 및 레이아웃 설정
st.set_page_config(
    page_title="정보통신 규제 및 설계 검토 AI 에이전트 - 용인특례시 처인구 (안전 검증 사본)",
    page_icon="📐",
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

    # Noto Sans KR 폰트 및 짤림 없는 여백 조절 CSS
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@500;700;800;900&display=swap');

        .block-container {
            padding-top: 3.2rem !important;
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
            height: 44px;
            width: auto;
            object-fit: contain;
            vertical-align: middle;
            flex-shrink: 0;
        }
        .brand-title {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 2.05rem;
            font-weight: 800;
            color: #1e3a8a;
            margin: 0;
            padding: 0;
            line-height: 1.35;
            letter-spacing: -0.02rem;
            display: inline-block;
            vertical-align: middle;
        }
        .brand-subtitle {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-size: 0.98rem;
            color: #334155;
            margin-bottom: 1.6rem;
            font-weight: 500;
            line-height: 1.6;
        }
        .guide-card {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 14px;
            padding: 1.4rem;
            box-shadow: 0 4px 15px rgba(15, 23, 42, 0.04);
            margin-bottom: 1.5rem;
            font-family: 'Noto Sans KR', sans-serif !important;
        }
        .server-info-box {
            background: #f8fafc;
            border-left: 4px solid #1d4ed8;
            padding: 14px 18px;
            border-radius: 6px;
            margin-bottom: 15px;
            font-family: 'Noto Sans KR', sans-serif !important;
        }
        .safe-badge {
            background-color: #dcfce7;
            color: #15803d;
            font-size: 0.82rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="safe-badge">🛡️ 8단계 무결성 예외 처리 검증 가동 중</div>', unsafe_allow_html=True)

    # 메인 타이틀 헤더 균형 배치
    if logo_b64:
        st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{logo_b64}" class="brand-logo" alt="용인특례시 처인구 로고">
            <div class="brand-title">정보통신 규제 및 설계 검토 AI 에이전트</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="brand-title">정보통신 규제 및 설계 검토 AI 에이전트</div>', unsafe_allow_html=True)

    st.markdown('<div class="brand-subtitle">정보통신 관련 법령, 기술기준, 설계 해설서 등을 기반으로 법적·기술적 근거 조항과 최적의 검토 결과를 제공하는 지능형 에이전트입니다.</div>', unsafe_allow_html=True)

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

    if "rag_uploader_key" not in st.session_state:
        st.session_state.rag_uploader_key = 0

    # ---------------------------------------------------
    # 📁 사이드바: 1) 사용자 개인 API Key 설정 + 2) 지식 문서 업로더
    # ---------------------------------------------------
    with st.sidebar:
        st.markdown("### 🔑 사용자 API Key 설정")
        st.markdown("API Key를 입력하면 브라우저 재접속/새로고침 시에도 **100% 자동 유지**됩니다.")
        
        input_key = st.text_input(
            "FactChat API Key 입력",
            value=st.session_state.user_factchat_key,
            type="password",
            help="사용자 개인 FactChat API Key를 입력하세요. 입력 시 새로고침이나 재접속을 해도 키가 자동으로 유지됩니다."
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
            st.success("✅ API Key가 자동 저장되었습니다! (새로고침 시에도 100% 유지)")
            st.rerun()
            
        if st.session_state.user_factchat_key:
            st.caption("🔒 **API Key 상태**: 영구 자동 기억 활성화됨")
            if st.button("🔑 기억된 API Key 삭제 (초기화)", use_container_width=True):
                st.session_state.user_factchat_key = ""
                try:
                    if "key" in st.query_params:
                        del st.query_params["key"]
                except Exception:
                    pass
                st.rerun()
        else:
            st.warning("⚠️ API Key를 입력하셔야 AI 검토를 시작할 수 있습니다.")
            
        st.divider()

        st.markdown("### 📥 정보통신 법령/기술기준/해설서 업로더 (관리자용)")
        st.markdown("방송통신설비 기술기준, 공사 표준시방서, 설계 해설서 문서(.hwp, .hwpx, .pdf)를 등록하여 지식 DB화합니다.")
        
        uploaded_files = st.file_uploader(
            "법령/기술기준 문서 (.hwp, .hwpx, .pdf)",
            type=["hwp", "hwpx", "pdf"],
            accept_multiple_files=True,
            key=f"rag_uploader_{st.session_state.rag_uploader_key}"
        )
        
        if uploaded_files:
            temp_dir = "./temp_ict_docs"
            os.makedirs(temp_dir, exist_ok=True)
            newly_indexed = False
            
            for uploaded_file in uploaded_files:
                try:
                    # 파일 손상 및 대용량 사전 검증
                    if uploaded_file.size > 50 * 1024 * 1024:
                        st.error(f"⚠️ {uploaded_file.name}: 파일 크기가 50MB를 초과하여 업로드가 제한됩니다.")
                        continue
                    if uploaded_file.size == 0:
                        st.error(f"⚠️ {uploaded_file.name}: 빈 파일(0 bytes)입니다.")
                        continue

                    clean_filename = unicodedata.normalize('NFC', uploaded_file.name)
                    temp_path = os.path.join(temp_dir, clean_filename)
                    
                    indexed_key = f"ict_idx_{clean_filename}_{uploaded_file.size}"
                    if indexed_key not in st.session_state:
                        with st.spinner(f"'{clean_filename}' 법령/기술기준 분석 및 적재 중..."):
                            with open(temp_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                                
                            extracted_text = extract_text_from_file(temp_path)
                            if not extracted_text.startswith("[오류]"):
                                num_chunks = index_ict_document(clean_filename, extracted_text)
                                st.session_state[indexed_key] = True
                                newly_indexed = True
                                st.success(f"✅ {clean_filename} ({num_chunks}개 조항 조각) 지식 DB 적재 완료!")
                            else:
                                st.error(f"❌ {clean_filename} 분석 실패: {extracted_text}")
                            
                            # 임시 가공 파일 안전 삭제 (메모리 릭 방지)
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
            indexed_list = get_indexed_ict_files()
        except Exception as db_e:
            indexed_list = []
            st.error(f"⚠️ 지식 DB 조회 중 일시적 오류가 발생했습니다: {db_e}")

        if indexed_list:
            st.markdown("#### 📚 연동된 문서 개별 관리:")
            for idx, f_name in enumerate(indexed_list):
                col1, col2 = st.columns([0.75, 0.25])
                with col1:
                    st.markdown(f"**📄 {f_name[:25]}...**" if len(f_name) > 25 else f"**📄 {f_name}**")
                with col2:
                    if st.button("🗑️ 삭제", key=f"del_single_{idx}_{f_name}"):
                        try:
                            if delete_single_ict_document(f_name):
                                for k in list(st.session_state.keys()):
                                    if f"ict_idx_{f_name}" in k:
                                        del st.session_state[k]
                                st.success(f"'{f_name}' 개별 삭제 완료!")
                                st.rerun()
                        except Exception as del_e:
                            st.error(f"삭제 처리 중 오류 발생: {del_e}")
                
            st.write("")
            if st.button("🚨 정보통신 지식 DB 전체 초기화", use_container_width=True):
                try:
                    if delete_all_ict_documents():
                        for k in list(st.session_state.keys()):
                            if k.startswith("ict_idx_"):
                                del st.session_state[k]
                        st.session_state.rag_uploader_key += 1
                        st.success("정보통신 규제 지식 DB가 전체 초기화되었습니다!")
                        st.rerun()
                except Exception as clear_e:
                    st.error(f"전체 초기화 중 오류 발생: {clear_e}")
        else:
            st.info("💡 연동된 정보통신 법령/기술기준 파일이 없습니다. 위에서 HWP, HWPX 또는 PDF 문서를 업로드해 주세요.")

    # ---------------------------------------------------
    # 메인 영역 탭 구성
    # ---------------------------------------------------
    tab_chat, tab_db_inspector = st.tabs([
        "💬 1. 정보통신 규제 & 설계 AI 검토 챗봇", 
        "📚 2. 연동된 정보통신 법령/기술기준 DB 현황"
    ])

    # ---------------------------------------------------
    # 탭 1: 정보통신 규제 & 설계 AI 검토 챗봇
    # ---------------------------------------------------
    with tab_chat:
        if "ict_chat_history" not in st.session_state:
            st.session_state.ict_chat_history = []

        if not st.session_state.ict_chat_history:
            st.markdown("""
            <div class="guide-card">
                <div style="font-weight:800; font-size:1.1rem; color:#0f172a; margin-bottom:8px;">💡 정보통신 규제 및 설계 검토 AI 에이전트 활용 가이드</div>
                1. 왼쪽 사이드바에서 <b>개인 API Key</b>를 입력해 주세요. (한번 입력하면 새로고침/재접속 시에도 자동 유지됩니다)<br>
                2. 연동된 법령, 기술기준, 설비기준, 해설서의 내용을 기반으로 규격 및 검토 사항을 질의하세요.<br>
                3. AI 에이전트가 <b>법령 조항 근거 인용, 규격 비교 표(Table), 적합성 결론</b>을 검토 브리핑합니다.<br><br>
                <b>질문 예시</b>: <i>"TPS실 주간선 관로의 최소 규격 기준과 관련 조항은 뭐야?", "구내통신 아울렛 Cat.6 설치 기준 및 단자함 수용 포트 규정 알려줘"</i>
            </div>
            """, unsafe_allow_html=True)

        for message in st.session_state.ict_chat_history:
            with st.chat_message(message["role"]):
                st.markdown(str(message.get("content") or ""))

        user_input = st.chat_input("정보통신 법령, 기술기준, 설계 규격에 대해 검토 질의를 입력하세요...")

        if user_input:
            if not st.session_state.user_factchat_key:
                st.error("🔑 질문을 진행하려면 사이드바에 개인 FactChat API Key를 먼저 입력해 주세요!")
            else:
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state.ict_chat_history.append({"role": "user", "content": user_input})
                
                with st.chat_message("assistant"):
                    with st.spinner("정보통신 관련 법령 및 기술기준 지식 DB 정밀 검토 및 탐색 중..."):
                        # 🛡️ 4. RAG 지식 DB 예외 안전 처리
                        try:
                            contexts = search_ict_contexts(user_input, n_results=10)
                        except Exception as rag_e:
                            contexts = []
                            st.warning(f"⚠️ 지식 DB 탐색 중 일시적 지연이 발생하여 종합 기술 지식으로 답변을 생성합니다. ({rag_e})")
                        
                        has_rag_context = bool(contexts)
                        rag_context_str = ""
                        if contexts:
                            rag_context_str = "\n\n[참조 근거 정보통신 법령/기술기준/해설서 내용]\n"
                            # 🛡️ 6. RAG 발췌문 최대 글자 수 캡핑 (4,000자 제한)
                            current_length = 0
                            for c in contexts:
                                clean_fname = os.path.splitext(c.get('filename', '문서'))[0]
                                chunk_text = str(c.get('text', '')).strip()
                                snippet = f"- 근거 법령/지침서 문서: 「{clean_fname}」\n  조항 및 발췌 내용: {chunk_text}\n\n"
                                if current_length + len(snippet) > 4000:
                                    break
                                rag_context_str += snippet
                                current_length += len(snippet)
                        
                        # 🎓 수석 정보통신 감리/설계 전문가 전용 프롬프트 (100% 원본 동등 보존)
                        ict_system_instruction = (
                            "너는 정보통신공사, 구내통신설비, 방송통신 설비기준, 소방/감리 규정 분야 최고의 수석 엔지니어이자 법률·기술 규제 검토 전문 에이전트인 '용인특례시 처인구 정보통신 규제 및 설계 검토 AI 에이전트'이다.\n\n"
                            "통신 관련 업무 담당자(공무원, 감리원, 설계 엔지니어, 시공사 기술자)의 질문에 대해 기술적·법적 근거에 기반하여 최고의 전문성과 신뢰도를 갖춘 검토 결과를 제공해야 한다.\n\n"
                            "답변을 작성할 때 사용자가 한눈에 규제 수치 및 검토 의견을 파악할 수 있도록 다음 작성 규칙을 반드시 철저하게 준수하라:\n\n"
                            "1. **📋 정보통신 기술 규격 및 요건의 마크다운 표(Table) 적극 활용**:\n"
                            "   - 법정 배관 관로 규격(Ø28 등), 구내통신 회선 등급(Cat.6 등), 단자함 예비율, 설치 수량/거리 기준은 반드시 마크다운 표(Table)로 정돈하여 직관적으로 비교 제시할 것.\n"
                            "   - **[절대 주의 - 표(Table) 내 근거 열 작성 규칙]**: 답변 내 표(Table)를 작성할 때 '근거' 열에는 절대로 '조각 5', '조각 N', '청크 번호' 같은 무의미한 내부 파싱 용어를 쓰지 마라! 대신 반드시 `「방송통신설비 기술기준」 [별표 1]` 또는 `「방송통신설비의 기술기준에 관한 규정」 제17조의3` 처럼 **실제 법령 명칭 및 세부 조항/별표 명칭**을 명시하라!\n\n"
                            "2. **⚖️ 관련 법령 조항 및 기술기준 명확 인용**:\n"
                            "   - 검토 의견 제시 시 근거가 되는 법령 명칭(예: 「방송통신설비의 기술기준에 관한 규정」, 「정보통신공사업법」 제N조, 관련 [별표 N]) 및 세부 수치 요건을 명확하게 밝힐 것.\n\n"
                            "3. **💡 시각적 이모지와 굵은 강조를 통한 독해성 향상**:\n"
                            "   - **적합/부적합 여부**, **주요 필수 준수사항**, **시정 조치 지시**, **주의사항** 등 핵심 항목은 글씨를 **굵게 강조**하고 내용에 어울리는 전문 시각 이모지(📐, ⚖️, 📡, 🔌, 🏢, 🚨, ✅, ⚠️, 📌 등)를 적절히 배치할 것.\n\n"
                            "4. **🧱 챕터 구분선과 소제목 구조화**:\n"
                            "   - 답변이 긴 경우 반드시 가로 구분선(---)과 소제목(### ⚖️ 1. 법적·기술적 근거 검토 등)을 사용하여 논리적 단락을 나누어 제공할 것.\n\n"
                            "5. **📌 [실효적 법령 근거 인용 지침]**:\n"
                            "   - 만약 아래에 '[참조 근거 정보통신 법령/기술기준/해설서 내용]'이 주어진 경우, 다른 거짓 지식을 합성하지 말고 철저하게 해당 조항 발췌 텍스트를 근거로 검토 결론을 도출하라.\n"
                            "   - 답변의 맨 마지막 줄에는 반드시 이모지 📌 와 함께 다음과 같이 실제 법령 명칭을 포함한 굵은 텍스트로 근거 출처를 명시하라 (절대로 '조각'이라는 단어를 쓰지 마라):\n"
                            "     **📌 본 검토 의견은 「[참조한 실제 법령/지침 문서명]」의 관계 법령 및 방송통신 기술기준을 토대로 검토 작성되었습니다.**\n"
                            "   - 만약 업로드된 참조 문서 내용이 아예 주어지지 않은 경우(RAG DB가 비어있는 경우)에는 AI의 종합 정보통신 공학/법령 일반 지식을 동원해 답변하되, 맨 마지막 줄에 **💡 본 검토 의견은 AI 수석 엔지니어의 일반 정보통신 기술 지식을 토대로 작성되었습니다. (더 정확한 법적/기술적 조항 검토를 원하시면 사이드바에서 지침서 문서를 적재해 주세요.)** 라는 안내 출처를 남길 것.\n\n"
                            "6. **🎓 품격 있는 전문가적 톤앤매너**:\n"
                            "   - 용인특례시 처인구 정보통신 수석 감리원으로서 명확하고 전문적이며, 든든하고 친절한 태도로 완결성 있는 검토 보고서를 작성하듯 답변하라."
                        )
                        
                        if rag_context_str:
                            ict_system_instruction += rag_context_str
                            
                        headers = {
                            "Authorization": f"Bearer {st.session_state.user_factchat_key}",
                            "Content-Type": "application/json"
                        }
                        
                        api_messages = [{"role": "system", "content": ict_system_instruction}]
                        # 🛡️ 6. 대화 히스토리 슬라이딩 윈도우 (최근 10개 메세지로 제한하여 토큰 초과 완전 방어)
                        recent_chats = st.session_state.ict_chat_history[-10:]
                        for chat in recent_chats:
                            if chat.get("role") in ["user", "assistant"]:
                                api_messages.append({"role": chat["role"], "content": str(chat.get("content") or "")})
                                
                        # 🛡️ 1. 다중 모델 순차 폴백 서킷 (gpt-5.5 ➡️ gpt-5.6-luna ➡️ gemini-3.6-flash)
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
                                    final_response = str(raw_content).strip() if raw_content else "검토 의견 답변이 완전히 생성되지 않았습니다. 질문을 다시 한번 입력해 주세요."
                                    
                                    st.markdown(final_response)
                                    st.session_state.ict_chat_history.append({"role": "assistant", "content": final_response})
                                    success = True
                                    st.rerun()
                                    break
                                else:
                                    last_err = f"HTTP {response.status_code} ({response.text[:80]})"
                            except Exception as req_e:
                                last_err = str(req_e)
                                
                        if not success:
                            err_text = f"⚠️ **검토 수행 중 API 통신 장애가 발생했습니다.** (사유: {last_err})\n\n사이드바의 FactChat API Key가 올바른지 확인하거나 잠시 후 다시 질문해 주세요."
                            st.markdown(err_text)

    # ---------------------------------------------------
    # 탭 2: 연동된 정보통신 법령/기술기준 DB 현황
    # ---------------------------------------------------
    with tab_db_inspector:
        st.markdown("### 📚 연동된 정보통신 규제 & 설계 지식 DB 현황")
        st.markdown("현재 지능형 에이전트에 등록되어 검토 근거로 활용 중인 법령, 기술기준, 설계 해설서 데이터를 확인합니다.")
        
        st.markdown("""
        <div class="server-info-box">
            <b>📂 [용인특례시 처인구 정보통신 지식 DB 시스템 안내]</b><br>
            • <b>지원 파일 형식</b>: <code>.hwp</code> (구형 바이너리), <code>.hwpx</code> (신형 한글 XML), <code>.pdf</code> (문서 표준)<br>
            • <b>DB 저장 위치</b>: <code>./chroma_db/ict_agent_documents.db</code><br>
            • <b>특징</b>: 업로드한 정보통신 관련 법령, 기술기준, 설계해설서는 800자 단위로 빠짐없이 쪼개져 고속 검토 지식베이스로 가동됩니다.
        </div>
        """, unsafe_allow_html=True)
        
        try:
            stats = get_ict_document_stats()
        except Exception as stats_e:
            stats = []
            st.error(f"DB 통계 조회 중 오류 발생: {stats_e}")

        if stats:
            st.markdown("#### 📄 1. 연동된 정보통신 규정 문서별 상세 집계")
            stats_df = pd.DataFrame(stats)
            stats_df.columns = ["법령/기술기준 파일명", "분할 조항 조각 수", "총 글자 수", "첫 번째 조항 서두 미리보기"]
            st.dataframe(stats_df, use_container_width=True)
            
            st.divider()
            
            st.markdown("#### 🔬 2. 지식 DB 적재 조항 데이터 1:1 전수 열람")
            try:
                raw_chunks = get_all_ict_chunks()
                chunks_df = pd.DataFrame(raw_chunks, columns=["파일명", "조항 번호 (Index)", "글자 수", "실제 저장된 법령/기술기준 텍스트"])
                st.dataframe(chunks_df, use_container_width=True, height=450)
            except Exception as chunk_e:
                st.error(f"DB 텍스트 데이터 열람 중 오류 발생: {chunk_e}")
        else:
            st.warning("💡 현재 연동된 정보통신 법령/기술기준 문서가 없습니다. 사이드바에서 HWP, HWPX 또는 PDF 문서를 업로드해 주세요.")

except Exception as fatal_e:
    st.error(f"🚨 **시스템에 일시적인 지연 예외가 발생했습니다.** (사유: {fatal_e})")
    st.info("💡 안전한 상태로 복구하려면 아래 버튼을 눌러주세요.")
    if st.button("🔄 챗봇 세션 안전 초기화 및 복구"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
