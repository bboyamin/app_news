import os
import requests
import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import streamlit as st
from datetime import datetime as dt, timezone, timedelta

# 한국 표준시 (KST = UTC + 9시간) 전역 설정
KST = timezone(timedelta(hours=9))

def get_kst_now():
    return dt.now(KST)

def get_kst_today():
    return get_kst_now().date()

# .env 파일로부터 환경 변수 로드
load_dotenv()

# Streamlit 페이지 테마 및 프리미엄 라이트 레이아웃 설정
st.set_page_config(
    page_title="전자신문 지면 브리핑",
    page_icon="📰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------
# 0. 프리미엄 라이트 Pretendard CSS 디자인 (자연스러운 개조)
# -------------------------------------------------------------
st.markdown("""
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css" />
<style>
    html, body, [class*="css"], .stApp {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
        background-color: #ffffff !important;
        color: #1e293b !important;
    }
    
    .main-title {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        letter-spacing: -0.5px !important;
        margin-top: 20px;
        margin-bottom: 8px;
        text-align: left;
    }
    
    .main-subtitle {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 24px;
        line-height: 1.5;
        text-align: left;
    }
    
    .section-header {
        font-size: 15px;
        font-weight: 800;
        color: #64748b;
        margin-top: 36px;
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #f1f5f9;
        padding-bottom: 6px;
    }
    
    .article-meta {
        font-size: 11px;
        font-weight: 700;
        color: #475569;
        background-color: #f1f5f9;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 12px;
    }
    
    /* 완벽한 줄글 가독성을 보장하는 고품격 요약 박스 */
    .summary-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px 24px;
        font-size: 15px;
        line-height: 1.8;
        color: #1e293b;
        margin-top: 8px;
        margin-bottom: 14px;
        white-space: pre-wrap !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.02);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid #f1f5f9;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: transparent;
        color: #94a3b8;
        font-weight: 700;
        font-size: 14px;
        padding: 8px 4px;
        transition: all 0.15s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #0f172a;
    }
    .stTabs [aria-selected="true"] {
        color: #0f172a !important;
        border-bottom: 2px solid #0f172a !important;
    }
    
    div.stButton > button {
        background: transparent !important;
        color: #334155 !important;
        border: none !important;
        border-bottom: 1px solid #f1f5f9 !important;
        border-radius: 0px !important;
        padding: 14px 4px !important;
        text-align: left !important;
        width: 100% !important;
        box-shadow: none !important;
        transition: all 0.15s ease !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        margin-bottom: 0px;
    }
    div.stButton > button:hover {
        color: #000000 !important;
        background: #f8fafc !important;
        padding-left: 8px !important;
    }
    
    .stLinkButton > a {
        background: #ffffff !important;
        color: #475569 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        padding: 8px 16px !important;
        transition: all 0.15s !important;
    }
    .stLinkButton > a:hover {
        color: #0f172a !important;
        border-color: #0f172a !important;
        background: #f8fafc !important;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #f8fafc !important;
        border-right: 1px solid #e2e8f0;
    }
    
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# FactChat API 설정
FACTCHAT_API_KEY = os.getenv("FACTCHAT_API_KEY")
FACTCHAT_BASE_URL = os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway"

# -------------------------------------------------------------
# 1. 고도화된 크롤링 및 자연스러운 고품격 브리핑 요약
# -------------------------------------------------------------

def fetch_etnews_html(ymd_str):
    urls = [
        f"https://pdf.etnews.com/pdf_today.html?ymd={ymd_str}",
        f"https://pdf.etnews.com/index.html?ymd={ymd_str}"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://pdf.etnews.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache"
    }
    
    session = requests.Session()
    for url in urls:
        try:
            res = session.get(url, headers=headers, timeout=8)
            if res.status_code == 200 and len(res.text) > 2000:
                return res.text
        except Exception:
            continue
            
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def get_news_list_by_date(ymd_str):
    html_text = fetch_etnews_html(ymd_str)
    if not html_text:
        return None
        
    try:
        soup = BeautifulSoup(html_text, "html.parser")
        
        boxes = soup.find_all("div", class_="box") or soup.find_all("dl", class_="box") or soup.find_all("div", class_="pdf_box")
        if not boxes:
            return None
            
        categorized_news = {}
        for box in boxes:
            section_title_el = box.find("dt") or box.find("strong") or box.find("h3")
            if not section_title_el:
                continue
            section_title = section_title_el.text.strip()
            
            links = box.find_all("a", target="_blank") or box.find_all("a")
            articles = []
            for link in links:
                title = link.text.strip()
                href = link.get("href", "")
                if not href or href == "#":
                    continue
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = "https://pdf.etnews.com" + href
                
                if title and href and ("javascript" not in href):
                    articles.append({"title": title, "url": href})
                    
            if articles:
                categorized_news[section_title] = articles
                
        return categorized_news if categorized_news else None
    except Exception:
        return None


def get_article_body(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://pdf.etnews.com/"
    }
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code != 200:
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        content_div = soup.find("article") or soup.find("div", class_="article_txt") or soup.find("div", class_="article_body") or soup.find("div", id="articleBody")
        
        if content_div:
            for s in content_div(["script", "style", "iframe", "ins", "button"]):
                s.extract()
            return content_div.text.strip()
        else:
            return soup.text[:3000].strip()
    except Exception:
        return None


def ai_summarize(title, content):
    if not FACTCHAT_API_KEY:
        return "⚠️ .env 파일에 FACTCHAT_API_KEY가 없습니다."
        
    headers = {
        "Authorization": f"Bearer {FACTCHAT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 🎓 자연스러운 연결 및 고품격 내러티브 브리핑 프롬프트
    prompt = f"""너는 대한민국 최고 수준의 수석 IT/산업 전문 언론 브리퍼이다.
딱딱한 번호 매기기(1, 2, 3)를 완전히 배제하고, 독자가 기사의 핵심 배경과 중요 수치, 향후 영향을 한 눈에 자연스럽고 매끄럽게 이해할 수 있는 '최적의 자연어 프리미엄 뉴스 브리핑'을 작성하라.

[작성 가이드라인 - 최고 수준 가독성 보장]:
1. **📌 [핵심 한 줄 요약]**: 맨 첫 줄에는 기사 전체의 핵심 결론을 명확하고 깔끔한 한 문장으로 제시하라.
2. **📖 [자연스러운 맥락 브리핑]**: 두 번째 단락부터는 딱딱한 번호 목록이 아닌, 자연스럽게 이어지는 글감 문단(2~3개 자연스러운 단락)으로 작성하라.
   - 첫 번째 단락: **사건 발생 배경 및 주요 사실/핵심 인물/기업**
   - 두 번째 단락: **구체적인 수치 데이터, 주요 투자/기술 규격 세부 내용**
   - 세 번째 단락: **산업계에 미칠 영향 및 향후 주시할 관전 포인트**
3. 딱딱하게 끊기지 않고 문장과 문장이 술술 읽히도록 완숙하고 격조 높은 한국어 문장 구조로 작성하라.
4. 인사말이나 사족(예: '요약해 드리겠습니다' 등)은 완전히 배제하라.

[기사 제목]: {title}
[기사 본문]:
{content[:3500]}
"""

    payload = {
        "model": "gpt-5.4",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(
            f"{FACTCHAT_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        response_json = response.json()
        return response_json['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"❌ 요약 실패 ({e})"

# -------------------------------------------------------------
# 2. UI 구성
# -------------------------------------------------------------

if "summaries" not in st.session_state:
    st.session_state.summaries = {}
if "selected_article" not in st.session_state:
    st.session_state.selected_article = None

today_kst = get_kst_today()

# 사이드바 레이아웃
st.sidebar.markdown("### 📅 지면 날짜 선택")
selected_date = st.sidebar.date_input(
    "조회 날짜",
    value=today_kst,
    max_value=today_kst,
    label_visibility="collapsed"
)
ymd_str = selected_date.strftime("%Y%m%d")

st.sidebar.write("")
if st.sidebar.button("🔄 지면 뉴스 실시간 다시 불러오기", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# 메인 타이틀 영역
st.markdown('<div class="main-title">📰 전자신문 지면 브리핑</div>', unsafe_allow_html=True)
st.markdown(f'<div class="main-subtitle">{selected_date.strftime("%Y년 %m월 %d일")} 자 전자신문 지면 기사입니다. 기사명을 누르면 자연스럽고 깊이 있는 AI 브리핑이 바로 확장됩니다.</div>', unsafe_allow_html=True)

# 실시간 기사 수집 실행
with st.spinner("지면 뉴스 목록을 수집 중..."):
    categorized_data = get_news_list_by_date(ymd_str)

is_weekend = selected_date.weekday() in [5, 6]

if not categorized_data:
    if is_weekend:
        st.warning(f"📅 {selected_date.strftime('%Y-%m-%d')} 은 주말(휴간일)이어서 지면 신문이 발행되지 않는 날입니다. 평일 날짜를 선택하시면 해당 일자의 지면 뉴스를 바로 보실 수 있습니다.")
    else:
        st.warning(f"📅 {selected_date.strftime('%Y-%m-%d')} 지면 정보를 불러오는 중입니다. 신문사 발행 직후(아침 06~07시)이거나 네트워크 수집 지연이 발생할 수 있습니다.")
        if st.button("🔄 지면 캐시 초기화 후 즉시 다시 조회하기"):
            st.cache_data.clear()
            st.rerun()
else:
    tab_list, tab_summary = st.tabs(["📝 오늘자 지면 목록", "💡 모아둔 요약 리포트"])
    
    with tab_list:
        sections = list(categorized_data.keys())
        selected_section = st.selectbox(
            "📖 지면 필터링",
            ["전체 지면 보기"] + sections,
            label_visibility="collapsed"
        )
        
        st.write("")
        
        for section, articles in categorized_data.items():
            if selected_section != "전체 지면 보기" and selected_section != section:
                continue
                
            st.markdown(f'<div class="section-header">{section}</div>', unsafe_allow_html=True)
            
            for idx, art in enumerate(articles):
                btn_key = f"feed_{ymd_str}_{section.replace(' ', '_')}_{idx}"
                is_active = (st.session_state.selected_article == btn_key)
                
                if is_active:
                    st.markdown(f"""
                    <style>
                        div.stButton > button[key*="{btn_key}"] {{
                            font-weight: 700 !important;
                            color: #0f172a !important;
                            background-color: #f8fafc !important;
                            border-left: 3px solid #0f172a !important;
                            padding-left: 8px !important;
                        }}
                    </style>
                    """, unsafe_allow_html=True)
                
                if st.button(f"📄  {art['title']}", key=btn_key):
                    if is_active:
                        st.session_state.selected_article = None
                    else:
                        st.session_state.selected_article = btn_key
                    st.rerun()
                
                if st.session_state.selected_article == btn_key:
                    st.markdown('<div style="padding: 12px 8px 16px 12px;">', unsafe_allow_html=True)
                    st.markdown(f'<span class="article-meta">📌 {section}</span>', unsafe_allow_html=True)
                    
                    if art["title"] in st.session_state.summaries:
                        summary_data = st.session_state.summaries[art["title"]]["summary"]
                        st.markdown(f'<div class="summary-box">{summary_data}</div>', unsafe_allow_html=True)
                        
                        col_action1, col_action2 = st.columns([1, 1])
                        with col_action1:
                            st.link_button("🌐 신문 기사 원문 보기", art["url"], use_container_width=True)
                        with col_action2:
                            st.download_button(
                                label="💾 이 요약본 파일 저장",
                                data=summary_data,
                                file_name=f"요약_{art['title'][:10]}.txt",
                                mime="text/plain",
                                key=f"dl_{btn_key}",
                                use_container_width=True
                            )
                    else:
                        with st.spinner("자연스러운 고품격 AI 요약 브리핑 작성 중..."):
                            content = get_article_body(art["url"])
                            if content:
                                result = ai_summarize(art["title"], content)
                                st.session_state.summaries[art["title"]] = {
                                    "url": art["url"],
                                    "section": section,
                                    "summary": result
                                }
                                st.rerun()
                            else:
                                st.error("기사 본문을 불러오지 못했습니다.")
                                
                    st.markdown('</div>', unsafe_allow_html=True)
            
    with tab_summary:
        st.subheader("📝 실시간 AI 뉴스 브리핑 리포트")
        st.markdown("지면 목록에서 읽어본 기사들의 요약본이 실시간 종합 보고서 형태로 취합되는 대시보드입니다.")
        
        if not st.session_state.summaries:
            st.info("지면 목록 탭에서 관심 있는 기사 제목을 클릭해 보세요! 요약 결과가 자동으로 이 리포트에 취합됩니다.")
        else:
            report_md = f"# 📝 {selected_date.strftime('%Y-%m-%d')} AI 뉴스 요약 리포트\n\n"
            
            for title, info in st.session_state.summaries.items():
                st.markdown(f"#### 📌 [{title}]({info['url']})")
                st.markdown(f'<span class="article-meta">지면: {info["section"]}</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="summary-box">{info["summary"]}</div>', unsafe_allow_html=True)
                st.write("")
                report_md += f"## [{title}]({info['url']}) ({info['section']})\n\n{info['summary']}\n\n---\n\n"
                
            st.write("---")
            
            col_action1, col_action2 = st.columns([2, 1])
            with col_action1:
                st.download_button(
                    label="📥 오늘자 요약 리포트 전체 다운로드 (.md)",
                    data=report_md,
                    file_name=f"AI_요약리포트_{ymd_str}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with col_action2:
                if st.button("🗑️ 요약 리포트 내역 비우기", use_container_width=True):
                    st.session_state.summaries = {}
                    st.session_state.selected_article = None
                    st.rerun()
