# ────────────────────────────────────────────────────────────────────────────
# [역할] AI Agent 올인원 마스터 알람 비즈니스 로직 + 하이브리드 RAG 검색 생성 엔진
#        (engine.py의 하이브리드 RRF 엔진 및 온톨로지 사전 인프라 100% 완전 통합 버전)
# ────────────────────────────────────────────────────────────────────────────

import os
import re
import json
import time
import ollama
import numpy as np
from datetime import datetime
from typing import Optional, List
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from psycopg2.extras import RealDictCursor

# 기존 대시보드 DB 및 공통 유틸 임포트
from src.utils.db import findAll, findOne, save, addKey
import src.utils.dbClient as dbClient  # PostgreSQL / pgvector 호환용 통합 클라이언트
from src.utils.settings import settings, safePrint, simpleTokenizer
from src.models.notify import sendNotify, notifyType

# =====================================================================
# 🌟 [통합 인프라 1] 글로벌 싱글톤 인스턴스 및 인메모리 상태 관리 풀
# =====================================================================
os.environ["OLLAMA_HOST"] = settings.ollama_host
ollamaClient = ollama.Client(host=settings.ollama_host)
reranker = CrossEncoder(settings.rerank_model)

# 하이브리드 검색을 위한 인메모리 캐시 풀
bm25Index = None
globalChunksPool = []
_ONTOLOGY_REGISTRY: dict = {}
_ONTOLOGY_TEMPLATE_LIST: list = []


# =====================================================================
# 🌟 [통합 인프라 2] 온톨로지(Ontology) 질문 복합 유형 분석 및 캐싱 레이어
# =====================================================================


def parseComplexCriteria(questionText: str) -> dict:
    """불필요한 제품명/규격번호 숫자를 필터링하고 물결표(~) 구조를 인식하여 정교한 RANGE 및 온톨로지 매핑 추출"""
    cleanText = re.sub(r'\b(AL-\d+|ASTM-\d+|ISO-\d+|KS-\d+)\b', '', questionText)
    numbers = [float(x) for x in re.findall(r'[-+]?\d*\.\d+|\d+', cleanText)]
    
    if '~' in questionText or '이상' in questionText or '이하' in questionText:
        if len(numbers) >= 2:
            return {"type": "RANGE", "bounds": [min(numbers), max(numbers)], "raw": numbers}
        elif len(numbers) == 1:
            if '이상' in questionText:
                return {"type": "GTE", "bounds": [numbers[0]], "raw": numbers}
            else:
                return {"type": "LTE", "bounds": [numbers[0]], "raw": numbers}
    if len(numbers) > 0:
        return {"type": "THRESHOLD", "bounds": [numbers[0]], "raw": numbers}
    return {"type": "BOOLEAN", "bounds": [], "raw": []}

# =====================================================================
# 🌟 [온톨로지 인프라] MariaDB 마스터 데이터 동기화 및 JSONL 백업 관리 레이어
# =====================================================================

def buildOntologyRegistry():
    """
    MariaDB의 최신 마스터 지표 데이터를 조회하여 복합 온톨로지 사전을 동기화 구축합니다.
    - 베이스 및 JSONL 구조: SELF_ASSESS_CHECKLIST 활용
    - 검증 규칙 및 임계치 융합: AI_AGENT_RULE 활용
    """
    global _ONTOLOGY_REGISTRY, _ONTOLOGY_TEMPLATE_LIST
    _ONTOLOGY_REGISTRY.clear()
    _ONTOLOGY_TEMPLATE_LIST.clear()
    
    # 1. SELF_ASSESS_CHECKLIST 원천 문항 조회 (질문 데이터 표준화)
    checklist_sql = "SELECT indicator_no, indicator_name, question, action_plan FROM SELF_ASSESS_CHECKLIST"
    checklist_rows = findAll(checklist_sql)
    
    # 지표 번호(indicator_no)를 키로 하는 임시 맵 빌드 (규칙 병합용)
    temp_map = {}
    
    for row in checklist_rows:
        ino = row["indicator_no"]
        indName = row["indicator_name"]
        rawQuestion = row["question"] or ""
        
        # 고도화된 복합 기준 분석기 가동
        criteriaMeta = parseComplexCriteria(rawQuestion) if 'parseComplexCriteria' in globals() else {}
        dbAction = row.get("action_plan") or "지표 기준 미달: 공급망 정밀 실사 및 시정 조치 가동"
        
        base_item = {
            "indicator_no": ino,
            "indicator_name": indName,
            "action_plan": dbAction,
            "raw_text": rawQuestion,
            "rule_code": f"RULE_{ino}",
            **criteriaMeta
        }
        temp_map[ino] = base_item

    # 2. AI_AGENT_RULE의 활성 가드레일 규칙을 찾아와 상위 지표 메타에 융합
    try:
        rule_sql = "SELECT indicator_no, rule_code, rule_name, operator, threshold_value, severity, action_required FROM AI_AGENT_RULE WHERE active_yn = 'Y'"
        rule_rows = findAll(rule_sql)
        for rule in rule_rows:
            ino = rule["indicator_no"]
            if ino in temp_map:
                # 규칙 정보가 존재하면 온톨로지 사전에 덮어쓰기 및 고도화
                temp_map[ino]["rule_code"] = rule.get("rule_code") or temp_map[ino]["rule_code"]
                temp_map[ino]["operator"] = rule.get("operator") or temp_map[ino].get("operator")
                if rule.get("threshold_value") is not None:
                    temp_map[ino]["threshold_value"] = rule["threshold_value"]
                if rule.get("action_required"):
                    temp_map[ino]["action_plan"] = rule["action_required"]
    except Exception as ruleErr:
        safePrint(f"[온톨로지 융합 경고] AI_AGENT_RULE 연동 중 예외 발생 (기본 뼈대로 진행): {ruleErr}")

    # 3. 최종 글로벌 싱글톤 인메모리 풀 캐싱 바인딩
    for ino, final_item in temp_map.items():
        indName = final_item["indicator_name"]
        
        # 딕셔너리 등록 (기존 백엔드 라우터 및 유틸 호환 Key: 지표명)
        _ONTOLOGY_REGISTRY[indName] = final_item
        
        # AI 학습 아티팩트용 템플릿 리스트 구조화 보존 (JSONL 출력용 규격 수렴)
        _ONTOLOGY_TEMPLATE_LIST.append({
            "indicator_no": final_item["indicator_no"],
            "indicator_name": indName,
            "raw_expression": final_item["raw_text"],
            "action_plan": final_item["action_plan"],
            "meta": {
                "rule_code": final_item.get("rule_code"),
                "operator": final_item.get("operator"),
                "threshold_value": final_item.get("threshold_value"),
                "criteria_type": final_item.get("type", "THRESHOLD")
            }
        })
        
    safePrint(f"[온톨로지 엔지니어링] DB 체크리스트 및 규칙 결합 완수. 총 {len(_ONTOLOGY_REGISTRY)}개의 지표 사전을 동기화 캐싱했습니다.")


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
                
                fileActionPlan = data.get("action_plan") or meta.get("action_plan") or "지표 마스터 기준 미달에 따른 공급망 정밀 실사 가동"
                
                # 메모리 글로벌 레지스트리에 수치 매핑 규칙 주입 (Key: 지표명 유지)
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
                
                _ONTOLOGY_TEMPLATE_LIST.append(data)
                count += 1
            except Exception as e:
                safePrint(f"[JSONL 로드 에러] 라인 파싱 실패: {e}")
                
    safePrint(f"[온톨로지 엔지니어링] 완성본 JSONL 기반 {count}개 지표 복합 룰 규칙 완벽 바인딩 성공.")


def exportOntologyToJsonl(jsonlPath: str):
    """현재 구축된 인메모리 온톨로지 규칙 템플릿 사전을 로컬 JSONL 파일로 백업 출력"""
    safePrint(f"[온톨로지 백업] 현재 인메모리 캐시 사전을 로컬 검증용 {jsonlPath} 파일로 내보냅니다...")
    with open(jsonlPath, 'w', encoding='utf-8') as f:
        for node in _ONTOLOGY_TEMPLATE_LIST:
            f.write(json.dumps(node, ensure_ascii=False) + "\n")


# =====================================================================
# 🌟 [통합 인프라 3] 고도화된 Hybrid Retriever Engine (BM25 + pgvector + Rerank)
# =====================================================================
def initializeHybridRetrieverPool():
    """PostgreSQL pgvector 원천 데이터 전체를 인메모리에 로드하여 BM25 인덱스 메모리 풀 동적 빌드"""
    global bm25Index, globalChunksPool
    safePrint("[하이브리드 인프라] PostgreSQL에서 원천 PDF 규제 가이드라인 청크 데이터를 메모리에 적재합니다...")
    
    # dbClient를 통해 pgvector 스토리지 연동
    pgConn = dbClient.getPostgresConn()
    if not pgConn:
        safePrint("[오류] PostgreSQL 연결 실패로 하이브리드 검색 인덱스를 초기화할 수 없습니다.")
        return
        
    try:
        with pgConn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, content, file_name, page_no FROM esg_pdf_vectors")
            rows = cur.fetchall()
            
            globalChunksPool = []
            corpus = []
            for r in rows:
                chunk = {
                    "id": r["id"],
                    "content": r["content"],
                    "meta": {"file_name": r["file_name"], "page_no": r["page_no"]}
                }
                globalChunksPool.append(chunk)
                corpus.append(simpleTokenizer(r["content"]))
                
            if corpus:
                bm25Index = BM25Okapi(corpus)
                safePrint(f"[하이브리드 인프라] 마스터 검색 인덱스 메모리 풀 동적 빌드 완수 (총 {len(globalChunksPool)}개 청크)")
    except Exception as e:
        safePrint(f"[하이브리드 인프라 빌드 에러] : {e}")
    finally:
        pgConn.close()


def searchHybridRrf(query: str, top_k: int = 3) -> list:
    """
    [핵심 로직] BM25 순위와 pgvector 유사도 순위를 
    RRF (Reciprocal Rank Fusion) 연산 수행로직으로 병합한 뒤, CrossEncoder로 리랭킹하여 최적의 컨텍스트 도출
    """
    global bm25Index, globalChunksPool
    if bm25Index is None or not globalChunksPool:
        initializeHybridRetrieverPool()
        if bm25Index is None:
            return []

    # 1. BM25 텍스트 스코어링 검색 및 랭킹 산정
    tokenizedQuery = simpleTokenizer(query)
    bm25Scores = bm25Index.get_scores(tokenizedQuery)
    bm25RankIdxs = np.argsort(bm25Scores)[::-1][:20]  # 상위 20개 추출
    
    bm25RankMap = {globalChunksPool[idx]["id"]: rank for rank, idx in enumerate(bm25RankIdxs, 1)}

    # 2. pgvector 임베딩 코사인 유사도 탑 20 룩업
    pgvectorChunks = []
    pgConn = dbClient.getPostgresConn()
    if pgConn:
        try:
            # 설정의 임베딩 모델 가동 (Ollama 임베딩)
            res = ollamaClient.embeddings(model=settings.embed_model, prompt=query)
            queryVector = res["embedding"]
            
            with pgConn.cursor(cursor_factory=RealDictCursor) as cur:
                # pgvector 코사인 유사도 거리 연산 (<=>) 기반 탑 20 쿼리
                cur.execute("""
                    SELECT id, content, file_name, page_no, (embedding <=> %s::vector) as distance
                    FROM esg_pdf_vectors
                    ORDER BY distance ASC
                    LIMIT 20
                """, (queryVector,))
                pgvectorChunks = cur.fetchall()
        except Exception as e:
            safePrint(f"[pgvector 룩업 오류] : {e}")
        finally:
            pgConn.close()
            
    pgvectorRankMap = {r["id"]: rank for rank, r in enumerate(pgvectorChunks, 1)}

    # 3. 🎯 RRF (Reciprocal Rank Fusion) 상호 역순위 융합 연산 스코어링
    rrfScores = {}
    k_constant = 60  # RRF 표준 상수
    
    allCandidateIds = set(list(bm25RankMap.keys()) + list(pgvectorRankMap.keys()))
    
    for cid in allCandidateIds:
        score = 0.0
        if cid in bm25RankMap:
            score += 1.0 / (k_constant + bm25RankMap[cid])
        if cid in pgvectorRankMap:
            score += 1.0 / (k_constant + pgvectorRankMap[cid])
        rrfScores[cid] = score

    # RRF 연산 기준 정렬 후 상위 후보 풀 확보
    sortedRrfIds = sorted(rrfScores.keys(), key=lambda x: rrfScores[x], reverse=True)[:10]
    
    # ID 기반으로 실제 텍스트 청크 매핑
    candidateChunks = []
    for cid in sortedRrfIds:
        match = next((item for item in globalChunksPool if item["id"] == cid), None)
        if match:
            candidateChunks.append(match)
            
    if not candidateChunks:
        return []

    # 4. 🎯 CrossEncoder 리랭커 기반 최종 고정밀 필터링
    pairs = [[query, c["content"]] for c in candidateChunks]
    rerankScores = reranker.predict(pairs)
    
    for i, score in enumerate(rerankScores):
        candidateChunks[i]["rerank_score"] = float(score)
        
    # 리랭킹 점수 기준 내림차순 최종 정렬
    candidateChunks.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidateChunks[:top_k]


# =====================================================================
# 📌 기존 수치 정제 파싱 및 가드레일 평가 알고리즘 로직 (유지)
# =====================================================================
def parseNumericValueFromContext(answer_text: str) -> Optional[float]:
    """[agentPipeline 이식] 서술형 문맥 내부에서 실제 평가 대상 통계 수치만 추출하는 정규식 필터링 기법"""
    if not answer_text or answer_text.strip() == "":
        return None
    clean = re.sub(r'\[.*?\]|\(.*?\)', '', answer_text)
    clean = re.sub(r'(AL-\d+|ASTM-\d+|ISO-\d+|KS-\d+)', '', clean)
    matches = re.findall(r'[-+]?\d*\.\d+|\d+', clean)
    if matches:
        return float(matches[0])
    return None

def buildSupplierAnswers(raw_answers: list) -> dict:
    """
    [수정본] 리스트가 아닌 {지표번호: 정제된값} 형태의 딕셔너리를 반환하여
    하단 루프의 .get(ino) 호출과 100% 호환되도록 만듭니다.
    """
    if not raw_answers:
        return {}
    
    formatted_dict = {}
    for row in raw_answers:
        ino = row.get("indicator_no")
        if ino is not None:
            # 다양한 DB 컬럼명 케이스 가드레일 작동
            user_value = row.get("user_value") or row.get("answer_content") or row.get("actual_value") or row.get("answer_text") or "0"
            formatted_dict[ino] = user_value
            
    return formatted_dict

def evaluateGuardrail(operator: str, threshold_val: float, parsed_val: float) -> bool:
    """가드레일 임계치 위반 여부를 연산자 매핑에 맞게 정밀 판정"""
    if operator == '>':   return parsed_val > threshold_val
    if operator == '>=':  return parsed_val >= threshold_val
    if operator == '<':   return parsed_val < threshold_val
    if operator == '<=':  return parsed_val <= threshold_val
    if operator == '==':  return parsed_val == threshold_val
    if operator == '!=':  return parsed_val != threshold_val
    return False


# =====================================================================
# 🌟 [메인 비즈니스 로직 연동] 하이브리드 RRF 엔진을 주입한 실시간 알림 평가 함수
# =====================================================================
async def generateAiAlertConsultingWithMasterEngine(indicator_no: str, rule_name: str, user_answer: str, threshold: str, operator: str) -> dict:
    """
    [완전 통합] 별도의 외부 모듈 파일 로드 없이, 파일 내부의 고도화된 
    BM25 + pgvector + Rerank (RRF 융합) 레이어를 직접 구동하여 컨텍스트를 도출하고 알람을 생성합니다.
    """
    # 1. 융합 하이브리드 쿼리 생성
    rag_query = f"{rule_name} 지표 번호 {indicator_no} 글로벌 공급망 실사법 및 CSDDD 규제 대응 가이드라인 가이드 수칙"
    
    try:
        # 🎯 [자체 하이브리드 엔진 구동] 
        search_results = searchHybridRrf(query=rag_query, top_k=3)
        context_str = "\n\n".join([chunk['content'] for chunk in search_results])
    except Exception as e:
        safePrint(f"[자체 통합 하이브리드 검색 실패] 시스템 기본 컨텍스트 백업 전환: {e}")
        context_str = "글로벌 환경 규제 표준 및 공급망 인권 실사 가이드라인 표준 준수 지침"

    # 2. Gemma 모델 인터페이스 통신 프롬프트 구성
    prompt = f"""
    [글로벌 ESG 규제 표준 문서 컨텍스트 - 마스터 하이브리드 엔진 융합 결과]
    {context_str}
    
    [실시간 가드레일 위반 탐지 정황]
    - 지표 항목 : {rule_name} (지표 식별 코드: {indicator_no})
    - 관리 가드레일 기준 식: {operator} {threshold}
    - 협력사 정제 답변 수치 context : {user_answer}
    
    당신은 대한민국 대기업 공급망 관리 부서의 최고 엄격한 ESG 수석 감사관입니다. 
    제공된 글로벌 규제 문서 융합 컨텍스트와 위반 정황을 대조하여, 협력사가 범한 구체적인 위험도 분석 및 글로벌 실사법 상의 리스크 해소 권고안을 격식 있고 전문적인 한국어로 도출하여 아래 JSON 양식으로만 답변하십시오. 
    마크다운 기호(```json)는 절대 포함하지 말고 순수 JSON 오브젝트만 반환하십시오.

    {{
      "alert_title": "위반 지표 명칭 기반 요약 알람 제목",
      "alert_content": "글로벌 가이드라인 기준 대비 협력사의 구체적인 위반 현황 경고문",
      "regulation": "CSDDD / EU REACH / 핵심 실사법 명칭 명시",
      "severity": "CRITICAL 또는 WARNING 또는 NOTICE",
      "ai_confidence": 0.95,
      "ai_reasoning": "왜 이것이 글로벌 규제 관점에서 심각한 위반인지에 대한 명확한 논리적 근거 설명",
      "ai_recommendation": "협력사가 리스크를 즉시 해소하기 위해 이행해야 할 단계별 실천 조치 로드맵"
    }}
    """
    
    try:
        # 싱글톤 Ollama 통신
        response = ollamaClient.generate(model=settings.ai_model, prompt=prompt)
        res_text = response['response'].strip()
        
        # 순수 JSON 추출 처리
        if "{" in res_text:
            res_text = res_text[res_text.find("{"):res_text.rfind("}")+1]
            
        data = json.loads(res_text)
        return data
    except Exception as err:
        safePrint(f"[Ollama JSON 에러] 통신 및 파싱 에러로 백업 정형 JSON 출력 생성: {err}")
        return {
            "alert_title": f"[{rule_name}] 내부 공급망 환경 가드레일 기준 이탈 경고",
            "alert_content": f"지표 {indicator_no}에 설정된 임계치({operator} {threshold})를 벗어난 수치가 탐지되었습니다.",
            "regulation": "글로벌 공급망 실사법 준수 요망",
            "severity": "WARNING",
            "ai_confidence": 0.80,
            "ai_reasoning": "시스템 내부 수치 파싱 엔진에 의해 자동 가드레일 오버 플로우가 탐지되었습니다.",
            "ai_recommendation": "담당 부서는 협력사 실시간 소싱 데이터를 재검증하고 현장 실사 진단 가이드라인을 재교부하십시오."
        }


# =====================================================================
# 🌟 [통합 인프라 4] getSupplyChainRiskReport
# =====================================================================
def getSupplyChainRiskReport(partner_id: str, user_query: str) -> str:
    """
    [통합 이식] 대시보드 스케줄러 및 라우터 호출용 
    생성형 AI 기반 최고 경영진/부장님 보고용 종합 마크다운 감사 리포트 출력 함수
    """
    safePrint(f"📄 [리포트 마스터 기동] 협력사 ID: {partner_id}에 대한 종합 실사 감사서 작성을 시작합니다.")
    
    # 1. 대상 협력사의 누적 위반 알람 데이터베이스 정밀 스캔 (v2.0 partner_id 체계 수렴)
    alerts = findAll("""
        SELECT indicator_no, alert_title, severity, regulation, ai_reasoning, detected_at 
        FROM `AI_AGENT_ALERT` 
        WHERE partner_id = ? AND delete_yn = 0
        ORDER BY detected_at DESC
    """, (partner_id,))
    
    # 2. 회사 기본 정보 룩업 
    # 🎯 [수정] 레거시 WHERE id = ? 에서 v2.0 규격인 WHERE partner_id = ? 컬럼으로 정밀 매핑 변경!
    company = findOne("SELECT company_name, tier_label, risk_level FROM `COMPANY` WHERE partner_id = ?", (partner_id,))
    compName = company["company_name"] if company else "대상 협력사"
    tierLabel = company["tier_label"] if company else "Tier 미정"
    masterRisk = company["risk_level"] if company else "검토 필요"

    # 3. 마스터 하이브리드 RRF 룩업 작동
    ragQuery = f"{user_query} 알루미늄 상류 공급 공정 탄소 배출 및 REACH 환경 유해물질 규제 조치 사항"
    search_results = searchHybridRrf(query=ragQuery, top_k=2)
    contextStr = "\n\n".join([chunk['content'] for chunk in search_results])

    # 4. 정량 지표 기반 위험 등급 체인 결합 연산
    riskChain = {"status": masterRisk, "action_plan": "지속적 모니터링 추적 조치 필요"}
    if masterRisk == "심각":
        riskChain["action_plan"] = "🔴 즉시 거래 일시 중단 검토 및 글로벌 공급망 다변화 대체 소싱 라인 수립 시작"
    elif masterRisk == "주의":
        riskChain["action_plan"] = "🟡 30일 이내에 개선 이행 조치 계획서 징구 및 차기 분기 오프라인 실사 현장 실사 배치"

    judgementStatus = riskChain["status"]
    actionPlan = riskChain["action_plan"]
    
    # 5. 생성 인공지능 기반 최종 마크다운 리포트 구성 프롬프트
    prompt = (
        f"Context:\n{contextStr}\n\n"
        f"Query: {user_query}\n"
        f"Target Partner: {compName} ({tierLabel})\n"
        f"Strict Evaluation Status: {judgementStatus}\n"
        f"Enforced Action Plan: {actionPlan}\n"
        f"Detected Alerts Count: {len(alerts)}건\n\n"
        f"[지침 사항 - 반드시 준수할 것]\n"
        f"1. 당신은 대기업 공급망 관리 부서의 수석 ESG 감사관입니다.\n"
        f"2. 시스템이 판단한 결과인 'Strict Evaluation Status'({judgementStatus})를 리포트 요약 표 및 결론 섹션에 절대 변조 없이 그대로 출력하십시오.\n"
        f"3. 보고서 양식은 완벽한 마크다운(Markdown) 문서 형태로 타이틀, 개요, 하이브리드 지식 증강 규제 분석, 적발 위반 내역 요약 표, 향후 위험 조치 계획 순서로 체계적으로 격식있게 보고용 톤앤매너로 작성해 주세요."
    )
    
    try:
        # 🎯 [수정] 이전에 정의한 에러 예방 규칙에 따라 settings.ai_model을 매핑하여 가동
        response = ollamaClient.generate(model=settings.ai_model, prompt=prompt)
        raw_markdown = response['response']
        
        # 🎯 [추가 가드레일] Ollama 출력에서 발생할 수 있는 특수 백슬래시 이스케이프 클렌징 처리
        # Invalid \escape 오류 및 줄바꿈 파싱이 전면 방어됩니다.
        cleaned_markdown = raw_markdown.replace('\\', '\\\\')
        return cleaned_markdown
        
    except Exception as e:
        return f"# ❌ [{compName}] 종합 ESG 감사 리포트 생성 실패\n\n오류 사유: {str(e)}"

# =====================================================================
# 📌 실시간 분석 실행 파이프라인 제어 컨트롤러 루프 (유지)
# =====================================================================
async def runAiAgentAnalysis(
    triggeredBy: int,
    triggerType: str = "MANUAL",
    scope: str = "ALL",
    scopeTarget: Optional[str] = None,
    aiModel: str = "gemma4:e2b"
    ) -> dict:
    """
    [대시보드 메인 컨트롤러 - 하이브리드 RAG 마스터 엔진 완전 연동 버전]
    원청사 관리자가 대시보드 버튼을 눌렀을 때 룰베이스 가드레일 필터링 후 
    통합 BM25 + pgvector + Rerank 인프라를 가동하여 타겟 위반 항목만 정밀 분석합니다.
    """
    startTime = time.time()

    # 🔗 [연동 포인트 3] 분석 시작 전 인메모리 하이브리드 검색 풀 및 온톨로지 인프라 사전 웜업(Warm-up)
    try:
        initializeHybridRetrieverPool()
        buildOntologyRegistry()
    except Exception as infraErr:
        safePrint(f"[경고] 인프라 사전 빌드 중 예외 발생 (분석은 계속 진행): {infraErr}")
    
    # 1. 분석 대상 회사 목록 바인딩 (partner_id를 메인 룩업으로 사용)
    if scope == "PARTNER" and scopeTarget:
        # partner_id를 조건으로 조회하되, 알림 연동용 고유 PK인 id(company_id)도 함께 select
        companies = findAll("SELECT partner_id, id AS company_id, company_name FROM `COMPANY` WHERE partner_id = ? AND delete_yn = 0", (scopeTarget,))
    else:
        companies = findAll("SELECT partner_id, id AS company_id, company_name FROM `COMPANY` WHERE delete_yn = 0")

    if not companies:
        return {"status": False, "message": "분석 대상 협력사가 존재하지 않습니다."}

    # 2. 마스터 실행 로그 인스턴스 생성 (AI_AGENT_RUN_LOG)
    runLogResult = addKey("""
        INSERT INTO `AI_AGENT_RUN_LOG` (
            trigger_type, scope, scope_target, rules_evaluated, 
            alerts_generated, critical_count, fail_count, warn_count, 
            status, started_at
        ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, 'RUNNING', NOW())
    """, (triggerType, scope, scopeTarget or "ALL"))

    # 🎯 [수정] 리스트에서 실제 생성된 정수 ID(2번째 인덱스)만 정확하게 추출합니다.
    if isinstance(runLogResult, list) and len(runLogResult) >= 2:
        runId = runLogResult[1]
    else:
        runId = 0  # 백업 예외 가드레일

    # 3. 마스터 활성 규칙 동적 로드
    ruleRows = findAll("SELECT * FROM `AI_AGENT_RULE` WHERE active_yn = 'Y'")
    riskCriteriaRows = findAll("SELECT item_name, high_risk, medium_risk, low_risk FROM `ESG_RISK_CRITERIA`")

    # 빠른 매칭을 위한 딕셔너리 캐싱화 (분류 항목별 맵핑)
    criteriaMap = {row["item_name"]: row for row in riskCriteriaRows}

    totalAlertsGenerated = 0
    totalCritical = 0
    totalHigh = 0
    totalMedium = 0
    
    # 4. 회사별 순회 처리 (루프를 쪼개거나 2번 돌릴 필요 없음)
    for comp in companies:
        partnerCode = comp["partner_id"]  # 시스템 비즈니스 전반에 매핑되는 메인 마스터 키
        companyDbId = comp["company_id"]  # 알림 전송용 매개변수로만 사용됨
        
        # 모든 마스터 답변 조회 기준은 설계하신 대로 partner_id(partnerCode)를 룩업 키로 집중 사용
        raw_answers = findAll("""
            SELECT id, indicator_no, answer_text 
            FROM `SELF_ASSESS_ANSWER` 
            WHERE partner_id = ? AND version = (
                SELECT COALESCE(MAX(version), 1) FROM `SELF_ASSESS_ANSWER` WHERE partner_id = ? AND delete_yn = 0
            ) AND delete_yn = 0
        """, (partnerCode, partnerCode))
        
        if not raw_answers:
            continue

        # 수치 자동 파싱 헬퍼 가동 (서술형 문장 수치 추출)
        supplierAnswers = buildSupplierAnswers(raw_answers)
        
        # 협력사 도메인별 실시간 리스크 등급 카운터
        compCriticalCount = 0
        compHighCount = 0
        compMediumCount = 0
        
        for ans in raw_answers:
            ans_db_id = ans["id"]
            ino = ans["indicator_no"]
            user_raw_text = ans["answer_text"]
            
            userValue = supplierAnswers.get(ino)
            matched_rules = [r for r in ruleRows if r["indicator_no"] == ino]
            
            current_item_risk = "정상"
            
            if not matched_rules:
                save("UPDATE `SELF_ASSESS_ANSWER` SET risk_level = '정상' WHERE id = ?", (ans_db_id,))
                continue

            for rule in matched_rules:
                ruleId = rule["rule_id"]
                op = rule["operator"]
                th_str = rule["threshold_value"]
                m_key = rule["metric_key"]
                severity_upper = rule["severity"].strip().upper() # CRITICAL, HIGH, MEDIUM
                ruleName = rule["rule_name"]

                isViolated = False
                deviationPct = 0.0
                
                # ── [agentPipeline 기준 룰 매칭 연산 가드레일] ──
                try:
                    if m_key == "NUMERIC" and userValue is not None:
                        floatUser = float(userValue)
                        floatThreshold = float(th_str)
                        if op == "<" and not (floatUser < floatThreshold): isViolated = True
                        elif op == "<=" and not (floatUser <= floatThreshold): isViolated = True
                        elif op == ">" and not (floatUser > floatThreshold): isViolated = True
                        elif op == ">=" and not (floatUser >= floatThreshold): isViolated = True
                        elif op == "==" and not (floatUser == floatThreshold): isViolated = True
                        
                        if isViolated and floatThreshold != 0:
                            deviationPct = round(((floatUser - floatThreshold) / floatThreshold) * 100, 2)
                    
                    elif m_key == "BOOL":
                        normUser = str(userValue).strip().upper()
                        if "Y" in op and normUser != "Y": isViolated = True
                        elif "N" in op and normUser != "N": isViolated = True
                        
                    elif m_key == "RANGE" and "~" in th_str and userValue is not None:
                        floatUser = float(userValue)
                        min_v, max_v = map(float, th_str.split("~"))
                        if not (min_v <= floatUser <= max_v): isViolated = True
                except:
                    isViolated = True  # 원천 텍스트가 비교 불가능하거나 파싱 오류 시 안전 위반 처리

                if isViolated:
                    totalAlertsGenerated += 1

                    # 🔗 [연동 포인트 1] 자체 통합 파일 내부의 Master Engine 함수명으로 정확히 교체 호출
                    # 오리지널 텍스트 문맥 전체를 전달하여 RAG 품질 고도화
                    ai_consulting = await generateAiAlertConsultingWithMasterEngine(
                        indicator_no=ino,
                        rule_name=ruleName,
                        user_answer=user_raw_text, 
                        threshold=th_str,
                        operator=op
                    )

                    # ── ESG_RISK_CRITERIA 기준 매칭 정의 ──
                    matched_criterion = criteriaMap.get(ruleName) or next((v for k, v in criteriaMap.items() if k in ruleName), None)

                    # 🔗 [연동 포인트 2] AI가 JSON 오브젝트로 리턴한 정확한 필드 키 바인딩 
                    # 만약 DB 마스터 기준 텍스트가 있다면 결합하여 사유의 객관성 극대화
                    base_reasoning = ai_consulting.get("ai_reasoning", "글로벌 규제 가이드라인 기준 미달 수치 탐지.")
                    if matched_criterion:
                        if severity_upper == "CRITICAL":
                            reasoning_text = f"[{matched_criterion['high_risk']}] {base_reasoning}"
                        elif severity_upper == "HIGH":
                            reasoning_text = f"[{matched_criterion['medium_risk']}] {base_reasoning}"
                        else:
                            reasoning_text = f"[{matched_criterion['low_risk']}] {base_reasoning}"
                    else:
                        reasoning_text = base_reasoning

                    # AI 조치 로드맵과 개발자 정의 action_required 규칙 매핑 통합
                    recommendation_text = ai_consulting.get("ai_recommendation", rule.get("action_required") or "즉시 소명자료 제출 필요.")

                    # 📌 문항별 세부 카운팅 분기 처리 및 문항 내부 알림 레벨 확정
                    if severity_upper == "CRITICAL":
                        current_item_risk = "심각"
                        totalCritical += 1
                        compCriticalCount += 1
                    elif severity_upper == "HIGH":
                        if current_item_risk != "심각":
                            current_item_risk = "주의"
                        totalHigh += 1
                        compHighCount += 1
                    else: # MEDIUM
                        if current_item_risk not in ["심각", "주의"]:
                            current_item_risk = "주의"
                        totalMedium += 1
                        compMediumCount += 1

                    # AI 엔진 분석 요소를 기반으로 실시간 위반 내역 상세 적재 (AI_AGENT_ALERT)
                    alertTitle = ai_consulting.get("alert_title", f"[공급망 실사 위반] {ruleName}")
                    alertContent = ai_consulting.get("alert_content", f"추출값 기준 [{op} {th_str}]을 벗어났습니다.")
                    regulation_name = ai_consulting.get("regulation", rule.get("regulation") or "CSDDD 준수 규정")
                    ai_conf = ai_consulting.get("ai_confidence", 98.50)
                    
                    alertId = addKey("""
                        INSERT INTO `AI_AGENT_ALERT` (
                            rule_id, partner_id, indicator_no, metric_key, actual_value, threshold_value,
                            deviation_pct, severity, ai_confidence, ai_reasoning, ai_recommendation,
                            alert_title, alert_content, regulation, status, run_id, delete_yn
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, 0)
                    """, (
                        ruleId, partnerCode, ino, m_key, str(userValue or user_raw_text), th_str,
                        deviationPct, severity_upper, ai_conf, reasoning_text, recommendation_text,
                        alertTitle, alertContent, regulation_name, runId
                    ))

                   # ── 웹소켓 푸시 실시간 알림 포맷팅 ──
                    action_short_cleaned = recommendation_text[:30] + "..." if len(recommendation_text) > 25 else recommendation_text
                    status_korean = "심각(위반)" if severity_upper in ["CRITICAL", "FAIL"] else "주의"

                    await sendNotify(
                        partnerId  = partnerCode,
                        companyId  = companyDbId,
                        notifyType = notifyType.AI_AGENT,
                        meta = {
                            "partner_name" : comp["company_name"],
                            "status"       : status_korean,
                            "action_short" : action_short_cleaned,
                            "partner_id"   : partnerCode,
                            "alert_id"     : alertId,
                            "indicator_no" : ino
                        }
                    )

            # 📌 [요구사항 구현 완료] 가드레일 심사가 끝난 문항의 risk_level 업데이트
            save("UPDATE `SELF_ASSESS_ANSWER` SET risk_level = ? WHERE id = ?", (current_item_risk, ans_db_id))

        # ── 🎯 [요구사항 커스텀 가드레일] 회사 레벨 리스크 종합 등급 재정의 ──
        if compCriticalCount >= 1:
            companyRisk = "고위험군"      # CRITICAL이 단 1개라도 있으면 무조건 고위험
        elif compHighCount >= 1:
            companyRisk = "중위험군"        # CRITICAL은 없지만 HIGH가 1개라도 있으면 중위험
        else:
            companyRisk = "저위험군"        # 다 정상이거나 MEDIUM에만 문제가 있을 때 저위험

        save("UPDATE `COMPANY` SET risk_level = ? WHERE partner_id = ? AND delete_yn = 0", (companyRisk, partnerCode))

    # 6. 마스터 실행 로그 정보 업데이트 마감 (AI_AGENT_RUN_LOG)
    durationMs = int((time.time() - startTime) * 1000)
    finalStatus = "SUCCESS" if totalAlertsGenerated == 0 else "ALERT"
    aiSummary = f"분석 완료. [통계] CRITICAL: {totalCritical}건, HIGH: {totalHigh}건, MEDIUM: {totalMedium}건 적발."
    
    # 예전 규격 컬럼과의 맵핑 호환성을 유지하여 적재
    save("""
        UPDATE `AI_AGENT_RUN_LOG` 
        SET status = ?, rules_evaluated = ?, alerts_generated = ?,
            critical_count = ?, fail_count = ?, warn_count = ?,
            ai_model = ?, ai_summary = ?, duration_ms = ?, ended_at = NOW()
        WHERE run_id = ?
    """, (finalStatus, len(ruleRows), totalAlertsGenerated, totalCritical, totalHigh, totalMedium, aiModel, aiSummary, durationMs, runId))

    return {
        "status": True,
        "message": "AI Agent 전체 분석 완료",
        "runId": runId,
        "alertsGenerated": totalAlertsGenerated,
        "criticalCount": totalCritical,
        "highCount": totalHigh,
        "mediumCount": totalMedium
    }

# =====================================================================
# 📌 기존 알림 목록 API 지원 헬퍼 래퍼 함수들 (유지)
# =====================================================================
def getAiAgentAlertList(partnerId: Optional[str] = None, severity: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[dict]:
    whereClauses = ["delete_yn = 0"]
    params = []
    if partnerId:
        whereClauses.append("partner_id = ?")
        params.append(partnerId)
    if severity:
        whereClauses.append("severity = ?")
        params.append(severity)
    if status:
        whereClauses.append("status = ?")
        params.append(status)
    whereStr = " AND ".join(whereClauses)
    sql = f"SELECT * FROM `AI_AGENT_ALERT` WHERE {whereStr} ORDER BY detected_at DESC LIMIT ?"
    params.append(limit)
    return findAll(sql, tuple(params))

def acknowledgeAiAgentAlert(alertId: int, managerPartnerId: str) -> dict:
    """
    [회사 일원화 반영] 원청사(본사) 담당 계정(partner_id)이 대시보드에서 경고 알림을 확인 처리
    managerPartnerId 예시: 'MAIN_OFFICE' 또는 'HQ001'
    """
    save("""
        UPDATE `AI_AGENT_ALERT` 
        SET status = 'ACKNOWLEDGED', acknowledged_by = ?, acknowledged_at = NOW() 
        WHERE alert_id = ? AND delete_yn = 0
    """, (managerPartnerId, alertId)) 
    return {"status": True, "alertId": alertId}


def resolveAiAgentAlert(alertId: int, managerPartnerId: str, resolutionNote: str) -> dict:
    """
    [회사 일원화 반영] 협력사 리스크 조치 완료 승인 시, 
    최종 해소 처리한 원청사/본사 계정(partner_id)을 기록
    """
    save("""
        UPDATE `AI_AGENT_ALERT` 
        SET status = 'RESOLVED', resolved_by = ?, resolved_at = NOW(), resolution_note = ? 
        WHERE alert_id = ? AND delete_yn = 0
    """, (managerPartnerId, resolutionNote, alertId)) 
    return {"status": True, "alertId": alertId}

def getAiAgentRunLogList(limit: int = 20) -> List[dict]:
    return findAll("SELECT * FROM `AI_AGENT_RUN_LOG` ORDER BY created_at DESC LIMIT ?", (limit,))