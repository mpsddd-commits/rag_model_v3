"""
Integrated ESG Hybrid Engine: Ingestion Pipeline, Hybrid Retriever, 
Ontology Rule Registry, and Hugging Face Dataset Exporter.
"""
import os
import re
import json
import time
import ollama
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

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
# 온톨로지(Ontology) 질문 복합 유형 분석 및 캐싱 로직
# ════════════════════════════════════════════════════════
def parse_complex_criteria(question_text: str) -> dict:
    """
    질문(question) 텍스트를 분석하여 수치 검증(단일/범위) 또는 Boolean 검증 유형을 판별하고
    검증에 필요한 마스터 기준값과 연산자를 딕셔너리 형태로 반환합니다.
    """
    result = {
        "criteria_type": "BOOL",  # 기본값: BOOL (~했습니까?, 있습니까? 등)
        "operator": "== Y",       # 합격 기준 오퍼레이터
        "threshold_value": None,
        "min_value": None,
        "max_value": None
    }
    
    if not question_text:
        return result

    # 1. 범위형 분석 ('범위 내에 있습니까')
    if "범위 내" in question_text or "범위 내에" in question_text:
        # 모든 소수점 및 정수 추출 (예: 1.00~1.50 -> ['1.00', '1.50'])
        nums = re.findall(r"\d+\.\d+|\d+", question_text)
        if len(nums) >= 2:
            result["criteria_type"] = "RANGE"
            result["min_value"] = float(nums[0])
            result["max_value"] = float(nums[1])
            result["operator"] = "BETWEEN"
            return result

    # 2. 단일 수치 비교형 분석 ('이하입니까', '미만입니까', '초과입니까', '이상입니까')
    nums = re.findall(r"\d+\.\d+|\d+", question_text)
    
    # 'Zero'나 '0건' 같은 특수 키워드 가드레일 처리
    if "Zero" in question_text or "zero" in question_text:
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
            return result
        elif "미만" in question_text:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = "<"
            result["threshold_value"] = val
            return result
        elif "초과" in question_text:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">"
            result["threshold_value"] = val
            return result
        elif "이상" in question_text or "충족" in question_text:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">="
            result["threshold_value"] = val
            return result

    # 3. 수치 조건이 없는 경우 여부 확인형 (BOOL 분기 고수)
    if "않습니까" in question_text:
        # (~하지 않습니까? -> 예, 하지 않습니다 가 합격이므로 로직상 N 또는 특수 체크 필요)
        result["operator"] = "== N"
        
    return result

def build_ontology_registry():
    """MariaDB의 최신 마스터 지표 데이터를 조회하여 복합 온톨로지 사전을 동기화 구축합니다."""
    global _ONTOLOGY_REGISTRY, _ONTOLOGY_TEMPLATE_LIST
    _ONTOLOGY_REGISTRY.clear()
    _ONTOLOGY_TEMPLATE_LIST.clear()
    
    sql = "SELECT indicator_no, indicator_name, question, action_plan FROM SELF_ASSESS_CHECKLIST"
    rows = db.find_all(sql)
    
    for row in rows:
        ind_name = row["indicator_name"]
        raw_question = row["question"]
        
        # 고도화된 복합 기준 분석기 호출
        criteria_meta = parse_complex_criteria(raw_question)
        
        # 1. 인메모리 온톨로지 딕셔너리 빌드
        _ONTOLOGY_REGISTRY[ind_name] = {
            "indicator_no": row["indicator_no"],
            "action_plan": row.get("action_plan", "즉시 시정 조치 가동"),
            "raw_text": raw_question,
            **criteria_meta  # 분기된 메타 정보 전량 언팩 적재
        }
        
        # 2. AI 학습 아티팩트용 템플릿 추가
        _ONTOLOGY_TEMPLATE_LIST.append({
            "indicator_no": row["indicator_no"],
            "indicator_name": ind_name,
            "raw_expression": raw_question,
            "meta": criteria_meta
        })
        
    safe_print(f"[온톨로지 엔지니어링] {len(_ONTOLOGY_REGISTRY)}개의 지표 온톨로지 복합 분기 규칙 캐싱 완료.")

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
    
    pairs = [[query, doc] for doc in candidates]
    rerank_scores = reranker.predict(pairs)
    scored_docs = sorted(zip(candidates, rerank_scores), key=lambda x: x[1], reverse=True)
    
    return [doc for doc, score in scored_docs[:top_k]]

# ════════════════════════════════════════════════════════
# ⚖️ [고도화] 지식 연동 온톨로지 다형성(Type) 룰 검증 엔진
# ════════════════════════════════════════════════════════
def evaluate_esg_by_ontology_advanced(matched_indicator_name: str, user_val: float | None, user_bool: str | None) -> tuple[str, str]:
    """
    추출된 온톨로지 유형(RANGE, NUMERIC, BOOL)에 따라 
    수치 연속형 대조 및 불리언 일치 여부를 다각도로 검증하여 합격/불합격을 판정합니다.
    """
    global _ONTOLOGY_REGISTRY
    if matched_indicator_name not in _ONTOLOGY_REGISTRY:
        return "진단 보류", "등록된 온톨로지 매핑 정보를 찾을 수 없습니다."
        
    spec = _ONTOLOGY_REGISTRY[matched_indicator_name]
    c_type = spec["criteria_type"]
    action = spec["action_plan"]
    is_passed = False

    # 분기 1: 범위형 검증 (RANGE)
    if c_type == "RANGE":
        if user_val is not None:
            min_v = spec["min_value"]
            max_v = spec["max_value"]
            is_passed = (min_v <= user_val <= max_v)
        else:
            is_passed = False # 수치 입력 누락 시 기본 불합격 가드레일

    # 분기 2: 단일 수치 비교형 검증 (NUMERIC)
    elif c_type == "NUMERIC":
        if user_val is not None:
            th = spec["threshold_value"]
            op = spec["operator"]
            if op == ">=": is_passed = (user_val >= th)
            elif op == "<=": is_passed = (user_val <= th)
            elif op == ">": is_passed = (user_val > th)
            elif op == "<": is_passed = (user_val < th)
        else:
            is_passed = False

    # 분기 3: 상태/확인형 불리언 검증 (BOOL)
    elif c_type == "BOOL":
        if user_bool:
            op = spec["operator"]
            clean_bool = user_bool.strip().upper()
            
            if "== Y" in op:
                is_passed = clean_bool in ["Y", "YES", "TRUE", "확인", "완료", "합격"]
            elif "== N" in op:
                is_passed = clean_bool in ["N", "NO", "FALSE", "미완료", "ZERO", "0건"]
        else:
            is_passed = False

    status = "합격" if is_passed else "불합격"
    return status, action

def get_supply_chain_risk_report(failed_short_name: str, judgement_status: str) -> dict:
    """
    [RM_TIER_TREE 연동] 불합격 판정 시, 해당 협력사로부터 
    상위 Tier 1 공급사까지의 위험 전파 경로를 실시간 추적합니다.
    """
    if judgement_status != "불합격":
        return {"risk_propagated": False, "propagation_path": []}

    node_info = db.find_one("SELECT raw_id, tier FROM RM_TIER_TREE WHERE short_name = %s LIMIT 1", (failed_short_name,))
    if not node_info:
        return {
            "partner_name": failed_short_name,
            "impact_level": "High",
            "action_plan": "즉시 공급망 정밀 실사단 파견 필요",
            "risk_propagated": True,
            "propagation_path": []
        }
        
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

def save_ai_inference_log(partner_name: str, query: str, result_text: str, status: str, risk_chain: dict, ai_model: str, duration: float):
    """
    [변경 완료] 새롭게 정의된 edu.AI_LOGS 테이블 스키마에 맞춰
    LLM 추론 결과 및 평가 로그를 MariaDB에 적재합니다.
    """
    # 1. 딕셔너리 형태의 risk_chain 데이터를 문자열 포맷(JSON)으로 직렬화
    risk_chain_json = json.dumps(risk_chain, ensure_ascii=False)
    
    # 2. 제공해주신 AI_LOGS 테이블의 컬럼명에 맞춰 SQL 쿼리 재구성
    # (log_id는 AUTO_INCREMENT, created_at은 DEFAULT current_timestamp()이므로 인서트문에서 배제)
    sql = """
        INSERT INTO AI_LOGS (
            partner_name, 
            user_query, 
            ai_evaluation, 
            judgement_status, 
            risk_chain_json, 
            ai_model, 
            inference_duration
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    try:
        # 내장된 db 유틸리티를 사용하여 데이터 바인딩 및 저장 실행
        db.save(sql, (
            partner_name, 
            query, 
            result_text,  # ai_evaluation 컬럼에 매핑
            status,       # judgement_status 컬럼에 매핑
            risk_chain_json, 
            ai_model, 
            duration      # inference_duration 컬럼에 매핑
        ))
        safe_print(f"[DB 로그 적재 성공] AI_LOGS 테이블에 '{partner_name}' 업체의 ESG 감사 이력이 보관되었습니다.")
    except Exception as e:
        safe_print(f"[DB 로그 적재 실패] AI_LOGS 적재 중 SQL 오류 발생: {e}")

# ════════════════════════════════════════════════════════
# 🔍 이원화 검색 인터페이스 바인딩 (여기에 배치합니다)
# ════════════════════════════════════════════════════════

# [Track 1] 실제 소스 코드 내부의 db 모듈(db.find_all)을 활용한 MariaDB 검색 함수 정의
def search_mariadb_keyword(user_query: str, partner_name: str) -> list:
    """
    MariaDB 지표 마스터 테이블에서 키워드 기반으로 기준 데이터를 검색합니다.
    """
    contexts = []
    # 정규식으로 한글/영문 키워드 추출 (예: '철', 'Fe')
    keywords = re.findall(r'[a-zA-Z가-힣]+', user_query)
    if not keywords:
        return contexts

    main_keyword = keywords[0]
    sql = """
        SELECT indicator_name, question, action_plan 
        FROM SELF_ASSESS_CHECKLIST 
        WHERE indicator_name LIKE %s OR question LIKE %s
    """
    search_pattern = f"%{main_keyword}%"
    
    # 내장된 db 유틸리티로 조회 실행
    results = db.find_all(sql, (search_pattern, search_pattern))
    
    for row in results:
        contexts.append(
            f"[MariaDB 기준지표] 지표명: {row['indicator_name']} | "
            f"점검문항: {row['question']} | "
            f"대응가이드: {row['action_plan']}"
        )
    return contexts

def process_esg_compliance_query_advanced(user_query: str, partner_name: str) -> dict:
    """
    [수정 완성본] 이원화 검색, 보수적 가드레일, 최종 사후검증 및 
    공급망 리스크 역추적 로직을 결합한 통합 감사 리포팅 파이프라인
    """
    
    # 1. 사용자 쿼리에서 수치 데이터 추출
    user_numbers = re.findall(r"\d+\.\d+|\d+", user_query)
    user_val = float(user_numbers[0]) if user_numbers else 0.0
    
    # 2. MariaDB + VectorDB 이원화 검색 실행
    mariadb_contexts = search_mariadb_keyword(user_query, partner_name) 
    vectordb_contexts = search_hybrid_documents(user_query, top_k=2)
    
    combined_contexts = mariadb_contexts + vectordb_contexts
    context_str = "\n".join(combined_contexts)
    
    # ════════════════════════════════════════════════════════
    # ⚖️ [개선] 보수적 가드레일 기반 동적 판정 레이어
    # ════════════════════════════════════════════════════════
    judgement_status = "검토 필요"
    action_plan = "정확한 매칭 기준이 없으므로 담당자 수동 검토 및 재실행 요망"

    # ⭐ [최우선 가드레일] 인권/아동/강제노동 관련 키워드가 쿼리에 있고 위반 사항(1건 이상)이 있으면 무조건 불합격!
    if any(kwd in user_query for kwd in ["아동", "강제노동", "인권위반"]) and user_val > 0:
        judgement_status = "불합격"
        action_plan = "① 즉시 공급 중단 ② CSDDD 이행계획서 징구 및 현장 정밀 실사단 파견"
    
    # 그 외의 경우에만 일반 수치 비교 진행
    else:
        keywords = re.findall(r'[a-zA-Z가-힣]+', user_query)
        master_row = None
        if keywords:
            main_keyword = keywords[0]
            sql_master = "SELECT question, action_plan FROM SELF_ASSESS_CHECKLIST WHERE indicator_name LIKE %s OR question LIKE %s LIMIT 1"
            master_row = db.find_one(sql_master, (f"%{main_keyword}%", f"%{main_keyword}%"))

        if master_row and master_row.get("question"):
            db_question = master_row["question"]
            db_action = master_row.get("action_plan", "즉시 시정 조치 가동")
            
            # (중략: 기존의 db_threshold 추출 및 일반 수치 비교 로직)
            # ...
            if is_violated:
                judgement_status = "불합격"
                action_plan = db_action
            else:
                judgement_status = "합격"
                action_plan = "마스터 기준 충족. 특이사항 없음"

    # 🎯 [사후 검증] 철 함량 강제 가드레일 (기존 유지)
    if any(kwd in user_query for kwd in ["Fe", "철", "Fe(철)"]) and user_val > 0.70:
        judgement_status = "불합격"
        action_plan = "① 즉시 공급 중단 및 공정 전수조사 ② 원자재 공급사 변경 검토 ③ 성분 분석 성적서(수입검사재) 재요구"

    # 3. 공급망 리스크 전파 경로 분석 호출 및 구조화
    risk_chain = get_supply_chain_risk_report(partner_name, judgement_status)
    
    if judgement_status == "불합격":
        risk_chain["action_plan"] = action_plan
    else:
        risk_chain["action_plan"] = "정기 모니터링 및 분기별 ESG 데이터 업데이트 트래킹"
        action_plan = risk_chain["action_plan"]
    
    # 4. 생성 인공지능 기반 감사 리포트 구성 (중략 - 기존 프롬프트 및 로깅 엔진 작동)
    prompt = (
       f"Context:\n{context_str}\n\n"
        f"Query: {user_query}\n"
        f"Strict Evaluation Status: {judgement_status}\n"
        f"Enforced Action Plan: {action_plan}\n\n"
        f"[지침 사항 - 반드시 준수할 것]\n"
        f"1. 당신은 엄격한 ESG 공급망 감사관입니다.\n"
        f"2. 시스템이 판단한 결과인 'Strict Evaluation Status'({judgement_status})를 리포트 표의 [평가 상태] 및 결론에 절대 변조 없이 그대로 출력하십시오.\n"
        f"3. 만약 상태가 '불합격' 또는 '검토 필요'라면, 표의 평가 상태를 **불합격** 또는 **검토 필요**로 명시하고 리포트 톤앤매너를 엄격한 경고조로 작성하십시오.\n"
        f"4. 'Enforced Action Plan'에 명시된 조치 계획 수칙을 '위험 조치 계획' 섹션에 누락 없이 마크다운 리스트로 포함하십시오.\n\n"
        f"위 데이터와 지침을 기초로 협력사 감사 리포트를 Markdown 양식으로 구성해 주세요."
    )
    
    start_time = time.time()
    target_model = settings.mariadb_ollama_model
    ai_resp = ollama_client.generate(model=target_model, prompt=prompt)["response"]
    inference_duration = time.time() - start_time
    
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