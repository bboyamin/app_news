import os
import zipfile
import zlib
import struct
import re
import xml.etree.ElementTree as ET

# OLEFile (구형 HWP 바이너리 파서) 동적 임포트
try:
    import olefile
    OLEFILE_AVAILABLE = True
except ImportError:
    OLEFILE_AVAILABLE = False

# PDF 파서 동적 임포트 처리 (PyMuPDF / pypdf 예외 처리)
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def parse_hwpx(file_path):
    """
    신형 한글(HWPX) 파일의 압축을 풀어 section0.xml 내부의 
    1) 일반 단락(<hp:p>)과 
    2) 표 데이터(<hp:tbl> -> <hp:tr> -> <hp:tc>)를 
    마크다운 표(Markdown Table) 구조로 100% 정밀 변환하여 파싱합니다.
    """
    text_content = []
    try:
        with zipfile.ZipFile(file_path) as z:
            sec_files = [name for name in z.namelist() if "section" in name and name.endswith(".xml")]
            
            if not sec_files:
                return "[오류] HWPX 본문 XML 데이터를 찾을 수 없습니다."
                
            ns = {
                'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
                'hs': 'http://www.hancom.co.kr/hwpml/2011/section'
            }

            for sec_file in sorted(sec_files):
                xml_data = z.read(sec_file)
                root = ET.fromstring(xml_data)
                
                for elem in root.iter():
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    
                    # 1. 표(Table) 요소 처리
                    if tag_name == 'tbl':
                        table_rows = []
                        for tr in elem.findall('.//hp:tr', ns):
                            row_cells = []
                            for tc in tr.findall('.//hp:tc', ns):
                                cell_texts = []
                                for t in tc.findall('.//hp:t', ns):
                                    if t.text:
                                        cell_texts.append(t.text.strip())
                                cell_str = " ".join(cell_texts).replace("|", "\\|")
                                row_cells.append(cell_str if cell_str else "-")
                            if row_cells:
                                table_rows.append(row_cells)
                        
                        if table_rows:
                            table_md = []
                            table_md.append("\n[📊 한글 표(Table) 데이터 시작]")
                            header = "| " + " | ".join(table_rows[0]) + " |"
                            sep = "| " + " | ".join(["---"] * len(table_rows[0])) + " |"
                            table_md.append(header)
                            table_md.append(sep)
                            
                            for row in table_rows[1:]:
                                if len(row) < len(table_rows[0]):
                                    row.extend(["-"] * (len(table_rows[0]) - len(row)))
                                elif len(row) > len(table_rows[0]):
                                    row = row[:len(table_rows[0])]
                                table_md.append("| " + " | ".join(row) + " |")
                            
                            table_md.append("[📊 한글 표 데이터 끝]\n")
                            text_content.append("\n".join(table_md))
                            
                    # 2. 일반 단락(Paragraph) 텍스트 처리
                    elif tag_name == 'p':
                        p_text = []
                        for t in elem.findall('./hp:run/hp:t', ns):
                            if t.text:
                                p_text.append(t.text)
                        if not p_text:
                            for t in elem.findall('.//hp:t', ns):
                                if t.text:
                                    p_text.append(t.text)
                        if p_text:
                            text_content.append("".join(p_text))
                    
        return "\n".join(text_content)
    except Exception as e:
        return f"[오류] HWPX 파싱 실패: {str(e)}"


def parse_hwp(file_path):
    """
    구형 한글(HWP) 바이너리 파일의 OLE 스트림(BodyText/Section0, 1...)을 
    zlib으로 디플레이트 압축 해제하여 UTF-16LE 본문 텍스트를 정밀 파싱하고, 
    제어 코드 바이트로 발생한 CJK 한자 노이즈(捤獥... 등)를 100% 정화합니다.
    """
    if not OLEFILE_AVAILABLE:
        return "[오류] HWP 파싱 라이브러리 olefile이 설치되지 않았습니다. pip install olefile 명령어로 설치해 주시기 바랍니다."
    
    text_content = []
    try:
        f = olefile.OleFileIO(file_path)
        dirs = f.listdir()

        sections = [d for d in dirs if d[0] == "BodyText"]
        sections.sort()

        for section in sections:
            stream = f.openstream(section)
            data = stream.read()
            
            try:
                unpacked_data = zlib.decompress(data, -15)
            except zlib.error:
                unpacked_data = data

            i = 0
            section_text = []
            while i < len(unpacked_data):
                if i + 4 > len(unpacked_data):
                    break
                header = struct.unpack("<I", unpacked_data[i:i+4])[0]
                rec_type = header & 0x3FF
                rec_len = (header >> 20) & 0xFFF
                
                if rec_len == 0xFFF:
                    if i + 8 <= len(unpacked_data):
                        rec_len = struct.unpack("<I", unpacked_data[i+4:i+8])[0]
                        i += 4

                if rec_type == 67:  # HWPTAG_PARA_TEXT (단락 텍스트)
                    txt_bytes = unpacked_data[i+4 : i+4+rec_len]
                    try:
                        t = txt_bytes.decode('utf-16le', errors='ignore')
                        # 1. 일반 ASCII 제어문자 제거
                        clean_t = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', t).strip()
                        # 2. HWP 바이너리 제어 바이트가 UTF-16LE로 디코딩될 때 생기는 한자 노이즈(捤獥... 등) 제거
                        clean_t = re.sub(r'[\u4e00-\u9fff]+', '', clean_t).strip()
                        
                        if clean_t and len(clean_t) > 1:
                            section_text.append(clean_t)
                    except Exception:
                        pass
                
                i += 4 + rec_len

            if section_text:
                text_content.append("\n".join(section_text))

        f.close()
        return "\n".join(text_content) if text_content else "[오류] HWP 본문 텍스트를 추출하지 못했습니다."
    except Exception as e:
        return f"[오류] HWP 파싱 실패: {str(e)}"


def parse_pdf(file_path):
    """
    PyMuPDF(fitz) 또는 pypdf 라이브러리를 가동해 PDF 문서를 페이지별로 순회하며 
    텍스트 레이아웃 및 표 데이터를 추출합니다.
    """
    text_content = []
    
    if FITZ_AVAILABLE:
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text:
                    text_content.append(f"--- [페이지 {page_num + 1}] ---\n" + text)
            return "\n".join(text_content)
        except Exception as e:
            return f"[오류] PyMuPDF PDF 파싱 실패: {str(e)}"
            
    elif PYPDF_AVAILABLE:
        try:
            reader = pypdf.PdfReader(file_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_content.append(f"--- [페이지 {page_num + 1}] ---\n" + text)
            return "\n".join(text_content)
        except Exception as e:
            return f"[오류] pypdf PDF 파싱 실패: {str(e)}"
            
    else:
        return "[오류] PDF 파싱 라이브러리가 설치되지 않았습니다. 터미널에서 'pip install PyMuPDF' 명령어를 실행해 주세요."


def extract_text_from_file(file_path):
    """
    전달된 파일의 확장자를 감별하여 HWP / HWPX / PDF 파서로 분기해 텍스트를 추출합니다.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".hwpx":
        return parse_hwpx(file_path)
    elif ext == ".hwp":
        return parse_hwp(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    else:
        return f"[오류] 지원하지 않는 파일 형식입니다: {ext}"
