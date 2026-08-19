import os
import json
import requests
import urllib.parse
import urllib3
import streamlit as st
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

# ==========================================
# 0. 초기 세팅 및 네트워크 최적화
# ==========================================
st.set_page_config(page_title="용인시 시정 동향 모니터링", page_icon="🏛️", layout="wide")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
FACTCHAT_API_KEY = os.getenv("FACTCHAT_API_KEY")
FACTCHAT_BASE_URL = os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway"
KEYWORD_FILE = "keywords_db.json"

# 전역 CSS 디자인 인젝션 (호버 효과 및 카드 디자인)
st.markdown("""
<style>
    .report-card {
        background-color: #ffffff;
        border: 1px solid #eaeaea;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: all 0.2s ease-in-out;
    }
    .report-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        border-color: #d0d7de;
    }
    .tag-badge {
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 12px;
    }
    .tag-news { background-color: #e3f2fd; color: #1565c0; }
    .tag-blog { background-color: #e8f5e9; color: #2e7d32; }
    .tag-cafe { background-color: #fff3e0; color: #e65100; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_network_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

session = get_network_session()

# ==========================================
# 1. 상태 관리
# ==========================================
if 'keywords' not in st.session_state:
    if os.path.exists(KEYWORD_FILE):
        try:
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                st.session_state.keywords = json.load(f)
        except Exception:
            st.session_state.keywords = ["용인특례시", "용인시", "처인구"]
    else:
        st.session_state.keywords = ["용인특례시", "용인시", "처인구"]

if 'llm_results' not in st.session_state:
    st.session_state.llm_results = {}

def save_keywords():
    with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
        json.dump(st.session_state.keywords, f, ensure_ascii=False)

# ==========================================
# 2. 네이버 API 데이터 수집 (정렬 로직 추가)
# ==========================================
@st.cache_data(ttl=300)
def fetch_naver_data(query, display_cnt, sort_type, target="news"):
    if not CLIENT_ID or not CLIENT_SECRET:
        return []
    url = f"https://openapi.naver.com/v1/search/{target}.json"
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    
    adjusted_query = f"용인 {query}" if target == "cafearticle" and "용인" not in query else query
    enc_text = urllib.parse.quote(adjusted_query)
    
    request_url = f"{url}?query={enc_text}&display={display_cnt}&sort={sort_type}"
    
    try:
        res = requests.get(request_url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("items", [])
    except Exception:
        pass
    return []

# ==========================================
# 3. 사내 LLM 분석 모듈
# ==========================================
def analyze_content_with_factchat(title, description):
    if not FACTCHAT_API_KEY or not FACTCHAT_BASE_URL:
        return {"summary": "API 설정 누락", "is_negative": False, "point": ""}
        
    system_prompt = """
    당신은 20년 경력의 공공기관 AI, IT 기술/경제/부동산 전문 분석가이다.
    복잡한 정보를 핵심만 추려 전달하며, 단순 홍보성 문구는 제외하고 데이터와 팩트 중심으로 요약한다.
    
    [분석 지침]
    1. 내용을 정확히 '3줄 요약'하라. (말투는 전문적이고 간결한 '다'체 통일)
    2. 내용 중 시민의 '부정, 불만, 민원, 비판, 갈등' 요소가 있다면 [위험도: 높음]으로 간주하고 구체적인 '불만 요점'을 2줄로 추출하라.
    """
    
    user_prompt = f"""
    제목: {title}\n내용: {description}
    출력 포맷(JSON): {{"summary": "1줄 요약...\\n2줄 요약...\\n3줄 요약...", "is_negative": true 또는 false, "point": "핵심요점"}}
    """
    
    payload = {
        "model": "gpt-5.4",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    headers = {"Authorization": f"Bearer {FACTCHAT_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res = session.post(f"{FACTCHAT_BASE_URL}/chat/completions", headers=headers, json=payload, verify=False, timeout=20)
        res.raise_for_status()
        result_text = res.json()['choices'][0]['message']['content'].strip()
        
        if "{" in result_text and "}" in result_text:
            result_text = result_text[result_text.find("{"):result_text.rfind("}")+1]
        return json.loads(result_text)
    except Exception as e:
        return {"summary": f"요약 중 통신 오류 발생: {e}", "is_negative": False, "point": ""}

# ==========================================
# 4. 화면 UI 렌더링 (사이드바 / 메인 분리)
# ==========================================

# --- [사이드바 통제실] ---
with st.sidebar:
    st.header("⚙️ 모니터링 설정")
    
    st.subheader("1. 정렬 및 수집 기준")
    sort_option = st.radio("데이터 정렬 방식", ["정확도/인기순 (sim)", "최신순 (date)"])
    sort_param = "sim" if "sim" in sort_option else "date"
    
    display_count = st.slider("채널별 수집 건수", min_value=5, max_value=30, value=10, step=5)
    st.divider()
    
    st.subheader("2. 키워드 선택")
    if not st.session_state.keywords:
        st.warning("등록된 키워드가 없습니다.")
        selected_kw = None
    else:
        selected_kw = st.radio("현재 모니터링 타겟", st.session_state.keywords, label_visibility="collapsed")
        
        if st.button("🗑️ 현재 키워드 삭제", use_container_width=True):
            st.session_state.keywords.remove(selected_kw)
            save_keywords()
            st.rerun()
            
    st.divider()
    st.subheader("3. 새 키워드 추가")
    new_keyword = st.text_input("키워드 입력", placeholder="예: 처인구")
    if st.button("➕ 등록", use_container_width=True) and new_keyword:
        if new_keyword not in st.session_state.keywords:
            st.session_state.keywords.append(new_keyword)
            save_keywords()
            st.rerun()

# --- [메인 데이터 패널] ---
if selected_kw:
    st.title(f"📊 '{selected_kw}' 실시간 시정 동향 모니터링")
    st.caption(f"기준: {sort_option.split(' ')[0]} | 채널당 {display_count}건 수집")
    
    tab_news, tab_comm = st.tabs(["📡 언론 보도 (News)", "💬 지역 여론 (블로그/카페)"])

    def clean_html(text):
        return text.replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')

    def render_article_card(item, unique_key, source_type="news"):
        title = clean_html(item['title'])
        desc = clean_html(item.get('description', item.get('desc', '')))
        link = item['link']
        date = item.get('pubDate', item.get('postdate', ''))
        date_html = f'<div style="font-size: 12px; color: #888; margin-bottom: 16px;">🕒 {date}</div>' if date else ''
        
        if source_type == "news":
            tag_html = "<span class='tag-badge tag-news'>📡 언론보도</span>"
        elif source_type == "blog":
            tag_html = "<span class='tag-badge tag-blog'>📌 네이버 블로그</span>"
        else:
            cafe_name = item.get('cafename', '지역 커뮤니티')
            tag_html = f"<span class='tag-badge tag-cafe'>👥 네이버 카페 ({cafe_name})</span>"

        html_content = f"""<div class="report-card">
{tag_html}
<h4 style="margin-top: 0; margin-bottom: 8px; font-size: 18px;">
    <a href="{link}" target="_blank" style="text-decoration: none; color: #1a73e8; font-weight: 600;">{title}</a>
</h4>
{date_html}
<p style="font-size: 15px; color: #444; line-height: 1.6; margin: 0;">{desc}</p>
</div>"""

        st.markdown(html_content, unsafe_allow_html=True)
        
        if link in st.session_state.llm_results:
            analysis = st.session_state.llm_results[link]
            with st.container(border=True):
                if analysis.get("is_negative"):
                    st.error(f"⚠️ **[리스크 요점 추출]:** {analysis.get('point')}")
                st.success(f"**🤖 FACTCHAT 핵심 요약**\n\n{analysis.get('summary')}")
        else:
            if st.button("🔍 AI 심층 요약 및 리스크 분석", key=f"btn_{unique_key}", use_container_width=True):
                with st.spinner("AI 분석가가 핵심을 추려내고 있습니다..."):
                    st.session_state.llm_results[link] = analyze_content_with_factchat(title, desc)
                    st.rerun()
        st.write("")

    with tab_news:
        news_items = fetch_naver_data(selected_kw, display_count, sort_param, "news")
        if news_items:
            for i, item in enumerate(news_items):
                render_article_card(item, unique_key=f"news_{selected_kw}_{i}", source_type="news")
        else:
            st.info("조건에 일치하는 보도자료가 검색되지 않았습니다. (네이버 API Key 설정을 확인해 주세요.)")

    with tab_comm:
        blogs = fetch_naver_data(selected_kw, display_count, sort_param, "blog")
        cafes = fetch_naver_data(selected_kw, display_count, sort_param, "cafearticle")
        
        combined = []
        for c in cafes: 
            c['source_type'] = 'cafe'
            combined.append(c)
            
        for b in blogs: 
            b['source_type'] = 'blog'
            combined.append(b)
            
        if combined:
            for i, item in enumerate(combined):
                render_article_card(item, unique_key=f"comm_{selected_kw}_{i}", source_type=item['source_type'])
        else:
            st.info("조건에 일치하는 커뮤니티 게시글이 검색되지 않았습니다.")

else:
    st.info("👈 좌측 제어반에서 모니터링할 타겟 키워드를 선택하세요.")
