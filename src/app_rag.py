import os
import json
import asyncio
import requests
import urllib3
import unicodedata
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# 로컬 HWPX/PDF 파서 및 SQLite RAG 엔진 임포트
from parser import extract_text_from_file
from rag_engine import (
    index_document, 
    search_relevant_contexts, 
    get_indexed_files, 
    get_detailed_document_stats,
    get_all_chunks_raw,
    delete_all_documents
)

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

# API 설정 로드
FACTCHAT_API_KEY = os.getenv("FACTCHAT_API_KEY")
FACTCHAT_BASE_URL = os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway"

# 🎨 스트림릿 페이지 설정 및 수려한 테마 적용
st.set_page_config(
    page_title="📂 HWPX/PDF 지능형 행정 비서",
    page_icon="📂",
    layout="wide"
)

# 프리미엄 CSS 주입
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
    }
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .brand-subtitle {
        font-size: 0.95rem;
        color: #5a6e7f;
        margin-bottom: 1.5rem;
    }
    .guide-card {
        background: #ffffff;
        border: 1px solid #e1e8ed;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
    }
    .server-info-box {
        background: #f8fafc;
        border-left: 4px solid #2563eb;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">📂 HWPX/PDF 지능형 행정 문서 비서</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-subtitle">한글(HWPX) 및 PDF 문서를 서버에 안전하게 적재하여 지식 검색 및 Q&A를 제공하는 포털입니다.</div>', unsafe_allow_html=True)

# ---------------------------------------------------
# 📁 [RAG 지식베이스] 업로더 상태 세션 변수
# ---------------------------------------------------
if "rag_uploader_key" not in st.session_state:
    st.session_state.rag_uploader_key = 0

# ---------------------------------------------------
# 📁 사이드바 업로더 & 관리자 대시보드
# ---------------------------------------------------
with st.sidebar:
    st.markdown("### 📥 행정 문서 업로더")
    st.markdown("여기에 HWPX 및 PDF 문서를 올려두시면 AI가 문서를 참조하여 답변합니다.")
    
    uploaded_files = st.file_uploader(
        "문서 업로드 (.hwpx, .pdf)",
        type=["hwpx", "pdf"],
        accept_multiple_files=True,
        key=f"rag_uploader_{st.session_state.rag_uploader_key}"
    )
    
    if uploaded_files:
        temp_dir = "./temp_docs"
        os.makedirs(temp_dir, exist_ok=True)
        newly_indexed = False
        
        for uploaded_file in uploaded_files:
            # 유니코드 한글 자소분리(NFD/NFC) 표준화
            clean_filename = unicodedata.normalize('NFC', uploaded_file.name)
            temp_path = os.path.join(temp_dir, clean_filename)
            
            indexed_key = f"rag_idx_{clean_filename}_{uploaded_file.size}"
            if indexed_key not in st.session_state:
                with st.spinner(f"'{clean_filename}' 분석 및 적재 중..."):
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                        
                    extracted_text = extract_text_from_file(temp_path)
                    if not extracted_text.startswith("[오류]"):
                        num_chunks = index_document(clean_filename, extracted_text)
                        st.session_state[indexed_key] = True
                        newly_indexed = True
                        st.success(f"✅ {clean_filename} ({num_chunks}개 조각) 적재 성공!")
                    else:
                        st.error(f"❌ {clean_filename} 분석 실패: {extracted_text}")
                        
        if newly_indexed:
            st.rerun()
                        
    indexed_list = get_indexed_files()
    if indexed_list:
        st.markdown("#### 📚 현재 DB에 연동된 지식 문서 목록:")
        for f_name in indexed_list:
            st.markdown(f"**📄 {f_name}**")
            
        st.write("")
        if st.button("🚨 지식베이스 전체 초기화", use_container_width=True):
            if delete_all_documents():
                for k in list(st.session_state.keys()):
                    if k.startswith("rag_idx_"):
                        del st.session_state[k]
                st.session_state.rag_uploader_key += 1
                st.success("지식베이스가 초기화되었습니다!")
                st.rerun()
    else:
        st.info("💡 등록된 지식 문서가 없습니다. 위에서 HWPX 또는 PDF 파일을 업로드해 주세요.")

# ---------------------------------------------------
# 메인 영역 탭 구성
# ---------------------------------------------------
tab_chat, tab_db_inspector = st.tabs([
    "💬 1. 스마트 문서 Q&A 챗봇", 
    "📊 2. 배포 서버 저장 위치 & DB 실시간 데이터 현황"
])

# ---------------------------------------------------
# 탭 1: 문서 대화 챗봇
# ---------------------------------------------------
with tab_chat:
    if "rag_chat_history" not in st.session_state:
        st.session_state.rag_chat_history = []

    if not st.session_state.rag_chat_history:
        st.markdown("""
        <div class="guide-card">
            <div style="font-weight:700; font-size:1.1rem; color:#1e3c72; margin-bottom:8px;">💡 스마트 문서 비서 사용법</div>
            1. 왼쪽 사이드바의 <b>[문서 업로드]</b> 공간에 HWPX 또는 PDF 문서를 넣어주세요.<br>
            2. 적재가 완료되면 아래 채팅창에 질문을 입력해 주세요.<br>
            3. AI가 서버 지식 DB에서 구절을 탐색하여 출처 인용 및 표 정리 답변을 제공합니다.
        </div>
        """, unsafe_allow_html=True)

    for message in st.session_state.rag_chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("연동된 문서에 대해 질문해 보세요... (예: 주요 사업 추진계획이 뭐야?)")

    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.rag_chat_history.append({"role": "user", "content": user_input})
        
        with st.chat_message("assistant"):
            with st.spinner("서버 지식 DB 탐색 중..."):
                contexts = search_relevant_contexts(user_input, n_results=3)
                
                rag_context_str = ""
                if contexts:
                    rag_context_str = "\n\n[참조된 로컬 행정 문서 내용]\n"
                    for c in contexts:
                        rag_context_str += f"- 출처: {c['filename']} (조각 {c['chunk_index'] + 1})\n  내용: {c['text'].strip()}\n\n"
                
                system_instruction = (
                    "너는 최고의 스마트 행정 문서 분석가 비서인 'RAG 스마트 문서 비서'이다.\n\n"
                    "답변을 작성할 때 가독성을 극적으로 끌어올려 사용자가 한눈에 파악할 수 있도록 반드시 다음 규칙을 절대적으로 준수해라:\n"
                    "1. **표(Table) 형식의 적극적인 활용**: 신청 자격 요건, 제출 서류 및 수치 데이터, 주요 일정 등은 가급적 마크다운 표(Table)를 짜서 구조적으로 정렬하여 나타낼 것.\n"
                    "2. **굵은 강조와 이모지**: 주요 마감 기한, 특이사항, 제출 시 유의사항 등 핵심 정보는 글씨를 **굵게 강조**하고 내용에 알맞은 시각적 이모지(🍱, 📅, 📊, 📂, 📌, ⚠️ 등)를 붙여라.\n"
                    "3. **구분선과 문단 쪼개기**: 답변이 긴 경우 반드시 가로 구분선(---)과 소제목(### 📂 제출 서류 리스트 등)을 사용하여 챕터를 읽기 좋게 끊어서 제공해라.\n"
                    "4. **[참조 문서 내용 인용 지침]**: 만약 아래에 '[참조된 로컬 행정 문서 내용]'이 주어진 경우, 다른 거짓 지식을 합성하지 말고 철저하게 해당 텍스트 내용만을 토대로 답변을 완성해라. 그리고 답변 맨 마지막에 반드시 이모지 📌 와 함께 **'이 내용은 [참조한 파일명]의 조각 내용을 토대로 작성되었습니다.'** 라는 출처를 굵은 텍스트로 남겨라.\n"
                    "5. **완결성**: 대화의 흐름에 맞추어 전문적이고 신뢰감 넘치며 친근하게 답해라."
                )
                
                if rag_context_str:
                    system_instruction += rag_context_str
                    
                headers = {
                    "Authorization": f"Bearer {FACTCHAT_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                api_messages = [{"role": "system", "content": system_instruction}]
                for chat in st.session_state.rag_chat_history:
                    if chat["role"] in ["user", "assistant"]:
                        api_messages.append({"role": chat["role"], "content": chat["content"]})
                        
                try:
                    payload = {
                        "model": "gpt-5.5",
                        "messages": api_messages,
                        "temperature": 0.15
                    }
                    
                    response = requests.post(
                        f"{FACTCHAT_BASE_URL}/chat/completions",
                        headers=headers,
                        json=payload,
                        verify=False,
                        timeout=40
                    )
                    response.raise_for_status()
                    response_json = response.json()
                    final_response = response_json['choices'][0]['message']['content']
                    
                    st.markdown(final_response)
                    st.session_state.rag_chat_history.append({"role": "assistant", "content": final_response})
                    st.rerun()
                    
                except Exception as e:
                    err_text = f"⚠️ **연동 오류가 발생했습니다.** (사유: {e})"
                    st.markdown(err_text)

# ---------------------------------------------------
# 탭 2: 배포 서버 저장 위치 & DB 실시간 데이터 현황 대시보드
# ---------------------------------------------------
with tab_db_inspector:
    st.markdown("### 📊 배포 서버 파일 저장 위치 & DB 데이터 현황")
    st.markdown("스트림릿 URL로 업로드된 파일이 배포된 서버의 어디에 저장되며, 어떤 텍스트 조각들이 적재되어 있는지 실시간 확인합니다.")
    
    st.markdown("""
    <div class="server-info-box">
        <b>📂 [배포 서버 내 파일 및 DB 물리적 저장 위치]</b><br>
        • <b>임시 파일 물리적 저장 경로</b>: <code>./temp_docs/</code> (서버 컨테이너 디스크)<br>
        • <b>SQLite DB 물리적 저장 경로</b>: <code>./chroma_db/rag_documents.db</code> (서버 컨테이너 DB 파일)<br>
        • <b>특징</b>: 모든 접속 사용자가 업로드한 파일은 배포된 서버의 단일 SQLite DB(<code>rag_documents.db</code>)에 전수 모여 저장됩니다.
    </div>
    """, unsafe_allow_html=True)
    
    # 1. 파일별 집계 현황 표
    stats = get_detailed_document_stats()
    if stats:
        st.markdown("#### 📄 1. 서버 DB에 적재된 문서별 상세 현황표")
        stats_df = pd.DataFrame(stats)
        stats_df.columns = ["파일명 (File Name)", "분할 조각 수 (Chunks)", "총 글자 수 (Total Chars)", "첫 번째 조각 서두 미리보기"]
        st.dataframe(stats_df, use_container_width=True)
        
        st.divider()
        
        # 2. 전수 텍스트 조각 브라우저
        st.markdown("#### 🔬 2. 서버 DB에 저장된 텍스트 조각(Chunk) 전수 열람")
        raw_chunks = get_all_chunks_raw()
        chunks_df = pd.DataFrame(raw_chunks, columns=["파일명", "조각 번호 (Index)", "글자 수", "실제 저장된 텍스트 본문"])
        st.dataframe(chunks_df, use_container_width=True, height=450)
    else:
        st.warning("💡 현재 배포 서버 DB에 적재된 문서가 없습니다. 왼쪽 사이드바에서 HWPX 또는 PDF 파일을 업로드해 보세요.")
