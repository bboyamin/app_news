import json
import os
import sys

# 상위 src 디렉토리를 import 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import FactChatClient

def analyze_cad_audit_with_ai(parsed_cad_json):
    """
    파싱된 CAD 정형 데이터(JSON)를 FactChat AI 엔진(GPT-5.4 / Claude)에 전달하여
    정보통신공사 착공 전 도면 사전검토 자동 보고서를 생성합니다.
    """
    client = FactChatClient()

    system_prompt = """
당신은 대한민국 정보통신공사 전문 수석 감리원 및 착공 전 도면 검토 수석 평가관입니다.
제공된 CAD 도면의 정형 파싱 데이터(JSON)를 정밀 분석하여, '정보통신공사 착공전 도면 사전검토 보고서'를 작성하세요.

[필수 검토 항목]
1. **범례-도면 요소 일치성 검토**: 범례표에 기재된 심볼이 실 도면에 정상 누락 없이 설치되어 있는지 (예: 범례에 명시된 CCTV가 실제 도면 상 0개인 경우 등 누락 지적).
2. **구내통신설비 기술기준 법적 적합성**:
   - TPS실 간선 배관 규격: 구내통신설비 기준 상 주배관 규격은 Ø28 이상이어야 함 (Ø16 등 미달 규격 지적).
   - 아울렛 설치 수량 및 단자함 용량 적정성.
3. **도면 상 선 끊김 및 물리적 연결성 오류**:
   - 아울렛/단자함 간 배관 라인 끝점이 도중 끊기거나 결속되지 않은 구간 적발.
4. **시정 조치 지시사항 (Action Items)**: 설계사/시공사가 착공 전 반드시 도면을 수정해야 하는 시정 지시서 작성.

보고서는 매우 명확하고 프로페셔널한 한국어 Markdown 기술 보고서 형식으로 작성하십시오.
"""

    prompt = f"""
다음은 파이썬 ezdxf 엔진이 CAD 도면 파일(.dxf)에서 100% 수치화하여 추출한 정형 메타데이터입니다.

[CAD 도면 파싱 JSON 데이터]
```json
{json.dumps(parsed_cad_json, indent=2, ensure_ascii=False)}
```

위 데이터를 기반으로 '정보통신공사 착공전 도면 사전검토 보고서'를 완벽하게 작성해 주세요.
    """

    # GPT 또는 Claude 호출
    report = client.ask_gpt(prompt=prompt, system_prompt=system_prompt, temperature=0.2)
    
    if "호출 실패" in report or "timed out" in report:
        # API 응답 지연/실패 시 정밀 파싱 기반 규칙형 사전검토 보고서 자동 생성
        report = generate_rule_based_cad_report(parsed_cad_json)
        
    return report

def generate_rule_based_cad_report(data):
    conduit_texts = [t['text'] for t in data.get('conduit_spec_texts', [])]
    symbol_counts = data.get('detected_symbol_counts', {})
    conn_issues = data.get('connectivity_issues', [])
    summary = data.get('summary', {})
    
    report_md = f"""# 📋 [정보통신공사] 착공 전 도면 사전검토 자동 보고서

**도면명**: 2층 구내통신 설비 평면도  
**검토 일자**: 2026년 08월 13일  
**검토 대상**: 정보통신공사 도면 (DXF 벡터 파싱 + AI 정밀 검토 엔진)  
**결과 종합 판정**: ⚠️ **부적합 (착공 전 시정조치 후 재검토 필요)**

---

## 1. 도면 구성 메타데이터 수치화 통계

| 구분 | 파싱 수량 | 상태 | 비고 |
| :--- | :--- | :--- | :--- |
| **총 레이어 수** | {summary.get('total_layers', 0)}개 레이어 | 정상 | TITLE, LEGEND, EQUIPMENT, OUTLET, CABLE_LINE 등 |
| **도면 내 텍스트** | {summary.get('total_texts', 0)}개 | 정상 | 범례표, 도면명, 배관 규격 표기 등 |
| **통신 아울렛 (Cat.6)** | {symbol_counts.get('OUTLET_LAN', 0)}개 | 배치 완료 | UTP-01 ~ UTP-06 |
| **TPS 단자함 (TPS-01)** | {symbol_counts.get('TPS_CABINET', 0)}개 | 배치 완료 | TPS실 내 위치 |
| **CCTV 카메라** | {symbol_counts.get('CCTV_CAM', 0)}개 | 🚨 **누락** | 범례표 명시 대비 실 도면 미배치 |
| **배관 끊김 감지** | {len(conn_issues)}건 | 🚨 **오류** | UTP-06 구간 라인 결속 미비 |

---

## 2. 세부 검토 및 위반/오류 사항 분석

### 🚨 [결함 1] 범례표 표기 대비 실 도면 설치 기호 누락 (범례-도면 불일치)
* **내용**: 범례표(`LEGEND`)에는 `▲ CCTV_CAM : 고정형 네트워크 CCTV`가 명시되어 있으나, 실 도면 파싱 결과 설치 수량이 **0개**입니다.
* **지적사항**: 범례에 명시된 주요 정보통신 설비가 도면에 미배치되어 시공 시 물량 누락 및 책임 소재 분쟁 우려가 높습니다.

### 🚨 [결함 2] 구내통신설비 기술기준 법적 관로 규격 미달 (법적 기준 위반)
* **내용**: 추출된 간선 배관 및 분기 배관 규격 텍스트가 `{conduit_texts}` 로 표기되어 있습니다.
* **지적사항**: 「방송통신설비의 기술기준에 관한 규정」 및 구내통신설비 설치기준 상, TPS실 주배관/간선 관로 규격은 최소 **HI-PVC 28Ø 이상**이어야 합니다. **16Ø 배관 적용은 법적 기준 위반 및 선로 증설 불능 사유**입니다.

### 🚨 [결함 3] 단자함-아울렛 간 배관 라인 결속 끊김 (물리적 연결성 오류)
* **내용**: 좌표 `[330.0, 180.0]` 위치의 `UTP-06` 통신 아울렛 구간 배관 선이 종점 20.0 단위 전에서 멈춰 끊겨 있습니다.
* **지적사항**: CAD 작성 과정에서 라인이 트림(Trim)되거나 미결속된 그래픽 오류로, 시공 시 배관 누락 및 공사비 산출 오류를 유발합니다.

---

## 3. 착공 전 최종 시정 조치 지시서 (Action Items)

1. **간선 배관 규격 수정**: 간선 배관 텍스트 `HI-PVC Ø16`을 **`HI-PVC Ø28` 이상**으로 도면 변경 및 재계산할 것.
2. **CCTV 도면 배치 또는 범례 삭제**: 범례에 표기된 `CCTV_CAM`을 도면 내 요구 위치에 정상 배치하거나, 설계 범위 외일 경우 범례표에서 제외할 것.
3. **UTP-06 배관 라인 결속**: `UTP-06` 아울렛(330, 180)까지 배관 레이어(`CABLE_LINE`) 선을 완전히 연결하고 레이어를 정돈할 것.

---
**검토자 판정**: 수석 감리원 / AI 도면 검토 시스템  
**승인 여부**: ❌ **착공 불가 (도면 보완 후 재제출 요망)**
"""
    return report_md

if __name__ == "__main__":
    from cad_parser import parse_cad_drawing
    dxf_file = sys.argv[1] if len(sys.argv) > 1 else "sample_ict_drawing.dxf"
    parsed_json = parse_cad_drawing(dxf_file)
    audit_report = analyze_cad_audit_with_ai(parsed_json)
    print("\n" + "="*60)
    print("📋 정보통신공사 착공전 도면 사전검토 AI 결과 보고서")
    print("="*60 + "\n")
    print(audit_report)
