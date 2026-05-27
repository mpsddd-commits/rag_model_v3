import os
import re
import pandas as pd
from pypdf import PdfReader
from utils.helpers import safe_print

def extract_and_chunk_pdf(pdf_path, chunk_size=600, chunk_overlap=150):
    """
    [하이브리드 시맨틱 분할]
    문장 구조를 무너뜨리지 않기 위해 마침표와 줄바꿈을 기준으로 먼저 쪼갠 뒤,
    의미적 덩어리를 유지하면서 글자 수 한도에 맞게 재귀적으로 결합하는 방식입니다.
    """
    safe_print(f"[PDF] '{pdf_path}' 하이브리드 시맨틱 청킹 시작...")
    reader = PdfReader(pdf_path)
    chunks_with_metadata = []
    file_name = os.path.basename(pdf_path)
    
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        text = page.extract_text()
        if not text or not text.strip():
            continue
            
        # 텍스트 노이즈 정제
        text = text.replace('\r\n', '\n').strip()
        
        # 규정 조항이나 서술형 문장 경계를 보존하기 위해 정규식으로 분할
        # 마침표, 물음표, 느낌표 뒤에 공백이나 줄바꿈이 오는 패턴을 문장 경계로 인식
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 문장 하나가 너무 긴 경우 예외 처리
            if len(sentence) > chunk_size:
                # 문장 내에서 강제 분할하되 기존 데이터 유실 방지
                if current_chunk:
                    chunks_with_metadata.append({
                        "content": current_chunk.strip(),
                        "source_file": file_name,
                        "source_type": "PDF",
                        "page_or_row": f"{page_num}페이지"
                    })
                    current_chunk = ""
                
                # 긴 문장을 sub-chunk 크기로 분할하여 강제 삽입
                sub_sentences = [sentence[i:i+chunk_size] for i in range(0, len(sentence), chunk_size - chunk_overlap)]
                for sub in sub_sentences:
                    chunks_with_metadata.append({
                        "content": sub.strip(),
                        "source_file": file_name,
                        "source_type": "PDF",
                        "page_or_row": f"{page_num}페이지"
                    })
                continue

            # 청크 결합 조건 체크
            if len(current_chunk) + len(sentence) + 1 > chunk_size:
                if current_chunk:
                    chunks_with_metadata.append({
                        "content": current_chunk.strip(),
                        "source_file": file_name,
                        "source_type": "PDF",
                        "page_or_row": f"{page_num}페이지"
                    })
                
                # Overlap 영역을 계산하여 문맥 연속성 유지
                overlap_start = max(0, len(current_chunk) - chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + " " + sentence
            else:
                current_chunk += (" " if current_chunk else "") + sentence
                
        # 페이지별 잔여 텍스트 마감
        if current_chunk.strip():
            chunks_with_metadata.append({
                "content": current_chunk.strip(),
                "source_file": file_name,
                "source_type": "PDF",
                "page_or_row": f"{page_num}페이지"
            })
            
    safe_print(f"[성공] PDF 하이브리드 분할 완료: 총 {len(chunks_with_metadata)} 개 청크.")
    return chunks_with_metadata


def extract_and_chunk_excel(excel_path):
    """
    [하이브리드 구조적 청킹]
    표 데이터의 행(Row)을 독립된 의미 개체로 취급하며, 
    공급망 정보나 지표 데이터의 탐색력을 강화하기 위해 [키: 값] 형태의 마크다운 느낌으로 변환합니다.
    """
    safe_print(f"[엑셀] '{excel_path}' 구조적 하이브리드 청킹 시작...")
    file_name = os.path.basename(excel_path)
    
    # 모든 컬럼을 텍스트화하여 결측치 처리 효율화
    df = pd.read_excel(excel_path, engine='openpyxl')
    df = df.fillna("")
    
    chunks_with_metadata = []
    for index, row in df.iterrows():
        row_text_list = []
        for col in df.columns:
            val = str(row[col]).strip()
            if val:
                # 컬럼 헤더와 셀 값을 일치시켜 정보 검색 매칭력 최적화
                row_text_list.append(f"[{col}]: {val}")
        
        if not row_text_list:
            continue
            
        # 의미론적 완결성을 가진 문장 형태로 조립
        chunk_text = " | ".join(row_text_list)
        full_chunk = f"설명: 해당 데이터는 {file_name}의 정보 항목입니다. 세부 내용 -> {chunk_text}"
        
        chunks_with_metadata.append({
            "content": full_chunk,
            "source_file": file_name,
            "source_type": "Excel",
            "page_or_row": f"{index + 1}번째 행"
        })
        
    safe_print(f"[성공] 엑셀 구조화 분할 완료: 총 {len(chunks_with_metadata)} 개 레코드 추출.")
    return chunks_with_metadata
