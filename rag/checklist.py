"""
ESG checklist management: Excel ingestion into MariaDB (uploader)
and BM25-based retrieval + AI numerical compliance checking (matcher).
"""
import os
import re
import json

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


def extract_and_compare(user_query: str, target_text: str, model_name: str | None = None) -> tuple[str, float | None]:
    """
    Sends target_text to the LLM to extract a numeric threshold + condition (GE/LE/LT/GT),
    then compares against the user's input value at the Python level.
    Returns (판정결과, 기준값) or ("ERROR*", None).
    """
    if model_name is None:
        model_name = settings.mariadb_ollama_model

    extraction_prompt = f"""
아래의 [체크리스트 텍스트]를 읽고, 합격 판정을 위한 '기준 숫자'와 '조건'을 분석하여 오직 지정된 JSON 형식으로만 응답하세요.

[체크리스트 텍스트]
{target_text}

[주의사항]
- '99.35% 이상' → {{"target_value": 99.35, "condition": "GE"}}
- '0.4 이하'    → {{"target_value": 0.4,   "condition": "LE"}}
- '0.35% 미만'  → {{"target_value": 0.35,  "condition": "LT"}}

[응답 JSON 형식]
{{"target_value": 기준숫자(실수형), "condition": "GE" 또는 "LE" 또는 "LT" 또는 "GT"}}
"""
    try:
        client = ollama.Client(host=settings.ollama_host)
        response = client.generate(model=model_name, prompt=extraction_prompt, options={"temperature": 0.0})
        rule = json.loads(response["response"].strip())
        target_value: float = rule["target_value"]
        condition: str = rule["condition"]

        user_numbers = re.findall(r"\d+\.\d+|\d+", user_query)
        if not user_numbers:
            return "ERROR_NO_NUM", None

        user_value = float(user_numbers[0])
        is_pass = {
            "GE": user_value >= target_value,
            "LE": user_value <= target_value,
            "LT": user_value < target_value,
            "GT": user_value > target_value,
        }.get(condition, False)

        return ("합격" if is_pass else "불합격"), target_value

    except Exception as e:
        safe_print(f"[수치 판정 에러] : {e}")
        return "ERROR", None


def process_esg_query(user_query: str, model_name: str | None = None) -> str:
    """
    Full pipeline: BM25 row lookup → AI numeric comparison → LLM guideline generation → DB log.
    """
    if model_name is None:
        model_name = settings.mariadb_ollama_model

    safe_print(f"\n[시스템] 유저 질문 접수: '{user_query}'")

    matched_row = search_checklist_row(user_query)
    if not matched_row:
        return "질문과 관련된 ESG 체크리스트 항목을 찾을 수 없습니다."

    safe_print(f"[시스템] 매칭 지표 번호 → {matched_row['indicator_no']}: {matched_row['indicator_name']}")

    status, base_val = extract_and_compare(user_query, matched_row["question"], model_name)

    if status == "ERROR_NO_NUM":
        return "수치 비교를 위해 구체적인 현재 수치(예: 0.25%)를 포함하여 질문해 주세요."
    if status == "ERROR" or base_val is None:
        return "시스템 오류로 수치를 판정하지 못했습니다. 관리자에게 문의하세요."

    safe_print(f"[시스템] 판정 완료 → {status} (기준치: {base_val})")

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

    try:
        user_numbers = re.findall(r"\d+\.\d+|\d+", user_query)
        user_val = float(user_numbers[0]) if user_numbers else 0.0
        db.save(
            "INSERT INTO ai_logs (user_query, indicator_no, detected_value, threshold_value, judgement_status) VALUES (?, ?, ?, ?, ?)",
            (user_query, matched_row["indicator_no"], user_val, base_val, status),
        )
        safe_print("[시스템] AI 판정 로그 저장 완료.")
    except Exception as log_err:
        safe_print(f"[경고] 로그 저장 오류 (시스템 작동에는 문제 없음): {log_err}")

    return final_answer


if __name__ == "__main__":
    upload_excel_to_db()