"""
ESG Ontology and In-Memory Rule-Based Mapping Registry.
Caches MariaDB master data into a fast Python lookup structure
to eliminate per-query database and LLM reasoning bottlenecks.
"""
import re
import json
import db
from settings import safe_print

# 전역 변수로 인메모리 온톨로지 사전 선언
# { "지표명": { "indicator_no": "...", "action_plan": "...", "risk_criteria": {...}, "threshold_value": 60.0, "operator": ">=" } }
_ONTOLOGY_REGISTRY: dict = {}

# [추가] 미리 규격화된 템플릿(JSON/JSONL용) 구조를 저장할 전역 리스트
_ONTOLOGY_TEMPLATE_LIST: list = []

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
    MariaDB의 듀얼 마스터 테이블을 통합 바인딩한 후,
    1) 인메모리 딕셔너리 캐시 구축
    2) [추가] JSON/JSONL 변환용 표준 템플릿 리스트 구조를 미리 빌드
    """
    global _ONTOLOGY_REGISTRY, _ONTOLOGY_TEMPLATE_LIST
    _ONTOLOGY_REGISTRY.clear()
    _ONTOLOGY_TEMPLATE_LIST.clear() 

    safe_print("[온톨로지] MariaDB 마스터 테이블 동기화 및 템플릿 빌드 중...")
    
    try:
        sql = """
            SELECT 
                c.indicator_name, 
                c.indicator_no, 
                c.question,
                c.action_plan,
                r.high_risk, 
                r.medium_risk, 
                r.low_risk
            FROM SELF_ASSESS_CHECKLIST c
            LEFT JOIN ESG_RISK_CRITERIA r ON c.indicator_name = r.item_name;
        """
        rows = db.find_all(sql)
        
        if not rows:
            safe_print("[경고] MariaDB 마스터 데이터가 비어 있습니다.")
            return False

        for row in rows:
            name = row.get("indicator_name", "").strip()
            if not name:
                continue

            pass_ex = row.get("pass_example", "")
            threshold_val, operator = parse_numeric_criteria(pass_ex)

            # --------------------------------------------------------
            # 기능 A: 기존 온톨로지 사전 구조화 (0.001초 고속 매칭용)
            # --------------------------------------------------------
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

            # --------------------------------------------------------
            # 🌟 기능 B: [신규] JSON / JSONL 변환용 표준 템플릿 리스트 적재
            # --------------------------------------------------------
            # 대처방안 텍스트를 미리 깔끔하게 배열(List) 구조로 변환
            raw_action = row.get("action_plan", "")
            steps = [s.strip() for s in raw_action.split("\n") if s.strip()]
            
            # 원하는 형태의 템플릿 형식을 지정하여 사전(Dict) 객체 생성
            template_item = {
                "indicator_id": f"ESG-IND-{row.get('indicator_no', '000')}",
                "indicator_name": name,
                "compliance_rule": {
                    "base_text": pass_ex,
                    "parsed_threshold": threshold_val,
                    "mathematical_operator": operator
                },
                "risk_matrix": {
                    "high_risk_condition": row.get("high_risk", ""),
                    "medium_risk_condition": row.get("medium_risk", ""),
                    "low_risk_condition": row.get("low_risk", "")
                },
                "structured_action_plans": steps  # ['1단계 조치', '2단계 조치'] 형태의 깔끔한 리스트
            }
            
            _ONTOLOGY_TEMPLATE_LIST.append(template_item)

        safe_print(f"[성공] 고속 인메모리 온톨로지 및 {len(_ONTOLOGY_TEMPLATE_LIST)}개 템플릿 리스트 빌드 완료!")
        return True

    except Exception as e:
        safe_print(f"[오류] 온톨로지 레지스트리 및 템플릿 빌드 실패: {e}")
        return False


# 🌟 [추가] 외부에서 빌드된 템플릿 리스트를 가져오는 함수
def get_ontology_template_list() -> list[dict]:
    """미리 파싱되어 저장된 JSON형태의 파이썬 리스트를 반환합니다."""
    return _ONTOLOGY_TEMPLATE_LIST


# 🌟 [추가] 데이터를 한 줄씩 JSON형태로 쪼갠 JSONL 파일로 바로 내보내는 내보내기 함수
def export_to_jsonl(output_file_path: str = "esg_ontology_template.jsonl") -> bool:
    """
    메모리에 적재된 템플릿 리스트를 LLM 학습이나 데이터 이관용
    JSONL(JSON Lines) 파일로 로컬 디렉토리에 저장합니다.
    """
    if not _ONTOLOGY_TEMPLATE_LIST:
        safe_print("[경고] 내보낼 템플릿 데이터가 존재하지 않습니다. 먼저 로드하세요.")
        return False
        
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            for item in _ONTOLOGY_TEMPLATE_LIST:
                # 내부 딕셔너리를 한 줄짜리 json 문자열로 변환하여 기록
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        safe_print(f"[완료] 온톨로지 데이터셋이 {output_file_path} 파일로 성공적으로 내보내졌습니다.")
        return True
    except Exception as e:
        safe_print(f"[오류] JSONL 파일 생성 중 실패: {e}")
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

if __name__ == "__main__":
    print("====== 온톨로지 동기화 및 데이터셋 추출 테스트 시작 ======")
    
    # 1. DB 동기화 및 인메모리 템플릿 빌드
    is_success = load_ontology_registry()
    
    if is_success:
        print("\n[성공] 데이터가 파이썬 메모리에 정상적으로 적재되었습니다.")
        print(f"현재 등록된 총 지표 개수: {len(_ONTOLOGY_REGISTRY)}개")
        
        # --------------------------------------------------------
        # 🌟 해결책 1: AI 학습 및 이관용 JSONL 파일 생성 함수 호출!!
        # --------------------------------------------------------
        # 함수를 실행해 주어야 드디어 폴더에 esg_ontology_template.jsonl 파일이 생깁니다.
        export_to_jsonl("esg_ontology_template.jsonl")
        
        # --------------------------------------------------------
        # 🌟 해결책 2: 실제 DB에 존재하는 지표명으로 매칭 테스트하기
        # --------------------------------------------------------
        # 사전에 등록된 55개 지표 중 첫 번째 진짜 지표명을 자동으로 가져와 테스트합니다.
        real_indicators = list(_ONTOLOGY_REGISTRY.keys())
        
        if real_indicators:
            test_indicator = real_indicators[0]  # 실제 존재하는 첫 번째 지표명
            test_value = 55.5
            
            print(f"\n[테스트] 실제 지표 '{test_indicator}'에 대해 수치 {test_value}%로 규칙 엔진 판정 진행...")
            result = evaluate_esg_compliance(test_indicator, test_value)
            
            print(json.dumps(result, indent=4, ensure_ascii=False))
            
            # 가상으로 아까 실패했던 '온실가스' 단어가 포함된 진짜 지표가 있는지 검색해 주는 서비스
            print("\n[팁] '온실가스' 단어가 포함된 실제 지표 리스트 검색 결과:")
            matched_hints = [k for k in real_indicators if "온실가스" in k or "탄소" in k]
            print(matched_hints if matched_hints else "('온실가스'나 '탄소'라는 단어가 포함된 지표가 DB에 없습니다.)")
            
    else:
        print("\n[실패] DB 연결 오류 또는 마스터 데이터가 비어 있습니다.")