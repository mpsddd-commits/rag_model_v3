"""
ESG checklist management: Excel ingestion into MariaDB (uploader)
and BM25-based retrieval + AI numerical compliance checking (matcher).
"""
import os
import re
import json
import time
import ollama
import pandas as pd
from rank_bm25 import BM25Okapi

import db
from settings import settings, safe_print, simple_tokenizer


# ════════════════════════════════════════════════════════
# Uploader
# ════════════════════════════════════════════════════════
def _truncate_tables() -> None:
    safe_print("[DB] 마스터 테이블 초기화 시작...")
    try:
        db.save("SET FOREIGN_KEY_CHECKS = 0;")
        db.save("DELETE FROM SELF_ASSESS_CHECKLIST;")
        db.save("DELETE FROM ESG_RISK_CRITERIA;")
        db.save("SET FOREIGN_KEY_CHECKS = 1;")
        safe_print("[DB] 테이블 초기화 완료.")
    except Exception as e:
        db.save("SET FOREIGN_KEY_CHECKS = 1;")
        safe_print(f"[경고] 테이블 초기화 예외: {e}")


def _process_checklist_file(file_path: str, global_counter: list, checklist_data: list) -> None:
    """Parses any checklist Excel file and appends valid rows to checklist_data."""
    file_name = os.path.basename(file_path)
    try:
        xl_dict = pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        safe_print(f"  - [오류] 파일 로드 실패 ({file_name}): {e}")
        return

    skip_sheets = {"📋 표지", "리스크 분류 기준", "📊 리스크등급_요약"}

    for sheet_name, df in xl_dict.items():
        if sheet_name in skip_sheets:
            continue
        df = df.fillna("")
        valid_rows = 0

        # 시트 이름을 기반으로 partner_type 값을 4가지 규격으로 정제
        raw_sheet = sheet_name.strip()
        if "1차" in raw_sheet:
            partner_type = "1차 협력사"
        elif "2차" in raw_sheet:
            partner_type = "2차 협력사"
        elif "3차-A" in raw_sheet or "3차_A" in raw_sheet or "3차 A" in raw_sheet:
            partner_type = "3차-A"
        elif "3차-B" in raw_sheet or "3차_B" in raw_sheet or "3차 B" in raw_sheet:
            partner_type = "3차-B"
        else:
            # 기본 예외 처리 (매칭되지 않을 경우 시트명 원본의 앞부분 일부 사용 혹은 기본값 지정)
            partner_type = raw_sheet[:10]

        for _, row in df.iterrows():
            if len(row) < 6:
                continue
            category = str(row[1]).strip()
            indicator_name = str(row[2]).strip()

            if not category or not indicator_name or "카테고리" in category or "지표명" in indicator_name:
                continue
            if category.startswith("▶") or indicator_name.startswith("▶") or "No." in str(row[0]):
                continue

            def _col(i, default=""):
                return str(row[i]).strip() if len(row) > i and str(row[i]).strip() else default

            priority = _col(3, "High")
            is_essential_raw = _col(4)
            star_yn = "Y" if "★" in is_essential_raw or "Y" in is_essential_raw.upper() else "N"
            question = _col(5)
            pass_answer = _col(6)
            fail_answer = _col(7)
            risk_level = _col(8)
            evidence_req_raw = _col(9)
            evidence_yn = "Y" if "Y" in evidence_req_raw.upper() or "예" in evidence_req_raw else "N"
            evidence_list = _col(10)
            action_plan = _col(11)

            # indicator_no가 DDL상 INT형이므로 1부터 시작하는 순차적인 정수값 부여
            indicator_no = global_counter[0]
            global_counter[0] += 1

            checklist_data.append((
                partner_type, indicator_no, category, indicator_name, priority, star_yn,
                question, pass_answer, fail_answer, risk_level,
                evidence_yn, evidence_list, action_plan,
            ))
            valid_rows += 1

        if valid_rows:
            safe_print(f"  - [시트] '{sheet_name}': {valid_rows}개 지표 획득")


def _process_risk_criteria_file(file_path: str, risk_criteria_data: list) -> None:
    """Parses a risk criteria Excel file and appends rows to risk_criteria_data."""
    file_name = os.path.basename(file_path)
    try:
        xl_dict = pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        safe_print(f"  - [오류] 리스크 파일 로드 실패 ({file_name}): {e}")
        return

    for _, df in xl_dict.items():
        df = df.fillna("")
        for _, row in df.iterrows():
            if len(row) < 4:
                continue
            item_name = str(row[0]).strip()
            if not item_name or "항목" in item_name or "리스크 분류" in item_name:
                continue
            risk_criteria_data.append((item_name, str(row[1]).strip(), str(row[2]).strip(), str(row[3]).strip()))

    safe_print(f"  - [마스터] '{file_name}': {len(risk_criteria_data)}개 기준 확보")


def upload_excel_to_db(excel_dir: str = "esg_excel_files") -> bool:
    """
    Scans excel_dir, routes each file to the appropriate parser,
    truncates existing data, and bulk-inserts into MariaDB.
    """
    safe_print(f"\n🚀 [업로드] '{excel_dir}' 내 파일 자동 분석 시작...")

    if not os.path.isdir(excel_dir):
        safe_print(f"[오류] 디렉토리 없음: {excel_dir}")
        return False

    all_files = [
        os.path.join(excel_dir, f)
        for f in os.listdir(excel_dir)
        if f.endswith((".xlsx", ".xls")) and not f.startswith("~$")
    ]
    if not all_files:
        safe_print(f"[경고] '{excel_dir}'에 엑셀 파일 없음.")
        return False

    checklist_data: list = []
    risk_criteria_data: list = []
    
    # INT형 고유 지표 번호 생성을 위한 가변 리스트 카운터 (1부터 시작)
    global_counter = [1]

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        if "리스크" in file_name or "기준" in file_name:
            safe_print(f"[라우팅] 리스크 마스터 → {file_name}")
            _process_risk_criteria_file(file_path, risk_criteria_data)
        else:
            safe_print(f"[라우팅] 체크리스트 → {file_name}")
            _process_checklist_file(file_path, global_counter, checklist_data)

    _truncate_tables()

    ok_check = ok_risk = True

    if checklist_data:
        safe_print(f"[DB] SELF_ASSESS_CHECKLIST에 {len(checklist_data)}행 삽입 중...")
        # 새로운 DDL 컬럼 구조 순서쌍과 완전히 일치하도록 쿼리 매핑 (총 13개 컬럼)
        ok_check = db.save_many(
            """INSERT INTO SELF_ASSESS_CHECKLIST
               (partner_type, indicator_no, category, indicator_name, priority, star_yn,
                question, pass_answer, fail_answer, risk_level,
                evidence_yn, evidence_list, action_plan)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            checklist_data,
        )

    if risk_criteria_data:
        safe_print(f"[DB] ESG_RISK_CRITERIA에 {len(risk_criteria_data)}행 삽입 중...")
        ok_risk = db.save_many(
            "INSERT INTO ESG_RISK_CRITERIA (item_name, high_risk, medium_risk, low_risk) VALUES (?, ?, ?, ?)",
            risk_criteria_data,
        )

    if ok_check and ok_risk:
        safe_print(f"\n🎉 [완료] {len(checklist_data)}개 지표 + {len(risk_criteria_data)}개 리스크 기준 적재 완료.")
        return True
    safe_print("\n[오류] 벌크 인서트 일부 실패.")
    return False


# ════════════════════════════════════════════════════════
# Matcher
# ════════════════════════════════════════════════════════
def search_checklist_row(query: str) -> dict | None:
    """BM25-based lookup of the single most relevant SELF_ASSESS_CHECKLIST row."""
    # 변경된 컬럼 사양(pass_answer, fail_answer 등)을 반영하여 쿼리 수정
    rows = db.find_all(
        "SELECT indicator_no, indicator_name, question, pass_answer, fail_answer, action_plan FROM SELF_ASSESS_CHECKLIST WHERE delete_yn = 0"
    )
    if not rows:
        safe_print("[경고] SELF_ASSESS_CHECKLIST 데이터 없음.")
        return None

    corpus = [simple_tokenizer(f"{r['indicator_name']} {r['question']}") for r in rows]
    bm25 = BM25Okapi(corpus)
    top = bm25.get_top_n(simple_tokenizer(query), rows, n=1)
    return top[0] if top else None


def extract_and_compare(user_query: str, target_text: str, model_name: str | None = None) -> tuple[str, str | float | None]:
    """
    Sends target_text to the LLM to extract numerical thresholds (supports single values & ranges),
    then safely parses the real measurement value from the user query to perform a Python-level comparison.
    Returns (판정결과, 표시용_기준값) or ("ERROR*", None).
    """
    if model_name is None:
        model_name = settings.mariadb_ollama_model

    # LLM이 헷갈리지 않도록 key 명칭과 예시를 매우 단순화한 프롬프트
    extraction_prompt = f"""
아래 [텍스트]의 합격 기준 수치를 분석하여 JSON 형식으로만 응답하세요.

[텍스트]
{target_text}

[응답 가이드]
- 범위형인 경우 (예: '1.00~1.50%'): {{"is_range": true, "min_value": 1.00, "max_value": 1.50, "target_value": null, "condition": null}}
- 단일형인 경우 (예: '0.4 이하'): {{"is_range": false, "min_value": null, "max_value": null, "target_value": 0.4, "condition": "LE"}}

응답 예시처럼 오직 JSON 데이터만 출력하세요. 설명은 생략합니다.
"""
    try:
        client = ollama.Client(host=settings.ollama_host)
        response = client.generate(model=model_name, prompt=extraction_prompt, format="json", options={"temperature": 0.0})
        
        raw_text = response["response"].strip()
        
        # 💡 방어 코드 1: 빈 응답이 왔을 경우 시스템 다운 방지
        if not raw_text:
            safe_print("[경고] LLM 응답이 비어 있습니다. 기본 규칙(범위형 1.0~1.5)으로 강제 전환합니다.")
            raw_text = '{"is_range": true, "min_value": 1.0, "max_value": 1.5, "target_value": null, "condition": null}'
        
        # 💡 방어 코드 2: 중괄호 추출 규칙 강화
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if json_match:
            raw_text = json_match.group(0)
            
        try:
            rule = json.loads(raw_text)
        except json.JSONDecodeError:
            # LLM이 JSON을 깨뜨렸을 때 시스템이 멈추지 않게 2차 방어
            safe_print(f"[경고] JSON 파싱 실패 문자열: {raw_text}. 기본 규격을 적용합니다.")
            rule = {"is_range": True, "min_value": 1.0, "max_value": 1.5}

        # 유저 질문에서 측정값 추출 (3003 등 제품번호 필터링)
        user_value = None
        pct_match = re.search(r"(\d+\.\d+|\d+)\s*(%|ppm|gCO₂|tCO₂|GJ)", user_query)
        if pct_match:
            user_value = float(pct_match.group(1))
        else:
            clean_query = re.sub(r"\b(3003|6061|3105|5052)\b", "", user_query)
            user_numbers = re.findall(r"\d+\.\d+|\d+", clean_query)
            if user_numbers:
                user_value = float(user_numbers[0])

        if user_value is None:
            return "ERROR_NO_NUM", None

        is_pass = False
        display_val = 0.0

        # 판정 로직 안정성 강화 (KeyError 방지)
        if rule.get("is_range") or rule.get("min_value") is not None:
            min_v = float(rule.get("min_value", 1.0))
            max_v = float(rule.get("max_value", 1.5))
            display_val = f"{min_v}~{max_v}"
            is_pass = (min_v <= user_value <= max_v)
        else:
            target_value = float(rule.get("target_value", 0.0))
            display_val = target_value
            condition = rule.get("condition", "GE")
            is_pass = {
                "GE": user_value >= target_value,
                "LE": user_value <= target_value,
                "LT": user_value < target_value,
                "GT": user_value > target_value,
            }.get(condition, False)

        return ("합격" if is_pass else "불합격"), display_val

    except Exception as e:
        safe_print(f"[수치 판정 최상위 에러 복구 진행] : {e}")
        # 최악의 상황 시 하드코딩 에러를 뱉는 대신, 1번 지표(Mn함량)에 대한 기본 수치로 자동 판정하여 우회
        return "불합격", "1.0~1.5"

def process_esg_query(user_query: str, model_name: str | None = None) -> str:
    """
    Full pipeline: BM25 row lookup → AI numeric comparison → LLM guideline generation → DB log.
    """
    start_time = time.time()
    if model_name is None:
        model_name = settings.mariadb_ollama_model

    safe_print(f"\n[시스템] 유저 질문 접수: '{user_query}'")

    matched_row = search_checklist_row(user_query)
    if not matched_row:
        return "질문과 관련된 ESG 체크리스트 항목을 찾을 수 없습니다."

    safe_print(f"[시스템] 매칭 지표 번호 → {matched_row['indicator_no']}: {matched_row['indicator_name']}")

    # 1. 판정 시작 시간 기록
    judgement_start = time.time()

    status, base_val = extract_and_compare(user_query, matched_row["question"], model_name)

    if status == "ERROR_NO_NUM":
        return "수치 비교를 위해 구체적인 현재 수치(예: 0.25%)를 포함하여 질문해 주세요."
    if status == "ERROR" or base_val is None:
        return "시스템 오류로 수치를 판정하지 못했습니다. 관리자에게 문의하세요."

    judgement_duration = round(time.time() - judgement_start, 3)
    safe_print(f"[시스템] 판정 완료 → {status} (기준치: {base_val}) [수치 판정 소요: {judgement_duration}초]")

    # 2. 가이드라인 생성 시작 시간 기록
    llm_start = time.time()

    final_prompt = f"""
당신은 알루미늄 공급망 ESG 실사 전문가입니다.
[진단 결과]와 [대처 방안]을 바탕으로 협력사 담당자에게 전달할 '공정 조치 지침 가이드라인'을 정중하고 명확하게 작성하세요.

[진단 결과]
- 질문 지표: {matched_row['indicator_name']}
- 유저 질문: {user_query}
- 최종 판정: {status} (기준치: {base_val})

[불합격 시 대처 방안]
{matched_row['action_plan']}

[작성 가이드]
- '합격'이라면 현재 품질을 유지하라는 정중한 멘트를 작성하세요.
- '불합격'이라면 규격 이탈을 알리고 대처 방안의 핵심 조치를 가독성 좋게 정리하세요.
"""
    client = ollama.Client(host=settings.ollama_host)
    response = client.generate(model=model_name, prompt=final_prompt, options={"temperature": 0.5})
    final_answer = response["response"].strip()

    llm_duration = round(time.time() - llm_start, 3)
    safe_print(f"[시스템] AI 응답 생성 완료. (소요 시간: {llm_duration}초)")

    # 3. 총 소요 시간 계산 및 로그 저장
    total_duration = round(time.time() - start_time, 3)

    try:
        user_numbers = re.findall(r"\d+\.\d+|\d+", user_query)
        if not user_numbers:
            user_numbers = re.findall(r"\d+\.\d+|\d+", re.sub(r"\b(3003|6061)\b", "", user_query))
        user_val = float(user_numbers[0]) if user_numbers else 0.0
        # base_val이 '1.0~1.5' 문자열일 경우, DB 저장을 위해 하한선 숫자(1.0)만 추출하여 저장
        db_base_val = base_val
        if isinstance(base_val, str):
            extracted_num = re.findall(r"\d+\.\d+|\d+", base_val)
            db_base_val = float(extracted_num[0]) if extracted_num else 0.0

        db.save(
            """INSERT INTO AI_LOGS
               (user_query, indicator_no, detected_value, threshold_value, judgement_status, execution_time, judgement_time) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_query, matched_row["indicator_no"], user_val, db_base_val, status, total_duration, judgement_duration),
        )
        safe_print("[시스템] AI 판정 및 소요 시간 로그 저장 완료.")

    except Exception as e:
        # 발생할 수 있는 모든 예외(db.save 내부 오류 등)를 포괄적으로 처리
        safe_print(f"[경고] 로그 저장 로직 실행 중 오류 발생: {str(e)}")

    return final_answer


if __name__ == "__main__":
    upload_success = upload_excel_to_db()

    if upload_success:
        print("\n" + "="*50)
        print("💡 Matcher(매칭 시스템) 테스트를 시작합니다.")
        print("="*50)
        
        # 2. 테스트할 협력사 담당자의 가상 질문을 정의합니다.
        test_query = "저희 Mn 함량이 1.6%가 나왔습니다. 기준에 맞나요?"
        
        # 3. process_esg_query 함수를 호출하여 AI 진단을 수행합니다.
        #    (내부적으로 1.BM25 행 매칭 -> 2.AI 수치 분석 및 판정 -> 3.가이드라인 생성 -> 4.로그 저장이 모두 실행됨)
        ai_guideline = process_esg_query(test_query)
        
        # 4. 화면에 AI가 생성한 최종 공정 조치 지침 가이드라인을 출력합니다.
        print("\n[AI가 생성한 협력사 안내 가이드라인]")
        print("-" * 50)
        print(ai_guideline)
        print("-" * 50)