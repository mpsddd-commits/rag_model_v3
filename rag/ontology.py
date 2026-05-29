"""
ESG Ontology and In-Memory Rule-Based Mapping Registry.
Caches MariaDB master data into a fast Python lookup structure
to eliminate per-query database and LLM reasoning bottlenecks.
"""
import re
import db
from settings import safe_print

# 전역 변수로 인메모리 온톨로지 사전 선언
# { "지표명": { "indicator_no": "...", "action_plan": "...", "risk_criteria": {...}, "threshold_value": 60.0, "operator": ">=" } }
_ONTOLOGY_REGISTRY: dict = {}


def parse_numeric_criteria(text_criteria: str) -> tuple[float | None, str]:
    """
    "60% 이상", "0.60% 이하" 등 줄글 형태의 기준 답변 예시에서
    비교 연산자와 임계 수치를 정규식으로 안전하게 추출합니다.
    """
    if not text_criteria:
        return None, ">="

    # 1. 숫자(실수/정수) 추출
    nums = re.findall(r"\d+\.\d+|\d+", text_criteria)
    if not nums:
        return None, ">="
    
    value = float(nums[0])
    
    # 2. 부호 연산자 식별
    if "이하" in text_criteria or "미만" in text_criteria or "<" in text_criteria or "≤" in text_criteria:
        operator = "<="
    else:
        operator = ">="  # 기본값은 이상/초과

    return value, operator


def load_ontology_registry() -> bool:
    """
    서버 혹은 CLI 시작 시 딱 한 번 실행되어 MariaDB의 듀얼 마스터 테이블을
    통합 바인딩한 후, 파이썬 전역 딕셔너리에 온톨로지 구조로 캐싱합니다.
    """
    global _ONTOLOGY_REGISTRY
    _ONTOLOGY_REGISTRY.clear()

    safe_print("[온톨로지] MariaDB 마스터 테이블 동기화 및 인메모리 캐시 구축 중...")
    
    try:
        # 두 테이블의 데이터를 지표명을 기준으로 결합하여 전수 로드
        sql = """
            SELECT 
                c.indicator_name, 
                c.indicator_no, 
                c.pass_example,
                c.action_plan,
                r.high_risk, 
                r.medium_risk, 
                r.low_risk
            FROM SELF_ASSESS_CHECKLIST c
            LEFT JOIN ESG_RISK_CRITERIA r ON c.indicator_name = r.item_name;
        """
        rows = db.find_all(sql)
        
        if not rows:
            safe_print("[경고] MariaDB 마스터 데이터가 비어 있습니다. 엑셀 업로더를 먼저 실행하세요.")
            return False

        for row in rows:
            name = row.get("indicator_name", "").strip()
            if not name:
                continue

            # pass_example 텍스트(ex: "60% 이상")에서 규칙 연산 수치 자동 파싱
            pass_ex = row.get("pass_example", "")
            threshold_val, operator = parse_numeric_criteria(pass_ex)

            # 온톨로지 사전 구조화
            _ONTOLOGY_REGISTRY[name] = {
                "indicator_no": row.get("indicator_no", "N/A"),
                "action_plan": row.get("action_plan", "대처방안 정보가 없습니다."),
                "threshold_value": threshold_val,
                "operator": operator,
                "risk_criteria": {
                    "high": row.get("high_risk", ""),
                    "medium": row.get("medium_risk", ""),
                    "low": row.get("low_risk", "")
                }
            }

        safe_print(f"[성공] 고속 인메모리 온톨로지 사전 바인딩 완료! (총 {len(_ONTOLOGY_REGISTRY)}개 지표 활성화)")
        return True

    except Exception as e:
        safe_print(f"[오류] 온톨로지 레지스트리 빌드 실패: {e}")
        return False


def find_matched_indicator(extracted_name: str) -> tuple[str | None, dict | None]:
    """
    AI가 추출한 지표명이 사전에 완벽히 일치하지 않더라도 
    부분 매칭(Sub-string matching)을 통해 사전의 Key를 안전하게 탐색합니다.
    """
    if not extracted_name:
        return None, None

    clean_name = extracted_name.strip()
    
    # 1. 완전 일치 매칭
    if clean_name in _ONTOLOGY_REGISTRY:
        return clean_name, _ONTOLOGY_REGISTRY[clean_name]

    # 2. 부분 포함 일치 매칭 (유연성 확보)
    for key, data in _ONTOLOGY_REGISTRY.items():
        if clean_name in key or key in clean_name:
            return key, data

    return None, None


def evaluate_esg_compliance(indicator_name: str, user_value: float) -> dict:
    """
    [핵심 규칙 엔진]
    추출된 지표명과 협력사의 입력 수치를 받아 0.001초 만에 
    합불 여부 판단 및 위험군 매핑을 수행하고 리포트용 데이터를 반환합니다.
    """
    official_name, meta = find_matched_indicator(indicator_name)
    
    if not meta:
        return {
            "is_matched": False,
            "status": "검증 요망",
            "risk_level": "미정",
            "report_action": f"'{indicator_name}' 지표는 마스터 온톨로지 사전에 등록되지 않은 항목입니다. 기준치 데이터베이스를 점검하세요."
        }

    threshold = meta["threshold_value"]
    operator = meta["operator"]
    action_plan = meta["action_plan"]
    risk_info = meta["risk_criteria"]

    # 기본값 설정
    is_pass = True

    # 파이썬 하드코딩 규칙 연산 (수치 임계치 자동 판정)
    if threshold is not None:
        if operator == "<=":
            is_pass = (user_value <= threshold)
        else:  # ">="
            is_pass = (user_value >= threshold)

    # 결과 매핑
    if is_pass:
        status = "합격 (PASS)"
        risk_level = "🟢 저위험 (Low Risk)"
        
        # 합격 시 깔끔한 안내 문구 생성
        report_action = "기준 이내 정상 확인 (현재의 우수한 품질 및 안전/환경 관리 상태를 항시 유지해 주시기 바랍니다.)"
    else:
        status = "불합격 (FAIL)"
        
        # 위험군(Risk Criteria) 텍스트를 파이썬 조건으로 한 번 더 매핑 가능
        # 여기서는 디폴트로 고위험/중위험 기준이 매핑되도록 처리
        risk_level = "🔴 고위험 (High Risk)" if "고위험" in risk_info["high"] else "🟡 중위험 (Medium Risk)"
        
        # 불합격 시 action_plan 줄바꿈을 파싱하여 동그라미 순번(①, ②, ③...) 형태로 리포트 정제
        report_action = f"- {official_name} 수치({user_value}%)가 마스터 기준치를 이탈하여 아래와 같이 조치를 지시함:\n"
        steps = [s.strip() for s in action_plan.split("\n") if s.strip()]
        
        for idx, step in enumerate(steps, 1):
            # ① (Unicode: 9311)을 기점으로 가독성 높은 기호 자동 부여
            bullet = chr(9311 + idx) if idx <= 20 else f"[{idx}]"
            report_action += f"   {bullet} {step}\n"

    return {
        "is_matched": True,
        "official_name": official_name,
        "indicator_no": meta["indicator_no"],
        "threshold": threshold,
        "operator": operator,
        "status": status,
        "risk_level": risk_level,
        "report_action": report_action.strip()
    }