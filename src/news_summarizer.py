import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# .env 파일로부터 환경 변수 로드
load_dotenv()

def get_today_news_list():
    target_url = "https://pdf.etnews.com/pdf_today.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"📰 [{target_url}] 에서 오늘의 지면 기사 목록을 가져오는 중...")
    
    try:
        res = requests.get(target_url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"페이지 로드 실패: {res.status_code}")
            return []
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 기사 목록이 포함된 dl 태그와 링크들 찾기
        news_items = []
        pdf_list = soup.find("ul", class_="pdf_list")
        if not pdf_list:
            print("기사 목록 레이아웃을 찾을 수 없습니다.")
            return []
            
        links = pdf_list.find_all("a", target="_blank")
        
        for link in links:
            title = link.text.strip()
            href = link.get("href", "")
            
            # 절대 경로로 변환
            if href.startswith("//"):
                href = "https:" + href
                
            if href and title:
                news_items.append({"title": title, "url": href})
                
        return news_items
        
    except Exception as e:
        print(f"기사 목록 수집 중 에러 발생: {e}")
        return []

def get_article_content(url):
    """
    개별 기사 URL로 접속하여 본문 텍스트만 추출합니다.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code != 200:
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 전자신문 기사 본문 영역 클래스명 (일반적으로 article_txt, article_body 등)
        # 여러 가능성 있는 본문 클래스 검사
        content_div = soup.find("article") or soup.find("div", class_="article_txt") or soup.find("div", class_="article_body")
        
        if content_div:
            # 본문 내 불필요한 스크립트, 광고 태그 제거
            for s in content_div(["script", "style", "iframe", "ins"]):
                s.extract()
            return content_div.text.strip()
        else:
            # 본문 태그를 특정하지 못한 경우 바디 텍스트 반환
            return soup.text[:2000].strip()
            
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

def factchat_summarize(title, content):
    """
    다른 챗봇 프로젝트에 사용한 FactChat API를 이용하여 기사 본문을 3줄 요약합니다.
    """
    api_key = os.getenv("FACTCHAT_API_KEY")
    base_url = clean_base_url(os.getenv("FACTCHAT_BASE_URL") or "https://factchat-cloud.mindlogic.ai/v1/gateway")
    
    if not api_key:
        print("   - [경고] FACTCHAT_API_KEY가 없습니다. 임시 요약기를 작동합니다.")
        return mock_llm_summarize(title, content)
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # AI에게 전달할 프롬프트 구성
    prompt = f"""아래 뉴스 기사를 읽고 핵심 요약 리스트 3줄(1, 2, 3 번호 형태)을 한국어로 작성해 주세요. 
기사 내용과 관련 없는 사족이나 안내문구는 생략하고 오직 요약 리스트만 응답해 주세요.

[기사 제목]: {title}
[기사 본문]:
{content[:2000]}
"""

    payload = {
        "model": "gpt-5.5",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            verify=False,
            timeout=25
        )
        response.raise_for_status()
        response_json = response.json()
        
        ai_response = response_json['choices'][0]['message']['content'].strip()
        
        # 각 줄 단위로 리스트화하여 반환
        lines = [line.strip() for line in ai_response.split("\n") if line.strip()]
        return lines
        
    except Exception as e:
        print(f"   - [경고] FactChat API 호출 중 오류 발생 ({e}). 임시 요약으로 대체합니다.")
        return mock_llm_summarize(title, content)

def mock_llm_summarize(title, content):
    """
    [임시 요약기] 실제 LLM API가 연동되지 않았을 때 작동하는 요약기 데모.
    """
    lines = [line.strip() for line in content.split("\n") if len(line.strip()) > 30]
    summary_lines = lines[:3] if len(lines) >= 3 else lines
    
    # 3줄 가상 요약문 리턴
    if not summary_lines:
        return ["본문을 불러올 수 없습니다."]
        
    return [f"요약 1: {summary_lines[0][:80]}...", 
            f"요약 2: {summary_lines[1][:80]}..." if len(summary_lines) > 1 else "",
            f"요약 3: {summary_lines[2][:80]}..." if len(summary_lines) > 2 else ""]

def make_news_summary_report():
    # 1. 오늘자 기사 목록 가져오기
    all_news = get_today_news_list()
    if not all_news:
        print("수집된 기사가 없습니다.")
        return
        
    # 무료 크레딧 및 속도를 위해 상위 5개 기사만 테스트 요약
    test_limit = 5
    target_news = all_news[:test_limit]
    print(f"\n📊 총 {len(all_news)}개 기사 중 상위 {test_limit}개 기사 요약을 진행합니다.")
    
    report_content = f"# 📰 오늘의 전자신문 핵심 요약 리포트\n\n- **생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
    
    for idx, item in enumerate(target_news):
        print(f"[{idx+1}/{test_limit}] 기사 수집 및 요약 중: {item['title']}")
        
        content = get_article_content(item["url"])
        if not content:
            print("   - 본문 수집 실패")
            continue
            
        # 2. FactChat AI를 통한 요약 수행
        summaries = factchat_summarize(item["title"], content)
        
        # 3. 리포트 마크다운 빌드
        report_content += f"## {idx+1}. [{item['title']}]({item['url']})\n\n"
        for line in summaries:
            if line:
                report_content += f"- {line}\n"
        report_content += "\n---\n\n"
        
    # 4. 파일 저장
    os.makedirs("src", exist_ok=True)
    report_path = "src/today_news_summary.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"\n🎉 [성공] 요약 리포트가 '{report_path}' 파일로 생성되었습니다!")
    print("👉 VS Code에서 해당 파일을 열고 [Cmd + Shift + V] 를 눌러 요약본을 읽어보세요.")

if __name__ == "__main__":
    from datetime import datetime
    make_news_summary_report()
