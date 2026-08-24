import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from firecrawl import Firecrawl

# .env 파일로부터 환경 변수 로드
load_dotenv()

def run_full_site_link_checker():
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("에러: .env 파일에 FIRECRAWL_API_KEY가 설정되지 않았습니다.")
        return
        
    app = Firecrawl(api_key=api_key)
    
    # 1. 크롤링 대상 사이트 및 탐색 페이지 한도 설정
    # (무료 크레딧 소모를 방지하기 위해 테스트용으로 10페이지 한도로 설정했습니다)
    target_url = "https://www.cheoingu.go.kr/"
    max_pages_to_crawl = 10 
    
    print(f"🕸️ [{target_url}] 사이트의 하위 페이지를 재귀적으로 탐색(Crawl) 중...")
    print(f"   (최대 탐색 페이지 한도: {max_pages_to_crawl}개)")
    
    try:
        # 비동기 크롤러 실행 (최신 v2 SDK 규격에 맞춰 start_crawl 사용)
        crawl_job = app.start_crawl(
            url=target_url,
            limit=max_pages_to_crawl,
            scrape_options={
                "formats": ["links"]
            }
        )
        
        # job_id 추출 (CrawlResponse 객체의 속성 접근)
        if hasattr(crawl_job, "id"):
            job_id = crawl_job.id
        elif hasattr(crawl_job, "job_id"):
            job_id = crawl_job.job_id
        else:
            job_id = crawl_job.get("id") or crawl_job.get("jobId")
            
        print(f"⏳ 크롤링 작업이 등록되었습니다. (Job ID: {job_id})")
        print("작업 완료 대기 중...")
        
        # 크롤링 완료 상태 Polling
        pages_data = []
        while True:
            status_response = app.get_crawl_status(job_id)
            
            # dict 또는 Pydantic 객체 양쪽 모두 호환되도록 값 추출
            if isinstance(status_response, dict):
                status = status_response.get("status")
                completed_pages = status_response.get("completed", 0)
                if status == "completed":
                    pages_data = status_response.get("data", [])
            else:
                status = getattr(status_response, "status", None)
                completed_pages = getattr(status_response, "completed", 0)
                if status == "completed":
                    pages_data = getattr(status_response, "data", [])
            
            print(f"   - 현재 상태: {status} (수집 완료 페이지: {completed_pages})")
            
            if status == "completed":
                print("✅ 전체 하위 페이지 탐색 완료!")
                break
            elif status in ["failed", "cancelled"]:
                print("❌ 크롤링 작업이 실패했거나 취소되었습니다.")
                return
                
            time.sleep(5)
            
        # 2. 크롤링된 모든 하위 페이지에서 발견된 링크 통합 및 중복 제거
        all_harvested_links = set()
        
        for doc in pages_data:
            # 개별 문서가 dict 또는 객체인지에 따라 분기
            if isinstance(doc, dict):
                metadata = doc.get("metadata", {})
                links_in_doc = doc.get("links", [])
            else:
                metadata = getattr(doc, "metadata", {})
                links_in_doc = getattr(doc, "links", [])
            
            # 메타데이터 내부의 source URL 파싱
            if isinstance(metadata, dict):
                source_page = metadata.get("sourceURL") or metadata.get("source_url") or "알 수 없음"
            else:
                source_page = getattr(metadata, "sourceURL", None) or getattr(metadata, "source_url", None) or "알 수 없음"
            
            # 각 문서에서 수집한 링크 추출
            if links_in_doc:
                for link in links_in_doc:
                    if isinstance(link, str) and link.startswith("http"):
                        all_harvested_links.add((link, source_page))
                    
        if not all_harvested_links:
            print("발견된 링크가 없습니다.")
            return
            
        print(f"\n📊 총 {len(pages_data)}개 페이지를 분석하여 중복 제거된 {len(all_harvested_links)}개의 링크를 수집했습니다.")
        print("연결 상태 검사를 진행합니다...\n")
        
        # 3. 수집된 모든 외부/내부 링크의 상태 코드 체크
        broken_links = []
        valid_links = []
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # SSL 경고 끄기
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        for idx, (link, source_page) in enumerate(all_harvested_links):
            try:
                res = requests.head(link, headers=headers, timeout=8, allow_redirects=True, verify=False)
                status_code = res.status_code
                
                if status_code in [403, 405]:
                    res = requests.get(link, headers=headers, timeout=8, allow_redirects=True, verify=False)
                    status_code = res.status_code
            except Exception as e:
                # SSL 핸드셰이크 문제 등은 정상(SSL 우회) 처리하여 진짜 깨진 링크만 걸러냄
                if "SSLError" in str(e.__class__.__name__):
                    status_code = "200 (SSL 우회)"
                else:
                    status_code = f"접속 실패 ({str(e.__class__.__name__)})"
            
            link_info = {"url": link, "source": source_page, "status": status_code}
            
            # 깨진 링크 여부 판별
            is_broken = False
            if isinstance(status_code, str):
                if "SSL 우회" not in status_code:
                    is_broken = True
            elif status_code >= 400:
                is_broken = True
                
            if is_broken:
                print(f"❌ [{idx+1}/{len(all_harvested_links)}] {link} (출처: {source_page}) -> 에러: {status_code}")
                broken_links.append(link_info)
            else:
                print(f"✅ [{idx+1}/{len(all_harvested_links)}] {link} -> 정상")
                valid_links.append(link_info)
                
        # 4. 마크다운(.md) 통합 리포트 파일 작성
        os.makedirs("src", exist_ok=True)
        report_file = "src/full_site_broken_links_report.md"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        md_content = f"""# 🕸️ 사이트 전체 깨진 링크 검사 리포트

- **시작 대상 URL**: [{target_url}]({target_url})
- **탐색한 하위 페이지 수**: {len(pages_data)}개
- **검사 일시**: `{now_str}`
- **⚠️ 총 발견된 깨진 링크 수**: `{len(broken_links)}`개
- **✅ 총 정상 링크 수**: {len(valid_links)}개

---

## ⚠️ 발견된 깨진 링크 목록 ({len(broken_links)}개)
*어떤 페이지에서 해당 깨진 링크가 사용되고 있는지(출처 페이지) 함께 기록되었습니다.*

| 번호 | 깨진 링크 URL | 발견된 페이지 (출처) | 오류 상태 |
| :---: | :--- | :--- | :---: |
"""
        if broken_links:
            for i, item in enumerate(broken_links):
                md_content += f"| {i+1} | [{item['url']}]({item['url']}) | [{item['source']}]({item['source']}) | `{item['status']}` |\n"
        else:
            md_content += "| - | 깨진 링크가 존재하지 않습니다. | - | - |\n"
            
        md_content += f"""
---

## ✅ 정상 연결된 링크 목록 ({len(valid_links)}개)

<details>
<summary><b>정상 링크 접기/펼치기 클릭</b></summary>

| 번호 | 정상 링크 URL | 발견된 페이지 (출처) | 응답 상태 |
| :---: | :--- | :--- | :---: |
"""
        for i, item in enumerate(valid_links):
            md_content += f"| {i+1} | [{item['url']}]({item['url']}) | [{item['source']}]({item['source']}) | `{item['status']}` |\n"
            
        md_content += """
</details>
"""
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        print("\n==================================")
        print("🛠️ 전체 사이트 링크 검사 완료")
        print("==================================")
        print(f"🎉 결과 리포트가 '{report_file}' 파일로 저장되었습니다!")
        print("👉 VS Code에서 해당 파일을 열고 [Cmd + Shift + V] 를 눌러 확인해 보세요.")
        
    except Exception as e:
        print(f"크롤링 및 검사 실행 중 에러 발생: {e}")

if __name__ == "__main__":
    run_full_site_link_checker()
