import streamlit as st
import os
import sys
import base64
import tempfile
import pandas as pd

# 상위 디렉토리 및 현재 디렉토리 모듈 경로 등록
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
sys.path.append(os.path.dirname(CURRENT_DIR))

from sample_dxf_generator import create_sample_ict_dxf
from cad_parser import parse_cad_drawing
from cad_renderer import render_dxf_to_png
from dwg_converter import convert_dwg_to_dxf

st.set_page_config(
    page_title="정보통신공사 도면 대화형 뷰어 & 항목 리스트",
    page_icon="📐",
    layout="wide"
)

st.title("📐 정보통신공사 착공 전 도면 대화형 뷰어 (마우스 확대/축소) & 항목 리스트")
st.caption("초기 버전과 동일하게 1) 마우스 휠 확대/축소 및 드래그 이동 뷰어와 2) 도면 구성 항목 전체 리스트를 제공합니다.")

# 1. 도면 파일 업로드 영역
col_file, col_btn = st.columns([3, 1])

uploaded_file = col_file.file_uploader("통신공사 CAD 도면 파일 (.dwg 또는 .dxf) 선택", type=["dwg", "dxf"])
run_sample = col_btn.button("🚀 샘플 통신 도면 불러오기", use_container_width=True)

target_dxf_path = None
file_display_name = ""

if uploaded_file is not None:
    file_display_name = uploaded_file.name
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        uploaded_tmp_path = tmp_file.name
    
    try:
        target_dxf_path = convert_dwg_to_dxf(uploaded_tmp_path)
    except Exception as e:
        st.error(f"도면 파싱 실패: {e}")
            
elif run_sample:
    file_display_name = "2층 구내통신 설비 평면도 (샘플)"
    sample_path = os.path.join(CURRENT_DIR, "sample_ict_drawing.dxf")
    create_sample_ict_dxf(sample_path)
    target_dxf_path = sample_path

# 2. 도면 읽기 및 2가지 기능만 집중 실행 (초기 대화형 마우스 줌 뷰어)
if target_dxf_path and os.path.exists(target_dxf_path):
    st.divider()
    
    parsed_data = parse_cad_drawing(target_dxf_path)
    img_path = os.path.join(CURRENT_DIR, "view_rendering.png")
    render_dxf_to_png(target_dxf_path, img_path, dpi=300)

    st.subheader(f"📁 [{file_display_name}] 도면 열람 준비 완료")
    
    tab_view, tab_list = st.tabs([
        "🖼️ 기능 1. 도면 100% 원본 대화형 뷰어 (마우스 휠 확대/축소/드래그)", 
        "📋 기능 2. 도면 구성 항목 100% 전체 리스트"
    ])

    # -------------------------------------------------------------
    # 기능 1: 초기 대화형 마우스 휠 줌 & 드래그 뷰어 (OpenSeadragon)
    # -------------------------------------------------------------
    with tab_view:
        st.markdown("#### 🖼️ 도면 100% 대화형 마우스 줌 뷰어")
        st.caption("💡 **마우스 조작 안내**: **마우스 휠을 굴려 확대/축소**, **마우스를 클릭한 채 드래그하여 이동**, 우측 하단 미니맵 내비게이터를 사용하세요.")
        
        if os.path.exists(img_path):
            with open(img_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
            img_data_url = f"data:image/png;base64,{encoded_string}"
            
            # 초기 모델 OpenSeadragon 60FPS 대화형 마우스 줌팬 엔진
            openseadragon_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
                <style>
                    body {{ margin: 0; padding: 0; background: #0b1329; overflow: hidden; }}
                    #openseadragon-viewer {{ width: 100vw; height: 720px; background-color: #0b1329; }}
                    .openseadragon-container {{ background-color: #0b1329 !important; }}
                </style>
            </head>
            <body>
                <div id="openseadragon-viewer"></div>
                <script>
                    var viewer = OpenSeadragon({{
                        id: "openseadragon-viewer",
                        prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
                        tileSources: {{ type: 'image', url: '{img_data_url}' }},
                        showNavigationControl: true,
                        showNavigator: true,
                        navigatorPosition: "BOTTOM_RIGHT",
                        animationTime: 0.25,
                        maxZoomPixelRatio: 8,
                        defaultZoomLevel: 1.0,
                        gestureSettingsMouse: {{
                            clickToZoom: false,
                            dblClickToZoom: true,
                            pinchToZoom: true,
                            scrollToZoom: true
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            st.components.v1.html(openseadragon_html, height=740)

            with open(img_path, "rb") as file:
                st.download_button(
                    label="📥 고해상도 2D 도면 이미지 (PNG) 다운로드",
                    data=file,
                    file_name=f"{file_display_name}_2D_Drawing.png",
                    mime="image/png"
                )

    # -------------------------------------------------------------
    # 기능 2: 도면 내 구성 항목 100% 전체 리스트
    # -------------------------------------------------------------
    with tab_list:
        st.markdown("#### 📋 도면 내에 존재하는 어떠한 항목들이 있는지 전체 리스트")
        st.caption("업로드된 도면 안에서 파싱된 모든 구성 항목(장비 기호, 배관 규격, 레이어, 텍스트)을 표 형태로 리스트업합니다.")
        
        # 1. 도면 내 주요 통신/건축 장비 및 기호 항목 리스트
        st.markdown("##### 1️⃣ 통신 장비 및 기호 항목 리스트 (Equipment & Symbol Items)")
        sym_map = parsed_data['detected_symbols']
        symbol_list = []
        for name, info in sym_map.items():
            symbol_list.append({
                "항목 명칭 (Item Name)": name,
                "항목 설명 및 종류": info['type'],
                "도면 레이어 (Layer)": info['layer'],
                "도면 내 수량": f"{info['count']} 개소"
            })
        st.dataframe(pd.DataFrame(symbol_list), use_container_width=True)

        st.divider()

        # 2. 도면 내 배관/관로 규격 텍스트 리스트
        st.markdown("##### 2️⃣ 배관 및 관로 규격 표기 리스트 (Conduit Specification Items)")
        conduit_texts = parsed_data['conduit_spec_texts']
        if conduit_texts:
            conduit_df = pd.DataFrame([
                {
                    "배관 규격 텍스트": t['text'],
                    "속한 레이어": t['layer'],
                    "도면 위치 좌표 [X, Y]": f"({t['position'][0]}, {t['position'][1]})"
                }
                for t in conduit_texts
            ])
            st.dataframe(conduit_df, use_container_width=True)
        else:
            st.info("도면에서 추출된 배관 규격 텍스트가 없습니다.")

        st.divider()

        # 3. 도면 내 레이어(Layer) 항목 리스트
        st.markdown("##### 3️⃣ 도면 레이어 구성 리스트 (CAD Layer Items)")
        layer_list = []
        for name, info in parsed_data['layers'].items():
            layer_list.append({
                "레이어 명 (Layer Name)": name,
                "레이어 색상 코드": info['color'],
                "레이어 포함 개체 수": f"{info['entity_count']} 개"
            })
        st.dataframe(pd.DataFrame(layer_list), use_container_width=True)

        st.divider()

        # 4. 도면 내 전체 텍스트/주석 항목 리스트
        st.markdown("##### 4️⃣ 도면 내 전체 텍스트/주석 항목 리스트 (All Raw Texts)")
        raw_texts = parsed_data['raw_texts']
        raw_text_df = pd.DataFrame([
            {
                "도면 텍스트 내용": t['text'],
                "속한 레이어": t['layer'],
                "도면 위치 좌표 [X, Y]": f"({t['position'][0]}, {t['position'][1]})"
            }
            for t in raw_texts
        ])
        st.dataframe(raw_text_df, use_container_width=True, height=350)

else:
    st.info("💡 위에서 통신공사 CAD 도면 파일(.dwg / .dxf)을 선택하시거나 **'샘플 통신 도면 불러오기'** 버튼을 누르시면 마우스 줌 뷰어와 구성 항목 리스트를 보실 수 있습니다.")
