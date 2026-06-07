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
from datetime import datetime
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from psycopg2.extras import RealDictCursor

import dbClient as db 
from settings import settings, safePrint, simpleTokenizer

# 싱글톤 인스턴스 전역 정의
os.environ["OLLAMA_HOST"] = settings.ollama_host
ollamaClient = ollama.Client(host=settings.ollama_host)
reranker = CrossEncoder(settings.rerank_model)

# 인메모리 파이프라인 전역 상태 관리 객체
bm25Index = None
globalChunksPool = []
_ONTOLOGY_REGISTRY: dict = {}
_ONTOLOGY_TEMPLATE_LIST: list = []


# ════════════════════════════════════════════════════════
# 온톨로지(Ontology) 질문 복합 유형 분석 및 캐싱 로직
# ════════════════════════════════════════════════════════
def parseComplexCriteria(questionText: str) -> dict:
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
    
    if not questionText:
        return result

    # 1. 전처리 가드레일: 의도치 않은 메타 숫자(4자리 제품명, ASTM 규격 번호 등)를 임시 제거
    # 예: Al 3003 -> Al , ASTM B209 -> ASTM B 로 변경하여 수치 인식 방지
    cleanText = re.sub(r"\b\d{4}\b", "", questionText)  # 4자리 숫자(3003 등) 제거
    cleanText = re.sub(r"B\d+", "B", cleanText)         # B209 등 규격명 뒤의 숫자 제거

    # 2. 범위형 분석 (문장에 '범위 내'가 있거나 숫자~숫자 구조가 명시적인 경우)
    # 정규식으로 [숫자][공백이나 물결][숫자] 형태를 직접 타겟팅 (예: 1.00~1.50)
    rangeMatch = re.search(r"(\d+\.\d+|\d+)\s*[~-]\s*(\d+\.\d+|\d+)", cleanText)
    
    if "범위 내" in questionText or rangeMatch:
        if rangeMatch:
            result["criteria_type"] = "RANGE"
            result["min_value"] = float(rangeMatch.group(1))
            result["max_value"] = float(rangeMatch.group(2))
            result["operator"] = "BETWEEN"
            return result
        else:
            # 물결표는 없지만 '범위 내' 키워드가 있는 경우 폴백 처리
            nums = re.findall(r"\d+\.\d+|\d+", cleanText)
            if len(nums) >= 2:
                result["criteria_type"] = "RANGE"
                result["min_value"] = float(nums[0])
                result["max_value"] = float(nums[1])
                result["operator"] = "BETWEEN"
                return result

    # 3. 단일 수치 비교형 분석 ('이하', '미만', '초과', '이상')
    nums = re.findall(r"\d+\.\d+|\d+", cleanText)
    
    if "Zero" in questionText or "zero" in questionText or "0건" in questionText:
        result["criteria_type"] = "NUMERIC"
        result["operator"] = "<="
        result["threshold_value"] = 0.0
        return result

    if nums:
        val = float(nums[0])
        if "이하" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = "<="
            result["threshold_value"] = val
        elif "미만" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = "<"
            result["threshold_value"] = val
        elif "초과" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">"
            result["threshold_value"] = val
        elif "이상" in questionText or "충족" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">="
            result["threshold_value"] = val

    # 4. 상태 확인형 불리언 가드
    if "않습니까" in questionText:
        result["operator"] = "== N"
        
    return result

def buildOntologyRegistry():
    """MariaDB의 최신 마스터 지표 데이터를 조회하여 복합 온톨로지 사전을 동기화 구축합니다."""
    global _ONTOLOGY_REGISTRY, _ONTOLOGY_TEMPLATE_LIST
    _ONTOLOGY_REGISTRY.clear()
    _ONTOLOGY_TEMPLATE_LIST.clear()
    
    sql = "SELECT indicator_no, indicator_name, question, action_plan FROM SELF_ASSESS_CHECKLIST"
    rows = db.findAll(sql)
    
    for row in rows:
        indName = row["indicator_name"]
        rawQuestion = row["question"]        
        # 고도화된 복합 기준 분석기 호출
        criteriaMeta = parseComplexCriteria(rawQuestion)
        
        # DB에 action_plan이 없는 경우 안전 가드
        dbAction = row.get("action_plan") or "지표 기준 미달: 공급망 정밀 실사 및 시정 조치 가동"
        
        # 1. 인메모리 온톨로지 딕셔너리 빌드
        _ONTOLOGY_REGISTRY[indName] = {
            "indicator_no": row["indicator_no"],
            "action_plan": dbAction,
            "raw_text": rawQuestion,
            **criteriaMeta  # 분기된 메타 정보 전량 언팩 적재
        }
        
        # 2. AI 학습 아티팩트용 템플릿 추가
        _ONTOLOGY_TEMPLATE_LIST.append({
            "indicator_no": row["indicator_no"],
            "indicator_name": indName,
            "raw_expression": rawQuestion,
            "action_plan": dbAction,
            "meta": criteriaMeta
        })
        
    safePrint(f"[온톨로지 엔지니어링] DB 원본 기반 {len(_ONTOLOGY_REGISTRY)}개의 지표 온톨로지 복합 분기 규칙 캐싱 완료.")

# ════════════════════════════════════════════════════════
# 수정 완료된 완성본 JSONL 기반 로드 로직
# ════════════════════════════════════════════════════════
def buildOntologyRegistryFromJsonl(jsonlPath: str = "./esgOntologyTemplate.jsonl"):
    """
    사용자가 오프라인에서 수정을 완료한 완성본 JSONL 파일을 직접 파싱하여 
    전역 온톨로지 사전 및 템플릿 메모리 구조를 동기화합니다.
    """
    global _ONTOLOGY_REGISTRY, _ONTOLOGY_TEMPLATE_LIST
    _ONTOLOGY_REGISTRY.clear()
    _ONTOLOGY_TEMPLATE_LIST.clear()
    
    if not os.path.exists(jsonlPath):
        safePrint(f"[경고] 완성본 온톨로지 파일이 존재하지 않습니다. DB 연동을 임시 가동합니다: {jsonlPath}")
        buildOntologyRegistry()
        return

    count = 0
    with open(jsonlPath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                indName = data["indicator_name"]
                rawQuestion = data["raw_expression"]
                meta = data["meta"]
                # DB action_plan을 우선하되, 파일에도 없으면 기본값 주입 (이중 안전장치)
                fileActionPlan = data.get("action_plan") or meta.get("action_plan") or "지표 마스터 기준 미달에 따른 공급망 정밀 실사 가동"
                
                # 메모리 글로벌 레지스트리에 수치 매핑 규칙 주입
                _ONTOLOGY_REGISTRY[indName] = {
                    "indicator_no": data["indicator_no"],
                    "action_plan": fileActionPlan,
                    "raw_text": rawQuestion,
                    "criteria_type": meta.get("criteria_type"),
                    "operator": meta.get("operator"),
                    "threshold_value": meta.get("threshold_value"),
                    "min_value": meta.get("min_value"),
                    "max_value": meta.get("max_value")
                }
                
                # AI 포맷 리스트 구조화 보존
                _ONTOLOGY_TEMPLATE_LIST.append(data)
                count += 1
            except Exception as e:
                safePrint(f"[JSONL 로드 에러] 라인 파싱 실패: {e}")
                
    safePrint(f"[온톨로지 엔지니어링] 완성본 JSONL 기반 {count}개 지표 복합 룰 규칙 완벽 바인딩 성공.")

# ════════════════════════════════════════════════════════
# 🔍 Hybrid Retriever Engine (BM25 + pgvector + Rerank)
# ════════════════════════════════════════════════════════
def getEmbedding(text: str) -> list:
    """Ollama에 로드된 임베딩 모델을 사용해 텍스트 벡터 추출"""
    if not text or not text.strip():
        return None
    try:
        # settings에 지정해 둔 임베딩 모델명이 있다면 그것을 쓰고, 
        # 없다면 기본 llama3.1이나 bge-m3 등 할당된 모델명을 적어줍니다.
        model_name = getattr(settings, "embed_model", settings.embed_model) 
        
        response = ollamaClient.embeddings(
            model=model_name,
            prompt=text
        )
        return response['embedding']
    except Exception as e:
        safePrint(f"❌ [Ollama Embedding Error]: {e}")
        return None

def searchHybridDocuments(userQuery: str, topK: int = 5) -> list:
    # 1. Sparse 검색 (BM25) 진행
    tokenizedQuery = simpleTokenizer(userQuery)
    sparseCandidates = []
    if bm25Index is not None:
        # BM25 스코어가 높은 순으로 정렬되어 나옴
        scores = bm25Index.get_scores(tokenizedQuery)
        topIdxs = np.argsort(scores)[::-1][:topK * 2]
        for rank, idx in enumerate(topIdxs):
            if scores[idx] > 0:
                sparseCandidates.append((globalChunksPool[idx], rank + 1)) # (텍스트, 순위)

    # 2. Dense 검색 (pgvector) 진행
    denseCandidates = []
    emb = getEmbedding(userQuery)
    if emb is not None:
        pgConn = None
        try:
            # PostgreSQL 커넥션 확보 (없으면 DB 자동 생성까지 수행됨)
            pgConn = db.getPostgresConn()
            
            # 결과 셋을 명세서 쿼리 규격(r['content'])에 맞추기 위해 RealDictCursor 사용
            with pgConn.cursor(cursor_factory=RealDictCursor) as cur:
                # 파이썬 리스트(emb)를 pgvector가 인식할 수 있는 문자열 형태로 포맷팅
                emb_str = f"[{','.join(map(str, emb))}]"
                
                # pgvector 전용 코사인 거리 연산 쿼리 수행
                query = "SELECT content FROM esg_pdf_vectors ORDER BY embedding <=> %s LIMIT %s;"
                cur.execute(query, (emb_str, topK * 2))
                rows = cur.fetchall()
                
                for rank, r in enumerate(rows):
                    denseCandidates.append((r['content'], rank + 1)) # (텍스트, 순위)
                    
        except Exception as pg_err:
            safePrint(f"[!] [pgvector 검색 장애]: {pg_err}")
        finally:
            if pgConn:
                pgConn.close() # 커넥션 자원 반환

    # 3. RRF (Reciprocal Rank Fusion) 연산 수행
    # 공식: Score = 1 / (60 + Sparse_Rank) + 1 / (60 + Dense_Rank)
    K = 60
    rrfScores = {}
    
    for chunk, rank in sparseCandidates:
        rrfScores[chunk] = rrfScores.get(chunk, 0.0) + (1.0 / (K + rank))
        
    for chunk, rank in denseCandidates:
        rrfScores[chunk] = rrfScores.get(chunk, 0.0) + (1.0 / (K + rank))

    # 4. RRF 점수가 높은 상위 후보군만 1차 필터링 (Reranker 연산량 반으로 감소)
    sortedCandidates = sorted(rrfScores.items(), key=lambda x: x[1], reverse=True)
    finalCandidates = [chunk for chunk, score in sortedCandidates[:topK * 2]]

    if not finalCandidates:
        return []

    # 5. 최종 CrossEncoder Re-ranking 진행
    pairs = [[userQuery, c] for c in finalCandidates]
    rerankScores = reranker.predict(pairs)
    
    rankedResults = sorted(zip(finalCandidates, rerankScores), key=lambda x: x[1], reverse=True)
    return [res[0] for res in rankedResults[:topK]]

# ════════════════════════════════════════════════════════
# ⚖️ 지식 연동 온톨로지 다형성(Type) 룰 검증 엔진
# ════════════════════════════════════════════════════════
def evaluateEsgByOntology(matchedIndicatorName: str, userVal: float | None, userBool: str | None) -> tuple[str, str]:
    """
    추출된 온톨로지 유형(RANGE, NUMERIC, BOOL)에 따라 
    수치 연속형 대조 및 불리언 일치 여부를 다각도로 검증하여 합격/불합격을 판정합니다.
    """
    global _ONTOLOGY_REGISTRY
    if matchedIndicatorName not in _ONTOLOGY_REGISTRY:
        return "진단 보류", "등록된 온톨로지 매핑 정보를 찾을 수 없습니다."
        
    spec = _ONTOLOGY_REGISTRY[matchedIndicatorName]
    cType = spec["criteria_type"]
    action = spec["action_plan"]
    isPassed = False

    # 분기 1: 범위형 검증 (RANGE)
    if cType == "RANGE":
        if userVal is not None:
            minV = spec["min_value"]
            maxV = spec["max_value"]
            isPassed = (minV <= userVal <= maxV)
        else:
            isPassed = False # 수치 입력 누락 시 기본 불합격 가드레일

    # 분기 2: 단일 수치 비교형 검증 (NUMERIC)
    elif cType == "NUMERIC":
        if userVal is not None:
            th = spec["threshold_value"]
            op = spec["operator"]
            if op == ">=": isPassed = (userVal >= th)
            elif op == "<=": isPassed = (userVal <= th)
            elif op == ">": isPassed = (userVal > th)
            elif op == "<": isPassed = (userVal < th)
        else:
            isPassed = False

    # 분기 3: 상태/확인형 불리언 검증 (BOOL)
    elif cType == "BOOL":
        if userBool:
            op = spec["operator"]
            cleanBool = userBool.strip().upper()
            
            if "== Y" in op:
                isPassed = cleanBool in ["Y", "YES", "TRUE", "확인", "완료", "합격"]
            elif "== N" in op:
                isPassed = cleanBool in ["N", "NO", "FALSE", "미완료", "ZERO", "0건"]
        else:
            isPassed = False

    status = "합격" if isPassed else "불합격"
    return status, action

def getSupplyChainRiskReport(failedShortName: str, judgementStatus: str) -> dict:
    """
    [RM_TIER_TREE 연동] 불합격 판정 시, 해당 협력사로부터 상위 Tier 1 공급사까지의 위험 전파 경로를 실시간 추적합니다.
    """
    if judgementStatus != "불합격":
        return {"risk_propagated": False, "propagation_path": []}

    nodeInfo = db.findOne("SELECT raw_id, tier FROM RM_TIER_TREE WHERE short_name = %s LIMIT 1", (failedShortName,))
    if not nodeInfo:
        return {
            "partner_name": failedShortName,
            "impact_level": "High",
            "action_plan": "즉시 공급망 정밀 실사단 파견 필요",
            "risk_propagated": True,
            "propagation_path": []
        }
        
    rawId = nodeInfo['raw_id']
    failedTier = nodeInfo['tier']
    affectedChain = db.findAll("""
        SELECT tier, short_name, item_name FROM RM_TIER_TREE 
        WHERE raw_id = %s AND tier < %s ORDER BY tier DESC
    """, (rawId, failedTier))

    propagationPath = [{"tier": failedTier, "short_name": failedShortName, "status": "위험 발생원 🔴"}]
    for row in affectedChain:
        propagationPath.append({
            "tier": row["tier"],
            "short_name": row["short_name"],
            "status": f"간접 리스크 전파 ⚠️ ({row['item_name']} 공급망 오염)"
        })
        
    return {
        "risk_propagated": True,
        "raw_id": rawId,
        "danger_level": "고위험 (High Risk)",
        "propagation_path": propagationPath,
        "action_plan": "즉시 상위 공급망 납품 검역 강화 및 대체 소싱(Alternative Sourcing) 프로세스 가동"
    }

def saveAiInferenceLog(partnerName: str, query: str, resultText: str, status: str, riskChain: dict, aiModel: str, duration: float):
    """
    [변경 완료] 새롭게 정의된 edu.AI_LOGS 테이블 스키마에 맞춰
    LLM 추론 결과 및 평가 로그를 MariaDB에 적재합니다.
    """
    # 1. 딕셔너리 형태의 risk_chain 데이터를 문자열 포맷(JSON)으로 직렬화
    riskChainJson = json.dumps(riskChain, ensure_ascii=False)
    
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
            partnerName, 
            query, 
            resultText,  # ai_evaluation 컬럼에 매핑
            status,       # judgement_status 컬럼에 매핑
            riskChainJson, 
            aiModel, 
            duration      # inference_duration 컬럼에 매핑
        ))
        safePrint(f"[DB 로그 적재 성공] AI_LOGS 테이블에 '{partnerName}' 업체의 ESG 감사 이력이 보관되었습니다.")
    except Exception as e:
        safePrint(f"[DB 로그 적재 실패] AI_LOGS 적재 중 SQL 오류 발생: {e}")


def processEsgComplianceQuery(userQuery: str, partnerName: str) -> dict:
    """
    [수정 완성본] 무거운 MariaDB 텍스트 조회를 완전히 제거하고,
    정제된 완성본 JSONL 온톨로지 캐시 데이터 + 비정형 PDF 하이브리드 검색 컨텍스트를 결합하여
    다형성 규칙 판정 및 보수적 가드레일을 수행하는 통합 감사 리포팅 파이프라인
    """
    global _ONTOLOGY_REGISTRY
    startTime = time.time()
    
    # 1. 사용자 쿼리에서 수치 데이터 및 불리언 경향 동적 분석
    userNumbers = re.findall(r"\d+\.\d+|\d+", userQuery)
    userVal = float(userNumbers[0]) if userNumbers else None    
    # 간단한 불리언 판별 가드레일 (쿼리에 특정 키워드가 발견되면 기본 Y 상태로 간주)
    userBool = "Y" if any(kwd in userQuery for kwd in ["확인", "발생", "검출", "1건", "있음", "탈락"]) else "N"
    
    # 2. [최적화] MariaDB 대신 로컬 온톨로지 사전을 탐색하여 텍스트 컨텍스트 및 매칭 지표 추출
    localOntologyContexts = []
    keywords = re.findall(r'[a-zA-Z가-힣0-9]+', userQuery)
    matchedIndicator = None
    
    if keywords:
        for kwd in keywords:
            for indName, spec in _ONTOLOGY_REGISTRY.items():
                # 검색어 키워드가 지표명이나 원문 문항 텍스트에 포함되어 있는지 매칭
                if kwd in indName or kwd in spec["raw_text"]:
                    if not matchedIndicator:
                        matchedIndicator = indName
                    localOntologyContexts.append(
                        f"[정제 완료 마스터 가이드라인] 지표명: {indName} | 기준문항: {spec['raw_text']}"
                    )
    
    # 3. 비정형 PDF 증빙 문서 대상 하이브리드(Vector + BM25) 리트리버 가동
    vectordbContexts = searchHybridDocuments(userQuery, topK=2)    
    # 지식 구조 컨텍스트와 문서 데이터 컨텍스트 병합
    combinedContexts = localOntologyContexts + vectordbContexts
    contextStr = "\n".join(combinedContexts) if combinedContexts else "참조 가능한 마스터 가이드라인 및 증빙 문서가 존재하지 않습니다."
    
    # ════════════════════════════════════════════════════════
    # ⚖️ 온톨로지 템플릿 Registry 기반 동적 규칙 검증 및 판정 레이어
    # ════════════════════════════════════════════════════════
    judgementStatus = "검토 필요"
    actionPlan = "정확한 매칭 기준이 없으므로 담당자 수동 검토 및 재실행 요망"
    
    # 매칭된 지표 규칙이 사전에 존재한다면 다형성(Type) 판정 엔진 작동
    if matchedIndicator:
        judgementStatus, fileSpecificAction = evaluateEsgByOntology(
            matchedIndicatorName=matchedIndicator,
            userVal=userVal,
            userBool=userBool
        )
        # 이제 .jsonl 파일에서 추출된 커스텀 조치 계획이 불합격 시 action_plan에 완벽히 주입됩니다.
        if judgementStatus == "불합격":
            actionPlan = fileSpecificAction
        elif judgementStatus == "합격":
            actionPlan = "마스터 기준 충족. 특이사항 없음"

    # ════════════════════════════════════════════════════════
    # 🚨 [최우선 가드레일] 인권/아동/강제노동 관련 위반 차단 레이어
    # ════════════════════════════════════════════════════════
    # 온톨로지 판정 결과보다 우선하여 무조건 불합격 처리하는 최상위 시스템 가드레일
    if any(kwd in userQuery for kwd in ["아동", "강제노동", "인권위반"]):
        if (userVal is not None and userVal > 0) or userBool == "Y":
            judgementStatus = "불합격"
            actionPlan = "① 즉시 공급 중단 ② CSDDD 이행계획서 징구 및 현장 정밀 실사단 파견"
    
    # 🎯 [사후 검증] 철 함량 강제 가드레일 (기존 유지)
    if any(kwd in userQuery for kwd in ["Fe", "철", "Fe(철)"]) and userVal is not None and userVal > 0.70:
        judgementStatus = "불합격"
        actionPlan = "① 즉시 공급 중단 및 공정 전수조사 ② 원자재 공급사 변경 검토 ③ 성분 분석 성적서(수입검사재) 재요구"

    # 4. 공급망 리스크 전파 경로 분석 호출 및 구조화
    riskChain = getSupplyChainRiskReport(partnerName, judgementStatus)
    
    if judgementStatus == "불합격":
        # 트리 기반 연쇄 전파 플랜이 특별히 정의되지 않았다면 사용자가 파일에 명시해둔 커스텀 조치 방안을 주입합니다.
        if not riskChain.get("propagation_path"):
            riskChain["action_plan"] = actionPlan
        else:
            # 연쇄 리스크가 전파되는 경우 트리 추적 리포트의 행동 양식을 최우선 활용하되, 본문에 병합 가능
            actionPlan = riskChain.get("action_plan", actionPlan)
    else:
        riskChain["action_plan"] = "정기 모니터링 및 분기별 ESG 데이터 업데이트 트래킹"
        actionPlan = riskChain["action_plan"]
    
    # 5. 생성 인공지능 기반 감사 리포트 구성
    prompt = (
        f"Context:\n{contextStr}\n\n"
        f"Query: {userQuery}\n"
        f"Strict Evaluation Status: {judgementStatus}\n"
        f"Enforced Action Plan: {actionPlan}\n\n"
        f"[지침 사항 - 반드시 준수할 것]\n"
        f"1. 당신은 엄격한 ESG 공급망 감사관입니다.\n"
        f"2. 시스템이 판단한 결과인 'Strict Evaluation Status'({judgementStatus})를 리포트 표의 [평가 상태] 및 결론에 절대 변조 없이 그대로 출력하십시오.\n"
        f"3. 만약 상태가 '불합격' 또는 '검토 필요'라면, 표의 평가 상태를 **불합격** 또는 **검토 필요**로 명시하고 리포트 톤앤매너를 엄격한 경고조로 작성하십시오.\n"
        f"4. 'Enforced Action Plan'에 명시된 조치 계획 수칙을 '위험 조치 계획' 섹션에 누락 없이 마크다운 리스트로 포함하십시오.\n\n"
        f"위 데이터와 지침을 기초로 협력사 감사 리포트를 Markdown 양식으로 구성해 주세요."
    )
    
    targetModel = settings.mariadb_ollama_model    
    try:
        aiResp = ollamaClient.generate(model=targetModel, prompt=prompt)["response"]
    except Exception as e:
        aiResp = f"LLM 생성 실패.\n상태: {judgementStatus}\n조치방안: {actionPlan}"

    inferenceDuration = time.time() - startTime
    
    # 디버깅/보존용 인스턴스 로깅 (필요시 주석 해제)
    saveAiInferenceLog(partnerName, userQuery, aiResp, judgementStatus, riskChain, targetModel, inferenceDuration)
    
    return {
        "evaluation_result": aiResp,
        "judgement_status": judgementStatus,
        "risk_chain_analysis": riskChain
    }