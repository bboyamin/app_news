import os
import sqlite3
import re

# 📂 로컬 SQLite 데이터베이스 파일 저장 경로
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../chroma_db"))
os.makedirs(DB_PATH, exist_ok=True)
DB_FILE = os.path.join(DB_PATH, "rag_documents.db")

def init_db():
    """
    RAG용 SQLite 데이터베이스 테이블을 1회 초기화합니다.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            chunk_index INTEGER,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

# 임포트 시점 초기화 실행
init_db()

def split_text(text, chunk_size=800, overlap=150):
    """
    문서의 맥락이 깨지지 않도록 슬라이딩 윈도우 방식으로 텍스트를 쪼갭니다.
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

def index_document(filename, text):
    """
    추출된 본문 텍스트를 문맥 조각(Chunk)으로 쪼개고 SQLite 테이블에 적재합니다.
    중복 등록을 방지하기 위해 기존 해당 파일명의 조각들은 1차 제거합니다.
    """
    chunks = split_text(text)
    if not chunks:
        return 0
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. 중복 제거
    cursor.execute("DELETE FROM document_chunks WHERE filename = ?", (filename,))
    
    # 2. 청크 적재
    for i, chunk in enumerate(chunks):
        cursor.execute(
            "INSERT INTO document_chunks (filename, chunk_index, content) VALUES (?, ?, ?)",
            (filename, i, chunk)
        )
        
    conn.commit()
    conn.close()
    return len(chunks)

def search_relevant_contexts(query, n_results=3):
    """
    자연어 질문(Query)에서 주요 형태소/키워드를 추출하고, 
    각 청크의 본문 텍스트 내 키워드 매칭 개수(빈도)를 스코어링하여 가장 유사한 Top-K 청크를 골라 반환합니다.
    """
    keywords = [w for w in re.split(r'[^a-zA-Z0-9가-힣]+', query) if len(w) > 1]
    if not keywords:
        keywords = [query] if query.strip() else []
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT filename, chunk_index, content FROM document_chunks")
    rows = cursor.fetchall()
    
    scored_chunks = []
    if keywords:
        for filename, chunk_index, content in rows:
            score = 0
            for kw in keywords:
                score += content.count(kw)
                
            if score > 0:
                scored_chunks.append((score, content, filename, chunk_index))
                
    if not scored_chunks and rows:
        rows.sort(key=lambda x: x[1])
        for filename, chunk_index, content in rows[:n_results]:
            scored_chunks.append((1, content, filename, chunk_index))
            
    conn.close()
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    contexts = []
    for score, content, filename, chunk_index in scored_chunks[:n_results]:
        contexts.append({
            "text": content,
            "filename": filename,
            "chunk_index": chunk_index
        })
        
    return contexts

def get_indexed_files():
    """
    현재 데이터베이스에 누적 기입되어 서비스 중인 파일명 목록을 조회합니다.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT filename FROM document_chunks")
    rows = cursor.fetchall()
    conn.close()
    return sorted([row[0] for row in rows])

def get_detailed_document_stats():
    """
    배포된 서버 DB에 저장된 파일별 조각 수, 총 글자 수, 미리보기 텍스트를 상세 조회합니다.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, COUNT(*), SUM(LENGTH(content)) FROM document_chunks GROUP BY filename")
    rows = cursor.fetchall()
    
    stats = []
    for filename, chunk_count, total_chars in rows:
        cursor.execute("SELECT content FROM document_chunks WHERE filename = ? AND chunk_index = 0", (filename,))
        first_chunk = cursor.fetchone()
        snippet = first_chunk[0][:80] + "..." if first_chunk else ""
        stats.append({
            "filename": filename,
            "chunk_count": chunk_count,
            "total_chars": total_chars,
            "snippet": snippet
        })
        
    conn.close()
    return stats

def get_all_chunks_raw():
    """
    DB에 적재된 모든 조각을 표 형태로 조회합니다.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, chunk_index, LENGTH(content), content FROM document_chunks ORDER BY filename, chunk_index")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_all_documents():
    """
    지식베이스 전체를 포맷합니다.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM document_chunks")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to clear SQLite DB: {e}")
        return False
