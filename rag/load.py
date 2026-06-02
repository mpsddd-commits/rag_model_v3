"""
ESG Data Loading Pipeline Module (load.py)
- MariaDB Excel Master Data Ingestion
- PostgreSQL pgvector PDF Chunking & Vector Ingestion
- Hugging Face Dataset Remote Backup
"""
import os
import re
import json
import datetime
import hashlib
import glob
import time
import numpy as np
import pandas as pd
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from datasets import Dataset  
from langchain_text_splitters import RecursiveCharacterTextSplitter
from psycopg2.extras import execute_values

import db_client as db
from settings import settings, safe_print, simple_tokenizer

# ======================================================================
# 0. PDF 텍스트 추출 및 슬라이딩 윈도우 청킹 (langchain splitter + 메타데이터 적용)
# ======================================================================
def extract_and_chunk_pdf(pdf_path: str, chunk_size: int = 1200, chunk_overlap: int = 300) -> list:
    """
    langchain-text-splitters를 활용하여 문맥(마침표, 줄바꿈)이 끊기지 않도록 가드레일을 치고,
    각 청크마다 [파일명 / Page 번호] 메타데이터를 본문에 주입하여 청킹을 수행합니다.
    """
    chunks = []
    file_name = os.path.basename(pdf_path)
    
    try:
        reader = PdfReader(pdf_path)
        
        # 1. 문장 단위 가드레일 분할기 정의
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,        # 1200자
            chunk_overlap=chunk_overlap,  # 300자
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""] # 줄바꿈과 마침표를 우선순위로 조절
        )
        
        # 2. 누락 방지 및 페이지별 트래킹을 위해 페이지 단위 루프 실행
        for idx, page in enumerate(reader.pages):
            page_no = idx + 1 # 1페이지부터 시작하도록 보정
            page_text = page.extract_text()
            
            if not page_text or not page_text.strip():
                continue # 스캔된 이미지 등으로 인해 텍스트가 없는 페이지 가드 스킵
            
            # 3. 해당 페이지의 텍스트를 슬라이딩 윈도우로 분할
            page_chunks = text_splitter.split_text(page_text)
            
            # 4. 분할된 각 청크에 출처 메타데이터 바인딩 및 정제
            for i, chunk_slice in enumerate(page_chunks):
                if not chunk_slice.strip():
                    continue
                
                # 연속된 줄바꿈 및 불필요한 공백 제거
                clean_slice = " ".join(chunk_slice.split())
                
                # LLM(Gemma)이 출처를 완벽히 인지하도록 텍스트 헤더에 메타데이터 강제 주입
                formatted_content = f"[{file_name} / Page {page_no}] {clean_slice}"
                
                # 고유 식별 해시값 생성 (페이지 정보와 인덱스를 결합하여 고유성 보장)
                chunk_id = hashlib.md5(f"{file_name}_P{page_no}_I{i}_{clean_slice[:20]}".encode()).hexdigest()
                
                chunks.append({
                    "chunk_id": chunk_id,
                    "file_name": file_name,
                    "content": formatted_content, # 메타데이터가 접두사로 붙은 텍스트
                    "doc_type": "PDF",
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
        safe_print(f"[정밀 청킹 완료] 파일명: {file_name} -> 생성된 총 청크 수: {len(chunks)}개")
                
    except Exception as e:
        safe_print(f"[오류] PDF 정밀 파싱 실패 ({file_name}): {e}")
        
    return chunks
# # ════════════════════════════════════════════════════════
# # 0. PDF 텍스트 추출 및 슬라이딩 윈도우 청킹 (누락 방지 추가)
# # ════════════════════════════════════════════════════════
# def extract_and_chunk_pdf(pdf_path: str, chunk_size: int = 1200, chunk_overlap: int = 300) -> list:
#     """150자 오버랩 연결 결합 세팅이 추가된 슬라이딩 윈도우 청킹 함수 (버그 수정 버전)"""
#     chunks = []
#     file_name = os.path.basename(pdf_path)
#     try:
#         reader = PdfReader(pdf_path)
#         full_text = "".join([page.extract_text() or "" for page in reader.pages])
        
#         # 텍스트가 정상적으로 추출되었는지 가드레일 확인
#         if not full_text.strip():
#             safe_print(f"[경고] PDF 파일에서 텍스트를 추출할 수 없습니다. (스캔된 이미지 또는 보안 설정 확인 필요): {file_name}")
#             return chunks

#         # 연속된 공백 및 줄바꿈을 단일 공백으로 정제
#         full_text = re.sub(r'\s+', ' ', full_text).strip()
        
#         # 500자 크기로 슬라이싱하되, 오버랩을 차감한 크기만큼 전진 (500 - 150 = 350자씩 이동)
#         step = chunk_size - chunk_overlap
#         if step <= 0: 
#             step = chunk_size  # 예외 방지 가드레일

#         # 루프 내부의 조기 break 제거 후 순수하게 range 제어권에 맡김
#         for i in range(0, len(full_text), step):
#             text_slice = full_text[i:i+chunk_size]
            
#             # 마지막 남은 자투리 텍스트가 너무 짧은 경우(예: 10자 미만) 무의미하므로 스킵 방지용 가드
#             if not text_slice.strip():
#                 continue
                
#             # 고유 식별을 위한 해시값 생성
#             chunk_id = hashlib.md5(f"{file_name}_{i}_{text_slice[:20]}".encode()).hexdigest()
#             chunks.append({
#                 "chunk_id": chunk_id,
#                 "file_name": file_name,
#                 "content": text_slice,
#                 "doc_type": "PDF",
#                 "timestamp": datetime.datetime.now().isoformat()
#             })
            
#         safe_print(f"[청킹 완료] 파일명: {file_name} -> 생성된 총 청크 수: {len(chunks)}개")
                
#     except Exception as e:
#         safe_print(f"[오류] PDF 파싱 실패 ({file_name}): {e}")
#     return chunks


# ════════════════════════════════════════════════════════
# 1. 마리아 DB 엑셀 적재 및 온톨로지 빌드 영역
# ════════════════════════════════════════════════════════
def parse_complex_criteria(question_text: str) -> dict:
    """
    [개선된 버전] 불필요한 제품명/규격번호 숫자를 필터링하고 
    물결표(~) 구조를 인식하여 정교한 RANGE 및 NUMERIC 마스터 기준값을 추출합니다.
    """
    result = {
        "criteria_type": "BOOL",
        "operator": "== Y",
        "threshold_value": None,
        "min_value": None,
        "max_value": None
    }
    
    if not question_text:
        return result

    # 1. 전처리 가드레일: 의도치 않은 메타 숫자(4자리 제품명, ASTM 규격 번호 등)를 임시 제거
    # 예: Al 3003 -> Al , ASTM B209 -> ASTM B 로 변경하여 수치 인식 방지
    clean_text = re.sub(r"\b\d{4}\b", "", question_text)  # 4자리 숫자(3003 등) 제거
    clean_text = re.sub(r"B\d+", "B", clean_text)         # B209 등 규격명 뒤의 숫자 제거

    # 2. 범위형 분석 (문장에 '범위 내'가 있거나 숫자~숫자 구조가 명시적인 경우)
    # 정규식으로 [숫자][공백이나 물결][숫자] 형태를 직접 타겟팅 (예: 1.00~1.50)
    range_match = re.search(r"(\d+\.\d+|\d+)\s*[~-]\s*(\d+\.\d+|\d+)", clean_text)
    
    if "범위 내" in question_text or range_match:
        if range_match:
            result["criteria_type"] = "RANGE"
            result["min_value"] = float(range_match.group(1))
            result["max_value"] = float(range_match.group(2))
            result["operator"] = "BETWEEN"
            return result
        else:
            # 물결표는 없지만 '범위 내' 키워드가 있는 경우 폴백 처리
            nums = re.findall(r"\d+\.\d+|\d+", clean_text)
            if len(nums) >= 2:
                result["criteria_type"] = "RANGE"
                result["min_value"] = float(nums[0])
                result["max_value"] = float(nums[1])
                result["operator"] = "BETWEEN"
                return result

    # 3. 단일 수치 비교형 분석 ('이하', '미만', '초과', '이상')
    nums = re.findall(r"\d+\.\d+|\d+", clean_text)
    
    if "Zero" in question_text or "zero" in question_text or "0건" in question_text:
        result["criteria_type"] = "NUMERIC"
        result["operator"] = "<="
        result["threshold_value"] = 0.0
        return result

    if nums:
        val = float(nums[0])
        if "이하" in question_text:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = "<="
            result["threshold_value"] = val
        elif "미만" in question_text:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = "<"
            result["threshold_value"] = val
        elif "초과" in question_text:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">"
            result["threshold_value"] = val
        elif "이상" in question_text or "충족" in question_text:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">="
            result["threshold_value"] = val

    # 4. 상태 확인형 불리언 가드
    if "않습니까" in question_text:
        result["operator"] = "== N"
        
    return result

def load_self_assess_checklist_to_mariadb(excel_dir: str):
    """엑셀의 각 시트(탭) 이름을 기반으로 마스터 데이터를 SELF_ASSESS_CHECKLIST 테이블에 적재합니다."""
    db.save("SET FOREIGN_KEY_CHECKS = 0;")
    db.save("TRUNCATE TABLE SELF_ASSESS_CHECKLIST;")
    db.save("SET FOREIGN_KEY_CHECKS = 1;")
    
    checklist_rows = []
    for pattern in ("*.xlsx", "*.xls"):
        for excel_path in glob.glob(os.path.join(excel_dir, pattern)):
            try:
                xl_dict = pd.read_excel(excel_path, sheet_name=None, header=0)
                for sheet_name, df in xl_dict.items():
                    sheet_name_clean = sheet_name.strip()
                    match = re.search(r"^(\d+차\s*협력사|\d+차-[A-Z])", sheet_name_clean)
                    partner_type = match.group(1).strip() if match else sheet_name_clean[:10]
                    
                    safe_print(f"[파싱 진행] 시트명: '{sheet_name}' -> 확정 partner_type: '{partner_type}'")
                    
                    for idx, row in df.iterrows():
                        row_vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                        if len(row_vals) >= 3:
                            indicator_no_raw = row_vals[0]
                            if not indicator_no_raw.replace('.0', '').isdigit():
                                continue
                            
                            checklist_rows.append((
                                partner_type, int(indicator_no_raw), 
                                row_vals[1] if len(row_vals) > 1 else "공통",
                                row_vals[2] if len(row_vals) > 2 else "미지정 지표",
                                row_vals[3] if len(row_vals) > 3 else "Normal",
                                row_vals[4] if len(row_vals) > 4 else "N",
                                row_vals[5] if len(row_vals) > 5 else "",
                                row_vals[6] if len(row_vals) > 6 else "",
                                row_vals[7] if len(row_vals) > 7 else "",
                                row_vals[8] if len(row_vals) > 8 else "중",
                                row_vals[9] if len(row_vals) > 9 else "N",
                                row_vals[10] if len(row_vals) > 10 else "",
                                row_vals[11] if len(row_vals) > 11 else "즉시 시정조치 가이드라인 가동",
                                0
                            ))
            except Exception as e:
                safe_print(f"[오류] '{os.path.basename(excel_path)}' 처리 중 크리티컬 예외 발생: {e}")
                
    if checklist_rows:
        sql = """
            INSERT INTO SELF_ASSESS_CHECKLIST (
                partner_type, indicator_no, category, indicator_name, priority, 
                star_yn, question, pass_answer, fail_answer, risk_level, 
                evidence_yn, evidence_list, action_plan, delete_yn
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.save_many(sql, checklist_rows)
        safe_print(f"\n[MariaDB 성공] 시트별 등급 분기 적용 완료 -> 총 {len(checklist_rows)}개 핵심 지표 마스터 적재 완료.")


def load_risk_criteria_to_mariadb(excel_dir: str):
    """'자가진단_리스크_분류_기준.xlsx' 파일을 읽어 ESG_RISK_CRITERIA 테이블에 전수 적재합니다."""
    db.save("SET FOREIGN_KEY_CHECKS = 0;")
    db.save("TRUNCATE TABLE ESG_RISK_CRITERIA;")
    db.save("SET FOREIGN_KEY_CHECKS = 1;")
    
    risk_criteria_rows = []
    seen_items = set()
    
    for pattern in ("*리스크*분류*.xlsx", "*리스크*분류*.xls", "자가진단_리스크_분류_기준.xlsx"):
        for excel_path in glob.glob(os.path.join(excel_dir, pattern)):
            try:
                xl_dict = pd.read_excel(excel_path, sheet_name=None, header=1)
                for sheet_name, df in xl_dict.items():
                    safe_print(f"[리스크 분류 파싱] 파일: {os.path.basename(excel_path)} / 시트명: '{sheet_name}'")
                    for idx, row in df.iterrows():
                        row_vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                        if len(row_vals) >= 4:
                            item_name, high_risk, medium_risk, low_risk = row_vals[0], row_vals[1], row_vals[2], row_vals[3]
                            if not item_name or item_name == "항목" or "기준 추천" in item_name:
                                continue
                            if item_name not in seen_items:
                                risk_criteria_rows.append((item_name, high_risk, medium_risk, low_risk))
                                seen_items.add(item_name)
            except Exception as e:
                safe_print(f"[오류] '{os.path.basename(excel_path)}' 리스크 기준 파싱 중 크리티컬 예외 발생: {e}")

    if risk_criteria_rows:
        sql_risk = """
            INSERT INTO ESG_RISK_CRITERIA (item_name, high_risk, medium_risk, low_risk) VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE high_risk = VALUES(high_risk), medium_risk = VALUES(medium_risk), low_risk = VALUES(low_risk);
        """
        db.save_many(sql_risk, risk_criteria_rows)
        safe_print(f"[MariaDB 성공] ESG_RISK_CRITERIA 테이블에 총 {len(risk_criteria_rows)}건의 마스터 기준 적재 완료.")


def build_ontology_registry():
    """MariaDB 데이터를 기반으로 복합 온톨로지 사전을 동기화 구축하고 engine.py의 캐시 레이어를 직접 갱신합니다."""
    import engine  # 💡 중요: 순환 참조를 피하기 위해 함수 내부 임포트 수행 및 engine 상태 직접 조작
    
    engine._ONTOLOGY_REGISTRY.clear()
    engine._ONTOLOGY_TEMPLATE_LIST.clear()
    
    sql = "SELECT indicator_no, indicator_name, question, action_plan FROM SELF_ASSESS_CHECKLIST"
    rows = db.find_all(sql)
    
    for row in rows:
        ind_name = row["indicator_name"]
        raw_question = row["question"]
        criteria_meta = parse_complex_criteria(raw_question)
        
        # engine.py 전역 딕셔너리와 리스트에 상태 직접 투영
        engine._ONTOLOGY_REGISTRY[ind_name] = {
            "indicator_no": row["indicator_no"],
            "action_plan": row.get("action_plan", "즉시 시정 조치 가동"),
            "raw_text": raw_question,
            **criteria_meta
        }
        engine._ONTOLOGY_TEMPLATE_LIST.append({
            "indicator_no": row["indicator_no"],
            "indicator_name": ind_name,
            "raw_expression": raw_question,
            "meta": criteria_meta
        })
    safe_print(f"[온톨로지 엔지니어링] {len(engine._ONTOLOGY_REGISTRY)}개의 지표 온톨로지 복합 분기 규칙 동기화 완료.")


def export_ontology_to_jsonl(output_filename: str = "esg_ontology_template.jsonl"):
    """구축된 온톨로지 리스트를 파인튜닝 지식 데이터 백업용 JSONL 파일로 출력합니다."""
    import engine
    if not engine._ONTOLOGY_TEMPLATE_LIST: return
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            for item in engine._ONTOLOGY_TEMPLATE_LIST:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        safe_print(f"[온톨로지 백업] AI 파인튜닝 포맷 이관 완료: {output_filename}")
    except Exception as e:
        safe_print(f"[온톨로지 백업 실패] : {e}")


# ════════════════════════════════════════════════════════
# 2. pgvector (PostgreSQL) 벡터 적재 및 허깅페이스 이관 영역
# ════════════════════════════════════════════════════════
def init_and_save_to_pgvector_auto_ontology(chunks: list, pg_table: str = "ESG_PDF_VECTORS"):
    """
    MariaDB 마스터 지표와 코사인 유사도가 0.5 이상인 청크만 선별하여 pgvector에 적재합니다.
    중복 및 유사도 미달로 제외된 청크들의 상세 내역을 수집하여 하단에 상세 분석 리포트를 출력합니다.
    """
    from engine import ollama_client  # 💡 engine에 싱글톤으로 선언된 클라이언트 공유 참조
    
    conn = db.get_postgres_conn()
    if not conn: 
        return
    
    try:
        # [단계 1] 마리아DB 마스터 지표 텍스트 및 임베딩 로드
        sql = "SELECT question FROM SELF_ASSESS_CHECKLIST WHERE question IS NOT NULL AND question != ''"
        master_rows = db.find_all(sql)
        
        master_vectors = []
        for row in master_rows:
            try:
                resp = ollama_client.embeddings(model=settings.embed_model, prompt=row["question"])
                vec = np.array(resp["embedding"])
                norm = np.linalg.norm(vec)
                if norm > 0: 
                    master_vectors.append((row["question"], vec, norm)) # 문항 텍스트도 함께 보관
            except Exception:
                continue

        with conn, conn.cursor() as cur:
            # [단계 2] PostgreSQL pgvector 테이블 구성 및 확장 기능 체크
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {pg_table} (
                    id SERIAL PRIMARY KEY, chunk_id TEXT UNIQUE, file_name TEXT,
                    content TEXT, embedding vector(1024), timestamp TEXT
                );
            """)
            
            data_to_insert = []
            total_chunks = len(chunks)
            start_time = time.time()
            
            # 🌟 제외 대상 트래킹을 위한 특수 저장소 레이어
            excluded_by_duplicate = []
            excluded_by_similarity = []
            
            safe_print(f"\n[자동 온톨로지 매칭] 총 {total_chunks}개 청크 검증 가동 (마스터 기준 문항 수: {len(master_vectors)}개)")

            for idx, chunk in enumerate(chunks, 1):
                try:
                    # 실시간 모니터링 주기용 출력
                    if idx % 20 == 0 or idx == total_chunks:
                        elapsed = time.time() - start_time
                        safe_print(f" -> 유사도 분석 및 임베딩 연산 중... [{idx}/{total_chunks}] ({idx/total_chunks*100:.1f}%) | 경과시간: {elapsed:.1f}초")
                    
                    cid = chunk["chunk_id"]
                    c_text = chunk["content"]
                    f_name = chunk["file_name"]
                    
                    # 🛡️ 1) 데이터베이스 내부 중복 체크 가드레일 (1차 제외 원인)
                    sql_check = f"SELECT 1 FROM {pg_table} WHERE chunk_id = %s LIMIT 1"
                    cur.execute(sql_check, (cid,))
                    if cur.fetchone():
                        # 줄바꿈 정제 후 중복 리스트에 바인딩
                        clean_text = " ".join(c_text.split())
                        excluded_by_duplicate.append(f"[{f_name}] {clean_text[:50]}...")
                        continue
                        
                    # 2) Ollama 기반 청크 데이터 벡터 변환
                    resp = ollama_client.embeddings(model=settings.embed_model, prompt=c_text)
                    curr_vec = np.array(resp["embedding"])
                    curr_norm = np.linalg.norm(curr_vec)
                    if curr_norm == 0: 
                        continue
                        
                    # 📉 3) 코사인 유사도 분석 가드레일 (2차 제외 원인)
                    is_valid_chunk = False if master_vectors else True
                    max_similarity = -1.0
                    
                    for q_text, ref_vec, ref_norm in master_vectors:
                        similarity = np.dot(ref_vec, curr_vec) / (ref_norm * curr_norm)
                        if similarity > max_similarity:
                            max_similarity = similarity
                        
                        if similarity >= 0.55:
                            is_valid_chunk = True
                            # 조기 종료(Break) 처리하지 않고, 최고 유사도를 기록하기 위해 마저 순회할 수도 있으나, 
                            # 속도를 위해 합격선 도달 시 루프를 탈출하도록 유지하되 최고 점수만 기록 보정
                            break
                    
                    if is_valid_chunk:
                        data_to_insert.append((cid, f_name, c_text, resp["embedding"], chunk["timestamp"]))
                    else:
                        # 기준 미달로 탈락한 청크 데이터의 세부 수치 바인딩
                        clean_text = " ".join(c_text.split())
                        excluded_by_similarity.append({
                            "file_name": f_name,
                            "score": max_similarity,
                            "text": clean_text[:60]
                        })
                        
                except Exception as ce:
                    safe_print(f"\n[경고] {idx}번째 청크 처리 예외 스킵: {ce}")
                    continue
            
            # ════════════════════════════════════════════════════════
            # 📊 [추가된 레이어] 제외된 청크 원인 규명 상세 분석 리포트 출력
            # ════════════════════════════════════════════════════════
            total_excluded = len(excluded_by_duplicate) + len(excluded_by_similarity)
            if total_excluded > 0:
                safe_print("\n" + "="*75)
                safe_print(f"🔍 [제외된 청크 상세 리포트 - 총 {total_excluded}개 청크 진단 완료]")
                safe_print("="*75)
                
                # 원인 1 출력 (중복)
                safe_print(f"1️⃣ [기존 데이터베이스 중복 가드레일 필터링] 총 {len(excluded_by_duplicate)}개")
                if excluded_by_duplicate:
                    for row in excluded_by_duplicate[:5]: # 너무 많으면 화면을 덮으므로 상위 5개 샘플링 출력
                        safe_print(f"  - {row}")
                    if len(excluded_by_duplicate) > 5:
                        safe_print(f"  ...외 {len(excluded_by_duplicate) - 5}개 청크 중복으로 적재 제외됨")
                else:
                    safe_print("  - 해당 사항 없음")
                
                # 원인 2 출력 (유사도 미달)
                safe_print(f"\n2️⃣ [ESG 마스터 지표 유사도 기준치 미달 ( < 0.55 ) 필터 탈락] 총 {len(excluded_by_similarity)}개")
                if excluded_by_similarity:
                    # 탈락 청크 중 아까운 순서(유사도 점수가 높았던 순서)로 정렬하여 상위 10개 출력
                    excluded_by_similarity.sort(key=lambda x: x["score"], reverse=True)
                    for row in excluded_by_similarity[:10]:
                        safe_print(f"  - [{row['file_name']}] (최고 유사도: {row['score']:.4f}) {row['text']}...")
                    if len(excluded_by_similarity) > 10:
                        safe_print(f"  ...외 {len(excluded_by_similarity) - 10}개 데이터 ESG 무관 텍스트(노이즈) 가드로 차단 처리")
                else:
                    safe_print("  - 해당 사항 없음")
                safe_print("="*75 + "\n")

            # [단계 4] 최종 필터 통과 데이터가 존재할 경우 벌크 인서트(execute_values) 단일 트랜잭션 수행
            if data_to_insert:
                safe_print(f"[PostgreSQL] 필터 통과한 {len(data_to_insert)}개 신규 청크 적재 (제외: {total_excluded}개)")
                execute_values(cur, f"""
                    INSERT INTO {pg_table} (chunk_id, file_name, content, embedding, timestamp)
                    VALUES %s ON CONFLICT (chunk_id) DO NOTHING;
                """, data_to_insert)
                conn.commit()
                safe_print(f"[PostgreSQL] pgvector 추가 적재 완료! (최종 소요시간: {time.time() - start_time:.1f}초)\n")
            else:
                safe_print(f"[PostgreSQL 알림] 기준(0.6) 만족 신규 청크 없음. (최종 소요시간: {time.time() - start_time:.1f}초)\n")
                
    except Exception as e:
        safe_print(f"[PostgreSQL 오류] 파이프라인 처리 실패: {e}")

# def init_and_save_to_pgvector_auto_ontology(chunks: list):
#     """MariaDB 마스터 지표와 코사인 유사도가 0.5 이상인 청크만 선별하여 pgvector에 적재합니다."""
#     from engine import ollama_client  # 💡 engine에 싱글톤으로 선언된 클라이언트 공유 참조
    
#     conn = db.get_postgres_conn()
#     if not conn: return
    
#     try:
#         sql = "SELECT question FROM SELF_ASSESS_CHECKLIST WHERE question IS NOT NULL AND question != ''"
#         master_rows = db.find_all(sql)
        
#         master_vectors = []
#         for row in master_rows:
#             try:
#                 resp = ollama_client.embeddings(model=settings.embed_model, prompt=row["question"])
#                 vec = np.array(resp["embedding"])
#                 norm = np.linalg.norm(vec)
#                 if norm > 0: master_vectors.append((vec, norm))
#             except Exception:
#                 continue

#         with conn, conn.cursor() as cur:
#             cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
#             cur.execute("""
#                 CREATE TABLE IF NOT EXISTS ESG_PDF_VECTORS (
#                     id SERIAL PRIMARY KEY, chunk_id TEXT UNIQUE, file_name TEXT,
#                     content TEXT, embedding vector(1024), timestamp TEXT
#                 );
#             """)
            
#             data_to_insert = []
#             filtered_out_count = 0
#             total_chunks = len(chunks)
#             start_time = time.time()
            
#             safe_print(f"\n[자동 온톨로지 매칭] 총 {total_chunks}개 청크 유사도 검증 가동 (기준 수: {len(master_vectors)}개)")

#             for idx, chunk in enumerate(chunks, 1):
#                 try:
#                     if idx % 20 == 0 or idx == total_chunks:
#                         elapsed = time.time() - start_time
#                         safe_print(f" -> 유사도 분석 및 임베딩 연산 중... [{idx}/{total_chunks}] ({idx/total_chunks*100:.1f}%) | 경과시간: {elapsed:.1f}초")
                        
#                     resp = ollama_client.embeddings(model=settings.embed_model, prompt=chunk["content"])
#                     curr_vec = np.array(resp["embedding"])
#                     curr_norm = np.linalg.norm(curr_vec)
#                     if curr_norm == 0: continue
                        
#                     is_valid_chunk = False if master_vectors else True
#                     for ref_vec, ref_norm in master_vectors:
#                         similarity = np.dot(ref_vec, curr_vec) / (ref_norm * curr_norm)
#                         if similarity >= 0.5:
#                             is_valid_chunk = True
#                             break
                    
#                     if is_valid_chunk:
#                         data_to_insert.append((chunk["chunk_id"], chunk["file_name"], chunk["content"], resp["embedding"], chunk["timestamp"]))
#                     else:
#                         filtered_out_count += 1
#                 except Exception as ce:
#                     safe_print(f"\n[경고] {idx}번째 청크 처리 예외 스킵: {ce}")
#                     continue
            
#             if data_to_insert:
#                 safe_print(f"[PostgreSQL] 필터 통과한 {len(data_to_insert)}개 신규 청크 적재 (제외: {filtered_out_count}개)")
#                 execute_values(cur, """
#                     INSERT INTO ESG_PDF_VECTORS (chunk_id, file_name, content, embedding, timestamp)
#                     VALUES %s ON CONFLICT (chunk_id) DO NOTHING;
#                 """, data_to_insert)
#                 conn.commit()
#                 safe_print(f"[PostgreSQL] pgvector 추가 적재 완료! (최종 소요시간: {time.time() - start_time:.1f}초)\n")
#             else:
#                 safe_print(f"[PostgreSQL 알림] 기준(0.5) 만족 신규 청크 없음. (최종 소요시간: {time.time() - start_time:.1f}초)\n")
#     except Exception as e:
#         safe_print(f"[PostgreSQL 오류] 파이프라인 처리 실패: {e}")


def export_pgvector_to_hf(repo_id: str):
    """PostgreSQL pgvector 테이블 전체를 원격 Hugging Face Hub 데이터셋으로 밀어 올려 백업합니다."""
    conn = db.get_postgres_conn()
    if not conn: return
    safe_print(f"[HuggingFace 백업] '{repo_id}' 허브 데이터셋 업로드 가동...")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT chunk_id, file_name, content, embedding, timestamp FROM ESG_PDF_VECTORS;")
            rows = cur.fetchall()
            
        if not rows:
            safe_print("[HuggingFace 백업 경고] 업로드할 원천 DB 데이터가 존재하지 않습니다.")
            return
            
        df = pd.DataFrame(rows, columns=["chunk_id", "file_name", "content", "embedding", "timestamp"])
        dataset = Dataset.from_pandas(df)
        dataset.push_to_hub(repo_id, private=False)
        safe_print(f"[HuggingFace 성공] 원격 업로드 완료 -> {repo_id}")
    except Exception as e:
        safe_print(f"[HuggingFace 오류] 원격 백업 실패: {e}")


# ════════════════════════════════════════════════════════
# 3. 통합 파이프라인 제어 진입점 (Orchestrator)
# ════════════════════════════════════════════════════════
def run_concurrent_ingestion_pipeline(pdf_dir: str, excel_dir: str, hf_repo: str = None):
    """Excel 마스터 데이터 및 PDF 임베딩 코사인 필터링, HF 클라우드 백업을 통합 수행하며 engine.py의 검색 구조를 갱신합니다."""
    import engine  # 💡 engine.py 전역 인덱스 갱신을 위해 상호 레이어 바인딩 진행
    
    safe_print("\n=== 🚀 [통합 파이프라인] 전처리 및 기준 기반 순차 적재 가동 ===")
    
    # [단계 1] 마리아 DB 마스터 초기화 및 온톨로지 캐시 구조 로컬 주입
    safe_print("[파이프라인 단계 1] MariaDB 마스터 테이블 구축 및 온톨로지 규칙 동기화...")
    load_self_assess_checklist_to_mariadb(excel_dir)
    load_risk_criteria_to_mariadb(excel_dir)
    build_ontology_registry()
    export_ontology_to_jsonl("esg_ontology_template.jsonl")
    
    # [단계 2] PDF 로드 및 마스터 매칭 기반 PostgreSQL pgvector 데이터 저장
    safe_print("[파이프라인 단계 2] PDF 가공 및 마스터 지표 기반 코사인 유사도(>=0.5) 적재 필터링 가동...")
    pdf_chunks = []
    for pdf_path in glob.glob(os.path.join(pdf_dir, "*.pdf")):
        pdf_chunks.extend(extract_and_chunk_pdf(pdf_path))
        
    if pdf_chunks:
        init_and_save_to_pgvector_auto_ontology(pdf_chunks)
        
        # 💡 [핵심 교정]: engine.py의 Retriever 상태 변수를 직접 덮어씌워 유실을 원천 차단합니다.
        engine.global_chunks_pool = pdf_chunks
        tokenized_corpus = [simple_tokenizer(c["content"]) for c in pdf_chunks]
        engine.bm25_index = BM25Okapi(tokenized_corpus)
        safe_print("[인메모리 동기화] 하이브리드 검색용 글로벌 인덱스(BM25Okapi) 실시간 결합 완료.")
        
    # [단계 3] 클라우드 백업용 허깅페이스 전송
    if hf_repo:
        safe_print("[파이프라인 단계 3] Hugging Face 벡터 데이터셋 원격 백업 트리거 가동...")
        export_pgvector_to_hf(repo_id=hf_repo)