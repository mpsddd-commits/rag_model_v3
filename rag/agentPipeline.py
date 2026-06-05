import os
import json
import time
from datetime import datetime
import mariadb

# 기존 프로젝트의 핵심 모듈 호출 레이어
import dbClient as db
from settings import settings, safePrint

# =====================================================================
# 1. esgOntologyTemplate.jsonl 명세를 AI_AGENT_RULE 마스터 테이블에 적재 (Upsert)
# =====================================================================
def syncOntologyRulesToDb(jsonlPath="./esgOntologyTemplate.jsonl"):
    """
    esgOntologyTemplate.jsonl 데이터를 정제하여 AI_AGENT_RULE 마스터 테이블에 벌크 적재합니다.
    BOOL 타입의 threshold_value 정제 및 regulation 동적 추출 로직이 추가되었습니다.
    """
    safePrint(f"[*] [AI_AGENT_RULE] 온톨로지 마스터 동기화 파이프라인 가동: {jsonlPath}")
    
    if not os.path.exists(jsonlPath):
        safePrint(f"[!] 에러: {jsonlPath} 원천 온톨로지 파일이 경로에 존재하지 않습니다.")
        return False

    # SELF_ASSESS_CHECKLIST 테이블로부터 지표별 마스터 메타 정보 로드
    indicatorMetaMap = {}
    try:
        mappingRows = db.findAll("SELECT indicator_no, partner_type, category FROM SELF_ASSESS_CHECKLIST")
        for row in mappingRows:
            ino = row["indicator_no"]
            if ino not in indicatorMetaMap:
                indicatorMetaMap[ino] = {
                    "partner_type": row["partner_type"],
                    "category": row["category"]
                }
        safePrint(f"[*] [매핑 동기화] SELF_ASSESS_CHECKLIST로부터 {len(indicatorMetaMap)}개의 원천 지표 메타데이터를 캐싱했습니다.")
    except Exception as e:
        safePrint(f"[!] 경고: SELF_ASSESS_CHECKLIST 조회 실패(기본값 매핑으로 보완): {e}")

    conn = db.getMariaConn()
    if not conn:
        safePrint("[!] MariaDB 연결을 가져오지 못해 적재를 중단합니다.")
        return False

    try:
        cursor = conn.cursor(dictionary=True)
        
        # 📌 regulation 컬럼 추가 및 ON DUPLICATE KEY UPDATE 명세 보완
        upsertSql = """
            INSERT INTO `AI_AGENT_RULE` (
                indicator_no,
                sub_id,
                rule_code,
                rule_name,
                category,
                tier_scope,
                metric_key,
                operator,
                threshold_value,
                fail_threshold,
                severity,
                notify_yn,
                action_required,
                regulation,
                active_yn
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Y', %s, %s, 'Y')
            ON DUPLICATE KEY UPDATE
                rule_code       = VALUES(rule_code),
                rule_name       = VALUES(rule_name),
                category        = VALUES(category),
                tier_scope      = VALUES(tier_scope),
                metric_key      = VALUES(metric_key),
                operator        = VALUES(operator),
                threshold_value = VALUES(threshold_value),
                fail_threshold  = VALUES(fail_threshold),
                severity        = VALUES(severity),
                action_required = VALUES(action_required),
                regulation      = VALUES(regulation),
                updated_at      = NOW()
        """

        recordsToInsert = []
        
        # 규제 키워격 동적 매핑용 리스트
        targetRegulations = ["CSDDD", "RoHS", "REACH", "IRA", "CBAM", "ILO", "IRMA", "IFC", "WHO"]

        with open(jsonlPath, "r", encoding="utf-8") as f:
            for lineNo, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    meta = data.get("meta", {})
                    
                    indicator_no = data["indicator_no"]
                    sub_id = data.get("sub_id", "MAIN")
                    
                    metaInfo = indicatorMetaMap.get(indicator_no, {"partner_type": "3차 적용", "category": "기타"})
                    db_category = metaInfo["category"]
                    db_tier_scope = metaInfo["partner_type"]
                    
                    rule_code = f"RULE_{str(indicator_no).zfill(3)}"
                    if sub_id != "MAIN":
                        rule_code += f"_{sub_id}"

                    m_key = meta.get("criteria_type", "NUMERIC")
                    op = meta.get("operator", "==")
                    
                    # 📌 [해결책 1] BOOL 타입의 threshold_value 보정 및 RANGE 분기 정교화
                    if m_key == "RANGE":
                        db_threshold = f"{meta.get('min_value')}~{meta.get('max_value')}"
                    elif m_key == "BOOL":
                        # operator 문장(예: '== Y')에서 Y/N 값을 보정하여 적재
                        if "Y" in op:
                            db_threshold = "Y"
                        elif "N" in op:
                            db_threshold = "N"
                        else:
                            db_threshold = "Y" # 기본값 처리
                    else:
                        db_threshold = str(meta.get("threshold_value", "")) if meta.get("threshold_value") is not None else ""

                    # 📌 [해결책 2] action_plan 및 raw_expression 내부에서 규제(Regulation) 정보 동적 추출
                    detectedRegs = []
                    fullTextContext = data.get("raw_expression", "") + " " + data.get("action_plan", "")
                    for reg in targetRegulations:
                        if reg in fullTextContext:
                            detectedRegs.append(reg)
                    
                    db_regulation = ", ".join(detectedRegs) if detectedRegs else "일반 가드레일"

                    record = (
                        indicator_no,
                        sub_id,
                        rule_code,
                        data["indicator_name"],
                        db_category,                  
                        db_tier_scope,                
                        m_key,                        
                        op,                           
                        db_threshold,                 
                        f"기준 스펙 범주 이탈 ({op} {db_threshold})", 
                        "WARN",                       
                        data["action_plan"],
                        db_regulation # 13번째 변수: regulation 컬럼 바인딩 추가
                    )
                    recordsToInsert.append(record)

                except json.JSONDecodeError:
                    continue

        if recordsToInsert:
            cursor.executemany(upsertSql, recordsToInsert)
            conn.commit()
            safePrint(f"[+] [AI_AGENT_RULE] 벌크 동기화 마감: 총 {len(recordsToInsert)}개 규칙 적재 성공.")
        else:
            safePrint("[!] 파싱 가공에 성공한 온톨로지 규칙 데이터가 없습니다.")

        cursor.close()
        return True

    except Exception as err:
        safePrint(f"[!] [AI_AGENT_RULE] 동기화 중 에러 발생: {err}")
        if conn and conn.open: 
            conn.rollback()
        return False
    finally:
        if conn and conn.open:
            conn.close()


# =====================================================================
# 2. 공급망 ESG 자가진단 위반 탐지 및 감사 결과 실시간 감사 에이전트 구동
# =====================================================================
def runComplianceAuditAgent(partnerCode: str, supplierAnswers: dict):
    """
    제공해주신 최신 AI_AGENT_RUN_LOG 및 AI_AGENT_ALERT 스키마 규격을 100% 반영한
    공급망 ESG 위반 탐지 및 실시간 감사 에이전트 메인 엔진입니다.
    """
    safePrint(f"\n[*] 협력사 [{partnerCode}] 공급망 ESG 자동 실사 에이전트 구동...")
    
    startTime = time.time()
    conn = db.getMariaConn()
    if not conn:
        safePrint("[!] DB 커넥션 유실로 에이전트 구동 실패")
        return

    runId = None
    rulesEvaluated = 0
    alertsGenerated = 0
    criticalCount = 0
    failCount = 0
    warnCount = 0

    try:
        cur = conn.cursor(dictionary=True)
        
        # 1단계: AI_AGENT_RUN_LOG 마스터 로그 개시 (AUTO_INCREMENT이므로 run_id 제외하고 INSERT)
        insertRunLogSql = """
            INSERT INTO `AI_AGENT_RUN_LOG` (
                trigger_type, scope, scope_target, rules_evaluated, 
                alerts_generated, critical_count, fail_count, warn_count, 
                status, started_at
            ) VALUES ('AUTOMATIC', 'PARTNER', %s, 0, 0, 0, 0, 0, 'RUNNING', NOW())
        """
        cur.execute(insertRunLogSql, (partnerCode,))
        conn.commit()
        
        # 생성된 BIGINT run_id 식별자 추출
        runId = cur.lastrowid
        
        # 2단계: 최신 활성화 온톨로지 마스터 규칙 로드 (AI_AGENT_RULE 구조와 매핑)
        cur.execute("SELECT * FROM `AI_AGENT_RULE` WHERE active_yn = 'Y'")
        ruleRows = cur.fetchall()
        rulesEvaluated = len(ruleRows)
        
        alertsToInsert = []
        
        # 3단계: 복합 연산 및 위반 심사 루프 작동
        for rule in ruleRows:
            ruleId = rule["rule_id"]
            ino = rule["indicator_no"]
            sub_id = rule["sub_id"]
            m_key = rule["metric_key"]
            op = rule["operator"]
            th_str = rule["threshold_value"]
            severity_upper = rule["severity"].strip().upper()
            
            # 유연한 멀티 파트 답변 매칭 메커니즘
            userValue = None
            if sub_id != "MAIN" and sub_id in supplierAnswers:
                userValue = supplierAnswers[sub_id]
            elif str(ino) in supplierAnswers:
                userValue = supplierAnswers[str(ino)]
            elif ino in supplierAnswers:
                userValue = supplierAnswers[ino]
                
            if userValue is None:
                continue

            isViolated = False
            deviationPct = 0.0
            
            try:
                if m_key == "NUMERIC" and userValue is not None:
                    floatUser = float(userValue)
                    floatThreshold = float(th_str)
                    
                    if op == "<" and not (floatUser < floatThreshold): isViolated = True
                    elif op == "<=" and not (floatUser <= floatThreshold): isViolated = True
                    elif op == ">" and not (floatUser > floatThreshold): isViolated = True
                    elif op == ">=" and not (floatUser >= floatThreshold): isViolated = True
                    elif op == "==" and not (floatUser == floatThreshold): isViolated = True
                    
                    # 수치형 지표 이탈 시 편차율(%) 연산 가공 (분모 0 방지)
                    if isViolated and floatThreshold != 0:
                        deviationPct = round(((floatUser - floatThreshold) / floatThreshold) * 100, 2)
                
                elif m_key == "BOOL":
                    normUser = str(userValue).strip().upper()
                    if "Y" in op and normUser != "Y": isViolated = True
                    elif "N" in op and normUser != "N": isViolated = True
                    
                elif m_key == "RANGE":
                    floatUser = float(userValue)
                    if "~" in th_str:
                        min_v, max_v = map(float, th_str.split("~"))
                        if not (min_v <= floatUser <= max_v): 
                            isViolated = True
                            if min_v != 0 and floatUser < min_v:
                                deviationPct = round(((floatUser - min_v) / min_v) * 100, 2)
                            elif max_v != 0 and floatUser > max_v:
                                deviationPct = round(((floatUser - max_v) / max_v) * 100, 2)

            except (ValueError, TypeError):
                isViolated = True

            # 4단계: 위반 감지 시 AI_AGENT_ALERT 적재 구조 빌드
            if isViolated:
                alertsGenerated += 1
                if severity_upper == "CRITICAL":
                    criticalCount += 1
                elif severity_upper == "FAIL":
                    failCount += 1
                else:
                    warnCount += 1
                
                alertTitle = f"[공급망 실사 위반] {rule['rule_name']} 기준 미달 알림"
                alertContent = (
                    f"협력사 제출 응답값 '{userValue}'가 허용 합격 기준인 "
                    f"[{op} {th_str}] 범위를 이탈하였습니다. 신속한 공급망 위험 조치가 필요합니다."
                )
                
                # AI 자동화 추론 데이터 세트 가공 매핑
                aiReasoning = f"평가 키 {m_key} 연산 결과, 임계치 명세 범주를 위반한 것으로 확정 판정함."
                aiRecommendation = rule.get("action_required") if rule.get("action_required") else "공급사 현장 실사 및 개선조치 계획서(CAPA) 제출을 즉시 요구하십시오."
                
                alertRecord = (
                    ruleId,
                    partnerCode,        # partner_id 컬럼에 바인딩
                    ino,                # indicator_no
                    m_key,              # metric_key
                    str(userValue),     # actual_value
                    th_str,             # threshold_value
                    deviationPct,       # deviation_pct
                    severity_upper,     # severity
                    95.50,              # ai_confidence
                    aiReasoning,        # ai_reasoning
                    aiRecommendation,   # ai_recommendation
                    alertTitle,         # alert_title
                    alertContent,       # alert_content
                    rule.get("regulation"), # regulation
                    runId               # run_id (BIGINT FK)
                )
                alertsToInsert.append(alertRecord)

        # 5단계: 대량 위반 알림 벌크 인서트 수행
        if alertsToInsert:
            insertAlertSql = """
                INSERT INTO `AI_AGENT_ALERT` (
                    rule_id, partner_id, indicator_no, metric_key, actual_value, 
                    threshold_value, deviation_pct, severity, ai_confidence, 
                    ai_reasoning, ai_recommendation, alert_title, alert_content, 
                    regulation, status, run_id, delete_yn
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPEN', %s, 0)
            """
            cur.executemany(insertAlertSql, alertsToInsert)

        # 6단계: 트랜잭션 마감 및 AI_AGENT_RUN_LOG 종합 마스터 정보 실시간 업데이트
        durationMs = int((time.time() - startTime) * 1000)
        finalStatus = "SUCCESS" if alertsGenerated == 0 else "ALERT"
        aiSummary = f"감사 에이전트가 총 {rulesEvaluated}개의 가드레일 룰셋을 기반으로 검증을 완료했습니다. 위반 알림 {alertsGenerated}건 발생."
        
        updateRunLogSql = """
            UPDATE `AI_AGENT_RUN_LOG` 
            SET status = %s,
                rules_evaluated = %s,
                alerts_generated = %s,
                critical_count = %s,
                fail_count = %s,
                warn_count = %s,
                ai_model = 'Rule-Engine-v2',
                ai_summary = %s,
                duration_ms = %s,
                ended_at = NOW()
            WHERE run_id = %s
        """
        cur.execute(updateRunLogSql, (
            finalStatus, rulesEvaluated, alertsGenerated, 
            criticalCount, failCount, warnCount, aiSummary, durationMs, runId
        ))
        
        conn.commit()
        safePrint(f"[+] 에이전트 실사 완료 (Run ID: {runId} | 위반: {alertsGenerated}건 [Crit: {criticalCount}, Fail: {failCount}, Warn: {warnCount}] | 소요시간: {durationMs}ms)")

    except mariadb.Error as err:
        safePrint(f"[!] 에이전트 구동 중 치명적 장애 발생: {err}")
        if conn and conn.open: 
            conn.rollback()
        
        if runId and conn and conn.open:
            try:
                with conn.cursor() as errCur:
                    durationMs = int((time.time() - startTime) * 1000)
                    errCur.execute(
                        "UPDATE `AI_AGENT_RUN_LOG` SET status = 'FAIL', error_message = %s, duration_ms = %s, ended_at = NOW() WHERE run_id = %s",
                        (str(err), durationMs, runId)
                    )
                    conn.commit()
            except:
                pass
    finally:
        if conn and conn.open:
            conn.close()

# =====================================================================
# 3. 로컬 독립 검증 부문
# =====================================================================
if __name__ == "__main__":
    # 1단계: 규칙 원천 파일 로드 및 동기화 기동
    syncOntologyRulesToDb("./esgOntologyTemplate.jsonl")
    
    # 2단계: 다중 서브 지표 처리가 포함된 가상의 답변집 테스트
    mockSupplierData = {
        "PAH": 12.5,     
        "DIOXIN": 0.04,  
        "36": "N"        
    }
    
    runComplianceAuditAgent("PARTNER_HYUNDAI_01", mockSupplierData)