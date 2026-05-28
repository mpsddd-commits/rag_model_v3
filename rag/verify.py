"""
ESG RAG Hybrid Reranking Integrity Verification CLI.
Interactive prompt for ESG compliance validation with MariaDB checklist
and risk criteria, hybrid retrieval, and AI-powered audit reporting.
"""
import sys
import datetime
import time

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
def get_integrity_checked_ai_response(model_name: str, query: str) -> tuple[str, str]:
    # ── 구간 1: BM25 상태 확인 및 복구
    t0 = time.time()
    check_and_ensure_bm25()
    safe_print(f"⏱️ DB & BM25 체크: {time.time() - t0:.2f}초")

    # ── 구간 2: 하이브리드 검색 (Dense + Sparse → Rerank)
    t1 = time.time()
    contexts = search_similar_documents(query, top_k=6, dense_n=50, sparse_n=50)
    safe_print(f"⏱️ 하이브리드 검색 및 리랭킹: {time.time() - t1:.2f}초")

    if not contexts:
        context_text = "⚠️ 현재 DB에 연관된 지표 및 리스크 판정 자료가 존재하지 않습니다."
    else:
        context_text = _format_contexts(contexts)

    strict_prompt = f"""당신은 알루미늄 공급망 Upstream 품질 및 ESG 정합성을 대조 검증하는 AI 실사 수석 감사관입니다.
절대로 SQL 쿼리나 DB 설계 자문을 출력하지 마십시오. 오직 실무 대응 지침 리포트 양식만 출력해야 합니다.

[핵심 지침]
1. [대상 지표 파악]: 사용자 질문에서 검증 지표와 입력 수치를 추출하십시오.
2. [DB 기준값 매칭]: 참고 데이터에서 합격/불합격 기준 수치와 우선순위를 파악하십시오.
3. [판정]: 입력값과 기준치를 수학적으로 대조하여 합격(PASS) 또는 불합격(FAIL)을 판정하십시오.
4. [리스크 등급]: 불합격 시 리스크 판정 마스터 기준으로 고위험🔴/중위험🟡/저위험🟢을 확정하십시오.
   - Critical 지표 불합격 또는 CSDDD/UFLPA/FEOC 직접 위반 시 무조건 고위험🔴.
5. [리포트]: 불합격 시 대처방안을 ①②③ 순번으로 단계별 기재하고 조치 기한을 명시하십시오.

[출력 포맷 - 반드시 이 양식만 출력]
--------------------------------------------------
■ 대상 지표/성분:
■ 입력 데이터 vs DB 기준치:
■ 우선순위 등급:
■ 최종 판정 결과: [합격(PASS) 또는 불합격(FAIL)]
■ 확정 리스크 등급:

[위험 대응 및 해결 리포트]
(합격 시: '기준 이내 정상 확인 (특이사항 없음)')
  ① ...
  ② ...
  ③ ...
■ 후속 조치 권고 기한:
--------------------------------------------------

[참고 데이터 (MariaDB 실시간 연동)]
{context_text}

[사용자 질문]
{query}
"""

    try:
        t2 = time.time()
        # _rag.ollama_client를 직접 사용 (main import 불필요)
        client = _rag.ollama_client
        response = client.generate(model=model_name, prompt=strict_prompt)
        safe_print(f"⏱️ Ollama LLM 추론: {time.time() - t2:.2f}초")

        ai_answer = response["response"]

        has_judgment = any(kw in ai_answer for kw in ["합격", "불합격", "PASS", "FAIL"])
        has_report   = any(kw in ai_answer for kw in ["리포트", "대처방안", "①", "후속 조치"])
        status = "정합성 완벽 통과 (PASS)" if (has_judgment and has_report) else "일반 답변 또는 검증 요망"
        return ai_answer, status

    except Exception as e:
        return f"AI 크로스 검증 중 오류: {e}", "오류 발생 (ERROR)"


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
    run_verification_cli(settings.verify_ollama_model)
