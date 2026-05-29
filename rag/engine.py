"""
Integrated ESG Hybrid Engine: Ingestion Pipeline, Hybrid Retriever, 
Ontology Rule Registry, and Hugging Face Dataset Exporter.
"""
import os
import re
import json
import datetime
import hashlib
import glob
import time
import ollama
import pandas as pd
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from psycopg2.extras import execute_values
from datasets import Dataset  # 🌟 허깅페이스 통합용 추가

import db_client as db
from settings import settings, safe_print, simple_tokenizer

# 싱글톤 인스턴스 전역 정의
os.environ["OLLAMA_HOST"] = settings.ollama_host
ollama_client = ollama.Client(host=settings.ollama_host)
reranker = CrossEncoder(settings.rerank_model)

# 인메모리 파이프라인 전역 상태 관리 객체
bm25_index = None
global_chunks_pool = []
_ONTOLOGY_REGISTRY: dict = {}
_ONTOLOGY_TEMPLATE_LIST: list = []


# ════════════════════════════════════════════════════════
# 🛠️ 온톨로지(Ontology) 전용 정규식 수치 분석 및 캐싱 로직
# ════════════════════════════════════════════════════════
def parse_numeric_criteria(text_criteria: str) -> tuple[float | None, str]:
    """줄글 형태의 마스터 기준 답변 예시에서 비교 연산자와 임계 수치를 정규식으로 안전하게 추출합니다."""
    if not text_criteria:
        return None, ">="
    nums = re.findall(r"\d+\.\d+|\d+", text_criteria)
    if not nums:
        return None, ">="
    value = float(nums[0])
    
    operator = ">="
    if "이하" in text_criteria or "미만" in text_criteria or "Zero" in text_criteria or "0.0" in text_criteria:
        operator = "<="
    elif "초과" in text_criteria:
        operator = ">"
    elif "미달" in text_criteria:
        operator = "<"
    return value, operator

def build_ontology_registry():
    """MariaDB의 최신 마스터 지표 데이터를 조회하여 메모리 내 온톨로지 사전을 완전히 동기화 구축합니다."""
    global _ONTOLOGY_REGISTRY, _ONTOLOGY_TEMPLATE_LIST
    _ONTOLOGY_REGISTRY.clear()
    _ONTOLOGY_TEMPLATE_LIST.clear()
    
    sql = "SELECT indicator_no, indicator_name, question, action_plan FROM SELF_ASSESS_CHECKLIST"
    rows = db.find_all(sql)
    
    for row in rows:
        ind_name = row["indicator_name"]
        raw_criteria = row["question"]
        val, op = parse_numeric_criteria(raw_criteria)
        
        # 1. 인메모리 딕셔너리 매핑 레이어 적재
        _ONTOLOGY_REGISTRY[ind_name] = {
            "indicator_no": row["indicator_no"],
            "action_plan": row.get("action_plan", "즉시 시정 조치 가동"),
            "threshold_value": val if val is not None else 0.0,
            "operator": op,
            "raw_text": raw_criteria
        }
        
        # 2. AI 학습용 및 아티팩트용 템플릿 리스트 생성
        _ONTOLOGY_TEMPLATE_LIST.append({
            "indicator_no": row["indicator_no"],
            "indicator_name": ind_name,
            "parsed_operator": op,
            "parsed_threshold": val if val is not None else 0.0,
            "raw_expression": raw_criteria
        })
        
    safe_print(f"[온톨로지 엔지니어링] 총 {len(_ONTOLOGY_REGISTRY)}개의 지표 온톨로지 규칙 캐싱 완료.")

def export_ontology_to_jsonl(output_filename: str = "esg_ontology_template.jsonl"):
    """구축된 온톨로지 리스트를 파인튜닝 지식 데이터 백업용 JSONL 파일로 출력합니다."""
    global _ONTOLOGY_TEMPLATE_LIST
    if not _ONTOLOGY_TEMPLATE_LIST:
        return
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            for item in _ONTOLOGY_TEMPLATE_LIST:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        safe_print(f"[온톨로지 백업] AI 파인튜닝 포맷 이관 완료: {output_filename}")
    except Exception as e:
        safe_print(f"[온톨로지 백업 실패] : {e}")


# ════════════════════════════════════════════════════════
# 🚀 Ingestion Pipeline (PDF pgvector + Excel MariaDB + HF 업로드 동시 처리)
# ════════════════════════════════════════════════════════
# 
def extract_and_chunk_pdf(pdf_path: str, chunk_size: int = 500, chunk_overlap: int = 150) -> list:
    """150자 오버랩 연결 결합 세팅이 추가된 슬라이딩 윈도우 청킹 함수"""
    chunks = []
    file_name = os.path.basename(pdf_path)
    try:
        reader = PdfReader(pdf_path)
        full_text = "".join([page.extract_text() or "" for page in reader.pages])
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        # 500자 크기로 슬라이싱하되, 다음 시작점은 350자(500 - 150) 뒤로 설정하여 150자가 중복 결합됨
        step = chunk_size - chunk_overlap
        if step <= 0: step = chunk_size  # 예외 방지 가드레일

        for i in range(0, len(full_text), step):
            text_slice = full_text[i:i+chunk_size]            
            # 고유 식별을 위한 해시값 생성
            chunk_id = hashlib.md5(f"{file_name}_{i}_{text_slice[:20]}".encode()).hexdigest()
            chunks.append({
                "chunk_id": chunk_id,
                "file_name": file_name,
                "content": text_slice,
                "doc_type": "PDF",
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            # 텍스트의 끝에 도달하면 루프 종료
            if i + chunk_size >= len(full_text):
                break
                
    except Exception as e:
        safe_print(f"[오류] PDF 파싱 실패 ({file_name}): {e}")
    return chunks

def init_and_save_to_pgvector(chunks: list):
    conn = db.get_postgres_conn()
    if not conn: return
    try:
        with conn, conn.cursor() as cur:
            # CREATE EXTENSION: PostgreSQL에서 기본적으로 제공하지 않는 특수한 기능(데이터 타입, 인덱스, 함수 등)을 추가할 때 사용하는 명령어
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ESG_PDF_VECTORS (
                    id SERIAL PRIMARY KEY,
                    chunk_id TEXT UNIQUE,
                    file_name TEXT,
                    content TEXT,
                    embedding vector(1024),
                    timestamp TEXT
                );
            """)
            
            data_to_insert = []
            for chunk in chunks:
                resp = ollama_client.embeddings(model=settings.embed_model, prompt=chunk["content"])
                data_to_insert.append((chunk["chunk_id"], chunk["file_name"], chunk["content"], resp["embedding"], chunk["timestamp"]))
            
            execute_values(cur, """
                INSERT INTO ESG_PDF_VECTORS (chunk_id, file_name, content, embedding, timestamp)
                VALUES %s ON CONFLICT (chunk_id) DO NOTHING;
            """, data_to_insert)
            conn.commit()
            safe_print(f"[PostgreSQL] {len(chunks)}개 PDF 벡터 스토어 동기화 완료.")
    except Exception as e:
        safe_print(f"[PostgreSQL 오류] pgvector 저장 실패: {e}")

def load_excel_to_mariadb(excel_dir: str):
    """
    엑셀의 각 시트(탭) 이름을 기반으로 partner_type을 동적으로 추출하여
    SELF_ASSESS_CHECKLIST 테이블에 마스터 데이터를 정합성 있게 적재합니다.
    
    [partner_type 변환 규칙]
    - '1차 협력사' -> '1차 협력사'
    - '2차 협력사 Hall제련' -> '2차 협력사'
    - '3차-A 채굴 (전체 3차 적용)' -> '3차-A'
    - '3차-B Bayer정련 (알루미나)' -> '3차-B'
    """
    # 1. 마스터 데이터 갱신을 위한 기존 테이블 초기화 및 외래키 체크 제어
    db.save("SET FOREIGN_KEY_CHECKS = 0;")
    db.save("TRUNCATE TABLE SELF_ASSESS_CHECKLIST;")
    db.save("SET FOREIGN_KEY_CHECKS = 1;")
    
    checklist_rows = []
    
    # 디렉토리 내 엑셀 파일 탐색
    for pattern in ("*.xlsx", "*.xls"):
        for excel_path in glob.glob(os.path.join(excel_dir, pattern)):
            try:
                # sheet_name=None 설정으로 모든 시트를 딕셔너리 형태로 호출
                # header=0 설정으로 최상단 제목 열(헤더)을 데이터 파싱에서 제외
                xl_dict = pd.read_excel(excel_path, sheet_name=None, header=0)
                
                for sheet_name, df in xl_dict.items():
                    # 시트 이름(탭 이름) 정제 로직 생성
                    sheet_name_clean = sheet_name.strip()
                    
                    # 정규식을 사용하여 '1차 협력사', '2차 협력사', '3차-A', '3차-B' 형태의 핵심 접두사 추출
                    match = re.search(r"^(\d+차\s*협력사|\d+차-[A-Z])", sheet_name_clean)
                    if match:
                        partner_type = match.group(1).strip()
                    else:
                        # 매칭 구조가 예외일 경우 공백 제거 후 10자까지만 폴백용으로 사용
                        partner_type = sheet_name_clean[:10]
                    
                    safe_print(f"[파싱 진행] 시트명: '{sheet_name}' -> 확정 partner_type: '{partner_type}'")
                    
                    for idx, row in df.iterrows():
                        # 결측치(NaN) 데이터를 빈 문자열('')로 안전 치환 후 텍스트 공백 제거
                        row_vals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                        
                        # 최소한 지표번호와 카테고리, 지표명이 존재할 수 있는 배열 길이인지 검증
                        if len(row_vals) >= 3:
                            indicator_no_raw = row_vals[0]
                            
                            # [안전 가드레일]: 지표번호 위치에 'No.', '항목' 등 문자열 헤더 유입 시 적재 건너뛰기
                            if not indicator_no_raw.isdigit():
                                continue
                            
                            # DDL 구조 및 제공된 데이터프레임 구조에 따른 1:1 변수 매핑
                            indicator_no   = int(indicator_no_raw) # 정수 변환
                            category       = row_vals[1] if len(row_vals) > 1 else "공통"
                            indicator_name = row_vals[2] if len(row_vals) > 2 else "미지정 지표"
                            priority       = row_vals[3] if len(row_vals) > 3 else "Normal"
                            star_yn        = row_vals[4] if len(row_vals) > 4 else "N"
                            question       = row_vals[5] if len(row_vals) > 5 else ""
                            pass_answer    = row_vals[6] if len(row_vals) > 6 else ""
                            fail_answer    = row_vals[7] if len(row_vals) > 7 else ""
                            risk_level     = row_vals[8] if len(row_vals) > 8 else "중"
                            evidence_yn    = row_vals[9] if len(row_vals) > 9 else "N"
                            evidence_list  = row_vals[10] if len(row_vals) > 10 else ""
                            action_plan    = row_vals[11] if len(row_vals) > 11 else "즉시 시정조치 가이드라인 가동"
                            
                            delete_yn      = 0  # 삭제 여부 기본값 FALSE(0)
                            
                            # 2. DDL insert 문 매핑 구조 파라미터 리스트업
                            checklist_rows.append((
                                partner_type,  
                                indicator_no,
                                category,
                                indicator_name,
                                priority,
                                star_yn,
                                question,
                                pass_answer,
                                fail_answer,
                                risk_level,
                                evidence_yn,
                                evidence_list,
                                action_plan,
                                delete_yn
                            ))
                            
            except Exception as e:
                safe_print(f"[오류] '{os.path.basename(excel_path)}' 처리 중 크리티컬 예외 발생: {e}")
                
    # 3. 데이터베이스 벌크 인서트 수행
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

def export_pgvector_to_hf(repo_id: str ):
    """ [복원] PostgreSQL pgvector에 저장된 모든 원천 지식 임베딩 데이터를 끌어올려 Hugging Face 허브로 원격 백업합니다."""
    conn = db.get_postgres_conn()
    if not conn: return
    safe_print(f"[HuggingFace 백업] '{repo_id}' 허브로 벡터 데이터셋 업로드를 시작합니다...")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT chunk_id, file_name, content, embedding, timestamp FROM ESG_PDF_VECTORS;")
            rows = cur.fetchall()
            
        if not rows:
            safe_print("[HuggingFace 백업 경고] 업로드할 데이터가 백엔드 DB에 존재하지 않습니다.")
            return
            
        # 데이터프레임 구조화 및 HF 전용 인스턴스 래핑
        df = pd.DataFrame(rows, columns=["chunk_id", "file_name", "content", "embedding", "timestamp"])
        dataset = Dataset.from_pandas(df)
        
        # 원격 전송 아키텍처 호출
        dataset.push_to_hub(repo_id, private=False)
        safe_print(f"[HuggingFace 성공] 백업 허브 빌드 및 업로드 완료 -> {repo_id}")
    except Exception as e:
        safe_print(f"[HuggingFace 오류] 원격 클라우드 업로드 실패: {e}")

def run_concurrent_ingestion_pipeline(pdf_dir: str, excel_dir: str, hf_repo: str = None):
    """[동시 다발 처리] PDF(pgvector) 적재, Excel(MariaDB) 적재, 온톨로지 캐싱 및 HF 백업을 원스톱으로 처리합니다."""
    safe_print("\n=== 🚀 [통합 파이프라인] 전처리 및 분기 동시 적재 가동 ===")
    
    # 1. PDF 가공(150자 중복 세팅 결합) 후 pgvector 적재 및 BM25 구축
    pdf_chunks = []
    for pdf_path in glob.glob(os.path.join(pdf_dir, "*.pdf")):
        pdf_chunks.extend(extract_and_chunk_pdf(pdf_path))
    if pdf_chunks:
        init_and_save_to_pgvector(pdf_chunks)
        
        global global_chunks_pool, bm25_index
        global_chunks_pool = pdf_chunks
        tokenized_corpus = [simple_tokenizer(c["content"]) for c in pdf_chunks]
        bm25_index = BM25Okapi(tokenized_corpus)
        
    # 2. 엑셀 마스터 적재 및 온톨로지 캐시 레이어 빌드 (동시 수행)
    load_excel_to_mariadb(excel_dir)
    build_ontology_registry()
    export_ontology_to_jsonl("esg_ontology_template.jsonl")
    
    # 3. 데이터셋 허깅페이스 파이프라인 원격 이관 트리거
    if hf_repo:
        export_pgvector_to_hf(repo_id=hf_repo)


# ════════════════════════════════════════════════════════
# 🔍 Hybrid Retriever Engine (BM25 + pgvector + Rerank)
# ════════════════════════════════════════════════════════
def search_hybrid_documents(query: str, top_k: int = 3) -> list:
    global bm25_index, global_chunks_pool
    candidates = []
    
    if bm25_index and global_chunks_pool:
        tokenized_query = simple_tokenizer(query)
        bm25_scores = bm25_index.get_scores(tokenized_query)
        top_bm25_idx = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k*2]
        for idx in top_bm25_idx:
            if bm25_scores[idx] > 0:
                candidates.append(global_chunks_pool[idx]["content"])

    try:
        conn = db.get_postgres_conn()
        if conn:
            query_embed = ollama_client.embeddings(model=settings.embed_model, prompt=query)["embedding"]
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT content FROM ESG_PDF_VECTORS 
                    ORDER BY embedding <=> %s::vector LIMIT %s;
                """, (query_embed, top_k*2))
                for row in cur.fetchall():
                    candidates.append(row[0])
    except Exception as e:
        safe_print(f"[Dense 검색 오류] : {e}")

    candidates = list(set(candidates))
    if not candidates: return []
    
    pairs = [[query, doc] for doc in candidates]
    rerank_scores = reranker.predict(pairs)
    scored_docs = sorted(zip(candidates, rerank_scores), key=lambda x: x[1], reverse=True)
    
    return [doc for doc, score in scored_docs[:top_k]]


# ════════════════════════════════════════════════════════
# ⚖️ 지식 연동 온톨로지 고속 룰 엔진 및 공급망 추론 결합
# ════════════════════════════════════════════════════════
def evaluate_esg_by_ontology(matched_indicator_name: str, current_value: float) -> tuple[str, str]:
    """🌟 [복원] 온톨로지 고속 매핑 규칙 구조를 사용해 대량 질의 오버헤드를 제어하는 고속 매칭 룰 검증부입니다."""
    global _ONTOLOGY_REGISTRY
    if matched_indicator_name not in _ONTOLOGY_REGISTRY:
        return "진단 보류", "등록된 온톨로지 매핑 정보를 찾을 수 없습니다."
        
    spec = _ONTOLOGY_REGISTRY[matched_indicator_name]
    th = spec["threshold_value"]
    op = spec["operator"]
    action = spec["action_plan"]
    
    # 파싱된 연산 기호 논리 구조 대조
    is_passed = False
    if op == ">=": is_passed = (current_value >= th)
    elif op == "<=": is_passed = (current_value <= th)
    elif op == ">": is_passed = (current_value > th)
    elif op == "<": is_passed = (current_value < th)
    
    status = "합격" if is_passed else "불합격"
    return status, action

def get_supply_chain_risk_report(failed_short_name: str, judgement_status: str) -> dict:
    if judgement_status != "불합격":
        return {"risk_propagated": False, "propagation_path": []}

    node_info = db.find_one("SELECT raw_id, tier FROM RM_TIER_TREE WHERE short_name = %s LIMIT 1", (failed_short_name,))
    if not node_info:
        return {"risk_propagated": False, "propagation_path": []}
        
    raw_id = node_info['raw_id']
    failed_tier = node_info['tier']

    affected_chain = db.find_all("""
        SELECT tier, short_name, item_name FROM RM_TIER_TREE 
        WHERE raw_id = %s AND tier < %s ORDER BY tier DESC
    """, (raw_id, failed_tier))

    propagation_path = [{"tier": failed_tier, "short_name": failed_short_name, "status": "위험 발생원 🔴"}]
    for row in affected_chain:
        propagation_path.append({
            "tier": row["tier"],
            "short_name": row["short_name"],
            "status": f"간접 리스크 전파 ⚠️ ({row['item_name']} 공급망 오염)"
        })
        
    return {
        "risk_propagated": True,
        "raw_id": raw_id,
        "danger_level": "고위험 (High Risk)",
        "propagation_path": propagation_path,
        "action_plan": "즉시 상위 공급망 납품 검역 강화 및 대체 소싱(Alternative Sourcing) 프로세스 가동"
    }

def save_ai_inference_log(partner_name: str, query: str, result_text: str, status: str, risk_chain: dict, ai_model: str, duration: float) -> bool:
    """
    🌟 [고도화]: AI 최종 추론 결과물, 리스크 체인, 사용 모델 및 순수 소요 시간을 AI_LOGS 테이블에 적재
    """
    sql = """
        INSERT INTO AI_LOGS 
        (partner_name, user_query, ai_evaluation, judgement_status, risk_chain_json, ai_model, inference_duration, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """
    try:
        # JSON 구조 데이터는 문자열로 직렬화하여 저장
        risk_chain_str = json.dumps(risk_chain, ensure_ascii=False)
        
        # 새롭게 정의된 DDL 속성 순서대로 파라미터 매핑 (duration은 소수점 둘째 자리까지 반올림)
        success = db.save(sql, (
            partner_name, 
            query, 
            result_text, 
            status, 
            risk_chain_str, 
            ai_model, 
            round(duration, 2)
        ))
        
        if success:
            safe_print(f"[AI 로그 백엔드] 협력사 '{partner_name}' 감사 로그 보관 완료 ({ai_model} / 소요시간: {duration:.2f}초)")
            return True
    except Exception as e:
        safe_print(f"[AI 로그 오류] AI_LOGS 마스터 레포지토리 적재 실패: {e}")
    return False


def process_esg_compliance_query(user_query: str, partner_name: str) -> dict:
    user_numbers = re.findall(r"\d+\.\d+|\d+", user_query)
    user_val = float(user_numbers[0]) if user_numbers else 0.0
    
    relevant_contexts = search_hybrid_documents(user_query, top_k=2)
    context_str = "\n".join(relevant_contexts)
    
    matched_indicator = "아동·강제노동 Zero 확인"
    judgement_status, action_plan = evaluate_esg_by_ontology(matched_indicator, user_val)
    
    if any(kwd in user_query for kwd in ["아동", "강제노동"]) and user_val > 0:
        judgement_status = "불합격"

    risk_chain = get_supply_chain_risk_report(partner_name, judgement_status)
    if judgement_status == "불합격" and "action_plan" in risk_chain:
        risk_chain["action_plan"] = action_plan
    
    prompt = f"Context:\n{context_str}\nQuery: {user_query}\nStatus: {judgement_status}\nAction: {action_plan}. 위 데이터를 기초로 협력사 감사 리포트를 Markdown 표 및 단락 양식으로 구성해 주세요."
    
    # 🌟 [시간 측정 시작]: LLM이 생성 연산을 시작하는 시점의 타임스탬프 기록
    start_time = time.time()
    
    target_model = settings.mariadb_ollama_model
    ai_resp = ollama_client.generate(model=target_model, prompt=prompt)["response"]
    
    # 🌟 [시간 측정 종료]: 연산이 끝난 시점의 차이를 구하여 순수 추론 시간 계산
    inference_duration = time.time() - start_time
    
    # 🌟 [적재 활성화]: 새로 추가된 target_model과 inference_duration 인자를 함께 넘겨줍니다.
    save_ai_inference_log(
        partner_name=partner_name,
        query=user_query,
        result_text=ai_resp,
        status=judgement_status,
        risk_chain=risk_chain,
        ai_model=target_model,
        duration=inference_duration
    )
    
    return {
        "evaluation_result": ai_resp,
        "judgement_status": judgement_status,
        "risk_chain_analysis": risk_chain
    }