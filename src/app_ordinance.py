import os
import json
import asyncio
import requests
import urllib3
import streamlit as st
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# SSL 경고 비활성화 및 환경 변수 로드
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

FACTCHAT_API_KEY = get_secret_safe("FACTCHAT_API_KEY") or os.getenv("FACTCHAT_API_KEY")
FACTCHAT_BASE_URL = clean_base_url(get_secret_safe("FACTCHAT_BASE_URL") or os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway")
LAW_OC = get_secret_safe("LAW_OC") or os.getenv("LAW_OC") or "a123456789001"

# 🎨 프리미엄 자치행정 스타일 테마 CSS 정의 (올리브/골드/매트그레이)
st.set_page_config(
    page_title="🏛️ 용인시 자치법규 AI 어시스텐트",
    page_icon="🏛️",
    layout="centered"
)

st.markdown("""
<style>
    /* 기본 마진 패딩 최적화 */
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 7rem !important;
        max-width: 750px !important;
    }

    /* 자치정부 느낌의 신뢰성 높은 헤더 */
    .gov-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #2c3e50 0%, #1e8449 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.05rem;
    }

    .gov-subtitle {
        font-size: 0.95rem;
        color: #7f8c8d;
        margin-bottom: 1.8rem;
        font-weight: 500;
    }

    /* 입체형 안내 카드 */
    .gov-card {
        background: #fdfefe;
        border: 1px solid #d5dbdb;
        border-radius: 14px;
        padding: 1.3rem;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.5rem;
    }

    .gov-card-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1e8449;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# 🏛️ 타이틀 영역
st.markdown('<div class="gov-title">🏛️ 용인시 자치법규 AI 어시스텐트</div>', unsafe_allow_html=True)
st.markdown('<div class="gov-subtitle">로컬 MCP 엔진을 기반으로 해외 차단 우려 없이 용인시 조례·규칙·자치법규를 실시간 조회하는 행정 보좌 시스템입니다.</div>', unsafe_allow_html=True)

# 🔑 법제처 키 누락 시 경고창 띄우기 (공용 키 사용 중일 때)
if LAW_OC == "a123456789001":
    st.warning(
        "⚠️ **임시 공용 테스트 키(a123456789001)로 작동 중입니다.**\n\n"
        "이 테스트 키는 일일 호출량 제한으로 인해 다른 사용자가 많이 쓰면 수시로 차단(ConnectTimeoutError)될 수 있습니다.\n"
        "원활하고 끊김 없는 실시간 자치법규 조회를 원하신다면 **[국가법령정보 오픈API](https://open.law.go.kr)**에서 무료로 개인 키를 받아 로컬의 `.env` 파일에 `LAW_OC=발급키` 형태로 설정해 주세요."
    )

# ===================================================
# 🔌 [비동기 MCP 연동 함수] Stdio Pipe 기반의 local 실행
# ===================================================
async def search_legislation_via_mcp(query_str: str) -> str:
    """
    로컬 Node.js 패키지 'korean-law-mcp'를 백그라운드 Stdio 파이프로 띄워
    법제처 오픈 API에 접속하고 자치법규 검색 결과 및 상세 본문을 체이닝 호출하여 획득합니다.
    """
    # 전역이 아닌 로컬 폴더에 설치된 라이브러리 및 npx 명령을 활용한 우회 구동
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "korean-law-mcp"],
        env={
            "LAW_OC": LAW_OC,
            "PATH": os.environ.get("PATH", "")
        }
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # MCP 서버가 노출 중인 도구 목록 조회
                tools_response = await session.list_tools()
                tool_names = [tool.name for tool in tools_response.tools]
                
                # 1. 1단계: 검색 실행 (search_law 등)
                target_tool = "search_law"
                if "search_law" not in tool_names:
                    possible_tools = [name for name in tool_names if "search" in name]
                    if possible_tools:
                        target_tool = possible_tools[0]
                    else:
                        return "[오류] 법령 검색용 도구를 MCP 서버에서 찾을 수 없습니다."
                
                # 검색 실행
                result = await session.call_tool(
                    name=target_tool,
                    arguments={"query": query_str}
                )
                
                # 결과 텍스트 취합
                search_output = ""
                for content in result.content:
                    if hasattr(content, 'text'):
                        search_output += content.text + "\n"
                
                if not search_output.strip() or "[NOT_FOUND]" in search_output:
                    return f"'{query_str}' 관련 자치법규를 찾지 못했습니다."
                
                # 2. 2단계: 결과 내용에서 자치법규 고유 ID 추출 (예: id="2106161", ID: 2106161 등)
                import re
                # id="2106161" 이나 ID: 2106161 형태의 숫자 6~8자리를 찾기 위한 정규식
                match_id = re.search(r'(?:id|ordinanceId|ID)[\s\:\=\'\"\`]*(\d{6,8})', search_output, re.IGNORECASE)
                
                # 만약 명시적인 id 라벨이 없더라도 숫자 단독 7자리가 있으면 획득 시도
                if not match_id:
                    match_id = re.search(r'\b(\d{7})\b', search_output)
                
                # 상세 본문 도구(get_ordinance)가 존재하고 ID를 파싱해 냈다면 2차 체이닝 실행
                if match_id and "get_ordinance" in tool_names:
                    target_id = match_id.group(1)
                    
                    # get_ordinance를 통한 본문 조회 호출
                    detail_result = await session.call_tool(
                        name="get_ordinance",
                        arguments={"id": target_id}
                    )
                    
                    detail_output = ""
                    for content in detail_result.content:
                        if hasattr(content, 'text'):
                            detail_output += content.text + "\n"
                            
                    return (
                        f"=== 자치법규 검색 정보 ===\n{search_output}\n\n"
                        f"=== [{query_str}] 상세 본문 조문 내용 ===\n{detail_output}"
                    )
                
                # 상세 본문 도구를 지원하지 않거나 ID가 매칭되지 않을 경우 목록 정보 폴백 리턴
                return search_output
                
    except Exception as e:
        return f"[오류] 로컬 MCP 서버 가동 및 연동 실패: {e}"

def extract_clean_search_query(user_query: str) -> str:
    """
    사용자의 질문에서 법령/조례 검색에 최적화된 핵심 법령명 키워드(예: '용인시 주차장')만
    추출하는 1차 LLM 전처리 함수입니다.
    """
    headers = {
        "Authorization": f"Bearer {FACTCHAT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_instruction = (
        "너는 사용자의 질문을 법제처 오픈 API 검색용 최적의 단어(법령명/조례명)로 정제해 주는 쿼리 파서(Query Parser)이다.\n"
        "사용자가 입력한 질문에서 '보여줘', '알려줘', '전문', '무엇이', '규정', '뜻', '내용', '기준', '관한' 등의 자연어, 요청어 및 불필요한 조사를 완전히 제거해라.\n"
        "오직 법제처 검색창에 입력했을 때 검색 성공률이 가장 높은 핵심 조례/법령 명칭 키워드(예: '용인시 주차장 설치 및 관리 조례' 또는 '용인시 소상공인 지원 조례')만 딱 한 단어로 출력해라.\n"
        "설명이나 다른 텍스트는 절대 붙이지 말고 오직 정제된 검색어 하나만 반환해라."
    )
    
    payload = {
        "model": "gpt-5.5",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.05
    }
    
    try:
        response = requests.post(
            f"{FACTCHAT_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            verify=False,
            timeout=15
        )
        response.raise_for_status()
        response_json = response.json()
        cleaned_query = response_json['choices'][0]['message']['content'].strip()
        cleaned_query = cleaned_query.replace('"', '').replace("'", "")
        return cleaned_query
    except Exception:
        return user_query

# 스트림릿 내 비동기 동기 래핑 실행 함수
def run_mcp_query(query_str: str) -> str:
    try:
        # Streamlit 스레드 내의 새로운 이벤트 루프 가동
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(search_legislation_via_mcp(query_str))
        loop.close()
        return result
    except Exception as e:
        return f"[오류] 비동기 처리 실패: {e}"

# ===================================================
# 💬 [대화 세션 관리 및 UI]
# ===================================================
if "ordinance_history" not in st.session_state:
    st.session_state.ordinance_history = []

# 대화가 비었을 때 기본 사용 가이드 렌더링
if not st.session_state.ordinance_history:
    st.markdown("""
    <div class="gov-card">
        <div class="gov-card-header">💡 용인시 자치법규 어시스텐트 활용 예시</div>
        AI가 로컬 방화벽 안전망 내부에서 조례를 직접 긁어와 정확한 법적 근거에 맞춰 대답합니다.<br><br>
        • "용인시 주차장 조례에 명시된 하이브리드/친환경 차량 할인 혜택이 뭐야?"<br>
        • "용인시 소상공인 지원 조례에 적힌 재정적 지원 대상을 요약해줘"<br>
        • "용인시 아동학대 예방 및 방지에 관한 조례를 알려줘"
    </div>
    """, unsafe_allow_html=True)

# 이전 대화 렌더링
for msg in st.session_state.ordinance_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력 받기
user_input = st.chat_input("용인시 조례나 자치법규에 대해 질문해 보세요... (예: 용인시 주차장 설치 기준)")

if user_input:
    # 1. 유저 말풍선 그리기 및 기록
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.ordinance_history.append({"role": "user", "content": user_input})
    
    # 2. AI 법규 RAG 가동
    with st.chat_message("assistant"):
        
        # (1) 1차 LLM 쿼리 정제 적용하여 검색 성공률 보장
        with st.spinner("질문 분석 및 검색어 정제 중..."):
            search_query = extract_clean_search_query(user_input)
                
        # (2) 로컬 MCP 서버 호출을 통해 정제된 키워드로 자치법규 실시간 검색
        with st.spinner(f"🔍 정제된 검색어 [{search_query}]로 실시간 자치법규 조회 중..."):
            mcp_data = run_mcp_query(search_query)
            
            # (2) Factchat completions API에 태워 보낼 System 프롬프트 정의
            system_instruction = (
                "너는 대한민국 용인시 자치법정의 전문 보좌관인 '용인시 자치법규 AI 어시스텐트'이다.\n\n"
                "사용자의 질문에 대해 법제처에서 실시간으로 긁어온 아래 [참조 자치법규 데이터]를 뼈대로 삼아 대답해라.\n"
                "답변을 작성할 때 반드시 다음 가독성 규칙을 준수해라:\n"
                "1. **조문과 단락의 구조화**: 신청 조건, 감면 혜택 비율, 설치 규격 등 구체적인 수치나 명세는 **반드시 마크다운 표(Table)**나 깔끔한 순번 리스트로 일목요연하게 비교해서 나타낼 것.\n"
                "2. **출처의 절대성**: 아래 [참조 자치법규 데이터]에 명시된 조항 번호(예: 제X조, 제X항)를 반드시 명시하여 사실에 기틀을 두고 서술해라.\n"
                "3. **마지막 이모지 피드백**: 답변 끝에는 항상 📌 와 함께 **'이 내용은 법제처 로컬 MCP를 통해 실시간 수집된 조례를 토대로 작성되었습니다.'** 라는 굵은 꼬리말을 얹을 것.\n"
                "4. 만약 검색 데이터가 오류이거나 아무것도 찾아지지 않은 상태라면, 오류 메시지 사유를 알려주고 '현재 임시 키를 사용 중이시라면 트래픽 초과일 수 있으니 .env 키 등록을 참고해 달라'고 안내해라."
            )
            
            # 참조 지식 장착
            system_instruction += f"\n\n[참조 자치법규 데이터]\n{mcp_data}\n\n"
            
            # API 전송용 메세지 패킹
            api_messages = [{"role": "system", "content": system_instruction}]
            for chat in st.session_state.ordinance_history:
                if chat["role"] in ["user", "assistant"]:
                    api_messages.append({"role": chat["role"], "content": chat["content"]})
            
            headers = {
                "Authorization": f"Bearer {FACTCHAT_API_KEY}",
                "Content-Type": "application/json"
            }
            
            try:
                payload = {
                    "model": "gpt-5.5",
                    "messages": api_messages,
                    "temperature": 0.1
                }
                
                response = requests.post(
                    f"{FACTCHAT_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    verify=False,
                    timeout=45
                )
                response.raise_for_status()
                response_json = response.json()
                final_answer = response_json['choices'][0]['message']['content']
                
                st.markdown(final_answer)
                st.session_state.ordinance_history.append({"role": "assistant", "content": final_answer})
                st.rerun()
                
            except Exception as e:
                err_txt = f"⚠️ **자치법규 조율 과정에서 오류가 발생했습니다.** (사유: {e})\n\n잠시 후 다시 질문해 주시거나 검색 키워드를 '용인시 주차장 조례'와 같이 간결하게 입력해 주세요."
                st.markdown(err_txt)
