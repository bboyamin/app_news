from hwpx import HwpxDocument

def build_report():
    doc = HwpxDocument.new()
    
    # -------------------------------------------------------------
    # 헬퍼 함수 정의
    # -------------------------------------------------------------
    def add_title(text):
        p = doc.add_paragraph()
        p.add_run(text, bold=True, size=18, color="1B4F72")
        doc.add_paragraph()
        
    def add_h1(text):
        p = doc.add_paragraph()
        p.add_run(text, bold=True, size=14, color="2874A6")
        
    def add_h2(text):
        p = doc.add_paragraph()
        p.add_run(text, bold=True, size=11, color="5DADE2")
        
    def add_body(text, bold_parts=None):
        p = doc.add_paragraph()
        if bold_parts:
            current_text = text
            for part in bold_parts:
                if part in current_text:
                    before, after = current_text.split(part, 1)
                    if before:
                        p.add_run(before, size=10)
                    p.add_run(part, bold=True, size=10, color="000000")
                    current_text = after
            if current_text:
                p.add_run(current_text, size=10)
        else:
            p.add_run(text, size=10)
            
    def add_bullet(text, bold_parts=None):
        p = doc.add_paragraph()
        p.add_run("  •  ", bold=True, size=10, color="2874A6")
        if bold_parts:
            current_text = text
            for part in bold_parts:
                if part in current_text:
                    before, after = current_text.split(part, 1)
                    if before:
                        p.add_run(before, size=10)
                    p.add_run(part, bold=True, size=10, color="1F4E79")
                    current_text = after
            if current_text:
                p.add_run(current_text, size=10)
        else:
            p.add_run(text, size=10)
            
    def add_space():
        doc.add_paragraph()

    # -------------------------------------------------------------
    # 문서 본문 작성
    # -------------------------------------------------------------
    add_title("2026년 용인시 상권 및 소상공인 공간 정보 융합 분석 보고서")
    
    add_body("본 보고서는 소상공인시장진흥공단의 2026년 3월 경기도 상가정보를 기반으로, 용인시 관내 총 46,022개 점포의 지리 정보(위도·경도)를 융합하여 DBSCAN 공간 분석을 수행하고 구별 특성을 규명한 종합 치안·상권 분석 보고서입니다.")
    add_space()
    
    add_h1("1. 핵심 요약 (Executive Summary)")
    add_bullet("\"공간 밀도 중심 상권 발견\": 용인시 전역에서 총 74개의 핫스팟 클러스터가 탐지되었으며, 수지구 풍덕천동 일대(수지구청역 사거리 배후)가 1,842개의 초밀집 점포를 형성하여 용인시 1위 핵심 상권으로 입증되었습니다.", ["\"공간 밀도 중심 상권 발견\":", "74개", "수지구 풍덕천동 일대", "1,842개", "1위 핵심 상권"])
    add_bullet("\"업종별 핫스팟의 산업 분화\": 수지구 핫스팟은 '학원 및 식음료', 기흥구 핫스팟은 '지식산업 및 경영 컨설팅', 처인구 핫스팟은 '전통시장 및 의류 패션'으로 기능적 분화가 극명하게 드러났습니다.", ["수지구 핫스팟은 '학원 및 식음료'", "기흥구 핫스팟은 '지식산업 및 경영 컨설팅'", "처인구 핫스팟은 '전통시장 및 의류 패션'"])
    add_bullet("\"구별 정책 시사점\": 수지는 학생 안전, 기흥은 청년 스타트업 오피스 네트워크 지원, 처인은 로컬 푸드 위생 치안 및 구도심 융합 활성화 대책이 요구됩니다.", ["구별 정책 시사점"])
    add_space()
    
    add_h1("2. 용인시 행정구별 점포 분포")
    add_body("용인시 3개 행정구의 상가 총량 및 비중 분석 결과입니다.")
    add_space()
    
    # [표 1] 작성
    table1 = doc.add_table(rows=4, cols=5)
    headers1 = ["순위", "행정구명", "점포수 (개)", "구성비 (%)", "상권 특징"]
    data1 = [
        ["1", "용인시 기흥구", "18,105", "39.34%", "테크노밸리 배후 비즈니스 및 뉴타운 상권"],
        ["2", "용인시 처인구", "15,553", "33.79%", "구도심 상권, 도농복합 외식 및 관광숙박 배후 상권"],
        ["3", "용인시 수지구", "12,364", "26.87%", "학원가 및 배후 아파트 생활 밀착형 상권"]
    ]
    
    for col_idx, header_text in enumerate(headers1):
        table1.set_cell_text(0, col_idx, header_text)
        table1.set_cell_shading(0, col_idx, "D6E4F0")
        
    for row_idx, row_data in enumerate(data1, start=1):
        for col_idx, val in enumerate(row_data):
            table1.set_cell_text(row_idx, col_idx, val)
            
    add_space()
    
    add_h1("3. 업종 대분류별 분석 및 구별 비교")
    add_body("용인시 전체 업종 구성은 음식(24.93%), 소매(21.34%), 과학·기술(13.66%), 교육(11.39%) 순입니다. 구별 비교 시 상권의 분화 상태를 뚜렷하게 관찰할 수 있습니다.")
    add_space()
    
    # [표 2] 작성
    table2 = doc.add_table(rows=11, cols=5)
    headers2 = ["업종 대분류", "용인시 전체", "기흥구 구성비", "수지구 구성비", "처인구 구성비"]
    data2 = [
        ["음식", "24.93%", "22.04%", "22.19%", "30.46%"],
        ["소매", "21.34%", "20.03%", "19.95%", "23.98%"],
        ["과학·기술", "13.66%", "18.64%", "13.54%", "7.97%"],
        ["교육", "11.39%", "11.75%", "16.57%", "6.85%"],
        ["수리·개인서비스", "10.88%", "10.64%", "10.10%", "11.79%"],
        ["부동산", "5.20%", "5.09%", "5.12%", "5.39%"],
        ["예술·스포츠", "4.60%", "4.42%", "4.80%", "4.64%"],
        ["시설관리·임대", "4.15%", "4.19%", "2.99%", "5.04%"],
        ["보건의료", "2.82%", "2.73%", "4.04%", "1.95%"],
        ["숙박", "1.02%", "0.46%", "0.70%", "1.92%"]
    ]
    
    for col_idx, header_text in enumerate(headers2):
        table2.set_cell_text(0, col_idx, header_text)
        table2.set_cell_shading(0, col_idx, "D6E4F0")
        
    for row_idx, row_data in enumerate(data2, start=1):
        for col_idx, val in enumerate(row_data):
            table2.set_cell_text(row_idx, col_idx, val)
            if row_data[0] == "교육" and col_idx == 3:
                table2.set_cell_shading(row_idx, col_idx, "FFEBEB")
            elif row_data[0] == "과학·기술" and col_idx == 2:
                table2.set_cell_shading(row_idx, col_idx, "EBF5FB")
            elif row_data[0] == "음식" and col_idx == 4:
                table2.set_cell_shading(row_idx, col_idx, "FFF9E6")
                
    add_space()
    
    add_h1("4. 위경도 좌표 기반 공간 핫스팟(Hotspot) 분석 (DBSCAN)")
    add_body("GPS 물리 좌표에 밀도 기반 공간 클러스터링(DBSCAN, 반경 100m 기준)을 수행하여, 가장 강력한 고밀도 밀집 구역 5곳을 도출했습니다.")
    add_space()
    
    # [표 3] 작성 (공간 핫스팟 표)
    table3 = doc.add_table(rows=6, cols=6)
    headers3 = ["순위", "핫스팟 구역", "중심 좌표", "밀집 점포수", "1순위 대표업종", "2순위 대표업종"]
    data3 = [
        ["1위", "수지구 풍덕천동 일대", "37.32394, 127.09659", "1,842개", "일반 교육(198개)", "한식(170개)"],
        ["2위", "기흥구 중동 일대", "37.27080, 127.15280", "1,432개", "본사·컨설팅(440개)", "광고(118개)"],
        ["3위", "기흥구 보정동 일대", "37.32043, 127.11172", "1,366개", "일반 교육(120개)", "본사·컨설팅(117개)"],
        ["4위", "기흥구 구갈동 일대", "37.27139, 127.12711", "1,279개", "본사·컨설팅(322개)", "광고(111개)"],
        ["5위", "처인구 김량장동 일대", "37.23559, 127.20578", "1,244개", "한식(139개)", "의류 소매(133개)"]
    ]
    
    for col_idx, header_text in enumerate(headers3):
        table3.set_cell_text(0, col_idx, header_text)
        table3.set_cell_shading(0, col_idx, "D6E4F0")
        
    for row_idx, row_data in enumerate(data3, start=1):
        for col_idx, val in enumerate(row_data):
            table3.set_cell_text(row_idx, col_idx, val)
            if "수지구 풍덕천동" in row_data[1]:
                table3.set_cell_shading(row_idx, col_idx, "FFEBEB")
                
    add_space()
    add_bullet("수지구 풍덕천동 (수지구청역 배후): 거대 사설 학원가와 청소년/학부모 대상 외식 소비가 결합된 용인시 최고의 밀집 복합 상권입니다.", ["수지구 풍덕천동"])
    add_bullet("기흥구 중동 및 구갈동: 요식업이 아닌 경영 컨설팅, 디자인, 오피스 등 '수직형 지식산업 비즈니스 소상공인'이 아파트형 공장에 초고밀 밀집한 업무 구역입니다.", ["기흥구 중동 및 구갈동"])
    add_bullet("처인구 김량장동 (용인중앙시장 배후): 전통시장과 패션·의류 소매업(133개)이 중심이 되는 가두점 생활 소비형 구도심 핫스팟입니다.", ["처인구 김량장동"])
    add_space()
    
    add_h1("5. 용인시 법정동별 및 인기 업종 순위")
    add_bullet("법정동 기준 점포수 순위: 1위 죽전동(3,077개) > 2위 구갈동(3,076개) > 3위 중동(2,986개) > 4위 풍덕천동(2,920개) 순입니다.", ["법정동 기준 점포수 순위"])
    add_bullet("골목 인기 업종: 1위 한식(4,805개, 10.44%) > 2위 기타 교육(2,668개, 5.80%) > 3위 기타 간이(2,529개) 순입니다.", ["골목 인기 업종"])
    add_space()
    
    add_h1("6. 결론 및 공공 시사점")
    add_bullet("공간 밀도 분석 결과를 토대로 수지구에는 통학 시간 교통 안전대책, 기흥구에는 지산 배후 테크스타트업 지원책, 처인구에는 재래시장 및 도심재생 인프라 지원책이 핀포인트로 적용되어야 효과를 극대화할 수 있습니다.", ["공간 밀도 분석 결과를 토대로"])
    
    # 문서 저장
    output_path = "/Users/bboyamin/my_project/factchat_project/src/용인시_상가상권정보_분석보고서_2026.hwpx"
    doc.save_to_path(output_path)
    print(f"HWPX Spatial Report successfully generated and saved to: {output_path}")

if __name__ == "__main__":
    build_report()
