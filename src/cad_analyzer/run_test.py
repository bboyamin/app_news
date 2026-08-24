import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.dirname(CURRENT_DIR))

from sample_dxf_generator import create_sample_ict_dxf
from cad_parser import parse_cad_drawing
from cad_renderer import render_dxf_to_png
from cad_ai_checker import analyze_cad_audit_with_ai

def main():
    print("=" * 60)
    print("🚀 [CAD 도면 분석 실증 테스트] 시작")
    print("=" * 60)

    # 1. 샘플 DXF 도면 생성
    dxf_path = os.path.join(CURRENT_DIR, "sample_ict_drawing.dxf")
    print(f"\n1. 샘플 정보통신공사 도면 생성 중: {dxf_path}")
    create_sample_ict_dxf(dxf_path)

    # 2. DXF 정형 파싱
    print("\n2. 파이썬 ezdxf 기반 텍스트, 레이어, 연결성 수치화 파싱 중...")
    parsed_json = parse_cad_drawing(dxf_path)
    print(f"   - 총 레이어 수: {parsed_data_summary(parsed_json)}")

    # 3. 2D 고해상도 이미지 렌더링
    png_path = os.path.join(CURRENT_DIR, "sample_ict_drawing.png")
    print(f"\n3. 도면 2D 고해상도 이미지 렌더링 중: {png_path}")
    render_dxf_to_png(dxf_path, png_path)

    # 4. FactChat AI 기반 착공 전 사전검토 분석
    print("\n4. FactChat AI 엔진 (구내통신설비 기술기준 검토) 분석 수행 중...")
    report = analyze_cad_audit_with_ai(parsed_json)

    print("\n" + "=" * 60)
    print("📋 [AI 착공전 도면 사전검토 보고서 결과]")
    print("=" * 60 + "\n")
    print(report)

    # 결과 보고서 저장
    report_file = os.path.join(CURRENT_DIR, "cad_audit_report_result.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n✅ 실증 테스트 완료! 보고서 저장됨: {report_file}")

def parsed_data_summary(data):
    s = data['summary']
    return f"레이어 {s['total_layers']}개, 텍스트 {s['total_texts']}개, 라인 {s['total_lines']}개, 원 {s['total_circles']}개"

if __name__ == "__main__":
    main()
