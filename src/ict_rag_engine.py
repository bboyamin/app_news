import os
import sqlite3
import re
import unicodedata

# 📂 정보통신 규제 & 설계 전용 DB 경로 설정
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../chroma_db"))
os.makedirs(DB_PATH, exist_ok=True)
DB_FILE = os.path.join(DB_PATH, "ict_agent_documents.db")

def init_ict_db():
    """
    정보통신 규제/기술기준 전용 SQLite DB 테이블 초기화
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ict_document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            chunk_index INTEGER,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

# 모듈 임포트 시 초기화
init_ict_db()

def split_ict_text(text, chunk_size=800, overlap=150):
    """
    법령 조항, 기술기준, 설계해설서의 단락과 수치 규격이 잘리지 않도록 
    800자 크기, 150자 오버랩 슬라이딩 윈도우로 정밀 분할합니다.
    """
    chunks = []
    text = text.strip()
    if not text:
        return chunks
        
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += (chunk_size - overlap)
        
    return chunks

def index_ict_document(filename, text):
    """
    정보통신 법령/기술기준/해설서 텍스트를 전수 쪼개어 지식 DB에 빠짐없이 적재합니다.
    """
    clean_filename = unicodedata.normalize('NFC', filename)
    chunks = split_ict_text(text)
    if not chunks:
        return 0
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 동일 파일 중복 인덱싱 방지
    cursor.execute("DELETE FROM ict_document_chunks WHERE filename = ?", (clean_filename,))
    
    for i, chunk in enumerate(chunks):
        cursor.execute(
            "INSERT INTO ict_document_chunks (filename, chunk_index, content) VALUES (?, ?, ?)",
            (clean_filename, i, chunk)
        )
        
    conn.commit()
    conn.close()
    return len(chunks)

def search_ict_contexts(query, n_results=10):
    """
    🎯 [100% 전수 문서 빠짐없는 종합 릴레이 검토 알고리즘]
    DB에 적재된 '모든 등록 문서(DISTINCT filename)'에서 최소 1개 이상의 대표/매칭 조항을 필수 포함하고,
    질문 키워드 및 조항 번호 매칭 가중치 점수가 높은 항목을 라운드로빈 방식으로 100% 교차 수집합니다.
    """
    keywords = [w for w in re.split(r'[^a-zA-Z0-9가-힣]+', query) if len(w) > 1]
    if not keywords:
        keywords = [query] if query.strip() else []

    article_matches = re.findall(r'(제?\s*\d+\s*조(?:\s*의\s*\d+)?)', query)
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT filename FROM ict_document_chunks")
    all_indexed_files = [row[0] for row in cursor.fetchall()]
    
    if not all_indexed_files:
        conn.close()
        return []

    cursor.execute("SELECT filename, chunk_index, content FROM ict_document_chunks")
    rows = cursor.fetchall()
    conn.close()
    
    file_chunks_map = {fname: [] for fname in all_indexed_files}
    
    for filename, chunk_index, content in rows:
        score = 0
        clean_fname = os.path.splitext(filename)[0]
        
        # A. 파일명(법령명) 매칭 (+100점)
        for kw in keywords:
            if kw.lower() in clean_fname.lower():
                score += 100
        
        # B. 조항 번호 정규식 매칭 (+80점)
        for art in article_matches:
            num_only = re.sub(r'[^\d]', '', art)
            if num_only and f"{num_only}조" in content:
                score += 80

        # C. 본문 키워드 매칭
        for kw in keywords:
            if kw not in ['정보통신', '기준', '관한', '내용', '알려줘', '설비']:
                score += content.count(kw) * 5
            else:
                score += content.count(kw) * 1
                
        score += 1
        file_chunks_map[filename].append((score, content, filename, chunk_index))
        
    for fname in file_chunks_map:
        file_chunks_map[fname].sort(key=lambda x: x[0], reverse=True)

    # 100% 전수 문서 필수 보장 릴레이 수집
    contexts = []
    added_keys = set()
    
    # 1라운드: 등록된 "모든 개별 문서"에서 가장 점수가 높은 Top-1 조항 100% 필수 1개씩 교차 수집
    for fname in all_indexed_files:
        if file_chunks_map[fname]:
            top_item = file_chunks_map[fname][0]
            item_key = (top_item[2], top_item[3])
            if item_key not in added_keys:
                added_keys.add(item_key)
                contexts.append({
                    "score": top_item[0],
                    "text": top_item[1],
                    "filename": top_item[2],
                    "chunk_index": top_item[3]
                })

    # 2라운드: 남은 쿼터 점수가 높은 순으로 추가 라운드로빈 획득
    max_rounds = max([len(v) for v in file_chunks_map.values()]) if file_chunks_map else 0
    for r in range(1, max_rounds):
        for fname in all_indexed_files:
            if r < len(file_chunks_map[fname]):
                item = file_chunks_map[fname][r]
                item_key = (item[2], item[3])
                if item_key not in added_keys:
                    added_keys.add(item_key)
                    contexts.append({
                        "score": item[0],
                        "text": item[1],
                        "filename": item[2],
                        "chunk_index": item[3]
                    })
                    if len(contexts) >= max(n_results, len(all_indexed_files) * 2):
                        break
        if len(contexts) >= max(n_results, len(all_indexed_files) * 2):
            break

    return contexts

def get_indexed_ict_files():
    """
    현재 DB에 연동되어 있는 정보통신 법령/기술기준 파일명 목록
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT filename FROM ict_document_chunks")
    rows = cursor.fetchall()
    conn.close()
    return sorted([row[0] for row in rows])

def get_ict_document_stats():
    """
    DB에 적재된 정보통신 문서별 조각 수, 총 글자 수 상세 집계
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, COUNT(*), SUM(LENGTH(content)) FROM ict_document_chunks GROUP BY filename")
    rows = cursor.fetchall()
    
    stats = []
    for filename, chunk_count, total_chars in rows:
        cursor.execute("SELECT content FROM ict_document_chunks WHERE filename = ? AND chunk_index = 0", (filename,))
        first_chunk = cursor.fetchone()
        snippet = first_chunk[0][:90] + "..." if first_chunk else ""
        stats.append({
            "filename": filename,
            "chunk_count": chunk_count,
            "total_chars": total_chars,
            "snippet": snippet
        })
        
    conn.close()
    return stats

def get_all_ict_chunks():
    """
    DB에 적재된 모든 정보통신 조각 열람
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, chunk_index, LENGTH(content), content FROM ict_document_chunks ORDER BY filename, chunk_index")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_single_ict_document(filename):
    """
    지정된 특정 1개 문서의 모든 데이터 조각만 DB에서 안전하게 개별 삭제합니다.
    """
    try:
        clean_filename = unicodedata.normalize('NFC', filename)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ict_document_chunks WHERE filename = ?", (clean_filename,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to delete single ICT document {filename}: {e}")
        return False

def delete_all_ict_documents():
    """
    지식 DB 전체 포맷
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ict_document_chunks")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to clear ICT DB: {e}")
        return False
