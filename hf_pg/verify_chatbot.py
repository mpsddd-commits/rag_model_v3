"""
ESG RAG Hybrid Reranking Integrity Verification CLI.
Provides an interactive command-line interface to submit validation questions,
retrieve relevant documents, run strict numerical AI compliance rules, and log results.
"""
import os
import sys
import datetime
import ollama
from rank_bm25 import BM25Okapi

# Import facade runners and core infrastructure
try:
    import main
    from main import (
        search_similar_documents, 
        get_db_connection, 
        simple_tokenizer
    )
except ImportError:
    safe_print("[오류] 'main.py' 파일을 찾을 수 없거나 연동에 실패했습니다.")
    safe_print("이 검증 스크립트는 하이브리드 리랭킹 엔진이 구현된 main.py와 같은 폴더에 있어야 합니다.")
    sys.exit(1)

from config.settings import settings
from utils.helpers import safe_print

# ────────────────────────────────────────────────────────
# 1. BM25 Index Recovery Safeguard for Isolated Runs
# ────────────────────────────────────────────────────────
def check_and_ensure_bm25():
    """
    verify_chatbot.py를 단독 실행했을 때 main.py의 BM25 인덱스가 메모리에 
    로드되어 있지 않은 상태를 방지하기 위해 DB 전수조사 후 인덱스를 자동 복구합니다.
    """
    if getattr(main, 'bm25_index', None) is None:
        safe_print("\n[안내] 메모리 내 BM25 인덱스가 유실되었거나 단독 실행되었습니다. 인덱스 복구를 시작합니다...")
        try:
            conn = get_db_connection(settings.postgres_conn_str)
            cur = conn.cursor()
            
            # Extract all chunk records and metadata from the document store
            cur.execute("SELECT content, source_file, source_type, page_or_row FROM esg_documents;")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            if not rows:
                safe_print("[경고] 데이터베이스에 구축된 지식(esg_documents)이 하나도 없습니다. main.py를 먼저 실행해 주세요.")
                return False
                
            reconstructed_chunks = []
            for row in rows:
                reconstructed_chunks.append({
                    "content": row[0],
                    "source_file": row[1],
                    "source_type": row[2],
                    "page_or_row": row[3]
                })
            
            # Synchronize into main facade (which syncs to search.hybrid_retriever)
            tokenized_corpus = [simple_tokenizer(chunk["content"]) for chunk in reconstructed_chunks]
            main.bm25_index = BM25Okapi(tokenized_corpus)
            main.global_chunks_pool = reconstructed_chunks
            
            safe_print(f"[성공] DB 기반 고성능 BM25 인덱스 복구 완료 ({len(reconstructed_chunks)} 개 청크 매핑)")
            return True
        except Exception as e:
            safe_print(f"[경고] BM25 인덱스 자동 복구 실패: {e}")
            return False
    return True

# ────────────────────────────────────────────────────────
# 2. Strict Numerical Verification Engine (Dense+Sparse Reranked)
# ────────────────────────────────────────────────────────
def get_integrity_checked_ai_response(model_name, query):
    """
    [하이브리드 리랭킹 정합성 검증 엔진]
    1) main.py의 Dense+Sparse 하이브리드 리랭킹 검색 함수 호출로 최고 정합성 컨텍스트 확보
    2) AI 프롬프트 주입 후 데이터 유실 검증 및 원인 분석 수행
    """
    # Ensure BM25 index is active
    check_and_ensure_bm25()
    
    # Retrieve top 3 contexts utilizing hybrid dense-sparse search + reranking
    retrieved_contexts = search_similar_documents(query, top_k=3, dense_n=10, sparse_n=10)
    
    if not retrieved_contexts:
        context = "⚠️ 현재 데이터베이스에 연관된 참고 자료가 전혀 존재하지 않습니다."
    else:
        formatted_context_list = []
        for c_idx, ctx in enumerate(retrieved_contexts):
            search_channel = ctx.get('search_type', 'Hybrid')
            formatted_context_list.append(
                f"[참고 자료 {c_idx+1}] (출처: {ctx['source_file']} | 위치: {ctx['page_or_row']} | 채널: {search_channel})\n내용: {ctx['content']}"
            )
        context = "\n\n".join(formatted_context_list)

    # Multi-rule strict data validation prompt injection
    strict_prompt = f"""당신은 제공된 문서의 데이터 정합성 및 공정 규격을 철저히 검증하고 사후 조치 가이드를 제공하는 기업용 ESG 품질 실사 AI 어시스턴트입니다.

[지침 명령어 - 필수 준수]
1. 입력된 [사용자 질문]이 제공된 [참고 문서]의 지식 범위 안에서 답변이 가능한지 선제적으로 판단하십시오.

2. [★핵심 - 수치 대소 비교 및 규격 판정 룰]:
   - 사용자 질문에 특정 수치(예: 0.25%, 100Mpa)가 포함되어 있고, 참고 문서에 해당 숫자 자체가 직접 언급되지 않았더라도, 해당 항목의 **'기준 범위(예: 0.05% ~ 0.20%)'나 '합격 규격'**이 명시되어 있다면 절대 '데이터가 없다'며 거절하지 마십시오.
   - 참고 문서의 오차 범위/기준치를 바탕으로 사용자의 질문 속 수치와 **수학적 대소 비교(>, <, =, )를 직접 수행**하십시오.
   - 비교 결과 기준치를 미달하거나 초과한다면, "문서상 규격 범위(X ~ Y)를 벗어난 수치이므로 규격 이탈(불합격) 상황"임을 논리적으로 추론하여 명확한 검증 답변을 제공하십시오.

3. [★신규 - 불합격 시 대처방안 및 조치사항 연계 룰]:
   - 위 2번 규칙에 의해 **'규격 이탈(불합격)' 혹은 '스펙 초과/미달'로 판정될 경우, 제공된 [참고 문서] 내부에서 `[불합격 시 대처방안]`, `[조치 사항]`, `[해결책]`, `[격리/재보정]` 등과 관련된 속성값이나 관련 기술 내용을 반드시 샅샅이 검색**하십시오.
   - 불합격 판정 하단에 **`[문서 기반 후속 대처방안]`**이라는 항목을 별도로 개설하여, 참고 문서에 기록된 대응 프로세스(예: 원료 투입량 재보정, 해당 로트 격리, 공급사 패널티 등)를 누락 없이 매칭하여 상세히 기술하십시오.

4. 질문 내용이 [참고 문서]에 명시된 도메인과 완전히 무관하거나, 대소 비교를 할 수 있는 최소한의 기준 수치조차 문서에 없다면, 그때만 아래 3가지 요소를 포함하여 답변하십시오:
   - [감지 및 거절]: 제공된 참고 문서의 범위를 벗어난 질문임을 명확히 안내.
   - [이유 설명]: 현재 데이터베이스(DB) 컨텍스트에 어떤 데이터가 누락되었거나 부족한지 논리적 원인 분석.
   - [해결책 제시]: 추후 데이터베이스에 '추가로 적재해야 하는 원본 데이터나 가이드라인의 종류'를 구체적으로 제안.

[참고 문서]
{context}

[사용자 질문]
{query}
"""

    try:
        # Resolve ollama client safely from main facade
        client = getattr(main, 'ollama_client', ollama)
        response = client.generate(model=model_name, prompt=strict_prompt)
        ai_answer = response['response']
        
        # Rule-based compliance audit categorization (PASS / PARTIAL / FAIL)
        detection_keywords = ["범위", "포함되어 있지", "제공된 문서", "확인할 수 없", "제한", "알 수 없", "누락"]
        solution_keywords = ["추가", "적재", "확보", "제시", "해결", "필요", "자료", "보완"]
        
        detected = any(kw in ai_answer for kw in detection_keywords)
        solution_provided = any(kw in ai_answer for kw in solution_keywords)
        
        if detected and solution_provided:
            status = "정합성 통과 (PASS - 범위 이탈 감지 및 해결책 제시 완료)"
        elif detected:
            status = "부분 통과 (PARTIAL - 이탈은 감지했으나 구체적 해결책 미흡)"
        else:
            status = "일반 답변 또는 검증 확인 요망 (정상 답변 혹은 할루시네이션 확인 필요)"
            
        return ai_answer, status

    except Exception as e:
        return f"AI 답변 생성 중 오류가 발생했습니다: {e}", "오류 발생 (ERROR)"

# ────────────────────────────────────────────────────────
# 3. Interactive CLI Loop & Disk Logging
# ────────────────────────────────────────────────────────
def record_and_run_verification(model_name):
    safe_print("\n" + "="*60)
    safe_print(f"🤖 [ESG RAG 하이브리드 리랭킹 정합성 검증 모드] 활성화 (모델: {model_name})")
    safe_print("  • 1단계 (pgvector + BM25) 및 2단계 (Cross-Encoder) 엔진이 연동되어 작동합니다.")
    safe_print("  • 데이터 누락 테스트 및 OOD(이상치) 입력 시 대안 제안 능력을 모니터링합니다.")
    safe_print("  • 종료하려면 '종료' 또는 'q'를 입력하세요.")
    safe_print("="*60)
    
    log_file = "rag_integrity_test_log.txt"
    
    while True:
        try:
            query = input("\n[검증할 질문 입력]: ").strip()
        except KeyboardInterrupt:
            safe_print("\n👋 정합성 검증 시스템을 종료합니다.")
            break
            
        if not query:
            continue
        if query.lower() in ['종료', 'q', 'quit', 'exit']:
            safe_print("👋 정합성 검증 시스템을 종료합니다.")
            break
            
        safe_print(f"\n🔍 [Hybrid Search + Reranker] 고속 입체 연산 중...")
        ai_response, detection_status = get_integrity_checked_ai_response(model_name, query)
        
        # Console output
        safe_print("\n" + "-"*50)
        safe_print(f"📊 [정합성 평가]: {detection_status}")
        safe_print("-" * 50)
        safe_print(ai_response)
        safe_print("-" * 50)
        
        # Record findings onto disk log
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"=== [검증 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===\n")
                f.write(f"사용자 질문: {query}\n")
                f.write(f"감지 상태: {detection_status}\n")
                f.write(f"AI 답변 및 해결책:\n{ai_response}\n")
                f.write("="*60 + "\n\n")
            safe_print(f"💾 하이브리드 검증 결과가 '{log_file}'에 안전하게 기록되었습니다.")
        except Exception as e:
            safe_print(f"⚠️ 로그 저장 실패: {e}")

# ────────────────────────────────────────────────────────
# CLI Entry Point
# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Load target model from unified settings or fallback to CLI default
    TARGET_MODEL = settings.verify_ollama_model
    
    # Run loop
    record_and_run_verification(TARGET_MODEL)