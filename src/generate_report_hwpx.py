import os
from hwpx import HwpxDocument

def build_report():
    doc = HwpxDocument.new()
    
    # -------------------------------------------------------------
    # 헬퍼 함수 정의
    # -------------------------------------------------------------
    def add_title(text):
        p = doc.add_paragraph()
        p.add_run(text, bold=True, size=18, color="1F4E79")
        # 빈 줄 추가
        doc.add_paragraph()
        
    def add_h1(text):
        p = doc.add_paragraph()
        p.add_run(text, bold=True, size=14, color="2E5B82")
        
    def add_h2(text):
        p = doc.add_paragraph()
        p.add_run(text, bold=True, size=11, color="4F709C")
        
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
        p.add_run("  •  ", bold=True, size=10, color="2E5B82")
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
    add_title("2024년 용인시 범죄 발생 현황 및 치안 분석 보고서")
    
    add_body("본 보고서는 경찰청의 2024년 12월 31일 기준 범죄 발생 지역별 통계와 행정안전부의 2024년 12월 말 기준 주민등록 인구통계를 결합하여, 용인시의 치안 현황을 분석하고 경기도 내 5대 대도시(수원·용인·고양·화성·성남)와 비교 분석한 보고서입니다.")
    add_space()
    
    add_h1("1. 핵심 요약 (Executive Summary)")
    add_bullet("\"가장 안전한 100만 대도시\": 용인시의 인구 10만 명당 범죄 발생 건수는 2,339.26건으로, 경기도 내 인구 90만 명 이상 5대 대도시 중 가장 낮았습니다 (수원 3,393.66건, 성남 3,131.75건 등 대비 매우 안전한 수준).", ["\"가장 안전한 100만 대도시\":", "2,339.26건", "가장 낮았습니다"])
    add_bullet("\"민생 강력·폭력범죄의 우수한 차단율\": 용인시의 인구 10만 명당 강력범죄(26.05건)와 폭력범죄(297.62건) 발생률은 5대 대도시 중 최하위를 기록하여, 시민들이 체감하는 물리적 치안 수준이 우수함을 입증했습니다.", ["\"민생 강력·폭력범죄의 우수한 차단율\":", "최하위"])
    add_bullet("\"마약류 범죄 청정 지역 유지\": 고양시(32.51건), 수원시(28.33건) 등 타 도시에 비해 용인시의 인구 10만 명당 마약범죄 발생률은 7.61건으로 매우 낮은 청정 수준을 보였습니다.", ["\"마약류 범죄 청정 지역 유지\":", "7.61건"])
    add_bullet("\"핵심 관리 대상: 사기 범죄\": 용인시 전체 범죄의 27.3%가 사기 범죄(6,964건)로 나타났습니다. 지능범죄 내에서의 비중은 84%에 달해 보이스피싱, 메신저 피싱 등 온라인/비대면 사기에 대한 적극적인 방어 및 홍보가 요구됩니다.", ["\"핵심 관리 대상: 사기 범죄\":", "27.3%", "사기 범죄(6,964건)"])
    add_bullet("\"도농복합지역의 특수성: 환경범죄 관리 필요\": 환경범죄 발생률(10만 명당 7.06건)은 화성시에 이어 2위로 높은 편입니다. 처인구 등 도농복합지대의 소규모 공장 및 개발 구역에 대한 정기적인 환경 법규 단속이 요구됩니다.", ["\"도농복합지역의 특수성: 환경범죄 관리 필요\":", "7.06건"])
    add_space()
    
    add_h1("2. 경기도 5대 대도시 범죄율 비교 (수원·용인·고양·화성·성남)")
    add_body("절대 건수만으로 비교할 경우 인구가 많은 지자체가 불리하므로, 각 지자체의 2024년 12월 31일 기준 주민등록인구를 반영하여 인구 10만 명당 범죄 발생 건수로 정밀하게 환산하여 비교하였습니다.")
    add_space()
    
    # [표 1] 작성
    table1 = doc.add_table(rows=6, cols=5)
    headers1 = ["순위", "도시명", "주민등록 인구수 (명)", "연간 총 범죄 발생 건수 (건)", "인구 10만 명당 범죄율 (건)"]
    data1 = [
        ["1", "경기도 수원시", "1,189,599", "40,371", "3,393.66"],
        ["2", "경기도 성남시", "925,584", "28,987", "3,131.75"],
        ["3", "경기도 화성시", "991,529", "27,300", "2,753.32"],
        ["4", "경기도 고양시", "1,073,506", "26,595", "2,477.40"],
        ["5", "경기도 용인시 (최우수)", "1,090,302", "25,505", "2,339.26"]
    ]
    
    for col_idx, header_text in enumerate(headers1):
        table1.set_cell_text(0, col_idx, header_text)
        table1.set_cell_shading(0, col_idx, "D6E4F0")
        
    for row_idx, row_data in enumerate(data1, start=1):
        for col_idx, val in enumerate(row_data):
            table1.set_cell_text(row_idx, col_idx, val)
            if "용인" in row_data[1]:
                table1.set_cell_shading(row_idx, col_idx, "F2F7FA")
                
    add_space()
    add_body("※ 용인시는 경기도 내 2위의 인구 규모(약 109만 명)를 가진 대도시임에도 불구하고, 절대 범죄 발생 건수(25,505건)와 인구 10만 명당 범죄율(2,339.26건) 모두 5대 대도시 중 압도적으로 가장 낮아 치안 지표가 매우 우수한 도시로 나타났습니다.")
    add_space()
    
    add_h1("3. 범죄 대분류별 상세 비교 및 용인시의 특성")
    add_h2("1) 치안 강점 분야 (상대적으로 매우 안전한 분야)")
    add_bullet("강력범죄 (살인·강도·강간 등): 수원(46.32) > 성남(38.46) > 화성(29.55) > 고양(28.50) > 용인(26.05) 순으로 강력범죄율이 5대 도시 중 가장 낮습니다. 뛰어난 방범 인프라가 작동함을 증명합니다.", ["강력범죄", "가장 낮습니다"])
    add_bullet("폭력범죄 (폭행·상해·협박 등): 수원(439.64) > 성남(416.17) > 화성(351.28) > 고양(350.91) > 용인(297.62) 순으로 용인시가 가장 낮습니다. 기흥, 수지 등 아파트 중심 주거 배후지역이 고루 퍼져 있는 구조 덕분입니다.", ["폭력범죄", "가장 낮습니다"])
    add_bullet("마약범죄: 고양(32.51) > 수원(28.33) > 화성(15.23) > 성남(12.10) > 용인(7.61) 순으로 용인시는 타 도시의 1/3~1/4에 불과한 매우 안전한 수치입니다.", ["마약범죄", "7.61"])
    add_space()
    
    add_h2("2) 주의 및 집중 관리 분야 (잠재적 치안 취약 분야)")
    add_bullet("환경범죄 (대기·수질·폐기물 오염 등): 화성(27.94) > 용인(7.06) > 고양(4.66) > 성남(1.40) > 수원(1.09) 순입니다. 처인구 중심의 반도체 클러스터 개발과 외곽 지역 소규모 제조업체 증가로 단속 건수가 높게 나타납니다.", ["환경범죄", "용인(7.06)"])
    add_bullet("교통범죄 (음주운전, 무면허 등): 화성(523.84) > 수원(478.31) > 성남(435.94) > 용인(368.06) > 고양(330.51) 순입니다. 고속도로 및 간선도로 밀집과 자가용 비율이 높아 교통 치안에 많은 신경을 기울여야 합니다.", ["교통범죄"])
    add_space()
    
    add_h1("4. 용인시 세부 범죄(중분류) 발생 순위 Top 10")
    add_body("용인시에서 실질적으로 가장 많이 발생한 세부 범죄(중분류)의 순위입니다.")
    add_space()
    
    # [표 2] 작성
    table2 = doc.add_table(rows=11, cols=6)
    headers2 = ["순위", "범죄 대분류", "범죄 중분류", "발생 건수 (건)", "10만 명당 건수 (건)", "비중 (%)"]
    data2 = [
        ["1", "지능범죄", "사기", "6,964", "638.72", "27.30%"],
        ["2", "교통범죄", "교통범죄", "4,013", "368.06", "15.73%"],
        ["3", "기타범죄", "기타범죄", "3,733", "342.38", "14.64%"],
        ["4", "절도범죄", "절도범죄", "3,200", "293.50", "12.55%"],
        ["5", "특별경제범죄", "특별경제범죄", "1,975", "181.14", "7.74%"],
        ["6", "폭력범죄", "폭행", "1,781", "163.35", "6.98%"],
        ["7", "지능범죄", "횡령", "988", "90.62", "3.87%"],
        ["8", "폭력범죄", "손괴", "754", "69.16", "2.96%"],
        ["9", "폭력범죄", "협박", "360", "33.02", "1.41%"],
        ["10", "풍속범죄", "성풍속범죄", "308", "28.25", "1.21%"]
    ]
    
    for col_idx, header_text in enumerate(headers2):
        table2.set_cell_text(0, col_idx, header_text)
        table2.set_cell_shading(0, col_idx, "D6E4F0")
        
    for row_idx, row_data in enumerate(data2, start=1):
        for col_idx, val in enumerate(row_data):
            table2.set_cell_text(row_idx, col_idx, val)
            if row_data[2] == "사기":
                table2.set_cell_shading(row_idx, col_idx, "FFEBEB")
                
    add_space()
    add_body("※ 사기 범죄 단일 유형이 용인시 전체 범죄의 1/4 이상(27.3%)을 차지하고 있습니다. 보이스피싱, 메신저 피싱 등 전기통신금융사기 차단을 위한 집중 방어가 필요합니다.")
    add_space()
    
    add_h1("5. 인구수 대비 범죄율 데이터 구득 및 연계 방안")
    add_h2("1) 추천 데이터 원천 (Data Sources)")
    add_bullet("행정안전부 주민등록 인구통계 (jumin.mois.go.kr): 월별/연도별 시군구 및 읍면동 인구의 원본 데이터 엑셀을 받을 수 있어 정합성이 가장 높습니다.", ["행정안전부 주민등록 인구통계"])
    add_bullet("통계청 KOSIS 국가통계포털 (kosis.kr): 주민등록인구 자료를 연도별로 아카이빙하고 있으며 가구 통계 등 다각적인 결합 분석이 가능합니다.", ["통계청 KOSIS 국가통계포털"])
    add_bullet("법무부 출입국·외국인정책본부: 공공데이터포털(data.go.kr)에 공개된 외국인 거주 통계를 함께 매칭하면 보다 정밀한 외국인 관련 치안율을 산출할 수 있습니다.", ["법무부 출입국·외국인정책본부"])
    add_space()
    
    add_h2("2) 데이터 매칭 프로세스")
    add_bullet("행정구역명 표준화: 범죄 데이터의 '경기도 용인시'와 인구통계의 '용인시'를 통일해 키(Key) 값 매칭을 수행합니다.", ["행정구역명 표준화"])
    add_bullet("수식 적용: 범죄발생률 = (범죄 발생 건수 / 주민등록 인구수) * 100,000 공식을 적용해 인구 10만 명당 범죄율 지표로 통일합니다.", ["수식 적용"])
    add_space()
    
    add_h1("6. 한계점 및 고려사항")
    add_bullet("유동인구 미반영: 실제 치안 리스크는 상업 밀집지의 주간 유동인구도 크게 작용합니다. 용인시는 상업지 유입 인구 대비 상주 주거 인구가 많아 상대적으로 인구 대비 범죄율이 낮아 보이는 특수성도 감안해야 합니다.", ["유동인구 미반영"])
    add_bullet("외국인 통계의 차이: 총 범죄 건수에는 주민등록 미등재 외국인의 범죄도 포함되어 있으므로 엄격하게는 등록외국인 수를 인구수에 포함하여 연산해야 오차를 낮출 수 있습니다.", ["외국인 통계의 차이"])
    
    # 문서 저장
    output_path = "/Users/bboyamin/my_project/factchat_project/src/용인시_범죄발생현황_분석보고서_2024.hwpx"
    doc.save_to_path(output_path)
    print(f"HWPX Report successfully generated and saved to: {output_path}")

if __name__ == "__main__":
    build_report()
