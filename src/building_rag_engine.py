import os
import sqlite3
import re
import unicodedata

# 📂 건축 법규 & 건축신고 전용 지식 DB 경로 설정
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../chroma_db"))
os.makedirs(DB_PATH, exist_ok=True)
DB_FILE = os.path.join(DB_PATH, "building_agent_documents.db")

def init_building_db():
    """
    건축 법규/조례/기술기준 전용 SQLite DB 테이블 초기화
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS building_document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            chunk_index INTEGER,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

# 모듈 임포트 시 초기화
init_building_db()

def split_building_text(text, chunk_size=800, overlap=150):
    """
    건축법 조항, 피난방재기준, 지자체 건축조례의 수치 및 요건 규격이 잘리지 않도록
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

def index_building_document(filename, text):
    """
    건축 법규/조례/해설서 텍스트를 전수 쪼개어 지식 DB에 적재합니다.
    """
    clean_filename = unicodedata.normalize('NFC', filename)
    chunks = split_building_text(text)
    if not chunks:
        return 0
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 기존 동일 파일 데이터가 있다면 중복 방지를 위해 삭제 후 재적재
    cursor.execute("DELETE FROM building_document_chunks WHERE filename = ?", (clean_filename,))
    
    for idx, chunk in enumerate(chunks):
        cursor.execute("""
            INSERT INTO building_document_chunks (filename, chunk_index, content)
            VALUES (?, ?, ?)
        """, (clean_filename, idx, chunk))
        
    conn.commit()
    conn.close()
    return len(chunks)

def search_building_contexts(query, n_results=8):
    """
    키워드 및 서브 스트링 매칭 기반 건축 법규 조항 정밀 탐색
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 검색 키워드 정제
    query_clean = re.sub(r'[^\w\s]', ' ', query)
    keywords = [k for k in query_clean.split() if len(k) >= 2]
    
    if not keywords:
        cursor.execute("SELECT filename, chunk_index, content FROM building_document_chunks LIMIT ?", (n_results,))
        rows = cursor.fetchall()
    else:
        # 키워드별 LIKE 조건 조합
        like_clauses = " OR ".join(["content LIKE ?" for _ in keywords])
        sql = f"""
            SELECT filename, chunk_index, content,
                   ({" + ".join(["(CASE WHEN content LIKE ? THEN 1 ELSE 0 END)" for _ in keywords])}) as score
            FROM building_document_chunks
            WHERE {like_clauses}
            ORDER BY score DESC, id ASC
            LIMIT ?
        """
        
        params = [f"%{k}%" for k in keywords] * 2 + [n_results]
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "filename": r[0],
            "chunk_index": r[1],
            "text": r[2]
        })
    return results

def get_indexed_building_files():
    """
    현재 연동된 건축 법규/조례 파일 목록 반환
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT filename FROM building_document_chunks ORDER BY filename ASC")
    files = [row[0] for row in cursor.fetchall()]
    conn.close()
    return files

def get_building_document_stats():
    """
    건축 법규 문서별 청크 개수 및 통계 집계
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT filename, COUNT(*), SUM(LENGTH(content)), MIN(content)
        FROM building_document_chunks
        GROUP BY filename
        ORDER BY filename ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    stats = []
    for r in rows:
        preview = r[3][:60].replace("\n", " ") + "..." if r[3] else ""
        stats.append({
            "filename": r[0],
            "chunk_count": r[1],
            "total_chars": r[2],
            "preview": preview
        })
    return stats

def get_all_building_chunks():
    """
    전체 청크 열람
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, chunk_index, LENGTH(content), content FROM building_document_chunks ORDER BY filename, chunk_index")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_single_building_document(filename):
    """
    특정 단일 건축 문서 삭제
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM building_document_chunks WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()
    return True

def delete_all_building_documents():
    """
    전체 건축 법규 DB 초기화
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM building_document_chunks")
    conn.commit()
    conn.close()
    return True
