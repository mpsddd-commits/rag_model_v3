import os
import json
import time
import re
import mariadb
import asyncio
from datetime import datetime
# 기존 프로젝트의 핵심 모듈 호출 레이어
import src.utils.dbClient as db
from src.utils.settings import settings, safePrint

# =====================================================================
# [공통 헬퍼] load.py 구조 기반 서술형 문장 내 수치 자동 정제 함수
# =====================================================================
def extractNumericValueFromText(text: str):
    """
    load.py의 parseComplexCriteria 기법을 적용하여 제품명/규격번호(4자리 숫자 등)를 필터링하고
    문장 내에서 '1.25'와 같은 핵심 실수(float) 데이터를 안전하게 추출합니다.
    """
    if not text:
        return None

    # 1. 전처리 가드레일: 의도치 않은 메타 숫자(4자리 제품명 3003, ASTM B209 등) 클렌징
    cleanText = re.sub(r"\b\d{4}\b", "", text)
    cleanText = re.sub(r"B\d+", "B", cleanText)

    # 2. 퍼센트 기호(%)가 붙어 있는 핵심 기입 데이터를 우선 포착
    percentMatch = re.search(r"(\d+\.\d+|\d+)\s*%", cleanText)
    if percentMatch:
        return float(percentMatch.group(1))

    # 3. 일반적인 수치 정규식 탐색
    nums = re.findall(r"\d+\.\d+|\d+", cleanText)
    if nums:
        return float(nums[0])
        
    return None

def buildSupplierAnswers(answers: list) -> dict:
    """
    DB에서 가져온 raw 답변 리스트를 수치 추출 가드레일을 거쳐 
    AI 룰 엔진이 즉시 매칭할 수 있는 딕셔너리 구조로 변환합니다.
    """
    supplierAnswers = {}
    for ans in answers:
        ino = ans.get("indicator_no")
        text = str(ans.get("answer_text", "")).strip()
        
        # 원본 텍스트 매핑 백업 (기본 폴백용)
        supplierAnswers[str(ino)] = text
        supplierAnswers[ino] = text
        
        # 통합 수치 전처리 레이어 가동
        extracted_num = extractNumericValueFromText(text)
        if extracted_num is not None:
            supplierAnswers[str(ino)] = extracted_num
            supplierAnswers[ino] = extracted_num
            
    return supplierAnswers

# def buildSupplierAnswers(answers: list) -> dict:
#     """
#     자가진단 답변 목록을 AI 룰 엔진이 매칭할 수 있는 supplierAnswers 딕셔너리로 변환합니다.
#     수치 추출 및 서브 지표(PAH, 다이옥신, 중금속 등) 동적 파싱을 수행합니다.
#     """
#     supplierAnswers = {}
#     for ans in answers:
#         ino = ans.get("indicator_no")
#         text = str(ans.get("answer_text", "")).strip()
        
#         # 기본 매핑
#         supplierAnswers[str(ino)] = text
#         supplierAnswers[ino] = text
        
#         # 특정 지표의 경우 sub_id로 파싱하여 추가 매핑
#         # 예: 35번 지표 (PAH / DIOXIN)
#         if ino == 35:
#             pah_match = re.search(r'PAH\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             dioxin_match = re.search(r'(?:DIOXIN|다이옥신)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             if pah_match:
#                 supplierAnswers["PAH"] = float(pah_match.group(1))
#             if dioxin_match:
#                 supplierAnswers["DIOXIN"] = float(dioxin_match.group(1))
                
#         # 예: 8번 지표 (AS / CD / PB)
#         elif ino == 8:
#             as_match = re.search(r'(?:AS|비소)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             cd_match = re.search(r'(?:CD|카드뮴)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             pb_match = re.search(r'(?:PB|납)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             if as_match:
#                 supplierAnswers["AS"] = float(as_match.group(1))
#             if cd_match:
#                 supplierAnswers["CD"] = float(cd_match.group(1))
#             if pb_match:
#                 supplierAnswers["PB"] = float(pb_match.group(1))
                
#         # 예: 9번 지표 (AL2O3 / SIO2)
#         elif ino == 9:
#             al_match = re.search(r'Al2O3\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             si_match = re.search(r'SiO2\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             if al_match:
#                 supplierAnswers["AL2O3"] = float(al_match.group(1))
#             if si_match:
#                 supplierAnswers["SIO2"] = float(si_match.group(1))
                
#         # 예: 19번 지표 (IAI_SGA / NA2O)
#         elif ino == 19:
#             sga_match = re.search(r'(?:IAI_SGA|순도)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             na2o_match = re.search(r'Na2O\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
#             if sga_match:
#                 supplierAnswers["IAI_SGA"] = float(sga_match.group(1))
#             if na2o_match:
#                 supplierAnswers["NA2O"] = float(na2o_match.group(1))
                
#         extracted_num = extractNumericValueFromText(text)
#         if extracted_num is not None:
#             # 장문의 서술형 문장 대신 "1.25" 같은 깔끔한 float 수치로 오버라이드합니다.
#             supplierAnswers[str(ino)] = extracted_num
#             supplierAnswers[ino] = extracted_num
            
#     return supplierAnswers

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
        mappingRows = db.findAll("SELECT indicator_no, partner_type, category, priority FROM SELF_ASSESS_CHECKLIST")
        for row in mappingRows:
            ino = row["indicator_no"]
            if ino not in indicatorMetaMap:
                indicatorMetaMap[ino] = {
                    "partner_type": row["partner_type"],
                    "category": row["category"],
                    "priority": str(row["priority"]).strip().upper() if row.get("priority") else "WARN"
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
                    
                    metaInfo = indicatorMetaMap.get(indicator_no, {"partner_type": "3차 적용", "category": "기타", "priority": "WARN"})
                    db_category = metaInfo["category"]
                    db_tier_scope = metaInfo["partner_type"]
                    db_severity = metaInfo["priority"] if metaInfo["priority"] in ["CRITICAL", "HIGH", "MEDIUM"] else "WARN"

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
                        db_severity,                       
                        data["action_plan"],
                        db_regulation 
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
# 📌 [함수 1] AI 자동 감사 가동 및 실시간 알림/위험군 적재 함수
# =====================================================================
def executeComplianceAudit(partnerCode: str, supplierAnswers: dict):
    """
    규칙 기반 ESG 자가진단 위반 탐지 및 실시간 DB 적재/알림 마스터 파이프라인
    - AI_AGENT_ALERT, ALARM 테이블 데이터 누적 적재
    - COMPANY 위험군 등급 실시간 갱신 및 WebSocket 실시간 푸시 토글
    """
    safePrint(f"\n[*] [AI 엔진] 협력사 [{partnerCode}] 공급망 ESG 규칙 검사 및 알림 파이프라인 가동...")
    startTime = time.time()
    
    conn = db.getMariaConn()
    if not conn:
        safePrint("[!] 에러: MariaDB 커넥션 유실로 감사 엔진 가동이 취소되었습니다.")
        return None

    runId = None
    try:
        cur = conn.cursor(dictionary=True)
        
        # 1. AI_AGENT_RUN_LOG 마스터 인스턴스 생성
        insertRunLogSql = """
            INSERT INTO `AI_AGENT_RUN_LOG` (
                trigger_type, scope, scope_target, rules_evaluated, 
                alerts_generated, critical_count, fail_count, warn_count, 
                status, started_at
            ) VALUES ('AUTOMATIC', 'PARTNER', %s, 0, 0, 0, 0, 0, 'RUNNING', NOW())
        """
        cur.execute(insertRunLogSql, (partnerCode,))
        conn.commit()
        runId = cur.lastrowid
        
        # 2. 마스터 규칙 로드 (active_yn = 'Y')
        cur.execute("SELECT * FROM `AI_AGENT_RULE` WHERE active_yn = 'Y'")
        ruleRows = cur.fetchall()
        rulesEvaluated = len(ruleRows)
        
        alertsToInsert = []
        alertsGenerated = 0
        criticalCount = 0
        failCount = 0
        warnCount = 0
        actionPlans = []
        
        # 3. 위반 연산 루프
        for rule in ruleRows:
            ruleId = rule["rule_id"]
            ino = rule["indicator_no"]
            sub_id = rule["sub_id"]
            m_key = rule["metric_key"]
            op = rule["operator"]
            th_str = rule["threshold_value"]
            severity_upper = rule["severity"].strip().upper()
            
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
                if m_key == "NUMERIC":
                    floatUser = float(userValue)
                    floatThreshold = float(th_str)
                    if op == "<" and not (floatUser < floatThreshold): isViolated = True
                    elif op == "<=" and not (floatUser <= floatThreshold): isViolated = True
                    elif op == ">" and not (floatUser > floatThreshold): isViolated = True
                    elif op == ">=" and not (floatUser >= floatThreshold): isViolated = True
                    elif op == "==" and not (floatUser == floatThreshold): isViolated = True
                    
                    if isViolated and floatThreshold != 0:
                        deviationPct = round(((floatUser - floatThreshold) / floatThreshold) * 100, 2)
                
                elif m_key == "BOOL":
                    normUser = str(userValue).strip().upper()
                    if "Y" in op and normUser != "Y": isViolated = True
                    elif "N" in op and normUser != "N": isViolated = True
                    
                elif m_key == "RANGE" and "~" in th_str:
                    floatUser = float(userValue)
                    min_v, max_v = map(float, th_str.split("~"))
                    if not (min_v <= floatUser <= max_v): 
                        isViolated = True
                        if min_v != 0 and floatUser < min_v:
                            deviationPct = round(((floatUser - min_v) / min_v) * 100, 2)
                        elif max_v != 0 and floatUser > max_v:
                            deviationPct = round(((floatUser - max_v) / max_v) * 100, 2)
            except:
                isViolated = True

            if isViolated:
                alertsGenerated += 1
                if severity_upper == "CRITICAL": criticalCount += 1
                elif severity_upper == "FAIL": failCount += 1
                else: warnCount += 1
                
                alertTitle = f"[공급망 실사 위반] {rule['rule_name']} 기준 미달"
                alertContent = f"제출값 '{userValue}'가 허용 기준 [{op} {th_str}]을 벗어났습니다."
                aiReasoning = f"평가 키 {m_key} 연산 결과, 임계치 위반 확정."
                aiRecommendation = rule.get("action_required") or "개선조치 계획서(CAPA) 제출 요구"
                
                alertsToInsert.append((
                    ruleId, partnerCode, ino, m_key, str(userValue), th_str, 
                    deviationPct, severity_upper, 95.50, aiReasoning, aiRecommendation, 
                    alertTitle, alertContent, rule.get("regulation"), runId
                ))
                
                actionPlans.append({
                    "indicator_no": ino,
                    "rule_name": rule["rule_name"],
                    "severity": severity_upper,
                    "actual_value": str(userValue),
                    "threshold_value": th_str,
                    "action_plan": aiRecommendation
                })

        # 4. 위반 상세 내역 데이터 벌크 저장 (AI_AGENT_ALERT)
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

        # 5. 실행 결과 요약 로그 마감
        durationMs = int((time.time() - startTime) * 1000)
        finalStatus = "SUCCESS" if alertsGenerated == 0 else "ALERT"
        aiSummary = f"총 {rulesEvaluated}개 마스터 규칙 대조 완료. 위반 {alertsGenerated}건 최종 판정."
        
        cur.execute("""
            UPDATE `AI_AGENT_RUN_LOG` 
            SET status = %s, rules_evaluated = %s, alerts_generated = %s,
                critical_count = %s, fail_count = %s, warn_count = %s,
                ai_model = 'Rule-Engine-v2-E2E', ai_summary = %s, duration_ms = %s, ended_at = NOW()
            WHERE run_id = %s
        """, (finalStatus, rulesEvaluated, alertsGenerated, criticalCount, failCount, warnCount, aiSummary, durationMs, runId))
        
        # 6. COMPANY 테이블 위험 등급 마이그레이션 갱신
        riskLevel = "고위험군" if criticalCount > 0 else ("중위험군" if (failCount > 0 or warnCount > 0) else "저위험군")
        cur.execute("UPDATE `COMPANY` SET risk_level = %s WHERE partner_id = %s AND delete_yn = 0", (riskLevel, partnerCode))
        
        # 7. 마스터 ALARM 테이블 최종 영구 적재 연동 (DBeaver 연동 확인용 핵심 코드)
        alarm_level = "warn" if finalStatus == "ALERT" else "info"
        if criticalCount > 0: alarm_level = "fail"
        
        insertAlarmSql = """
            INSERT INTO `ALARM` (partner_id, type, level, title, content, path, meta_json, is_read, delete_yn, created_at)
            VALUES (%s, 'AI_AGENT', %s, %s, %s, %s, %s, 0, 0, NOW())
        """
        
        cur.execute("SELECT COUNT(*) as cnt FROM `COMPANY` WHERE risk_level = '고위험군' AND delete_yn = 0")
        highRiskCount = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM `COMPANY` WHERE risk_level = '중위험군' AND delete_yn = 0")
        mediumRiskCount = cur.fetchone()["cnt"]
        
        wsMessage = {
            "title": f"🔴 [자가진단 완료] 감사 판정 - {'불합격' if alertsGenerated > 0 else '합격'}",
            "content": f"위반 {alertsGenerated}건 발생. (고위험군: {highRiskCount}개사 / 중위험군: {mediumRiskCount}개사 관리 중)",
            "path": f"/esg/dashboard?partnerId={partnerCode}",
            "meta": {"partner_id": partnerCode, "status": "불합격" if alertsGenerated > 0 else "합격", "action_plans": actionPlans}
        }
        
        cur.execute(insertAlarmSql, (
            partnerCode, alarm_level, wsMessage["title"], wsMessage["content"], 
            wsMessage["path"], json.dumps(wsMessage["meta"], ensure_ascii=False)
        ))
        conn.commit()
        safePrint(f"[+] [ALARM 적재] AI 에이전트 실사 알림이 ALARM 테이블에 안전하게 적재되었습니다. (Run ID: {runId})")
        
        # 8. 실시간 프론트엔드 대시보드 푸시용 비동기 WebSocket 트리거
        from src.utils.websc import manager
        async def sendWsAlerts():
            if manager.isConnected(partnerCode):
                await manager.sendToPartner(partnerCode, wsMessage)
        try:
            asyncio.get_event_loop().run_until_complete(sendWsAlerts())
        except:
            pass

        return runId
    except mariadb.Error as e:
        safePrint(f"[!] [에이전트 에러] 트랜잭션 오류 발생으로 롤백합니다: {e}")
        if conn: conn.rollback()
        return None
    finally:
        if conn: conn.close()

# =====================================================================
# 📌 [함수 2] 기존 main.py 스타일의 자가진단 텍스트 요약 보고서 생성 함수
# =====================================================================
def generateSelfAssessReport(partnerCode: str, supplierAnswers: dict) -> str:
    """
    [기존 main.py 서빙 로직 이식] 자가진단 정제 데이터 및 온톨로지 규칙을 결합하여
    경영진 보고 및 화면 표출용 종합 진단서 요약 텍스트(마크다운 규격)를 생성합니다.
    """
    conn = db.getMariaConn()
    if not conn:
        return "DB 연결 실패로 텍스트 보고서를 바인딩할 수 없습니다."
        
    report_lines = []
    try:
        cur = conn.cursor(dictionary=True)
        
        cur.execute("SELECT company_name, risk_level FROM `COMPANY` WHERE partner_id = %s AND delete_yn = 0", (partnerCode,))
        comp = cur.fetchone()
        comp_name = comp["company_name"] if comp else partnerCode
        risk_lvl = comp["risk_level"] if comp else "미정"

        report_lines.append(f"# 📋 공급망 ESG 자가진단 종합 AI 실사 보고서")
        report_lines.append(f"- **대상 협력사명**: {comp_name} ({partnerCode})")
        report_lines.append(f"- **AI 리스크 등급**: **{risk_lvl}**")
        report_lines.append(f"- **보고서 출력기준**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"\n---\n")
        
        cur.execute("SELECT * FROM `AI_AGENT_RULE` WHERE active_yn = 'Y'")
        rules = cur.fetchall()
        
        report_lines.append(f"## 📊 온톨로지 규칙 기반 가드레일 상세 대조 내역")
        violation_count = 0
        normal_count = 0
        
        for rule in rules:
            ino = rule["indicator_no"]
            sub_id = rule["sub_id"]
            th_str = rule["threshold_value"]
            op = rule["operator"]
            m_key = rule["metric_key"]
            
            userValue = None
            if sub_id != "MAIN" and sub_id in supplierAnswers:
                userValue = supplierAnswers[sub_id]
            elif str(ino) in supplierAnswers:
                userValue = supplierAnswers[str(ino)]
            elif ino in supplierAnswers:
                userValue = supplierAnswers[ino]
                
            if userValue is None:
                continue
                
            is_violated = False
            try:
                if m_key == "NUMERIC":
                    if op == "<" and not (float(userValue) < float(th_str)): is_violated = True
                    elif op == "<=" and not (float(userValue) <= float(th_str)): is_violated = True
                    elif op == ">" and not (float(userValue) > float(th_str)): is_violated = True
                    elif op == ">=" and not (float(userValue) >= float(th_str)): is_violated = True
                    elif op == "==" and not (float(userValue) == float(th_str)): is_violated = True
                elif m_key == "BOOL":
                    if "Y" in op and str(userValue).strip().upper() != "Y": is_violated = True
                    elif "N" in op and str(userValue).strip().upper() != "N": is_violated = True
                elif m_key == "RANGE" and "~" in th_str:
                    min_v, max_v = map(float, th_str.split("~"))
                    if not (min_v <= float(userValue) <= max_v): is_violated = True
            except:
                is_violated = True
                
            status_tag = "🚨 [위반 감지]" if is_violated else "✅ [정상 기준 충족]"
            if is_violated: violation_count += 1
            else: normal_count += 1
                
            report_lines.append(
                f"### {status_tag} 문항 {ino}. {rule['rule_name']}\n"
                f"- **연계 글로벌 규제**: {rule.get('regulation') or '글로벌 일반 공급망 가이드라인'}\n"
                f"- **실제 추출 데이터(Actual)**: `{userValue}`\n"
                f"- **합격 임계 기준(Threshold)**: `{op} {th_str}`\n"
            )
            if is_violated:
                report_lines.append(f"- **💡 추천 개선 조치 방안(CAPA)**: {rule.get('action_required')}\n")

        report_lines.insert(4, f"## 📝 총평 및 AI 감사 종합 의견\n"
                              f"본 협력사의 자가진단 문서를 파싱하여 정밀 분석한 결과, 총 {normal_count + violation_count}개 맵핑 문항 중 "
                              f"**정상 반영 {normal_count}건**, **가드레일 위반 {violation_count}건**이 최종 발견되었습니다. "
                              f"안전한 공급망 관리를 위해 위반 조치 방안 명세에 따라 시정 조치 계획서 작성을 권장합니다.\n")

    except Exception as e:
        report_lines.append(f"\n[!] 분석 과정 중 예외 발생: {e}")
    finally:
        if conn: conn.close()
        
    return "\n".join(report_lines)

if __name__ == "__main__":
    # 예시: 비동기 함수 실행 가동
    asyncio.run(syncOntologyRulesToDb(jsonlPath="./esgOntologyTemplate.jsonl"))