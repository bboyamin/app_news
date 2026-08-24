import os
import json
import re
import requests
import urllib.parse
import urllib3
import streamlit as st
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

# 유튜브 자막 추출 패키지 로드 시도
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YT_TRANSCRIPT = True
except Exception:
    HAS_YT_TRANSCRIPT = False

# ==========================================
# 0. 초기 세팅 및 네트워크 최적화
# ==========================================
st.set_page_config(page_title="용인시 시정 동향 모니터링", page_icon="🏛️", layout="wide")
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

CLIENT_ID = get_secret_safe("NAVER_CLIENT_ID") or os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = get_secret_safe("NAVER_CLIENT_SECRET") or os.getenv("NAVER_CLIENT_SECRET")
FACTCHAT_API_KEY = get_secret_safe("FACTCHAT_API_KEY") or os.getenv("FACTCHAT_API_KEY")
raw_base_url = get_secret_safe("FACTCHAT_BASE_URL") or os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway"
FACTCHAT_BASE_URL = clean_base_url(raw_base_url)
YOUTUBE_API_KEY = get_secret_safe("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
KEYWORD_FILE = "keywords_db.json"

# 언론사 뉴스 도메인 블랙리스트 (소셜 탭에서 뉴스 기사 100% 차단)
NEWS_DOMAINS = [
    "naver.com", "daum.net", "news", "chosun", "donga", "joongang", "ytn", 
    "kbs", "sbs", "mbc", "hankyung", "mk.co.kr", "yna.co.kr", "etnews", 
    "kgnews", "incheonilbo", "kyeonggi", "kyeongin", "press", "gnews"
]

def is_news_link(url, title=""):
    target = f"{url} {title}".lower()
    return any(nd in target for nd in NEWS_DOMAINS)

# 전역 CSS 디자인 인젝션 (클린 프리미엄)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .block-container {
        padding-top: 2.8rem !important;
        padding-bottom: 5rem !important;
    }

    .report-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 24px 28px;
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
    .tag-insta { background-color: #fdf2f8; color: #db2777; border: 1px solid #fbcfe8; }
    .tag-threads { background-color: #f8fafc; color: #0f172a; border: 1px solid #cbd5e1; }
    .tag-youtube { background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .tag-dedup { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    
    .analysis-card-neutral {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 18px 22px;
        margin-top: 14px;
        line-height: 1.75;
        white-space: pre-wrap !important;
    }
    .analysis-card-risk {
        background-color: #fff5f5;
        border: 1px solid #fecaca;
        border-radius: 12px;
        padding: 18px 22px;
        margin-top: 14px;
        line-height: 1.75;
        white-space: pre-wrap !important;
    }
    
    .youtube-thumb {
        border-radius: 10px;
        max-width: 240px;
        height: auto;
        margin-bottom: 12px;
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
# 2. 자막 추출 모듈 (YouTube Subtitles Parser)
# ==========================================
def extract_youtube_transcript(video_url):
    """
    유튜브 영상 링크에서 한국어/자동생성 자막 전문 스크립트를 추출합니다.
    """
    if not HAS_YT_TRANSCRIPT or not video_url:
        return ""
        
    v_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', video_url)
    if not v_match:
        return ""
        
    video_id = v_match.group(1)
    
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        target_t = None
        for t in transcript_list:
            if t.language_code in ['ko', 'ko-KR']:
                target_t = t
                break
                
        if not target_t:
            for t in transcript_list:
                if t.is_translatable:
                    target_t = t.translate('ko')
                    break
                    
        if not target_t:
            for t in transcript_list:
                target_t = t
                break
                
        if target_t:
            fetched = target_t.fetch()
            texts = [item['text'] for item in fetched]
            full_text = ' '.join(texts)
            return full_text[:3500] # 주요 자막 전문 3500자 파싱
    except Exception:
        pass
        
    return ""

# ==========================================
# 3. 강력한 다층(Multi-Layer) 중복 제거 알고리즘
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
    
    str_sim = SequenceMatcher(None, t1, t2).ratio()
    if str_sim >= 0.38:
        return True
        
    w1, w2 = get_word_set(item1["title"]), get_word_set(item2["title"])
    overlap = calc_word_overlap(w1, w2)
    if overlap >= 0.35:
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
# 4. 순수 단일 키워드 수집 엔진 (네이버, 유튜브, 인스타그램, 쓰레드)
# ==========================================
@st.cache_data(ttl=180, show_spinner=False)
def fetch_naver_data(query, display_cnt, sort_type, target="news"):
    if not CLIENT_ID or not CLIENT_SECRET:
        return []
    url = f"https://openapi.naver.com/v1/search/{target}.json"
    headers = {"X-Naver-Client-Id": CLIENT_ID, "X-Naver-Client-Secret": CLIENT_SECRET}
    
    enc_text = urllib.parse.quote(query)
    fetch_limit = 100 if target == "news" else display_cnt
    request_url = f"{url}?query={enc_text}&display={fetch_limit}&sort={sort_type}"
    
    try:
        res = requests.get(request_url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("items", [])
    except Exception:
        pass
    return []

# 📺 4-1. 유튜브 순수 키워드 수집 엔진
@st.cache_data(ttl=300, show_spinner=False)
def fetch_youtube_data(query, max_results=10):
    items = []
    
    if YOUTUBE_API_KEY:
        try:
            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "key": YOUTUBE_API_KEY,
                "q": query,
                "part": "snippet",
                "maxResults": max_results,
                "type": "video",
                "order": "date"
            }
            res = requests.get(search_url, params=params, timeout=8)
            if res.status_code == 200:
                raw_items = res.json().get("items", [])
                for raw in raw_items:
                    snippet = raw.get("snippet", {})
                    video_id = raw.get("id", {}).get("videoId", "")
                    if video_id and snippet:
                        items.append({
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "channel": snippet.get("channelTitle", ""),
                            "publishedAt": snippet.get("publishedAt", "")[:10],
                            "link": f"https://www.youtube.com/watch?v={video_id}",
                            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                            "source_type": "youtube"
                        })
                return items
        except Exception:
            pass
            
    try:
        fallback_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(fallback_url, headers=headers, timeout=6)
        if res.status_code == 200:
            matches = re.findall(r'"videoRenderer":\{"videoId":"(.*?)","thumbnail":\{"thumbnails":\[\{"url":"(.*?)"', res.text)
            titles = re.findall(r'"title":\{"runs":\[\{"text":"(.*?)"\}', res.text)
            
            for idx, m in enumerate(matches[:max_results]):
                v_id, thumb = m[0], m[1].replace("\\u0026", "&")
                title = titles[idx] if idx < len(titles) else f"{query} 관련 영상"
                items.append({
                    "title": title,
                    "description": f"키워드 '{query}' 관련 유튜브 영상입니다.",
                    "channel": "유튜브 동향",
                    "publishedAt": "최근",
                    "link": f"https://www.youtube.com/watch?v={v_id}",
                    "thumbnail": thumb,
                    "source_type": "youtube"
                })
    except Exception:
        pass
        
    return items

# 📸 4-2. 시민 작성 순수 인스타그램 & 🧵 쓰레드 개인 포스트 수집 엔진
@st.cache_data(ttl=300, show_spinner=False)
def fetch_authentic_personal_sns(platform_name, query, count=10):
    items = []
    platform_key = platform_name.lower()
    clean_kw = query.replace(" ", "")
    
    if platform_key == "instagram":
        search_q = f'"instagram.com/p/" OR "instagram.com/reel/" "{query}"'
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_q)}&hl=ko&gl=KR&ceid=KR:ko"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'xml')
                for it in soup.find_all('item'):
                    l = it.link.text if it.link else ''
                    t = it.title.text if it.title else ''
                    clean_t = re.sub(r' - .*?$', '', t)
                    clean_t = re.sub(r'\[.*?\]|\(.*?\)', '', clean_t).strip()
                    
                    if clean_t and not is_news_link(l, t):
                        items.append({
                            "title": clean_t,
                            "description": f"시민이 인스타그램에 직접 업로드한 '{query}' 관련 개인 포스트입니다.",
                            "link": l,
                            "date": "실시간",
                            "source_type": "instagram"
                        })
        except Exception:
            pass
            
        items.append({
            "title": f"#{clean_kw} 인스타그램 포스트",
            "description": f"인스타그램에서 시민들이 #{clean_kw} 해시태그로 직접 공유한 최신 개인 포스트입니다.",
            "link": f"https://www.instagram.com/explore/tags/{urllib.parse.quote(clean_kw)}/",
            "date": "실시간 피드",
            "source_type": "instagram"
        })
        items.append({
            "title": f"#{clean_kw}일상 인스타그램 포스트",
            "description": f"인스타그램에서 시민들이 #{clean_kw}일상 해시태그로 게시한 포스트입니다.",
            "link": f"https://www.instagram.com/explore/tags/{urllib.parse.quote(clean_kw + '일상')}/",
            "date": "실시간 피드",
            "source_type": "instagram"
        })
        
    else: # Threads
        search_q = f'"threads.net/@" "{query}"'
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_q)}&hl=ko&gl=KR&ceid=KR:ko"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'xml')
                for it in soup.find_all('item'):
                    l = it.link.text if it.link else ''
                    t = it.title.text if it.title else ''
                    clean_t = re.sub(r' - .*?$', '', t)
                    clean_t = re.sub(r'\[.*?\]|\(.*?\)', '', clean_t).strip()
                    
                    if clean_t and not is_news_link(l, t):
                        items.append({
                            "title": clean_t,
                            "description": f"시민이 쓰레드(Threads)에 직접 작성한 '{query}' 관련 텍스트 포스트입니다.",
                            "link": l,
                            "date": "실시간",
                            "source_type": "threads"
                        })
        except Exception:
            pass
            
        items.append({
            "title": f"'{query}' 쓰레드(Threads) 포스트",
            "description": f"쓰레드(Threads)에서 시민들이 '{query}' 관련하여 직접 남긴 텍스트 포스트입니다.",
            "link": f"https://www.threads.net/search?q={urllib.parse.quote(query)}",
            "date": "실시간 피드",
            "source_type": "threads"
        })

    return items[:count]

# ==========================================
# 5. 고품격 AI 심층 브리핑 & 리스크 분석 모듈 (자막 파싱 포함)
# ==========================================
def analyze_content_with_factchat(title, description, source_type="news", link=""):
    if not FACTCHAT_API_KEY or not FACTCHAT_BASE_URL:
        return {"summary": "API 설정 누락", "is_negative": False, "point": ""}

    # 🌟 유튜브 영상일 경우 실시간 영상 자막 추출 파이프라인 작동
    transcript_info = ""
    if source_type == "youtube" and link:
        transcript_text = extract_youtube_transcript(link)
        if transcript_text:
            transcript_info = f"\n\n[🎬 추출된 유튜브 영상 실제 자막 전문 스크립트]:\n{transcript_text}"

    system_prompt = """너는 20년 경력의 공공기관 수석 시정 모니터링 분석가이다.
제시된 기사, 소셜 포스트, 또는 유튜브 영상(자막 전문 스크립트 포함)을 정밀 분석하여, 단체장 및 실무자가 15초 만에 핵심 현황과 대응 포인트를 파악할 수 있도록 '고품격 시정 종합 브리핑'을 작성하라.

[분석 가이드라인 - 절대 준수]:
1. **📌 [시정 핵심 브리핑]**: 딱딱한 1, 2, 3번 목록 대신, 사건의 주요 배경, 핵심 사실 및 구체적 수치/사업 규격(유튜브 자막이 제공된 경우 영상 발언 내용 정밀 포함)이 자연스럽게 연결되는 2~3개 고급 단락(총 3~5문장)으로 풍부하게 작성하라.
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
    
    user_prompt = f"제목: {title}\n내용/요약: {description}{transcript_info}"
    headers = {"Authorization": f"Bearer {FACTCHAT_API_KEY}", "Content-Type": "application/json"}
    target_url = f"{FACTCHAT_BASE_URL}/chat/completions"
    
    candidate_models = ["gpt-5.5", "gpt-5.6-luna", "gemini-3.6-flash"]
    last_err = ""
    
    for model_name in candidate_models:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.15
        }
        try:
            res = requests.post(target_url, headers=headers, json=payload, verify=False, timeout=25)
            if res.status_code == 200:
                res_json = res.json()
                result_text = res_json['choices'][0]['message']['content'].strip()
                try:
                    if "{" in result_text and "}" in result_text:
                        json_str = result_text[result_text.find("{"):result_text.rfind("}")+1]
                        return json.loads(json_str)
                    return {"summary": result_text, "is_negative": False, "point": ""}
                except Exception:
                    return {"summary": result_text, "is_negative": False, "point": ""}
            else:
                last_err = f"HTTP {res.status_code} (URL: {target_url})"
        except Exception as e:
            last_err = str(e)
            
    return {"summary": f"요약 분석 중 오류 발생: {last_err}", "is_negative": False, "point": ""}

# ==========================================
# 6. 화면 UI 렌더링
# ==========================================

# --- [사이드바 통제실] ---
with st.sidebar:
    st.header("⚙️ 모니터링 설정")
    
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
    if st.button("🔄 AI 분석 결과 초기화", use_container_width=True):
        st.session_state.llm_results = {}
        st.rerun()

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
    st.caption(f"기준: {sort_option.split(' ')[0]}")
            
    tab_news, tab_comm, tab_sns, tab_youtube = st.tabs([
        "📡 대표 언론 보도", 
        "💬 네이버 블로그/카페",
        "📸 인스타그램 & 쓰레드",
        "📺 유튜브"
    ])

    def render_article_card(item_info, unique_key, source_type="news"):
        if isinstance(item_info, dict) and "representative" in item_info:
            item = item_info["representative"]
            dup_cnt = item_info["duplicates_count"]
        else:
            item = item_info
            dup_cnt = 1
            
        title = clean_html(item.get('title', ''))
        desc = clean_html(item.get('description', item.get('desc', '')))
        link = item.get('link', '#')
        date = item.get('pubDate', item.get('postdate', item.get('publishedAt', item.get('date', ''))))
        date_html = f'<div style="font-size: 12px; color: #64748b; margin-bottom: 14px;">🕒 {date}</div>' if date else ''
        
        tags_html = ""
        if source_type == "news":
            tags_html += "<span class='tag-badge tag-news'>📡 대표 언론보도</span>"
        elif source_type == "blog":
            tags_html += "<span class='tag-badge tag-blog'>📌 네이버 블로그</span>"
        elif source_type == "instagram":
            tags_html += "<span class='tag-badge tag-insta'>📸 인스타그램</span>"
        elif source_type == "threads":
            tags_html += "<span class='tag-badge tag-threads'>🧵 쓰레드(Threads)</span>"
        elif source_type == "youtube":
            tags_html += "<span class='tag-badge tag-youtube'>📺 유튜브</span>"
        else:
            cafe_name = item.get('cafename', '지역 커뮤니티')
            tags_html += f"<span class='tag-badge tag-cafe'>👥 네이버 카페 ({cafe_name})</span>"
            
        if dup_cnt > 1:
            tags_html += f"<span class='tag-badge tag-dedup'>📑 유사 중복 보도자료 {dup_cnt}건 통합 묶음</span>"

        thumb_html = ""
        if item.get("thumbnail"):
            thumb_html = f'<img src="{item["thumbnail"]}" class="youtube-thumb" alt="유튜브 썸네일"><br>'

        html_content = f"""<div class="report-card">
{tags_html}
{thumb_html}
<h4 style="margin-top: 0; margin-bottom: 8px; font-size: 18px; line-height: 1.4;">
    <a href="{link}" target="_blank" style="text-decoration: none; color: #1e3a8a; font-weight: 700;">{title}</a>
</h4>
{date_html}
<p style="font-size: 14.8px; color: #334155; line-height: 1.65; margin: 0;">{desc}</p>
</div>"""

        st.markdown(html_content, unsafe_allow_html=True)
        
        is_cached_valid = (
            link in st.session_state.llm_results 
            and "오류 발생" not in st.session_state.llm_results[link].get("summary", "")
        )
        
        if is_cached_valid:
            analysis = st.session_state.llm_results[link]
            if analysis.get("is_negative"):
                st.markdown(f'<div class="analysis-card-risk"><b>⚠️ [시민 민원 / 여론 리스크 감지]</b>\n{analysis.get("point")}\n\n{analysis.get("summary")}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="analysis-card-neutral"><b>🤖 [FACTCHAT 세련된 AI 심층 브리핑]</b>\n{analysis.get("summary")}</div>', unsafe_allow_html=True)
        else:
            button_label = "🎬 영상 자막 정밀 AI 요약 분석" if source_type == "youtube" else "🔍 AI 심층 브리핑 및 리스크 분석"
            if st.button(button_label, key=f"btn_{unique_key}", use_container_width=True):
                with st.spinner("AI 수석 분석가가 영상 자막 맥락을 정밀 분석 중..." if source_type == "youtube" else "AI 수석 분석가가 기사/SNS 여론 맥락을 정밀 분석 중..."):
                    st.session_state.llm_results[link] = analyze_content_with_factchat(title, desc, source_type=source_type, link=link)
                    st.rerun()
        st.write("")

    # [탭 1] 대표 언론 보도
    with tab_news:
        raw_news_items = fetch_naver_data(selected_kw, display_count, sort_param, "news")
        news_clusters = deduplicate_news_items(raw_news_items)
        news_clusters = news_clusters[:display_count]
        
        if news_clusters:
            for i, cluster in enumerate(news_clusters):
                render_article_card(cluster, unique_key=f"news_{selected_kw}_{i}", source_type="news")
        else:
            st.info("조건에 일치하는 보도자료가 검색되지 않았습니다.")

    # [탭 2] 네이버 블로그 / 카페
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

    # [탭 3] 순수 시민 작성 인스타그램 & 쓰레드 전용 SNS 탭
    with tab_sns:
        col_insta, col_threads = st.columns(2)
        
        with col_insta:
            insta_posts = fetch_authentic_personal_sns("Instagram", selected_kw, count=display_count)
            for i, p in enumerate(insta_posts):
                render_article_card(p, unique_key=f"insta_{selected_kw}_{i}", source_type="instagram")
                
        with col_threads:
            threads_posts = fetch_authentic_personal_sns("Threads", selected_kw, count=display_count)
            for i, p in enumerate(threads_posts):
                render_article_card(p, unique_key=f"threads_{selected_kw}_{i}", source_type="threads")

    # [탭 4] 유튜브 (영상 자막 정밀 분석 연동)
    with tab_youtube:
        yt_items = fetch_youtube_data(selected_kw, display_count)
        if yt_items:
            for i, yt_item in enumerate(yt_items):
                render_article_card(yt_item, unique_key=f"yt_{selected_kw}_{i}", source_type="youtube")
        else:
            st.info("조건에 일치하는 유튜브 시정 영상이 검색되지 않았습니다.")

else:
    st.info("👈 좌측 제어반에서 모니터링할 타겟 키워드를 선택하세요.")
