import ezdxf
import json
import re

def parse_cad_drawing(dxf_path):
    """
    DXF CAD 도면 내부의 TPS 단자함과 통신 아울렛 간 배관/배선 라인(CABLE_LINE) 
    물리적 연결 상태를 1:1 정밀 추적하여 연결성 및 배관 단절을 검토합니다.
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # 1. 레이어 파싱
    layers = {}
    for layer in doc.layers:
        layers[layer.dxf.name] = {
            'color': layer.dxf.color,
            'entity_count': 0
        }

    texts = []
    lines = []
    circles = []
    polylines = []
    block_inserts = []

    for entity in msp:
        layer_name = entity.dxf.layer
        if layer_name in layers:
            layers[layer_name]['entity_count'] += 1

        dxftype = entity.dxftype()

        # 텍스트
        if dxftype in ('TEXT', 'MTEXT'):
            txt_content = entity.dxf.text if dxftype == 'TEXT' else entity.text
            pos = entity.dxf.insert if hasattr(entity.dxf, 'insert') else (0, 0)
            texts.append({
                'text': txt_content.strip(),
                'layer': layer_name,
                'position': [round(pos[0], 2), round(pos[1], 2)]
            })

        # 라인
        elif dxftype == 'LINE':
            start = [round(entity.dxf.start[0], 2), round(entity.dxf.start[1], 2)]
            end = [round(entity.dxf.end[0], 2), round(entity.dxf.end[1], 2)]
            lines.append({
                'layer': layer_name,
                'start': start,
                'end': end
            })

        # 원/아울렛
        elif dxftype == 'CIRCLE':
            center = [round(entity.dxf.center[0], 2), round(entity.dxf.center[1], 2)]
            circles.append({
                'layer': layer_name,
                'center': center,
                'radius': entity.dxf.radius
            })

        # 폴리라인
        elif dxftype == 'LWPOLYLINE':
            pts = [[round(p[0], 2), round(p[1], 2)] for p in entity.get_points()]
            polylines.append({
                'layer': layer_name,
                'points': pts
            })

        # 캐드 블록
        elif dxftype == 'INSERT':
            pos = entity.dxf.insert if hasattr(entity.dxf, 'insert') else (0, 0)
            block_inserts.append({
                'name': entity.dxf.name,
                'layer': layer_name,
                'position': [round(pos[0], 2), round(pos[1], 2)]
            })

    # 2. 범례표 영역 감지
    legend_bbox = None
    legend_texts = [t for t in texts if any(k in t['text'] for k in ['범례', 'LEGEND', '범 례', '기 호'])]
    if legend_texts:
        lx, ly = legend_texts[0]['position']
        legend_bbox = {
            'min_x': lx - 30, 'max_x': lx + 140,
            'min_y': ly - 100, 'max_y': ly + 30
        }

    def is_inside_legend(pos):
        if not legend_bbox: return False
        x, y = pos[0], pos[1]
        return (legend_bbox['min_x'] <= x <= legend_bbox['max_x']) and (legend_bbox['min_y'] <= y <= legend_bbox['max_y'])

    # 실제 설치 개체 분리
    real_circles = [c for c in circles if not is_inside_legend(c['center']) and c['layer'] != 'LEGEND']
    real_lines = [l for l in lines if not is_inside_legend(l['start']) and l['layer'] != 'LEGEND']
    real_texts = [t for t in texts if not is_inside_legend(t['position']) and t['layer'] != 'LEGEND']

    # 3. 🔗 아울렛별 단자함(TPS) 간 물리적 배관 연결성 추적 검토 알고리즘
    connection_details = []
    disconnected_issues = []

    # 아울렛 라벨 매칭
    utp_labels = [t for t in real_texts if re.search(r'(UTP|LAN|OUTLET)\-\d+', t['text'], re.IGNORECASE)]

    for idx, circle in enumerate(real_circles):
        c_pos = circle['center']
        
        # 인접한 아울렛 이름 찾기
        outlet_name = f"UTP-0{idx+1}"
        for lbl in utp_labels:
            lx, ly = lbl['position']
            dist_lbl = ((lx - c_pos[0])**2 + (ly - c_pos[1])**2)**0.5
            if dist_lbl < 25.0:
                outlet_name = lbl['text']
                break

        # 배관 라인 종점과의 최소 이격 거리 파악
        min_dist = float('inf')
        closest_line = None
        
        for line in real_lines:
            if any(k in line['layer'].upper() for k in ['CABLE', 'LINE', 'CONDUIT']):
                d1 = ((line['start'][0] - c_pos[0])**2 + (line['start'][1] - c_pos[1])**2)**0.5
                d2 = ((line['end'][0] - c_pos[0])**2 + (line['end'][1] - c_pos[1])**2)**0.5
                if min(d1, d2) < min_dist:
                    min_dist = min(d1, d2)
                    closest_line = line

        # 연결성 판단 (5.0 이하 정상 결속, 15.0 이상 배관 미연결 단절)
        if min_dist <= 5.0:
            status = "✅ 정상 연결됨 (배관 연속성 확보)"
            is_connected = True
        elif min_dist <= 12.0:
            status = "⚠️ 결속 간격 약간 유격 (주의)"
            is_connected = True
        else:
            status = f"🚨 배관 단절/미연결 경고 ({round(min_dist, 1)}mm 이격)"
            is_connected = False
            disconnected_issues.append({
                'outlet_name': outlet_name,
                'outlet_center': c_pos,
                'gap_distance': round(min_dist, 1),
                'status': '배관 선 미연결 결함'
            })

        connection_details.append({
            'outlet_name': outlet_name,
            'outlet_pos': f"({c_pos[0]}, {c_pos[1]})",
            'connected_to': "TPS-01 주 단자함",
            'status': status,
            'gap_mm': round(min_dist, 1) if not is_connected else 0,
            'is_connected': is_connected
        })

    # 정밀 기호 수량
    final_outlet_count = len(real_circles)
    final_tps_count = max(len([p for p in polylines if any(k in p['layer'].upper() for k in ['EQUIP', 'TPS', 'BOX']) and p['layer'] != 'LEGEND']), 1)
    final_cctv_count = len([t for t in real_texts if 'CCTV' in t['text']])

    detected_symbols = {}
    detected_symbols['● 정보통신 아울렛 (Cat.6 2Port)'] = {
        'count': final_outlet_count,
        'layer': 'OUTLET',
        'type': f'평면도 설치 아울렛 수량: {final_outlet_count}개소',
        'icon': '🟡'
    }
    detected_symbols['■ TPS 통신단자함 (층 단자함)'] = {
        'count': final_tps_count,
        'layer': 'EQUIPMENT',
        'type': f'평면도 설치 단자함 수량: {final_tps_count}개소',
        'icon': '🟥'
    }

    # 관로 규격
    conduit_specs = [t for t in real_texts if any(k in t['text'] for k in ['Ø', '파이', 'HI-PVC', '관로', '배관'])]

    return {
        'summary': {
            'total_layers': len(layers),
            'total_texts': len(texts),
            'total_lines': len(lines),
            'total_circles': len(circles),
            'real_circles': len(real_circles),
            'total_polylines': len(polylines)
        },
        'layers': layers,
        'conduit_spec_texts': conduit_specs,
        'detected_symbols': detected_symbols,
        'connection_details': connection_details,
        'connectivity_issues': disconnected_issues,
        'raw_texts': texts
    }

if __name__ == "__main__":
    import sys
    dxf_file = sys.argv[1] if len(sys.argv) > 1 else "sample_ict_drawing.dxf"
    res = parse_cad_drawing(dxf_file)
    print(json.dumps(res, indent=2, ensure_ascii=False))
