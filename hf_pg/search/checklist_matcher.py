import re
import json
import ollama
from rank_bm25 import BM25Okapi

from config.settings import settings
import database.mariadb_client as db
from utils.helpers import safe_print, simple_tokenizer

# 1. Search checklist row using BM25
def search_checklist_row(query):
    """
    일일이 쿼리를 분기하지 않고, 사용자의 질문 키워드를 바탕으로
    MariaDB의 'esg_checklist' 테이블에서 가장 연관성 높은 1개 행을 찾아 반환합니다.
    """
    sql = "SELECT indicator_no, indicator_name, question, pass_example, fail_example, action_plan FROM esg_checklist"
    rows = db.find_all(sql)
    
    if not rows:
        safe_print("[경고] MariaDB esg_checklist 테이블에 데이터가 없습니다.")
        return None

    # BM25 형태소 분석을 위한 말뭉치(Corpus) 빌드
    corpus = []
    for row in rows:
        # 지표명과 질문을 결합하여 검색 매칭력을 높임
        search_target = f"{row['indicator_name']} {row['question']}"
        corpus.append(simple_tokenizer(search_target))
        
    bm25 = BM25Okapi(corpus)
    tokenized_query = simple_tokenizer(query)
    
    # 질문과 가장 유사한 상위 1개 데이터 추출
    top_rows = bm25.get_top_n(tokenized_query, rows, n=1)
    
    return top_rows[0] if top_rows else None

# 2. Extract and compare numerical rules using AI
def extract_and_compare(user_query, target_text, model_name=None):
    """
    TextArea(질문 혹은 기준 문장)를 LLM에 전달하여 수치 기준 JSON을 얻고,
    사용자 질문의 숫자와 파이썬 레벨에서 정밀 대소 비교를 수행합니다.
    """
    if model_name is None:
        model_name = settings.mariadb_ollama_model

    extraction_prompt = f"""
    아래의 [체크리스트 텍스트]를 읽고, 합격 판정을 위한 '기준 숫자'와 '조건'을 분석하여 오직 지정된 JSON 형식으로만 응답하세요.
    
    [체크리스트 텍스트]
    {target_text}
    
    [주의사항]
    - 만약 '99.35% 이상' 이라면 -> "target_value": 99.35, "condition": "GE"
    - 만약 '0.4 이하' 라면 -> "target_value": 0.4, "condition": "LE"
    - 만약 '0.35% 미만' 이라면 -> "target_value": 0.35, "condition": "LT"
    
    [응답 JSON 형식]
    {{
        "target_value": 기준숫자(실수형),
        "condition": "GE" 또는 "LE" 또는 "LT" 또는 "GT"
    }}
    """
    
    try:
        # Configure client mapping
        os_host = settings.ollama_host
        client = ollama.Client(host=os_host)
        
        # Ollama를 통한 정형 규격 추출 (온도는 일관성을 위해 0.0)
        response = client.generate(
            model=model_name, 
            prompt=extraction_prompt, 
            options={"temperature": 0.0}
        )
        
        # AI 응답 JSON 파싱
        rule = json.loads(response['response'].strip())
        target_value = rule["target_value"]   # DB 텍스트에서 파싱된 기준치
        condition = rule["condition"]         # DB 텍스트에서 파싱된 조건문
        
        # 사용자 질문 문자열에서 실수 또는 정수 형태의 현재 상태 수치 추출
        user_numbers = re.findall(r'\d+\.\d+|\d+', user_query)
        if not user_numbers:
            return "ERROR_NO_NUM", None
            
        user_value = float(user_numbers[0])   # 사용자가 입력한 값
        
        # 파이썬 레벨에서 안전하게 대소 비교 가동 (정합성 100%)
        if condition == "GE": is_pass = (user_value >= target_value)
        elif condition == "LE": is_pass = (user_value <= target_value)
        elif condition == "LT": is_pass = (user_value < target_value)
        elif condition == "GT": is_pass = (user_value > target_value)
        else: is_pass = False
        
        status = "합격" if is_pass else "불합격"
        return status, target_value
        
    except Exception as e:
        safe_print(f"[수치 판정 에러] : {e}")
        return "ERROR", None

# 3. Master function to coordinate process
def process_esg_query(user_query, model_name=None):
    """
    유저 질문 접수 -> MariaDB 행 검색 -> AI 수치 판정 -> 최종 가이드 문장 생성 -> 로그 저장
    """
    if model_name is None:
        model_name = settings.mariadb_ollama_model

    safe_print(f"\n[시스템] 유저 질문 접수: '{user_query}'")
    
    # ── Step 1. 질문과 매칭되는 MariaDB 행 찾기
    matched_row = search_checklist_row(user_query)
    if not matched_row:
        return "질문과 관련된 ESG 체크리스트 항목을 찾을 수 없습니다."
    
    safe_print(f"[시스템] 매칭된 지표 발견 -> 지표번호 {matched_row['indicator_no']}: {matched_row['indicator_name']}")
    
    # ── Step 2. AI 수치 파싱 및 파이썬 정밀 비교 가동
    status, base_val = extract_and_compare(user_query, matched_row['question'], model_name)
    
    if status == "ERROR_NO_NUM":
        return "수치 비교를 위해 구체적인 현재 수치(예: 0.25%)를 포함하여 질문해 주세요."
    elif status == "ERROR" or base_val is None:
        return "시스템 일시적 오류로 수치를 판정하지 못했습니다. 관리자에게 문의하세요."
        
    safe_print(f"[시스템] 판정 완료 -> 결과: [{status}] (기준치: {base_val})")
    
    # ── Step 3. 판정 결과를 들고 LLM에게 유저에게 줄 최종 보고서/가이드 문장 작성을 요청
    final_prompt = f"""
    당신은 알루미늄 공급망 ESG 실사 전문가입니다. 
    [진단 결과]와 [대처 방안]을 바탕으로, 협력사 담당자에게 전달할 '공정 조치 지침 가이드라인'을 아주 정중하고 명확한 문장으로 작성해 주세요.
    
    [진단 결과]
    - 질문 지표: {matched_row['indicator_name']}
    - 유저의 질문 내용: {user_query}
    - 최종 판정 상태: {status} (체크리스트 내부 기준 수치: {base_val})
    
    [불합격 시 대처 방안 (Action Plan)]
    {matched_row['action_plan']}
    
    [작성 가이드]
    - '합격' 상태라면 축하와 함께 현재 품질을 유지하라는 정중한 멘트를 작성하세요.
    - '불합격' 상태라면 현재 규격을 이탈했음을 알리고, 위에 제공된 [불합격 시 대처 방안]의 핵심 조치 사항들을 가독성 좋게 정리해서 안내하세요.
    """
    
    # Configure client mapping
    client = ollama.Client(host=settings.ollama_host)
    
    # 최종 가이드라인 문장 생성
    response = client.generate(
        model=model_name,
        prompt=final_prompt,
        options={"temperature": 0.5} # 답변 문장의 자연스러움을 위해 약간의 온도를 줌
    )
    final_answer = response['response'].strip()
    
    # ── Step 4. AI 판정 결과 로그 저장 (db.py 활용)
    try:
        user_numbers = re.findall(r'\d+\.\d+|\d+', user_query)
        user_val = float(user_numbers[0]) if user_numbers else 0.0
        
        insert_sql = """
            INSERT INTO ai_logs (user_query, indicator_no, detected_value, threshold_value, judgement_status)
            VALUES (?, ?, ?, ?, ?)
        """
        insert_params = (user_query, matched_row['indicator_no'], user_val, base_val, status)
        db.save(insert_sql, insert_params)
        safe_print("[시스템] DB에 AI 판정 로그 저장이 완료되었습니다.")
    except Exception as log_error:
        safe_print(f"[경고] 로그 저장 중 오류 발생 (시스템 작동에는 문제 없음): {log_error}")

    return final_answer
