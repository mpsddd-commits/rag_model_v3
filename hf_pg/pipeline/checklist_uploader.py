# import os
# import pandas as pd
# from config.settings import settings
# import database.mariadb_client as db
# from utils.helpers import safe_print

# def upload_checklist_excel(excel_path="esg_excel_files/협력사별_자가진단_체크리스트.xlsx"):
#     """
#     지정한 폴더(또는 단일 파일) 안에 있는 모든 ESG 체크리스트 Excel 파일을 읽어와
#     멀티 시트를 포함한 모든 데이터를 유효성 검증 후 MariaDB에 정확히 1:1 적재합니다.
#     """
#     safe_print(f"\n[업로드] 엑셀 경로 '{excel_path}'에서 ESG 체크리스트 로드 중...")

#     if not os.path.exists(excel_path):
#         safe_print(f"[오류] 경로를 찾을 수 없습니다: {excel_path}")
#         return False

#     # 📂 파일 리스트 구성
#     files_to_process = []
#     if os.path.isdir(excel_path):
#         for f in os.listdir(excel_path):
#             if f.endswith(('.xlsx', '.xls')) and not f.startswith('~$'):
#                 files_to_process.append(os.path.join(excel_path, f))
#         if not files_to_process:
#             safe_print(f"[경고] 폴더 '{excel_path}' 안에 엑셀 파일(.xlsx, .xls)이 없습니다.")
#             return False
#     else:
#         files_to_process = [excel_path]

#     checklist_data = []
#     counters = {"ENV": 1, "SOC": 1, "GOV": 1}   # 전역 카운터

#     # 📑 파일별 파싱
#     for file_p in files_to_process:
#         file_name = os.path.basename(file_p)
#         safe_print(f"[프로세스] 파일 로드 중: {file_name}")
        
#         try:
#             # 🌟 [해결책 1] sheet_name=None 으로 설정하여 멀티 시트 전량 확보
#             xl_dict = pd.read_excel(file_p, sheet_name=None, header=None) 
#         except Exception as e:
#             safe_print(f"[오류] 엑셀 파일 로드 실패 ({file_name}): {e}")
#             continue

#         # 시트별 순회
#         for sheet_name, df in xl_dict.items():
#             # 대시보드나 기준 설명 시트 스킵
#             if sheet_name in ["📋 표지", "리스크 분류 기준", "📊 리스크등급_요약"]:
#                 continue

#             df = df.fillna("")
#             safe_print(f"  - [시트 파싱] '{sheet_name}' 시트 분석 중 (총 {len(df)}개 행)...")

#             for idx, row in df.iterrows():
#                 # 최소 컬럼 수 필터링 (최소 11개 이상 컬럼이 존재해야 함)
#                 if len(row) < 11:
#                     continue

#                 category       = str(row[1]).strip()   # 카테고리
#                 indicator_name = str(row[2]).strip()   # 지표명
                
#                 # 헤더 및 대분류 행 스킵 조건
#                 if not category or not indicator_name or "카테고리" in category or "지표명" in indicator_name:
#                     continue
#                 if category.startswith("▶") or indicator_name.startswith("▶"):
#                     continue

#                 # 🌟 [보안책 1] 기본키 중복 방지 고유 코드 생성
#                 # 예: 시트이름이 '1차 협력사'이고 엑셀 No가 '40'이면 -> '1차_40' 형태로 접두사 활용하여 충돌 방지
#                 # 또는 기존 방식(ENV-001)을 유지하되 파일 전체에 대해 카운터가 절대 중복되지 않도록 전역 관리
#                 raw_no = str(row[0]).strip()
                
#                 # 안전하게 인덱스 매핑으로 변환 데이터 추출
#                 priority       = str(row[3]).strip() if str(row[3]).strip() else "High"
#                 is_essential_v = str(row[4]).strip()
#                 question       = str(row[5]).strip()
#                 pass_criteria  = str(row[6]).strip()
#                 fail_criteria  = str(row[7]).strip()
#                 risk_level     = str(row[8]).strip()
#                 evidence_req_v = str(row[9]).strip()
#                 evidence_list  = str(row[10]).strip()
                
#                 # 🌟 [보안책 2] 인덱스 아웃 에러 방지하면서 action_plan 안전하게 가져오기
#                 action_plan = ""
#                 if len(row) > 11:
#                     action_plan = str(row[11]).strip()

#                 # 데이터 정제 (Y/N 규격화)
#                 is_essential = "Y" if "★" in is_essential_v or "Y" in is_essential_v.upper() else "N"
#                 evidence_required = "Y" if "Y" in evidence_req_v.upper() or "예" in evidence_req_v else "N"

#                 # 코드 프리픽스 분류 기법
#                 if any(x in category for x in ["환경", "공정", "품질", "화학", "기후", "에너지"]):
#                     prefix = "ENV"
#                 elif any(x in category for x in ["인권", "노동", "사회", "안전", "보건"]):
#                     prefix = "SOC"
#                 else:
#                     prefix = "GOV"

#                 # 고유 ID 생성 (시트 힌트를 주어 중복 완전 격파)
#                 # 예시결과: ENV-1차 협력사-001
#                 sheet_hint = sheet_name.replace(" ", "_")
#                 indicator_no = f"{prefix}-{sheet_hint}-{counters[prefix]:03d}"
#                 counters[prefix] += 1

#                 checklist_data.append(
#                     (
#                         indicator_no, category, indicator_name, priority, is_essential,
#                         question, pass_criteria, fail_criteria, risk_level,
#                         evidence_required, evidence_list, action_plan
#                     )
#                 )

#     # 🚫 검증
#     if not checklist_data:
#         safe_print("[경고] 업로드할 유효한 체크리스트 행이 존재하지 않습니다.")
#         return False

#     # 📊 DB 적재 실행
#     safe_print(f"[DB] MariaDB 'esg_checklist' 테이블에 총 {len(checklist_data)} 행 삽입 시도...")
#     try:
#         db.save("SET FOREIGN_KEY_CHECKS = 0;")
#         db.save("DELETE FROM esg_checklist;")
#         db.save("SET FOREIGN_KEY_CHECKS = 1;")
#         safe_print("[DB] 기존 테이블 데이터를 깨끗하게 비웠습니다.")
#     except Exception as e:
#         db.save("SET FOREIGN_KEY_CHECKS = 1;")
#         safe_print(f"[경고] 테이블 초기화 실패: {e}")

#     insert_sql = """
#         INSERT INTO esg_checklist
#         (
#             indicator_no, category, indicator_name, priority, is_essential, 
#             question, pass_example, fail_example, risk_level, 
#             evidence_required, evidence_list, action_plan
#         )
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#     """
    
#     success = db.save_many(insert_sql, checklist_data)

#     if success:
#         safe_print(f"🎉 [성공] 모든 파일과 멀티 시트에서 총 {len(checklist_data)}개의 지표가 완벽하게 동기화되어 적재되었습니다!")
#         return True
#     else:
#         safe_print("[오류] 데이터베이스 벌크 적재에 실패했습니다.")
#         return False

# if __name__ == "__main__":
#     upload_checklist_excel()

import os
import pandas as pd
from config.settings import settings
import database.mariadb_client as db
from utils.helpers import safe_print

def truncate_tables():
    """
    적재 시작 전 기존 마스터 테이블의 데이터를 깨끗하고 안전하게 비웁니다.
    """
    safe_print("[DB] 마스터 테이블 데이터 초기화 시작...")
    try:
        db.save("SET FOREIGN_KEY_CHECKS = 0;")
        db.save("DELETE FROM esg_checklist;")
        db.save("DELETE FROM esg_risk_criteria;")
        db.save("SET FOREIGN_KEY_CHECKS = 1;")
        safe_print("[DB] esg_checklist 및 esg_risk_criteria 테이블이 초기화되었습니다.")
    except Exception as e:
        db.save("SET FOREIGN_KEY_CHECKS = 1;")
        safe_print(f"[경고] 테이블 초기화 중 예외 발생: {e}")


def process_generic_checklist(file_path, counters, checklist_data):
    """
    어떤 양식의 체크리스트 파일이 들어오더라도 시트 구조를 분석하여 
    유효한 데이터 행을 동적으로 추출하고 리스트에 누적합니다.
    """
    file_name = os.path.basename(file_path)
    try:
        xl_dict = pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        safe_print(f"  - [오류] 파일 로드 실패 ({file_name}): {e}")
        return

    for sheet_name, df in xl_dict.items():
        # 제외 대상 고정 시스템 시트 스킵
        if sheet_name in ["📋 표지", "리스크 분류 기준", "📊 리스크등급_요약"]:
            continue

        df = df.fillna("")
        valid_rows = 0

        for idx, row in df.iterrows():
            # 최소 유효 데이터 컬럼 확보 검증 (카테고리, 지표명, 질문 등 최소 6개 열 이상 필수)
            if len(row) < 6:
                continue

            category       = str(row[1]).strip()
            indicator_name = str(row[2]).strip()

            # 메인 헤더, 템플릿 안내 행, 대분류 행(▶) 유연하게 스킵
            if not category or not indicator_name or "카테고리" in category or "지표명" in indicator_name:
                continue
            if category.startswith("▶") or indicator_name.startswith("▶") or "No." in str(row[0]):
                continue

            # 🌟 [범용성 보완] 엑셀 열 개수가 가변적이더라도 에러 없이 동적 인덱스 가용 처리
            priority       = str(row[3]).strip() if len(row) > 3 and str(row[3]).strip() else "High"
            is_essential_v = str(row[4]).strip() if len(row) > 4 else ""
            question       = str(row[5]).strip() if len(row) > 5 else ""
            pass_criteria  = str(row[6]).strip() if len(row) > 6 else ""
            fail_criteria  = str(row[7]).strip() if len(row) > 7 else ""
            risk_level     = str(row[8]).strip() if len(row) > 8 else ""
            evidence_req_v = str(row[9]).strip() if len(row) > 9 else ""
            evidence_list  = str(row[10]).strip() if len(row) > 10 else ""
            action_plan    = str(row[11]).strip() if len(row) > 11 else ""

            # 데이터 정제 표준화 (Y/N)
            is_essential = "Y" if "★" in is_essential_v or "Y" in is_essential_v.upper() else "N"
            evidence_required = "Y" if "Y" in evidence_req_v.upper() or "예" in evidence_req_v else "N"

            # 도메인 카테고리 식별 및 코드 부여
            if any(x in category for x in ["환경", "공정", "품질", "화학", "기후", "에너지"]):
                prefix = "ENV"
            elif any(x in category for x in ["인권", "노동", "사회", "안전", "보건"]):
                prefix = "SOC"
            else:
                prefix = "GOV"

            # 🌟 중복 없는 글로벌 유니크 기본키(PK) 발급 규칙 생성
            clean_sheet = sheet_name.replace(" ", "_").replace("-", "_")
            indicator_no = f"{prefix}-{clean_sheet}-{counters[prefix]:03d}"
            counters[prefix] += 1

            checklist_data.append(
                (
                    indicator_no, category, indicator_name, priority, is_essential,
                    question, pass_criteria, fail_criteria, risk_level,
                    evidence_required, evidence_list, action_plan
                )
            )
            valid_rows += 1
            
        if valid_rows > 0:
            safe_print(f"  - [시트 적재 완료] '{sheet_name}' 시트에서 유효 지표 {valid_rows}개 획득")


def process_generic_risk_criteria(file_path, risk_criteria_data):
    """
    파일명에 '리스크' 또는 '기준'이 들어간 마스터 파일을 파싱하여 
    위험 등급 분류 매트릭스 데이터를 추출합니다.
    """
    file_name = os.path.basename(file_path)
    try:
        xl_dict = pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        safe_print(f"  - [오류] 리스크 파일 로드 실패 ({file_name}): {e}")
        return

    for sheet_name, df in xl_dict.items():
        df = df.fillna("")
        for idx, row in df.iterrows():
            if len(row) < 4:
                continue
            
            item_name   = str(row[0]).strip() # 항목 명칭
            high_risk   = str(row[1]).strip() # 고위험 기준
            medium_risk = str(row[2]).strip() # 중위험 기준
            low_risk    = str(row[3]).strip() # 저위험 기준

            if not item_name or "항목" in item_name or "리스크 분류" in item_name:
                continue

            risk_criteria_data.append((item_name, high_risk, medium_risk, low_risk))
            
    safe_print(f"  - [마스터 적재 완료] '{file_name}' 파일에서 리스크 매트릭스 {len(risk_criteria_data)}개 기준 확보")


def main(excel_dir="esg_excel_files"):
    """
    설정된 폴더 내의 모든 파일을 스캔하여 성격에 맞는 테이블로 통합 벌크 업로드를 수행합니다.
    """
    safe_print(f"\n🚀 [통합 파이프라인] '{excel_dir}' 내 전수 데이터 자동 분석 시작...")

    if not os.path.exists(excel_dir) or not os.path.isdir(excel_dir):
        safe_print(f"[오류] 지정한 디렉토리가 존재하지 않습니다: {excel_dir}")
        return False

    # 데이터 누적용 컨테이너 및 전역 일련번호 카운터
    checklist_data = []
    risk_criteria_data = []
    counters = {"ENV": 1, "SOC": 1, "GOV": 1}

    # 1단계: 폴더 내부 스캔 및 동적 분류 (Dynamic Categorization)
    all_files = [os.path.join(excel_dir, f) for f in os.listdir(excel_dir) if f.endswith(('.xlsx', '.xls')) and not f.startswith('~$')]

    if not all_files:
        safe_print(f"[경고] 폴더 '{excel_dir}' 내에 실행 가능한 엑셀 파일이 존재하지 않습니다.")
        return False

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        
        # 🌟 [해결책] 파일명 키워드를 분석하여 알맞은 파싱 알고리즘으로 동적 매핑 호출
        if "리스크" in file_name or "기준" in file_name:
            safe_print(f"[라우팅] 리스크 분류 마스터 파일 감지 -> {file_name}")
            process_generic_risk_criteria(file_path, risk_criteria_data)
        else:
            safe_print(f"[라우팅] 공급망/협력사 체크리스트 파일 감지 -> {file_name}")
            process_generic_checklist(file_path, counters, checklist_data)

    # 2단계: 기존 DB 테이블 일괄 초기화
    truncate_tables()

    # 3단계: 최종 안전 벌크 인서트(Bulk Insert) 실행
    success_checklist = True
    success_risk = True

    if checklist_data:
        safe_print(f"[DB] 'esg_checklist' 테이블에 {len(checklist_data)}개 행 데이터 삽입 중...")
        insert_check_sql = """
            INSERT INTO esg_checklist
            (
                indicator_no, category, indicator_name, priority, is_essential, 
                question, pass_example, fail_example, risk_level, 
                evidence_required, evidence_list, action_plan
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        success_checklist = db.save_many(insert_check_sql, checklist_data)

    if risk_criteria_data:
        safe_print(f"[DB] 'esg_risk_criteria' 테이블에 {len(risk_criteria_data)}개 행 데이터 삽입 중...")
        insert_risk_sql = """
            INSERT INTO esg_risk_criteria (item_name, high_risk, medium_risk, low_risk)
            VALUES (?, ?, ?, ?)
        """
        success_risk = db.save_many(insert_risk_sql, risk_criteria_data)

    # 최종 결과 종합 리포트 출력
    if success_checklist and success_risk:
        safe_print("\n==================================================================")
        safe_print(f"🎉 [성공] 동적 적재 파이프라인 완수! 총 {len(checklist_data)}개 지표 및 {len(risk_criteria_data)}개 리스크 기준 적재 완료.")
        safe_print("==================================================================")
        return True
    else:
        safe_print("\n[오류] 데이터베이스 벌크 인서트 중 일부 과정에 실패가 발생했습니다.")
        return False

if __name__ == "__main__":
    main()