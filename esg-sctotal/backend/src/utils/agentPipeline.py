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
def extractNumericValueFromText(text: str):
    """
    load.py의 parseComplexCriteria 알고리즘을 기반으로 가공됨.
    문장 내 불필요한 제품명/규격번호(4자리 숫자 등)를 필터링하고
    질문하신 '1.25'와 같은 알짜배기 실수(float) 데이터를 강제 추출합니다.
    """
    if not text:
        return None

    # 1. 전처리 가드레일: 의도치 않은 메타 숫자(4자리 제품명, ASTM 규격 번호 등) 임시 제거
    cleanText = re.sub(r"\b\d{4}\b", "", text)  # 4자리 숫자(3003 등) 제거
    cleanText = re.sub(r"B\d+", "B", cleanText) # B209 등 규격명 뒤의 숫자 제거

    # 2. 범위형 수치 구조가 먼저 발견되는 경우 (예: 1.00~1.50) 대표값으로 첫 번째 값 타겟팅 방지용
    # 여기서는 "Mn 함량은 1.25%로... 기준(1.00~1.50%)" 일 때, 
    # 본인의 실제 '함량' 수치인 앞쪽 숫자를 먼저 캐치하기 위해 단일 수치 패턴을 우선 탐색하거나
    # 문맥 안에서 '%'가 붙어 있는 본인 응답 데이터를 우선 타겟팅합니다.
    percentMatch = re.search(r"(\d+\.\d+|\d+)\s*%", cleanText)
    if percentMatch:
        return float(percentMatch.group(1))

    # 3. 일반적인 수치 정규식 풀링
    nums = re.findall(r"\d+\.\d+|\d+", cleanText)
    if nums:
        return float(nums[0])
        
    return None


def buildSupplierAnswers(answers: list) -> dict:
    """
    자가진단 답변 목록을 AI 룰 엔진이 매칭할 수 있는 supplierAnswers 딕셔너리로 변환합니다.
    수치 추출 및 서브 지표(PAH, 다이옥신, 중금속 등) 동적 파싱을 수행합니다.
    """
    supplierAnswers = {}
    for ans in answers:
        ino = ans.get("indicator_no")
        text = str(ans.get("answer_text", "")).strip()
        
        # 기본 매핑
        supplierAnswers[str(ino)] = text
        supplierAnswers[ino] = text
        
        # 특정 지표의 경우 sub_id로 파싱하여 추가 매핑
        # 예: 35번 지표 (PAH / DIOXIN)
        if ino == 35:
            pah_match = re.search(r'PAH\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            dioxin_match = re.search(r'(?:DIOXIN|다이옥신)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            if pah_match:
                supplierAnswers["PAH"] = float(pah_match.group(1))
            if dioxin_match:
                supplierAnswers["DIOXIN"] = float(dioxin_match.group(1))
                
        # 예: 8번 지표 (AS / CD / PB)
        elif ino == 8:
            as_match = re.search(r'(?:AS|비소)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            cd_match = re.search(r'(?:CD|카드뮴)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            pb_match = re.search(r'(?:PB|납)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            if as_match:
                supplierAnswers["AS"] = float(as_match.group(1))
            if cd_match:
                supplierAnswers["CD"] = float(cd_match.group(1))
            if pb_match:
                supplierAnswers["PB"] = float(pb_match.group(1))
                
        # 예: 9번 지표 (AL2O3 / SIO2)
        elif ino == 9:
            al_match = re.search(r'Al2O3\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            si_match = re.search(r'SiO2\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            if al_match:
                supplierAnswers["AL2O3"] = float(al_match.group(1))
            if si_match:
                supplierAnswers["SIO2"] = float(si_match.group(1))
                
        # 예: 19번 지표 (IAI_SGA / NA2O)
        elif ino == 19:
            sga_match = re.search(r'(?:IAI_SGA|순도)\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            na2o_match = re.search(r'Na2O\s*:?\s*(\d+\.?\d*)', text, re.IGNORECASE)
            if sga_match:
                supplierAnswers["IAI_SGA"] = float(sga_match.group(1))
            if na2o_match:
                supplierAnswers["NA2O"] = float(na2o_match.group(1))
                
        extracted_num = extractNumericValueFromText(text)
        if extracted_num is not None:
            # 장문의 서술형 문장 대신 "1.25" 같은 깔끔한 float 수치로 오버라이드합니다.
            supplierAnswers[str(ino)] = extracted_num
            supplierAnswers[ino] = extracted_num
            
    return supplierAnswers


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

        # 7단계: 위험군 산정 및 업데이트
        if criticalCount > 0:
            riskLevel = "고위험군"
        elif failCount > 0 or warnCount > 0:
            riskLevel = "중위험군"
        else:
            riskLevel = "저위험군"
            
        cur.execute("""
            UPDATE `COMPANY`
            SET risk_level = %s
            WHERE partner_id = %s AND delete_yn = 0
        """, (riskLevel, partnerCode))
        conn.commit()
        safePrint(f"[*] [위험군 업데이트] partner_id={partnerCode} -> risk_level={riskLevel}")

        # 8단계: 위험군 통계 산출 (고위험군/중위험군 수)
        cur.execute("SELECT COUNT(*) as cnt FROM `COMPANY` WHERE risk_level = '고위험군' AND delete_yn = 0")
        highRiskCount = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM `COMPANY` WHERE risk_level = '중위험군' AND delete_yn = 0")
        mediumRiskCount = cur.fetchone()["cnt"]

        # 9단계: 각 진단 항목별 액션플랜 추출
        cur.execute("""
            SELECT rule_id, indicator_no, alert_title, alert_content, severity, ai_recommendation, threshold_value, actual_value
            FROM `AI_AGENT_ALERT`
            WHERE run_id = %s AND delete_yn = 0
        """, (runId,))
        alerts = cur.fetchall()
        
        actionPlans = []
        for alert in alerts:
            cur.execute("SELECT rule_name FROM `AI_AGENT_RULE` WHERE rule_id = %s", (alert["rule_id"],))
            rule_row = cur.fetchone()
            rule_name = rule_row["rule_name"] if rule_row else f"지표 {alert['indicator_no']}"
            
            actionPlans.append({
                "indicator_no": alert["indicator_no"],
                "rule_name": rule_name,
                "severity": alert["severity"],
                "actual_value": alert["actual_value"],
                "threshold_value": alert["threshold_value"],
                "action_plan": alert["ai_recommendation"] or "공급사 현장 실사 및 개선조치 계획서(CAPA) 제출을 즉시 요구하십시오."
            })

        # 10단계: 원청사 식별 및 실시간 WebSocket 푸시
        cur.execute("SELECT parent_id, company_name FROM `COMPANY` WHERE partner_id = %s AND delete_yn = 0", (partnerCode,))
        partnerInfo = cur.fetchone()
        partnerName = partnerInfo["company_name"] if partnerInfo else partnerCode
        parentId = partnerInfo["parent_id"] if partnerInfo else None
        
        cur.execute("SELECT partner_id FROM `COMPANY` WHERE (tier = 0 OR tier_label = '원청사') AND delete_yn = 0")
        primeRows = cur.fetchall()
        primeIds = [row["partner_id"] for row in primeRows]
        
        targetPartnerIds = set(primeIds)
        if parentId:
            targetPartnerIds.add(parentId)

        wsMessage = {
            "id": None,
            "companyId": partnerCode,
            "type": "AI_AGENT",
            "title": f"🔴 [자가진단 완료] {partnerName} 감사 판정 - {'불합격' if alertsGenerated > 0 else '합격'}",
            "content": f"총 {alertsGenerated}건 위반 감지. 고위험군: {highRiskCount}사, 중위험군: {mediumRiskCount}사",
            "isRead": False,
            "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "time": "방금 전",
            "path": f"/esg/dashboard?partnerId={partnerCode}",
            "meta": {
                "partner_id": partnerCode,
                "partner_name": partnerName,
                "status": "불합격" if alertsGenerated > 0 else "합격",
                "high_risk_count": highRiskCount,
                "medium_risk_count": mediumRiskCount,
                "action_plans": actionPlans
            }
        }
        try:
            # 알림 수준 정의 (위반 수위에 맞게 매핑)
            alarm_level = "warn" if finalStatus == "ALERT" else "info"
            if criticalCount > 0:
                alarm_level = "fail"

            insertAlarmSql = """
                INSERT INTO `ALARM` (
                    partner_id,
                    type,
                    level,
                    title,
                    content,
                    path,
                    meta_json,
                    is_read,
                    delete_yn,
                    created_at
                ) VALUES (%s, 'AI_AGENT', %s, %s, %s, %s, %s, 0, 0, NOW())
            """
            
            # JSON 형태로 프론트엔드 호환용 메타데이터 정형화
            alarm_meta_json = json.dumps(wsMessage["meta"], ensure_ascii=False)
            
            cur.execute(insertAlarmSql, (
                partnerCode,            # partner_id (예: NSM-001)
                alarm_level,            # level (fail/warn/info)
                wsMessage["title"],     # title
                wsMessage["content"],   # content
                wsMessage["path"],      # path
                alarm_meta_json         # meta_json (체크 제약조건 호환 유효 JSON)
            ))
            conn.commit()
            safePrint(f"[+] [ALARM 테이블] AI 에이전트 알림 적재 성공 (partner_id={partnerCode})")
            
        except Exception as alarm_err:
            safePrint(f"[!] [ALARM 테이블] 적재 중 오류 발생: {alarm_err}")


        from src.utils.websc import manager
        
        async def sendWsAlerts():
            for pId in targetPartnerIds:
                if manager.isConnected(pId):
                    await manager.sendToPartner(pId, wsMessage)
                    safePrint(f"[WS 알림 송신 성공] target_partner_id={pId}")
                    
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(sendWsAlerts())
                else:
                    loop.run_until_complete(sendWsAlerts())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(sendWsAlerts())
        except Exception as ws_ex:
            safePrint(f"[WS 알림 송신 에러] {ws_ex}")

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