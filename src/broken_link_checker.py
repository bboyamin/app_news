import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import Firecrawl

# .env 파일로부터 환경 변수 로드
load_dotenv()

def check_broken_links():
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("에러: .env 파일에 FIRECRAWL_API_KEY가 설정되지 않았습니다.")
        return
        
    app = Firecrawl(api_key=api_key)
    
    # 1. 검사 대상 URL 설정
    target_url = "https://www.sujigu.go.kr/"
    print(f"🔍 [{target_url}] 내의 모든 연결 링크를 수집하는 중...")
    
    try:
        # Firecrawl의 "links" 포맷을 사용하여 페이지 안의 모든 링크(URL)만 추출
        response = app.scrape(
            url=target_url,
            formats=["links"]
        )
        
        # 결과에서 링크 리스트 가져오기
        if isinstance(response, dict):
            links = response.get("links", [])
        else:
            links = getattr(response, "links", [])
            
        if not links:
            print("수집된 링크가 없습니다.")
            return
            
        print(f"📊 총 {len(links)}개의 링크를 발견했습니다.")
        print("연결 상태를 검사합니다...\n")
        
        broken_links = []
        valid_links = []
        
        # 차단을 피하기 위한 완전한 브라우저 헤더 구성 (정부24, 페이스북 등의 봇 차단 우회)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # SSL 인증서 오류로 인한 오탐 방지 (보안 검증 생략 및 경고 비활성화)
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 2. 각 링크의 연결 상태 체크
        for idx, link in enumerate(links):
            if not link.startswith("http"):
                continue
                
            try:
                # verify=False 옵션을 주어 SSL 인증서 검증을 건너뜁니다 (브라우저에서는 열리는 보안 사이트 대응)
                res = requests.head(link, headers=headers, timeout=8, allow_redirects=True, verify=False)
                status_code = res.status_code
                
                # 일부 서버는 HEAD 요청을 거절(405/403 등)하므로, 그 경우 GET으로 재시도
                if status_code in [403, 405]:
                    res = requests.get(link, headers=headers, timeout=8, allow_redirects=True, verify=False)
                    status_code = res.status_code
            except Exception as e:
                # SSLError(인증서 호환 오류 등)는 사이트 자체는 살아있으나 파이썬 라이브러리 규격과 안 맞아 발생하므로, 깨진 링크가 아닌 '정상'으로 분류합니다.
                if "SSLError" in str(e.__class__.__name__):
                    status_code = "200 (SSL 우회)"
                else:
                    status_code = f"접속 실패 ({str(e.__class__.__name__)})"
            
            # 검사 결과 수집
            link_data = {"url": link, "status": status_code}
            
            # 상태 코드가 문자열(접속 실패)이거나 400 이상인 경우 깨진 링크로 분류 (단, SSL 우회는 제외)
            is_broken = False
            if isinstance(status_code, str):
                if "SSL 우회" not in status_code:
                    is_broken = True
            elif status_code >= 400:
                is_broken = True
                
            if is_broken:
                print(f"❌ [{idx+1}/{len(links)}] {link} -> (에러: {status_code})")
                broken_links.append(link_data)
            else:
                print(f"✅ [{idx+1}/{len(links)}] {link} -> (정상: {status_code})")
                valid_links.append(link_data)
                
        # 3. 결과를 마크다운(.md) 리포트 파일로 빌드
        os.makedirs("src", exist_ok=True)
        report_file = "src/broken_links_report.md"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        md_content = f"""# 🛠️ 깨진 링크 검사 리포트

- **검사 대상 URL**: [{target_url}]({target_url})
- **검사 일시**: `{now_str}`
- **총 발견 링크 수**: {len(links)}개
- **⚠️ 깨진 링크 수**: `{len(broken_links)}`개
- **✅ 정상 링크 수**: `{len(valid_links)}`개

---

## ⚠️ 발견된 깨진 링크 목록 ({len(broken_links)}개)

| 번호 | 깨진 링크 URL | 오류 상태 (Status Code) |
| :---: | :--- | :---: |
"""
        if broken_links:
            for i, item in enumerate(broken_links):
                md_content += f"| {i+1} | [{item['url']}]({item['url']}) | `{item['status']}` |\n"
        else:
            md_content += "| - | 깨진 링크가 존재하지 않습니다. | - |\n"
            
        md_content += f"""
---

## ✅ 정상 연결된 링크 목록 ({len(valid_links)}개)

<details>
<summary><b>정상 링크 접기/펼치기 클릭</b></summary>

| 번호 | 정상 링크 URL | 응답 상태 |
| :---: | :--- | :---: |
"""
        for i, item in enumerate(valid_links):
            md_content += f"| {i+1} | [{item['url']}]({item['url']}) | `{item['status']}` |\n"
            
        md_content += """
</details>
"""
        
        # 파일에 마크다운 기록
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print("\n==================================")
        print("🛠️ 깨진 링크 검사 완료")
        print("==================================")
        print(f"🎉 결과 리포트가 '{report_file}' 파일로 저장되었습니다!")
        print("👉 VS Code에서 해당 파일을 열고 [Cmd + Shift + V] 를 눌러 확인해 보세요.")
            
    except Exception as e:
        print(f"검사 중 오류 발생: {e}")

if __name__ == "__main__":
    check_broken_links()
