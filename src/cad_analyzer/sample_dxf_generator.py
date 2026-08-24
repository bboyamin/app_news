import ezdxf

def create_sample_ict_dxf(filename="sample_ict_drawing.dxf"):
    """
    건축 벽체, 문, 창문, 치수선, TPS실, 통신 아울렛 및 배관선이 100% 완전하게 포함된
    고품질 정보통신공사 건축 평면도(DXF)를 생성합니다.
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # 1. 레이어 정의 (AutoCAD 표준 색상 코드)
    doc.layers.new(name='A-WALL', dxfattribs={'color': 7})      # 흰색 (외벽/내벽)
    doc.layers.new(name='A-DOOR', dxfattribs={'color': 2})      # 노란색 (문/개호부)
    doc.layers.new(name='A-WINDOW', dxfattribs={'color': 4})    # Cyan (창문)
    doc.layers.new(name='A-DIM', dxfattribs={'color': 3})       # 녹색 (치수선)
    doc.layers.new(name='TITLE', dxfattribs={'color': 7})      # 흰색 (표제란)
    doc.layers.new(name='LEGEND', dxfattribs={'color': 3})     # 녹색 (범례표)
    doc.layers.new(name='EQUIPMENT', dxfattribs={'color': 1})  # 빨간색 (TPS, 단자함)
    doc.layers.new(name='OUTLET', dxfattribs={'color': 2})     # 노란색 (아울렛)
    doc.layers.new(name='CABLE_LINE', dxfattribs={'color': 5})  # 파란색 (배관라인)
    doc.layers.new(name='TEXT_SPEC', dxfattribs={'color': 6})   # 자홍색 (규격표기)

    # 2. 도면 외곽선 및 표제란 (Title Block)
    msp.add_lwpolyline([(0, 0), (500, 0), (500, 360), (0, 360), (0, 0)], dxfattribs={'layer': 'TITLE'})
    msp.add_text("도면명: 2층 구내통신 설비 건축 통합 평면도", dxfattribs={'layer': 'TITLE', 'height': 6.0}).set_placement((15, 340))
    msp.add_text("공사명: 용인 스마트 공공청사 신축공사 | 축척: 1/100", dxfattribs={'layer': 'TITLE', 'height': 4.5}).set_placement((15, 325))
    msp.add_text("설계: (주)통신엔지니어링 | 검토: 착공전 도면 검토시스템", dxfattribs={'layer': 'TITLE', 'height': 4.0}).set_placement((15, 312))

    # 3. 건축 외벽 (Outer Walls) 및 내벽 (Inner Walls)
    # 외벽 굵은 라인
    msp.add_lwpolyline([(140, 40), (480, 40), (480, 300), (140, 300), (140, 40)], dxfattribs={'layer': 'A-WALL'})
    msp.add_lwpolyline([(145, 45), (475, 45), (475, 295), (145, 295), (145, 45)], dxfattribs={'layer': 'A-WALL'})

    # 내벽 및 실 구분 (사무실-1, 사무실-2, TPS실, 복도)
    msp.add_line((145, 170), (475, 170), dxfattribs={'layer': 'A-WALL'}) # 중앙 복도 벽
    msp.add_line((310, 170), (310, 295), dxfattribs={'layer': 'A-WALL'}) # 사무실1 / 사무실2 경계벽
    msp.add_line((230, 45), (230, 170), dxfattribs={'layer': 'A-WALL'})   # TPS실 / 회의실 경계벽

    # 4. 건축 문 (Doors) 및 창문 (Windows)
    # 문 (DOOR 호 및 개구부)
    doors = [(210, 170), (280, 170), (360, 170), (200, 45)]
    for dx, dy in doors:
        msp.add_line((dx, dy), (dx + 20, dy), dxfattribs={'layer': 'A-DOOR'})
        msp.add_arc(center=(dx, dy), radius=20, start_angle=0, end_angle=90, dxfattribs={'layer': 'A-DOOR'})

    # 창문 (Windows)
    msp.add_line((140, 100), (140, 140), dxfattribs={'layer': 'A-WINDOW'})
    msp.add_line((480, 100), (480, 140), dxfattribs={'layer': 'A-WINDOW'})

    # 5. 실 명칭 (Room Labels)
    msp.add_text("사무실 A (행정팀)", dxfattribs={'layer': 'TITLE', 'height': 4.5}).set_placement((180, 260))
    msp.add_text("사무실 B (ICT운영팀)", dxfattribs={'layer': 'TITLE', 'height': 4.5}).set_placement((340, 260))
    msp.add_text("TPS실 (통신실)", dxfattribs={'layer': 'TITLE', 'height': 4.5}).set_placement((160, 110))
    msp.add_text("중앙 복도", dxfattribs={'layer': 'TITLE', 'height': 4.0}).set_placement((320, 110))

    # 6. 범례 표 (Legend Table Box)
    msp.add_lwpolyline([(15, 190), (135, 190), (135, 295), (15, 295), (15, 190)], dxfattribs={'layer': 'LEGEND'})
    msp.add_text("[ 정보통신 범례표 ]", dxfattribs={'layer': 'LEGEND', 'height': 4.0}).set_placement((20, 280))
    msp.add_text("■ TPS_CABINET : TPS 통신단자함", dxfattribs={'layer': 'LEGEND', 'height': 3.0}).set_placement((20, 262))
    msp.add_text("● OUTLET_LAN  : 정보통신 아울렛 (Cat.6 2Port)", dxfattribs={'layer': 'LEGEND', 'height': 3.0}).set_placement((20, 247))
    msp.add_text("▲ CCTV_CAM    : 고정형 네트워크 CCTV", dxfattribs={'layer': 'LEGEND', 'height': 3.0}).set_placement((20, 232))
    msp.add_text("━ CONDUIT_LINE : 배관 및 배선 라인", dxfattribs={'layer': 'LEGEND', 'height': 3.0}).set_placement((20, 217))

    # 7. 치수선 (Dimensions)
    msp.add_line((140, 310), (480, 310), dxfattribs={'layer': 'A-DIM'})
    msp.add_line((140, 305), (140, 315), dxfattribs={'layer': 'A-DIM'})
    msp.add_line((480, 305), (480, 315), dxfattribs={'layer': 'A-DIM'})
    msp.add_text("전체 가로 폭: 34,000 mm", dxfattribs={'layer': 'A-DIM', 'height': 3.5}).set_placement((280, 315))

    # 8. 통신 단자함 및 아울렛 배치
    # TPS-01 함체
    msp.add_lwpolyline([(170, 60), (195, 60), (195, 85), (170, 85), (170, 60)], dxfattribs={'layer': 'EQUIPMENT'})
    msp.add_text("TPS-01", dxfattribs={'layer': 'EQUIPMENT', 'height': 3.0}).set_placement((172, 70))

    # 통신 아울렛 (6개)
    outlets = [
        (200, 240, "UTP-01"),
        (260, 240, "UTP-02"),
        (350, 240, "UTP-03"),
        (420, 240, "UTP-04"),
        (260, 200, "UTP-05"),
        (420, 200, "UTP-06"),
    ]

    for x, y, label in outlets:
        msp.add_circle((x, y), radius=4.5, dxfattribs={'layer': 'OUTLET'})
        msp.add_text(label, dxfattribs={'layer': 'OUTLET', 'height': 2.5}).set_placement((x - 6, y - 8))

    # 9. 배관 라인 및 관로 규격 텍스트
    # 상부 아울렛 연결 간선
    msp.add_line((195, 72), (200, 240), dxfattribs={'layer': 'CABLE_LINE'})
    msp.add_line((200, 240), (260, 240), dxfattribs={'layer': 'CABLE_LINE'})
    msp.add_line((260, 240), (350, 240), dxfattribs={'layer': 'CABLE_LINE'})
    msp.add_line((350, 240), (420, 240), dxfattribs={'layer': 'CABLE_LINE'})

    # 하부 아울렛 연결 (의도적 결속 오류: UTP-06(420, 200) 전 400에서 라인 끊김)
    msp.add_line((195, 72), (260, 200), dxfattribs={'layer': 'CABLE_LINE'})
    msp.add_line((260, 200), (400, 200), dxfattribs={'layer': 'CABLE_LINE'}) # 420까지 가야 하는데 400에서 끊김

    # 관로 규격 텍스트
    msp.add_text("간선배관: HI-PVC Ø16 x 1", dxfattribs={'layer': 'TEXT_SPEC', 'height': 3.2}).set_placement((205, 140))
    msp.add_text("분기배관: HI-PVC Ø16", dxfattribs={'layer': 'TEXT_SPEC', 'height': 2.8}).set_placement((270, 210))

    doc.saveas(filename)
    print(f"Full Architectural ICT DXF Drawing created: {filename}")
    return filename

if __name__ == "__main__":
    create_sample_ict_dxf()
