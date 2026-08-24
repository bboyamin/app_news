import os
from dotenv import load_dotenv
from firecrawl import Firecrawl

# .env 파일로부터 환경 변수 로드
load_dotenv()

def run_test():
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("에러: .env 파일에 FIRECRAWL_API_KEY가 설정되지 않았습니다.")
        return
        
    print(f"Firecrawl API 키 로드 성공 (앞부분 일부: {api_key[:10]}...)")
    
    # 1. Firecrawl 클라이언트 초기화
    app = Firecrawl(api_key=api_key)
    
    # 2. 테스트 크롤링 대상 URL 설정
    target_url = "https://www.cheoingu.go.kr"
    print(f"\n{target_url} 페이지를 스크래핑하는 중...")
    
    try:
        # 3. 스크래핑 실행 (마크다운 포맷 추출)
        response = app.scrape(
            url=target_url,
            formats=["markdown"],
            only_main_content=True
        )
        
        # 4. 결과 출력
        print("\n=== 스크래핑 성공! ===")
        
        # dict 또는 객체 모두 지원하도록 안전하게 추출
        if isinstance(response, dict):
            metadata = response.get("metadata", {})
            markdown_content = response.get("markdown", "")
        else:
            metadata = getattr(response, "metadata", {})
            markdown_content = getattr(response, "markdown", "")

        print("메타데이터:")
        print(metadata)
        
        # 5. 결과를 result.md 파일로 저장
        output_file = "src/result.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        print(f"\n🎉 [성공] 마크다운 결과가 '{output_file}' 파일로 저장되었습니다!")
        print("👉 VS Code에서 이 파일을 열고 마우스 우클릭 -> '미리 보기 열기(Open Preview)'를 누르시거나")
        print("👉 단축키 [Cmd + Shift + V] (Mac) / [Ctrl + Shift + V] (Windows)를 누르면 예쁘게 렌더링된 웹 화면을 바로 볼 수 있습니다.")
        
    except Exception as e:
        print(f"\n에러 발생: {e}")

if __name__ == "__main__":
    run_test()
