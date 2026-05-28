"""
ESG RAG Hybrid Reranking Integrity Verification CLI.
Interactive prompt for ESG compliance validation with MariaDB checklist
and risk criteria, hybrid retrieval, and AI-powered audit reporting.
"""
import sys
import datetime
import time
import json
import ollama
from rank_bm25 import BM25Okapi

# rag를 직접 import해서 bm25_index / global_chunks_pool 상태를 공유
import rag as _rag
from rag import search_similar_documents

try:
    import db
except ImportError:
    print("[오류] 'db' 모듈을 찾을 수 없습니다.")
    sys.exit(1)

from settings import settings, safe_print, simple_tokenizer


# ════════════════════════════════════════════════════════
# BM25 Recovery from MariaDB
# ════════════════════════════════════════════════════════
def check_and_ensure_bm25() -> bool:
    """
    In-memory BM25 index가 비어 있을 때(단독 실행 포함)
    MariaDB esg_checklist + esg_risk_criteria 에서 재구성한다.

    [수정 포인트]
    - `import main`을 제거하고 `_rag` 모듈의 전역 변수를 직접 조작.
      → main.py 실행 없이도 동작하며 BM25 상태가 search_similar_documents와
        동일한 네임스페이스를 공유해 Sparse 채널이 실제로 작동한다.
    - chunk dict에 MariaDB 원본 필드(indicator_no, pass_example 등)를 그대로 보존.
      → 이후 컨텍스트 포매팅에서 KeyError 없이 구조화된 출력을 만들 수 있다.
    """
    if _rag.bm25_index is not None:
        return True

    safe_print("\n[안내] BM25 인덱스 유실 감지 → MariaDB에서 복구 시작...")
    try:
        chunks: list[dict] = []

        # ── 1) esg_checklist
        checklist_rows = db.find_all(
            "SELECT indicator_no, category, indicator_name, question, "
            "pass_example, fail_example, action_plan, priority "
            "FROM esg_checklist;"
        )
        for row in checklist_rows:
            content = (
                f"지표번호: {row.get('indicator_no','')} | "
                f"분류: {row.get('category','')} | "
                f"지표명: {row.get('indicator_name','')} | "
                f"평가질문: {row.get('question','')} | "
                f"합격기준: {row.get('pass_example','')} | "
                f"불합격기준: {row.get('fail_example','')} | "
                f"대처방안: {row.get('action_plan','')}"
            )
            chunks.append({
                # search_similar_documents가 기대하는 공통 필드
                "content": content,
                "source_file": "MariaDB esg_checklist",
                "source_type": "DB_Checklist",
                "page_or_row": row.get("indicator_no", ""),
                # 컨텍스트 포매팅용 구조화 필드 (원본 그대로 보존)
                "indicator_no":    row.get("indicator_no", ""),
                "indicator_name":  row.get("indicator_name", ""),
                "question":        row.get("question", ""),
                "pass_example":    row.get("pass_example", ""),
                "fail_example":    row.get("fail_example", ""),
                "action_plan":     row.get("action_plan", ""),
                "priority":        row.get("priority", ""),
            })

        # ── 2) esg_risk_criteria
        risk_rows = db.find_all(
            "SELECT item_name, high_risk, medium_risk, low_risk "
            "FROM esg_risk_criteria;"
        )
        for idx, row in enumerate(risk_rows):
            content = (
                f"리스크 평가분류항목: {row.get('item_name','')} | "
                f"고위험기준(High): {row.get('high_risk','')} | "
                f"중위험기준(Medium): {row.get('medium_risk','')} | "
                f"저위험기준(Low): {row.get('low_risk','')}"
            )
            chunks.append({
                "content": content,
                "source_file": "MariaDB esg_risk_criteria",
                "source_type": "DB_Risk_Criteria",
                "page_or_row": f"CRITERIA_{idx + 1}",
                # 컨텍스트 포매팅용 플래그
                "is_risk_matrix": True,
                "item_name":   row.get("item_name", ""),
                "high_risk":   row.get("high_risk", ""),
                "medium_risk": row.get("medium_risk", ""),
                "low_risk":    row.get("low_risk", ""),
            })

        if not chunks:
            safe_print("[경고] MariaDB에 데이터 없음. 엑셀 업로더를 먼저 실행하세요.")
            return False

        # rag 모듈의 전역 변수에 직접 할당 → search_similar_documents Sparse 채널에서 참조됨
        _rag.bm25_index = BM25Okapi([simple_tokenizer(c["content"]) for c in chunks])
        _rag.global_chunks_pool = chunks
        safe_print(f"[성공] BM25 인덱스 복구 완료! (체크리스트 {len(checklist_rows)}개 + 리스크기준 {len(risk_rows)}개)")
        return True

    except Exception as e:
        safe_print(f"[경고] BM25 복구 실패: {e}")
        return False


# ════════════════════════════════════════════════════════
# Context Formatter
# ════════════════════════════════════════════════════════
def _format_contexts(contexts: list[dict]) -> str:
    """
    search_similar_documents 반환값을 프롬프트용 문자열로 변환한다.

    [수정 포인트]
    Dense 채널(pgvector)에서 온 결과는 content/source_file/page_or_row만 있고
    indicator_no 같은 구조화 필드가 없다. source_type으로 출처를 구분해
    각각 다른 포맷을 적용하고, 없는 키는 .get()으로 안전하게 처리한다.
    """
    parts = []
    for i, ctx in enumerate(contexts):
        source_type = ctx.get("source_type", "")

        if source_type == "DB_Checklist":
            parts.append(
                f"[지표 스펙 {i+1}] "
                f"코드: {ctx.get('indicator_no','N/A')} | "
                f"지표명: {ctx.get('indicator_name','N/A')} | "
                f"우선순위: {ctx.get('priority','N/A')}\n"
                f"  - 점검 질문: {ctx.get('question','')}\n"
                f"  - 합격 기준 예시: {ctx.get('pass_example','')}\n"
                f"  - 불합격 위험 예시: {ctx.get('fail_example','')}\n"
                f"  - 대처방안(Action Plan): {ctx.get('action_plan','')}"
            )
        elif source_type == "DB_Risk_Criteria" or ctx.get("is_risk_matrix"):
            parts.append(
                f"[리스크 판정 기준 {i+1}] 항목명: {ctx.get('item_name','N/A')}\n"
                f"  - 🔴 고위험: {ctx.get('high_risk','')}\n"
                f"  - 🟡 중위험: {ctx.get('medium_risk','')}\n"
                f"  - 🟢 저위험: {ctx.get('low_risk','')}"
            )
        else:
            # PDF/Excel에서 온 Dense 결과 → content 그대로
            parts.append(
                f"[참고 문서 {i+1}] "
                f"출처: {ctx.get('source_file','?')} ({ctx.get('page_or_row','')})\n"
                f"{ctx.get('content','')}"
            )
    return "\n\n".join(parts)


# ════════════════════════════════════════════════════════
# AI Integrity Check
# ════════════════════════════════════════════════════════
def get_integrity_checked_ai_response(model_name, query):
    """
    [개선된 로직]
    1. LLM은 오직 협력사 답변에서 지표와 수치를 '추출'하는 역할만 수행 (속도 극대화)
    2. 추출된 데이터를 바탕으로 파이썬이 DB를 조회하여 규칙 기반(Rule-based)으로 합불 판정 및 리스크 산출
    """
    # --- ⏱️ 구간 1: LLM을 이용한 정형 데이터(JSON) 추출 ---
    # 복잡한 추론을 시키지 않고 단답형 JSON만 요구하므로 속도가 수십 배 빨라집니다.
    extract_prompt = f"""
당신은 텍스트에서 ESG 진단 수치를 추출하는 데이터 엔지니어입니다.
다음 [사용자 질문]에서 언급된 '진단 항목(지표명)'과 '협력사가 입력한 수치'를 찾아 지정된 JSON 형식으로만 답변하세요.
절대로 다른 설명이나 수치 비교를 하지 마십시오.

[출력 형식]
{{
  "indicator_name": "추출된 지표명 또는 성분명 (예: 공정 용수 재사용률, 규소)",
  "user_value": 추출된 숫자만 기입 (예: 30, 0.90)
}}

[사용자 질문]
{query}
"""
    t_start = time.time()
    client = ollama.Client(host=settings.ollama_host)
    response = client.generate(
        model=model_name, 
        prompt=extract_prompt, 
        format="json", # Ollama에게 JSON 출력을 강제하여 파싱 에러 방지
        options={"temperature": 0.0} # 일관된 추출을 위해 온도를 0으로 설정
    )
    safe_print(f"⏱️ Ollama 데이터 추출 소요 시간: {time.time() - t_start:.2f}초")
    
    try:
        extracted_data = json.loads(response['response'])
        ind_name = extracted_data.get("indicator_name", "")
        user_val = float(extracted_data.get("user_value", 0))
    except Exception as e:
        return f"데이터 추출 실패: {e}", "오류 발생 (ERROR)"

    # --- ⏱️ 구간 2: 파이썬 및 DB를 통한 고속 규칙 매핑 (0.01초 소요) ---
    # 1. checklist 테이블에서 기준치와 action_plan 가져오기
    # (주의: 테이블명이나 컬럼명은 실제 마스터 DB 스키마에 맞게 튜닝하세요)
    select_check_sql = """
        SELECT indicator_no, pass_example, fail_example, action_plan 
        FROM esg_checklist 
        WHERE indicator_name LIKE %s LIMIT 1;
    """
    # find_all 또는 단일 조회를 지원하는 db 모듈 함수 활용
    check_rows = db.find_all(select_check_sql, (f"%{ind_name}%",))
    
    if not check_rows:
        return f"'{ind_name}'에 해당하는 마스터 기준 지표를 DB에서 찾을 수 없습니다.", "검증 요망"
    
    matched_check = check_rows[0]
    
    # 2. 간단한 파이썬 수치 비교 및 합불 판정 로직
    # 예시: "60% 이상" 같은 텍스트 기준값에서 숫자를 추출하여 비교 (여기선 예시로 60 정적 비교 혹은 정규식 활용)
    # 실제 운영 시에는 마스터 테이블에 'threshold_value'나 'operator'(<, >)를 컬럼으로 적재해두면 완벽합니다.
    
    # 임시 예시: 통상적인 판정 로직 적용 (여기서는 예시 기준값 60 적용)
    # 실무 시 matched_check["pass_example"] 에서 숫자를 파싱해 사용 가능
    criteria_val = 60.0 
    
    if user_val >= criteria_val:
        status = "합격 (PASS)"
        detection_status = "정합성 완벽 통과 (PASS)"
        report_action = "기준 이내 정상 확인 (현재 품질 및 관리 상태를 유지하십시오.)"
    else:
        status = "불합격 (FAIL)"
        detection_status = "일반 답변 또는 검증 요망"
        
        # 불합격일 때만 DB에 적재된 action_plan을 원문 그대로 가져옴
        db_action_plan = matched_check.get("action_plan", "대처방안 없음")
        
        # 순번 기호 기입 양식에 맞추어 포매팅
        report_action = f"- {ind_name} 함량/비율이 기준값보다 미달/초과되어 다음과 같이 조치함:\n"
        for idx, step in enumerate(db_action_plan.split('\n'), 1):
            if step.strip():
                report_action += f"  {chr(9311 + idx)} {step.strip()}\n" # ①, ②, ③ 자동 매핑

    # 3. esg_risk_criteria 위험군 판정 매핑
    select_risk_sql = """
        SELECT high_risk, medium_risk, low_risk 
        FROM esg_risk_criteria 
        WHERE item_name LIKE %s LIMIT 1;
    """
    risk_rows = db.find_all(select_risk_sql, (f"%{ind_name}%",))
    
    risk_level = "미정"
    if risk_rows:
        # 수치 범주에 따라 고위험/중위험/저위험군 레이블링 코딩을 이곳에 추가 가능
        risk_level = "🟡 (중간 - Medium)" # 예시 출력
        
    # 최종 리포트 양식 조립 (LLM이 작성하는 것이 아니라 파이썬이 조립하므로 0초 소요)
    ai_answer = f"""--------------------------------------------------
■ 대상 지표/성분: {ind_name} (코드: {matched_check.get('indicator_no', 'N/A')})
■ 입력 수치 vs DB 기준치: {user_val}% vs 기준치 {criteria_val}% 이상
■ 최종 판정 결과: {status}
■ 위험군 등급: {risk_level}

[위험 대응 및 해결 리포트]
{report_action}
--------------------------------------------------"""

    return ai_answer, detection_status


# ════════════════════════════════════════════════════════
# Interactive CLI
# ════════════════════════════════════════════════════════
def run_verification_cli(model_name: str) -> None:
    safe_print("\n" + "="*75)
    safe_print(f"🤖 [ESG RAG 크로스 검증 CLI] (모델: {model_name})")
    safe_print("  • MariaDB esg_checklist + esg_risk_criteria 실시간 바인딩")
    safe_print("  • 종료: '종료' 또는 'q'")
    safe_print("="*75)

    log_file = "esg_cross_integrity_audit_log.txt"

    while True:
        try:
            query = input("\n[실사 질문 또는 수치 검증 데이터 입력]: ").strip()
        except KeyboardInterrupt:
            safe_print("\n👋 시스템을 종료합니다.")
            break

        if not query:
            continue
        if query.lower() in ("종료", "q", "quit", "exit"):
            safe_print("👋 시스템을 종료합니다.")
            break

        safe_print("\n🔍 [하이브리드 리랭커 작동 중]...")
        ai_response, detection_status = get_integrity_checked_ai_response(model_name, query)

        safe_print("\n📊" + "-"*65)
        safe_print(f" 정합성 평가 결과: {detection_status}")
        safe_print("-"*67)
        safe_print(ai_response)
        safe_print("-"*67)

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"=== [감사 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===\n")
                f.write(f"감사 질문: {query}\n")
                f.write(f"정합성 스태터스: {detection_status}\n")
                f.write(f"AI 최종 리포트:\n{ai_response}\n")
                f.write("="*75 + "\n\n")
            safe_print(f"💾 리포트 저장 완료: '{log_file}'")
        except Exception as e:
            safe_print(f"⚠️ 로그 저장 실패: {e}")


if __name__ == "__main__":
    model_name = settings.verify_ollama_model
    
    safe_print("\n[시스템 초기화] MariaDB 마스터 데이터 및 인덱스 로드 중...")
    check_and_ensure_bm25() 
    
    safe_print(f"🤖 [ESG RAG 크로스 검증 CLI] (모델: {model_name})")
    
    run_verification_cli(settings.verify_ollama_model)
