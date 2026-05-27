"""
ESG RAG Hybrid Reranking Integrity Verification CLI (MariaDB Checklist & Risk Criteria Integrated).
Provides an interactive command-line interface to submit validation questions,
retrieve relevant documents, run strict numerical AI compliance rules, and log results.
"""
import os
import sys
import datetime
import ollama
from rank_bm25 import BM25Okapi
import time

# Import facade runners and core infrastructure
try:
    import main
    from main import (
        search_similar_documents, 
        simple_tokenizer
    )
    # 제공된 mariadb_client 연동
    import database.mariadb_client as db
except ImportError:
    print("[오류] 'main.py' 또는 'database.mariadb_client' 파일을 찾을 수 없거나 연동에 실패했습니다.")
    sys.exit(1)

from config.settings import settings
from utils.helpers import safe_print

# ────────────────────────────────────────────────────────
# 1. MariaDB Checklist & Risk Criteria Index Recovery Safeguard
# ────────────────────────────────────────────────────────
def check_and_ensure_bm25():
    """
    [MariaDB 하이브리드 동기화 구조]
    메모리 내 BM25 인덱스가 유실되었거나 단독 실행되었을 때,
    mariadb_client의 find_all 함수를 활용하여 데이터를 조회하고 복구합니다.
    (dictionary=True 구조를 반영하여 안전하게 파싱합니다)
    """
    if getattr(main, 'bm25_index', None) is None:
        safe_print("\n[안내] 메모리 내 BM25 인덱스가 유실되었거나 단독 실행되었습니다. MariaDB 전수 마스터 인덱스 복구를 시작합니다...")
        try:
            reconstructed_chunks = []

            # 🌟 1) esg_checklist 테이블 데이터 로드 (find_all 활용)
            select_check_sql = """
                SELECT indicator_no, category, indicator_name, question, pass_example, fail_example, action_plan 
                FROM esg_checklist;
            """
            check_rows = db.find_all(select_check_sql)
            
            if check_rows:
                for row in check_rows:
                    # mariadb_client가 dictionary=True 이므로 Key값으로 안전하게 접근합니다.
                    ind_no = row.get("indicator_no", "")
                    cat = row.get("category", "")
                    ind_name = row.get("indicator_name", "")
                    q = row.get("question", "")
                    p_ex = row.get("pass_example", "")
                    f_ex = row.get("fail_example", "")
                    a_plan = row.get("action_plan", "")

                    combined_content = (
                        f"지표번호: {ind_no} | 분류: {cat} | 지표명: {ind_name} | 평가질문: {q} | "
                        f"합격기준: {p_ex} | 불합격기준: {f_ex} | 대처방안: {a_plan}"
                    )
                    reconstructed_chunks.append({
                        "content": combined_content,
                        "source_file": "MariaDB esg_checklist 테이블",
                        "source_type": "DB_Checklist",
                        "page_or_row": ind_no,
                        "indicator_no": ind_no,
                        "category": cat,
                        "indicator_name": ind_name,
                        "question": q,
                        "pass_example": p_ex,
                        "fail_example": f_ex,
                        "action_plan": a_plan
                    })

            # 🌟 2) esg_risk_criteria 테이블 데이터 로드 (find_all 활용)
            select_risk_sql = """
                SELECT item_name, high_risk, medium_risk, low_risk 
                FROM esg_risk_criteria;
            """
            risk_rows = db.find_all(select_risk_sql)
            
            if risk_rows:
                for r_idx, row in enumerate(risk_rows):
                    i_name = row.get("item_name", "")
                    h_risk = row.get("high_risk", "")
                    m_risk = row.get("medium_risk", "")
                    l_risk = row.get("low_risk", "")

                    combined_risk = (
                        f"리스크 평가분류항목: {i_name} | 고위험기준(High): {h_risk} | "
                        f"중위험기준(Medium): {m_risk} | 저위험기준(Low): {l_risk}"
                    )
                    reconstructed_chunks.append({
                        "content": combined_risk,
                        "source_file": "MariaDB esg_risk_criteria 테이블",
                        "source_type": "DB_Risk_Criteria",
                        "page_or_row": f"CRITERIA_{r_idx+1}",
                        "is_risk_matrix": True,
                        "item_name": i_name,
                        "high_risk": h_risk,
                        "medium_risk": m_risk,
                        "low_risk": l_risk
                    })
            
            if not reconstructed_chunks:
                safe_print("[경고] MariaDB 데이터베이스에 적재된 지식 컨텍스트가 전무합니다. 엑셀 업로더를 먼저 실행해 주세요.")
                return False
                
            # 토큰화 및 BM25 인덱스 동기화 빌드
            tokenized_corpus = [simple_tokenizer(chunk["content"]) for chunk in reconstructed_chunks]
            main.bm25_index = BM25Okapi(tokenized_corpus)
            main.global_chunks_pool = reconstructed_chunks
            
            safe_print(f"[성공] MariaDB 듀얼 테이블(지표 및 리스크 마스터) 통합 BM25 인덱스 빌드 완료! (총 {len(reconstructed_chunks)}개 컨텍스트 확보)")
            return True
        except Exception as e:
            safe_print(f"[경고] MariaDB 기반 통합 BM25 인덱스 자동 복구 실패: {e}")
            return False
    return True

def get_integrity_checked_ai_response(model_name, query):
    
    # ⏱️ 구간 1: DB 및 BM25 체크 소요 시간 측정
    t0 = time.time()
    check_and_ensure_bm25()
    safe_print(f"⏱️ DB & BM25 체크 소요 시간: {time.time() - t0:.2f}초")
    
    # ⏱️ 구간 2: 하이브리드 검색 및 리랭커 호출 (순수 쿼리 사용, 전수 검색 유도)
    t1 = time.time()
    retrieved_contexts = search_similar_documents(query, top_k=6, dense_n=50, sparse_n=50)
    safe_print(f"⏱️ 하이브리드 검색 및 리랭커 소요 시간: {time.time() - t1:.2f}초")
    
    # --- 컨텍스트 포맷팅 ---
    if not retrieved_contexts:
        context = "⚠️ 현재 데이터베이스(MariaDB)에 연관된 지표 및 리스크 판정 참고 자료가 존재하지 않습니다."
    else:
        formatted_context_list = []
        for c_idx, ctx in enumerate(retrieved_contexts):
            search_channel = ctx.get('search_type', 'Hybrid')
            if "indicator_no" in ctx:
                formatted_context_list.append(
                    f"[지표 스펙 {c_idx+1}] (코드: {ctx['indicator_no']} | 지표명: {ctx['indicator_name']})\n"
                    f"  - 점검 질문 내용: {ctx['question']}\n"
                    f"  - 합격 판정 기준 답변 예시: {ctx['pass_example']}\n"
                    f"  - 불합격 위험 기준 답변 예시: {ctx['fail_example']}\n"
                    f"  - 해당 지표 위험 감지 시 대처방안(Action Plan): {ctx['action_plan']}"
                )
            elif ctx.get("is_risk_matrix") is True:
                formatted_context_list.append(
                    f"[리스크 판정 마스터 기준 {c_idx+1}] (항목명: {ctx['item_name']})\n"
                    f"  - 🔴 고위험 (High Risk) 기준: {ctx['high_risk']}\n"
                    f"  - 🟡 중위험 (Medium Risk) 기준: {ctx['medium_risk']}\n"
                    f"  - 🟢 저위험 (Low Risk) 기준: {ctx['low_risk']}"
                )
            else:
                formatted_context_list.append(
                    f"[참고 자료 {c_idx+1}] 내용을 그대로 준수하십시오:\n{ctx['content']}"
                )
        context = "\n\n".join(formatted_context_list)

# 🔍 [범용 공급망 ESG 자가진단 및 리스크 매트릭스 검증 엔진 프롬프트]
    strict_prompt = f"""당신은 알루미늄 공급망 Upstream(원자재 채굴, Bayer 정련, Hall 제련, 1차 합금화·압연)의 품질 및 ESG 정합성을 대조 검증하는 AI 실사 수석 감사관입니다.
    절대로 가상의 데이터베이스 구조 설계(CREATE TABLE 등)나 개발자 지향적인 SQL 쿼리 자문 답변을 작성하지 마십시오. 오직 실무 대응 지침 리포트 양식만 출력해야 합니다.

    [가장 중요한 핵심 지침 명령어 - 무조건 복종]
    1. [대상 지표 및 입력 수치 파악]:
    - [사용자 질문]에서 검증하고자 하는 핵심 성분, 품질 스펙 또는 ESG 관리 지표(예: 규소, 망간, 탄소집약도, 유해물질 등)와 사용자가 입력한 현재 '기입 값(수치 및 답변 문맥)'을 명확히 추출하십시오.

    2. [DB 마스터 기준값 및 우선순위 매칭]:
    - 제공된 [참고 데이터]에서 해당 지표에 매칭되는 '합격 기준 답변(예시)' 및 '불합격 위험 기준 답변(예시)'에 명시된 숫자식(예: >=99.35%, >0.60%, >0.8 등)과 해당 지표의 '우선순위(Critical, High, Medium)'를 파악하십시오.

    3. [다차원 수치 비교 및 합격/불합격 판정]:
    - 사용자가 입력한 '기입 값'과 DB에서 찾아낸 '합격/불합격 기준 수치'를 수학적·논리적으로 대조 연산하십시오.
    - 기입 값이 합격 범위를 충족하면 **[최종 판정 결과: 합격 (PASS)]**으로 판정하십시오.
    - 기입 값이 불합격 위험 임계치를 초과/미달하거나 부합하면 **[최종 판정 결과: 불합격 (FAIL)]**으로 엄격히 판정하십시오.

    4. [글로벌 리스크 등급 확정 (리스크 분류 기준 100% 매핑)]:
    - 판정 결과가 **[불합격 (FAIL)]**인 경우, 제공된 [리스크 판정 마스터 기준]의 5가지 범주(우선순위 기준, 규제 영향, 재무 리스크, 공급망 영향, 조치 기한)를 대조하여 최종 리스크 등급을 **[고위험 🔴] / [중위험 🟡] / [저위험 🟢]** 중 하나로 확정하십시오.
    * 필수 매핑 규칙: 'Critical' 지표에서 불합격했거나, CSDDD/UFLPA/FEOC 직접 위반 혹은 대체 소싱 불가능 사유에 걸릴 경우 무조건 **[고위험 🔴]**으로 확정해야 합니다.

    5. [위험 대응 및 해결 리포트 작성]:
    - 판정이 **[불합격 (FAIL)]**인 경우, [참고 데이터] 내 해당 지표의 `[불합격 시 대처방안]`에 명시된 구체적인 실무 행동 지침(원문에 정의된 내용)을 파악하십시오.
    - 파악한 대처방안을 생략하지 말고 **순번 기호(①, ②, ③...)를 사용하여 단계별로 명확하게 기입**하고, 마스터 기준의 [조치 기한](예: 즉시 조치 D+3~D+7, 30일 내 개선 계획 제출 등)과 연계하여 리포트를 완성하십시오.

    [리포트 출력 포맷 양식 - 반드시 이 규격만 출력할 것]
    --------------------------------------------------
    ■ 대상 지표/성분: [예: 알루미나(Al₂O₃) 순도]
    ■ 입력 데이터 vs DB 기준치: [예: 97.5% vs 기준치 99.35% 이상]
    ■ 우선순위 등급: [예: Critical 또는 High]
    ■ 최종 판정 결과: [합격(PASS) 또는 불합격(FAIL)]
    ■ 확정 리스크 등급: [예: 고위험 🔴 (Critical 지표 불합격 및 공급 중단 리스크 반영)]

    [위험 대응 및 해결 리포트]
    (※ 불합격 시에만 작성, 합격 시에는 '- 기준 이내 정상 확인 (특이사항 없음)'으로 기재)
    - [대상 지표/성분명]이 마스터 불합격 기준 조건을 이탈하여 다음과 같이 실무 긴급 조치를 발령함:
    ① [DB에서 찾은 대처방안 1단계]
    ② [DB에서 찾은 대처방안 2단계]
    ③ [DB에서 찾은 대처방안 3단계]
    
    ■ 후속 조치 권고 기한: [예: 즉시 조치 (D+3~D+7) 및 경영진 에스컬레이션 필수]
    --------------------------------------------------

    [참고 데이터 (MariaDB 실시간 연동 데이터셋)]
    {context}

    [사용자 질문]
    {query}
    """
#     # 🔍 [범용 수치 검증 엔진 고도화 프롬프트]
#     strict_prompt = f"""당신은 공급망(Upstream) 원자재, 전처리, 성형 공정의 품질 및 ESG 수치 정합성을 대조 검증하는 AI 수석 감사관입니다.
# 절대로 가상의 데이터베이스 스키마를 설계하거나 SQL 쿼리를 제안하는 기술 자문을 하지 마십시오. 오직 수치 대조 결과와 실무 이행 리포트만 작성하십시오.

# [가장 중요한 핵심 지침 명령어 - 무조건 복종]
# 1. [대상 성분 및 기입 수치 추출]:
#    - [사용자 질문]에서 검증하고자 하는 핵심 성분/지표(예: 규소, 구리, 탄소 등)와 사용자가 입력한 현재 '기입 숫자(수치)'를 정확히 파악하십시오.

# 2. [DB 마스터 기준값 검색 및 변환]:
#    - 제공된 [참고 데이터]에서 해당 성분/지표에 매칭되는 '합격 판정 기준' 또는 '불합격 위험 기준'에 명시된 기준값(수치식 및 임계치)을 검색하여 숫자로 추출하십시오.

# 3. [다차원 수치 비교 및 합격/불합격 판정]:
#    - 사용자가 입력한 '기입 숫자'와 DB에서 찾아낸 '기준값'을 수학적으로 비교 연산하십시오.
#    - 기입 숫자가 합격 범위를 충족하면 **[최종 결과: 합격 (PASS)]**으로 판정하십시오.
#    - 기입 숫자가 불합격 위험 기준(임계치 초과 또는 미달)에 걸린다면 **[최종 결과: 불합격 (FAIL)]**으로 엄격히 판정하십시오.

# 4. [불합격 시 리스크 해결 리포트 작성 룰]:
#    - 판정 결과가 **[불합격 (FAIL)]**인 경우, 해당 성분/지표에 대해 [참고 데이터] 내에 정의된 `[해당 지표 위험 감지 시 대처방안(Action Plan)]`의 구체적인 실무 행동 지침을 누락 없이 파악하십시오.
#    - 파악한 대처방안을 반드시 원문 양식에 맞추어 **순번 기호(①, ②, ③...)를 사용하여 단계별로 명확하게 기입**하십시오.

# [리포트 출력 포맷 양식]
# --------------------------------------------------
# ■ 대상 지표/성분: [예: 규소(Si)]
# ■ 입력 수치 vs DB 기준치: [예: 0.90% vs 기준치 0.60% 이하]
# ■ 최종 판정 결과: [합격(PASS) 또는 불합격(FAIL)]

# [위험 대응 및 해결 리포트]
# (※ 불합격 시에만 작성, 합격 시에는 '기준 이내 정상 확인'으로 대체)
# - [해당 성분명] 함량이 기준값보다 높아 다음과 같이 조치함:
#   ① [DB에서 찾은 대처방안 1단계]
#   ② [DB에서 찾은 대처방안 2단계]
#   ③ [DB에서 찾은 대처방안 3단계]
# --------------------------------------------------

# [참고 데이터 (MariaDB 실시간 연동 데이터셋)]
# {context}

# [사용자 질문]
# {query}
# """

    try:
        # ⏱️ 구간 3: Ollama LLM 생성
        t2 = time.time()
        client = getattr(main, 'ollama_client', ollama)
        response = client.generate(model=model_name, prompt=strict_prompt)
        safe_print(f"⏱️ Ollama LLM 추론 소요 시간: {time.time() - t2:.2f}초")
        
        ai_answer = response['response']
        
        # --- 후속 분류 및 상태 체크 키워드 트래킹 ---
        is_matrix_mapped = any(kw in ai_answer for kw in ["합격", "불합격", "PASS", "FAIL", "vs"])
        is_action_linked = any(kw in ai_answer for kw in ["리포트", "대처방안", "액션 플랜", "①"])
        
        if is_matrix_mapped and is_action_linked:
            status = "정합성 완벽 통과 (PASS)"
        else:
            status = "일반 답변 또는 검증 요망"
            
        return ai_answer, status

    except Exception as e:
        return f"AI 크로스 검증 답변 생성 중 치명적인 오류가 발생했습니다: {e}", "오류 발생 (ERROR)"

# ────────────────────────────────────────────────────────
# 3. Interactive CLI Loop & Disk Logging
# ────────────────────────────────────────────────────────
def record_and_run_verification(model_name):
    safe_print("\n" + "="*75)
    safe_print(f"🤖 [ESG RAG MariaDB 지표셋 X 리스크 매트릭스 크로스 검증 CLI] (모델: {model_name})")
    safe_print("  • MariaDB 내 esg_checklist와 esg_risk_criteria 마스터 테이블이 하이브리드 벡터 검색에 실시간 바인딩됩니다.")
    safe_print("  • 수치 이탈 검증과 동시에 글로벌 리스크 기준표 기반 등급(고/중/저) 판정을 모니터링합니다.")
    safe_print("  • 종료하려면 '종료' 또는 'q'를 입력하세요.")
    safe_print("="*75)
    
    log_file = "esg_cross_integrity_audit_log.txt"
    
    while True:
        try:
            query = input("\n[실사 질문 또는 수치 검증 데이터 입력]: ").strip()
        except KeyboardInterrupt:
            safe_print("\n👋 크로스 정합성 검증 시스템을 종료합니다.")
            break
            
        if not query:
            continue
        if query.lower() in ['종료', 'q', 'quit', 'exit']:
            safe_print("👋 크로스 정합성 검증 시스템을 종료합니다.")
            break
            
        safe_print(f"\n🔍 [듀얼 마스터 테이블 다차원 대조 연산 + 하이브리드 리랭커 작동 중]...")
        ai_response, detection_status = get_integrity_checked_ai_response(model_name, query)
        
        # 콘솔 가독성 출력
        safe_print("\n" + "📊" + "-"*65)
        safe_print(f" 정합성 평가 결과: {detection_status}")
        safe_print("-" * 67)
        safe_print(ai_response)
        safe_print("-" * 67)
        
        # 디스크 파일 검증 기록 아카이빙
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"=== [크로스 감사 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ===\n")
                f.write(f"감사 질문(데이터 입력): {query}\n")
                f.write(f"인프라 정합성 스태터스: {detection_status}\n")
                f.write(f"AI 수석 감사관 최종 리포트:\n{ai_response}\n")
                f.write("="*75 + "\n\n")
            safe_print(f"💾 크로스 검증 리포트가 '{log_file}'에 영구 저장되었습니다.")
        except Exception as e:
            safe_print(f"⚠️ 감사 로그 디스크 저장 실패: {e}")



# CLI Entry Point
if __name__ == "__main__":
    TARGET_MODEL = settings.verify_ollama_model
    record_and_run_verification(TARGET_MODEL)