import os
import json
import re
import requests
import urllib.parse
import urllib3
import streamlit as st
from difflib import SequenceMatcher
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

# 전역 CSS 디자인 인젝션
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    .report-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px 26px;
        margin-bottom: 18px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
        transition: all 0.2s ease-in-out;
    }
    .report-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07);
        border-color: #cbd5e1;
    }
    .tag-badge {
        font-size: 11px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 12px;
        margin-right: 6px;
    }
    .tag-news { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .tag-blog { background-color: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .tag-cafe { background-color: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
    .tag-dedup { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    
    .analysis-card-neutral {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 18px;
        margin-top: 12px;
        line-height: 1.7;
        white-space: pre-wrap !important;
    }
    .analysis-card-risk {
        background-color: #fff5f5;
        border: 1px solid #fecaca;
        border-radius: 12px;
        padding: 18px;
        margin-top: 12px;
        line-height: 1.7;
        white-space: pre-wrap !important;
    }
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
# 2. 강력한 다층(Multi-Layer) 중복 제거 알고리즘
# ==========================================
MAJOR_MEDIA_LIST = [
    "연합뉴스", "KBS", "SBS", "MBC", "YTN", "조선일보", "중앙일보", "동아일보", 
    "매일경제", "한국경제", "전자신문", "경향신문", "한겨레", "경기일보", "중부일보", 
    "인천일보", "기호일보", "경기신문", "뉴시스", "뉴스1"
]

def clean_html(text):
    if not text:
        return ""
    text = text.replace('<b>', '').replace('</b>', '').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
    return text.strip()

def clean_title_for_sim(title):
    cleaned = clean_html(title)
    cleaned = re.sub(r'\[.*?\]|\(.*?\)|<.*?>', '', cleaned)
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    return cleaned.strip()

def get_word_set(title):
    cleaned = clean_title_for_sim(title)
    words = [w for w in cleaned.split() if len(w) >= 2]
    return set(words)

def calc_word_overlap(set1, set2):
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    min_len = min(len(set1), len(set2))
    return len(intersection) / float(min_len)

def get_media_authority_score(item):
    link = item.get("originallink", "") or item.get("link", "")
    title = item.get("title", "")
    score = 0
    for media in MAJOR_MEDIA_LIST:
        if media in title or media in link:
            score += 20
            break
    if "news.naver.com" in link:
        score += 10
    return score

def is_duplicate_news(item1, item2):
    t1 = clean_title_for_sim(item1["title"])
    t2 = clean_title_for_sim(item2["title"])
    
    # 1. 문자열 유사도
    str_sim = SequenceMatcher(None, t1, t2).ratio()
    if str_sim >= 0.38:
        return True
        
    # 2. 단어 키워드 오버랩
    w1, w2 = get_word_set(item1["title"]), get_word_set(item2["title"])
    overlap = calc_word_overlap(w1, w2)
    if overlap >= 0.40:
        return True
        
    return False

def deduplicate_news_items(items):
    if not items:
        return []
        
    clusters = []
    for item in items:
        matched_cluster = None
        for cluster in clusters:
            if is_duplicate_news(item, cluster["representative"]):
                matched_cluster = cluster
                break
                
        if matched_cluster:
            matched_cluster["duplicates_count"] += 1
            matched_cluster["all_items"].append(item)
            if get_media_authority_score(item) > get_media_authority_score(matched_cluster["representative"]):
                matched_cluster["representative"] = item
        else:
            clusters.append({
                "representative": item,
                "duplicates_count": 1,
                "all_items": [item]
            })
            
    return clusters

# ==========================================
# 3. 네이버 API 수집
# ==========================================
@st.cache_data(ttl=180, show_spinner=False)
def fetch_naver_data(query, display_cnt, sort_type, target="news"):
    if not CLIENT_ID or not CLIENT_SECRET:
        return []
    url = f"https://openapi.naver.com/v1/search/{target}.json"
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    
    adjusted_query = f"용인 {query}" if target == "cafearticle" and "용인" not in query else query
    enc_text = urllib.parse.quote(adjusted_query)
    
    fetch_limit = 100 if target == "news" else display_cnt
    request_url = f"{url}?query={enc_text}&display={fetch_limit}&sort={sort_type}"
    
    try:
        res = requests.get(request_url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("items", [])
    except Exception:
        pass
    return []

# ==========================================
# 4. 고품격 AI 심층 브리핑 & 리스크 분석 모듈
# ==========================================
def analyze_content_with_factchat(title, description):
    if not FACTCHAT_API_KEY or not FACTCHAT_BASE_URL:
        return {"summary": "API 설정 누락", "is_negative": False, "point": ""}
        
    system_prompt = """너는 20년 경력의 공공기관 수석 시정 모니터링 분석가이다.
제시된 기사 및 민원/여론 게시글을 정밀 분석하여, 단체장 및 실무자가 15초 만에 핵심 현황과 대응 포인트를 파악할 수 있도록 '고품격 시정 종합 브리핑'을 작성하라.

[분석 가이드라인 - 절대 준수]:
1. **📌 [시정 핵심 브리핑]**: 딱딱한 1, 2, 3번 목록 대신, 사건의 주요 배경, 핵심 사실 및 구체적 수치/사업 규격이 자연스럽게 연결되는 2~3개 고급 단락(총 3~5문장)으로 풍부하게 작성하라.
2. **⚠️ [민원/갈등/리스크 판단 및 요점]**:
   - 시민의 부정적 민원, 갈등, 비판, 정책 불만, 시정 위험 요소가 있는 경우 `is_negative`를 `true`로 설정하고, **주요 불만 및 갈등 원인**을 자연스러운 2문장으로 구체적으로 명시하라.
   - 긍정적이거나 일반 보도인 경우 `is_negative`를 `false`로 설정하라.
3. 인사말이나 사족은 배제하고 아래 JSON 포맷으로 정확히 출력하라.

[출력 포맷(JSON 규격)]:
{
  "summary": "📌 [시정 핵심 브리핑]\n자연스럽게 연결되는 1단락...\n\n자연스럽게 이어지는 2단락...",
  "is_negative": true 또는 false,
  "point": "⚠️ [시민 민원/갈등 요점]\n주요 불만 원인 및 대응 필요사항..."
}
"""
    
    user_prompt = f"제목: {title}\n내용/요약: {description}"
    
    payload = {
        "model": "gpt-5.4",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.15
    }
    headers = {"Authorization": f"Bearer {FACTCHAT_API_KEY}", "Content-Type": "application/json"}
    
    try:
        res = session.post(f"{FACTCHAT_BASE_URL}/chat/completions", headers=headers, json=payload, verify=False, timeout=25)
        res.raise_for_status()
        result_text = res.json()['choices'][0]['message']['content'].strip()
        
        if "{" in result_text and "}" in result_text:
            result_text = result_text[result_text.find("{"):result_text.rfind("}")+1]
        return json.loads(result_text)
    except Exception as e:
        return {"summary": f"요약 분석 중 오류 발생: {e}", "is_negative": False, "point": ""}

# ==========================================
# 5. 화면 UI 렌더링
# ==========================================

# --- [사이드바 통제실] ---
with st.sidebar:
    st.header("⚙️ 모니터링 설정")
    
    if st.button("🔄 실시간 데이터 강제 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    
    st.subheader("1. 정렬 및 수집 기준")
    sort_option = st.radio("데이터 정렬 방식", ["정확도/인기순 (sim)", "최신순 (date)"])
    sort_param = "sim" if "sim" in sort_option else "date"
    
    display_count = st.slider("채널별 표시 건수", min_value=5, max_value=30, value=10, step=5)
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
    col_t1, col_t2 = st.columns([0.8, 0.2])
    with col_t1:
        st.title(f"📊 '{selected_kw}' 실시간 시정 동향 모니터링")
        st.caption(f"기준: {sort_option.split(' ')[0]} | 키워드 단어 오버랩 기반 100% 중복 기사 클러스터링 제거 완료")
    with col_t2:
        st.write("")
        if st.button("🔄 캐시 비우고 재조회", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
    tab_news, tab_comm = st.tabs(["📡 대표 언론 보도 (중복제거 100% 적용)", "💬 지역 여론 (블로그/카페)"])

    def render_article_card(item_info, unique_key, source_type="news"):
        if isinstance(item_info, dict) and "representative" in item_info:
            item = item_info["representative"]
            dup_cnt = item_info["duplicates_count"]
        else:
            item = item_info
            dup_cnt = 1
            
        title = clean_html(item['title'])
        desc = clean_html(item.get('description', item.get('desc', '')))
        link = item['link']
        date = item.get('pubDate', item.get('postdate', ''))
        date_html = f'<div style="font-size: 12px; color: #64748b; margin-bottom: 14px;">🕒 {date}</div>' if date else ''
        
        tags_html = ""
        if source_type == "news":
            tags_html += "<span class='tag-badge tag-news'>📡 대표 언론보도</span>"
        elif source_type == "blog":
            tags_html += "<span class='tag-badge tag-blog'>📌 네이버 블로그</span>"
        else:
            cafe_name = item.get('cafename', '지역 커뮤니티')
            tags_html += f"<span class='tag-badge tag-cafe'>👥 네이버 카페 ({cafe_name})</span>"
            
        if dup_cnt > 1:
            tags_html += f"<span class='tag-badge tag-dedup'>📑 유사 중복 보도자료 {dup_cnt}건 통합 묶음</span>"

        html_content = f"""<div class="report-card">
{tags_html}
<h4 style="margin-top: 0; margin-bottom: 8px; font-size: 18px; line-height: 1.4;">
    <a href="{link}" target="_blank" style="text-decoration: none; color: #1e3a8a; font-weight: 700;">{title}</a>
</h4>
{date_html}
<p style="font-size: 14.8px; color: #334155; line-height: 1.65; margin: 0;">{desc}</p>
</div>"""

        st.markdown(html_content, unsafe_allow_html=True)
        
        if link in st.session_state.llm_results:
            analysis = st.session_state.llm_results[link]
            if analysis.get("is_negative"):
                st.markdown(f'<div class="analysis-card-risk"><b>⚠️ [시민 민원 / 여론 리스크 감지]</b>\n{analysis.get("point")}\n\n{analysis.get("summary")}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="analysis-card-neutral"><b>🤖 [FACTCHAT 세련된 AI 심층 브리핑]</b>\n{analysis.get("summary")}</div>', unsafe_allow_html=True)
        else:
            if st.button("🔍 AI 심층 브리핑 및 리스크 분석", key=f"btn_{unique_key}", use_container_width=True):
                with st.spinner("AI 수석 분석가가 기사 맥락과 리스크를 정밀 분석 중..."):
                    st.session_state.llm_results[link] = analyze_content_with_factchat(title, desc)
                    st.rerun()
        st.write("")

    with tab_news:
        raw_news_items = fetch_naver_data(selected_kw, display_count, sort_param, "news")
        news_clusters = deduplicate_news_items(raw_news_items)
        news_clusters = news_clusters[:display_count]
        
        if news_clusters:
            for i, cluster in enumerate(news_clusters):
                render_article_card(cluster, unique_key=f"news_{selected_kw}_{i}", source_type="news")
        else:
            st.info("조건에 일치하는 보도자료가 검색되지 않았습니다.")

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
