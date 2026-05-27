import os
import pandas as pd
from config.settings import settings
import database.mariadb_client as db
from utils.helpers import safe_print

def upload_checklist_excel(excel_path="esg_excel_files/알루미늄_Al3003_ESG_지표셋_대처방안추가.xlsx"):
    """
    Parses the ESG criteria from the specified Excel sheet (② 전체_지표셋)
    and uploads the records directly into MariaDB's 'esg_checklist' table.
    Generates standard keys like ENV-01, SOC-02 matching the DDL definitions.
    """
    safe_print(f"\n[업로드] 엑셀 파일 '{excel_path}'에서 ESG 체크리스트 로드 중...")
    
    if not os.path.exists(excel_path):
        safe_print(f"[오류] 엑셀 파일을 찾을 수 없습니다: {excel_path}")
        return False
        
    try:
        # Load the checklist sheet, skipping the first row (Title banner)
        df = pd.read_excel(excel_path, sheet_name="② 전체_지표셋", skiprows=1)
        df = df.fillna("")
    except Exception as e:
        safe_print(f"[오류] 엑셀 파일 로드 실패: {e}")
        return False

    safe_print(f"[프로세스] 총 {len(df)}개 레코드 파싱 시작...")
    
    # Counters to generate codes (ENV-01, SOC-01, GOV-01)
    counters = {"ENV": 1, "SOC": 1, "GOV": 1}
    
    checklist_data = []
    
    for idx, row in df.iterrows():
        # Column mappings (based on parsed layout)
        no_val = row.iloc[0]
        category = str(row.iloc[1]).strip()
        indicator_name = str(row.iloc[2]).strip()
        pass_criteria = str(row.iloc[15]).strip()  # '합격 기준' used as numeric evaluation target
        fail_criteria = str(row.iloc[16]).strip()  # '불합격 기준'
        action_plan = str(row.iloc[20]).strip()    # '불합격 시 대처방안 (조치사항)'
        
        # Skip description or empty spacer rows
        if not indicator_name or "지표명" in indicator_name or not category:
            continue
            
        # Determine standard category prefix
        if "환경" in category:
            prefix = "ENV"
        elif "인권" in category or "노동" in category:
            prefix = "SOC"
        else:
            prefix = "GOV"
            
        # Generate standardized PK e.g., ENV-01, SOC-02
        indicator_no = f"{prefix}-{counters[prefix]:02d}"
        counters[prefix] += 1
        
        # In this context, 'pass_criteria' acts as the main rule question containing threshold values (e.g. TRIR <= 2.0)
        checklist_data.append((
            indicator_no,
            indicator_name,
            pass_criteria,      # question
            pass_criteria,      # pass_example
            fail_criteria,      # fail_example
            action_plan         # action_plan
        ))

    if not checklist_data:
        safe_print("[경고] 업로드할 유효한 체크리스트 행이 존재하지 않습니다.")
        return False
        
    safe_print(f"[DB] MariaDB 'esg_checklist' 테이블 업로드 시도 중 ({len(checklist_data)}개 행)...")
    
    # Empty existing records to avoid duplicate keys during runs
    try:
        db.save("SET FOREIGN_KEY_CHECKS = 0;")
        db.save("TRUNCATE TABLE esg_checklist;")
        db.save("SET FOREIGN_KEY_CHECKS = 1;")
        safe_print("[DB] 이전 체크리스트 데이터를 비우고 재생성했습니다 (TRUNCATE).")
    except Exception as truncate_err:
        safe_print(f"[경고] 기존 테이블 초기화 실패 (무시하고 진행): {truncate_err}")

    # Bulk insert utilizing DB client
    insert_sql = """
        INSERT INTO esg_checklist (indicator_no, indicator_name, question, pass_example, fail_example, action_plan)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    success = db.save_many(insert_sql, checklist_data)
    
    if success:
        safe_print(f"🎉 [성공] 총 {len(checklist_data)}개의 ESG 체크리스트 지표가 MariaDB에 안정적으로 업로드되었습니다!")
        # Print a small preview of the uploaded records
        safe_print("\n---- [체크리스트 업로드 미리보기] ----")
        for rec in checklist_data[:3]:
            safe_print(f"[{rec[0]}] {rec[1]} -> 기준: {rec[2][:40]}...")
        safe_print("---------------------------------------")
        return True
    else:
        safe_print("[오류] MariaDB 체크리스트 벌크 인서트에 실패했습니다. DB 연결 및 DDL 스키마를 검토하세요.")
        return False

if __name__ == "__main__":
    upload_checklist_excel()
