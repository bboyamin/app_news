import os
import re
import glob
import pandas as pd
import numpy as np
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TEMP_DOC_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_docs", "합본예산서(세출)_산출근거별.csv")

def ensure_data_dir():
    """데이터 저장 디렉토리 생성 및 초기 2026년 데이터 세팅"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    
    file_2026 = os.path.join(DATA_DIR, "budget_2026.csv")
    if not os.path.exists(file_2026) and os.path.exists(TEMP_DOC_PATH):
        try:
            df = load_raw_csv(TEMP_DOC_PATH)
            save_processed_csv(df, 2026)
        except Exception as e:
            print(f"Error seeding 2026 budget data: {e}")

def load_raw_csv(filepath_or_buffer):
    """CSV 파일 인코딩 및 멀티 레벨 헤더 자동 처리 파싱 (속도 최적화)"""
    encodings = ["utf-8", "utf-8-sig", "cp949", "euc-kr"]
    df_raw = None
    
    for enc in encodings:
        try:
            if hasattr(filepath_or_buffer, 'seek'):
                filepath_or_buffer.seek(0)
            df_raw = pd.read_csv(filepath_or_buffer, encoding=enc, low_memory=False)
            break
        except Exception:
            continue
            
    if df_raw is None:
        raise ValueError("CSV 파일 인코딩을 읽을 수 없습니다 (UTF-8 / CP949 지원)")

    # 1행이 서브헤더 ('경정', '기정', '증감' 등)인지 확인하고 처리
    if df_raw.iloc[0].astype(str).str.contains("경정|기정|증감").any():
        df = df_raw.iloc[1:].copy()
    else:
        df = df_raw.copy()
        
    return clean_budget_dataframe(df)

def clean_budget_dataframe(df):
    """예산 데이터프레임 고속 벡터화 정제"""
    df.columns = [str(c).strip() for c in df.columns]
    
    # 회계연도 컬럼 처리
    if '회계연도' in df.columns:
        yr_series = pd.to_numeric(df['회계연도'].astype(str).str.replace(',', '', regex=False), errors='coerce')
        df['회계연도'] = yr_series.ffill().bfill().fillna(2026).astype(int)
    else:
        df['회계연도'] = 2026

    # 필수 텍스트 컬럼 기본값 처리
    text_cols = ['예산구분', '분야명', '부문명', '위원회명', '정책사업명', '단위사업명', 
                 '회계명', '세부사업명', '부서명', '편성목명', '통계목명', '의무/재량구분', '산출근거명', '산출근거식']
    
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("-").astype(str).str.strip()
        else:
            df[col] = "-"

    # 오염 데이터 행 제거 ('0', '-', '7,200' 등 이상치 행 제거)
    df = df[~df['부서명'].isin(['0', 'nan', 'N/A'])].copy()
    df = df[~df['세부사업명'].isin(['0', 'nan', 'N/A'])].copy()

    # 금액 컬럼 벡터화 고속 변환
    amount_cols = ['예산액', '기정액', '비교증감', '국고보조금', '균특보조금', '기금보조금', 
                   '특별교부세', '광역보조금', '특별조정교부금', '자체재원']
    
    for col in amount_cols:
        if col in df.columns:
            cleaned_s = df[col].astype(str).str.replace(',', '', regex=False).str.replace('원', '', regex=False).str.strip()
            df[col + '_num'] = pd.to_numeric(cleaned_s, errors='coerce').fillna(0.0)
        else:
            df[col + '_num'] = 0.0

    # 예산액 억 원 단위 보조 컬럼 생성
    df['예산액_억원'] = df['예산액_num'] / 100000.0
    df['기정액_억원'] = df['기정액_num'] / 100000.0
    df['비교증감_억원'] = df['비교증감_num'] / 100000.0
    
    return df

def save_processed_csv(df, year):
    """정제된 데이터프레임을 연도별 CSV로 저장"""
    ensure_data_dir()
    df['회계연도'] = int(year)
    out_path = os.path.join(DATA_DIR, f"budget_{year}.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    st.cache_data.clear()
    return out_path

def get_available_years():
    """저장된 예산서 연도 목록 반환"""
    ensure_data_dir()
    files = glob.glob(os.path.join(DATA_DIR, "budget_*.csv"))
    years = []
    for f in files:
        m = re.search(r"budget_(\d{4})\.csv", os.path.basename(f))
        if m:
            years.append(int(m.group(1)))
    return sorted(years, reverse=True)

def read_csv_robust(filepath_or_buffer):
    """모든 한글 CSV 인코딩(UTF-8, CP949, EUC-KR)에 대응하는 무적 파일 로더"""
    encodings = ["utf-8-sig", "cp949", "euc-kr", "utf-8"]
    for enc in encodings:
        try:
            if hasattr(filepath_or_buffer, 'seek'):
                filepath_or_buffer.seek(0)
            return pd.read_csv(filepath_or_buffer, encoding=enc, low_memory=False)
        except Exception:
            continue
    if hasattr(filepath_or_buffer, 'seek'):
        filepath_or_buffer.seek(0)
    return pd.read_csv(filepath_or_buffer, encoding="utf-8", encoding_errors="replace", low_memory=False)

@st.cache_data(show_spinner=False)
def load_year_data(year):
    """특정 연도 예산 데이터 로드 (다중 인코딩 및 RAM 캐싱 적용)"""
    ensure_data_dir()
    filepath = os.path.join(DATA_DIR, f"budget_{year}.csv")
    if not os.path.exists(filepath):
        if str(year) == "2026" and os.path.exists(TEMP_DOC_PATH):
            df = load_raw_csv(TEMP_DOC_PATH)
            save_processed_csv(df, 2026)
            return df
        return pd.DataFrame()
        
    df = read_csv_robust(filepath)
    return clean_budget_dataframe(df)

@st.cache_data(show_spinner=False)
def load_all_years_data():
    """전체 연도 데이터 병합 로드 (Streamlit RAM 캐싱 적용)"""
    years = get_available_years()
    if not years:
        return pd.DataFrame()
    dfs = []
    for y in years:
        df = load_year_data(y)
        if not df.empty:
            dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def save_uploaded_budget_file(file_buffer, year):
    """업로드된 CSV 파일을 파싱하고 연도별 저장소에 보관"""
    df = load_raw_csv(file_buffer)
    save_processed_csv(df, year)
    return len(df)

def delete_year_data(year):
    """특정 연도 데이터 삭제"""
    filepath = os.path.join(DATA_DIR, f"budget_{year}.csv")
    if os.path.exists(filepath):
        os.remove(filepath)
        st.cache_data.clear()
        return True
    return False
