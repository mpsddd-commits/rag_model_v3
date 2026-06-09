# src/models/aiAgentNotify.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] AI Agent 전용 알람 비즈니스 로직
#        72개 ESG 지표 룰셋 평가 → 위반 감지 → 알람 발송
#
# [처리 흐름]
#   1. AI_AGENT_RULE 테이블에서 활성 룰 조회
#   2. 협력사 데이터(COMPANY)에서 metric_key 값 추출
#   3. operator + threshold_value로 룰 평가
#   4. 위반 시 AI_AGENT_ALERT INSERT
#   5. notify.py sendNotify() 호출 → ALARM INSERT + 웹소켓 푸시
#   6. AI_AGENT_RUN_LOG에 실행 결과 기록
#
# [의존성]
#   utils/db.py       → findAll, findOne, save, addKey
#   models/notify.py  → sendNotify
#   utils/websc.py    → manager (websocket)
# ────────────────────────────────────────────────────────────────────────────

import json
import time
from datetime import datetime
from typing import Optional, List
from src.utils.db import findAll, findOne, save, addKey
from src.models.notify import sendNotify


# ============================================================
# ■ AI Agent 알림 타입 (notify.py NOTIFY_CONFIG에 추가 필요)
# ============================================================

class aiAgentNotifyType:
    AI_AGENT = "AI_AGENT"   # AI Agent가 감지한 위반 알람


# ============================================================
# ■ 룰 평가 엔진
# ============================================================

def evaluateRule(metricValue, operator: str, threshold) -> bool:
    """
    [역할] operator + threshold로 metricValue 평가
    [반환] True = 위반 / False = 정상

    [지원 operator]
      <, <=, >, >=, =, !=
      IN          : threshold가 JSON 배열인 경우 포함 여부
      EXISTS      : metricValue가 NULL/공백이 아닌 경우
    """
    if metricValue is None or metricValue == "":
        return operator == "EXISTS"  # EXISTS만 비어있을 때 True

    try:
        # 숫자 비교
        if operator in (">", ">=", "<", "<="):
            mVal = float(metricValue)
            tVal = float(threshold)
            if operator == ">":  return mVal > tVal
            if operator == ">=": return mVal >= tVal
            if operator == "<":  return mVal < tVal
            if operator == "<=": return mVal <= tVal

        # 문자열 동일 비교
        if operator == "=":  return str(metricValue) == str(threshold)
        if operator == "!=": return str(metricValue) != str(threshold)

        # IN 비교 (threshold = JSON 배열 문자열)
        if operator == "IN":
            arr = json.loads(threshold) if isinstance(threshold, str) else threshold
            return str(metricValue) in [str(v) for v in arr]

        # EXISTS
        if operator == "EXISTS":
            return metricValue not in (None, "", 0, "0", "N")

    except (ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"[evaluateRule ERROR] {e}")
        return False

    return False


# ============================================================
# ■ 룰 위반 시 AI Agent Alert + ALARM 생성
# ============================================================

async def createAiAgentAlert(
    rule: dict,
    partner: dict,
    actualValue,
    runId: Optional[int] = None,
) -> dict:
    """
    [역할] 룰 위반 감지 시 AI_AGENT_ALERT INSERT + ALARM 푸시

    [처리]
      1. 메시지 템플릿 치환 ({partner}, {value} 등)
      2. AI 신뢰도/근거/권장조치 생성 (실제는 AI Model 호출)
      3. AI_AGENT_ALERT INSERT
      4. notify.py sendNotify(AI_AGENT) 호출 → ALARM + 웹소켓 푸시
      5. AI_AGENT_ALERT.alarm_id 업데이트
    """
    partnerName = partner.get("company_name", partner.get("partner_id"))
    severity    = rule["severity"]
    template    = rule.get("notify_template", "")

    # ── Step 1. 템플릿 치환
    try:
        content = template.format(
            partner = partnerName,
            value   = actualValue,
            threshold = rule["threshold_value"],
            unit    = rule.get("unit", ""),
        )
    except KeyError as e:
        content = f"{partnerName} 룰 위반: {rule['rule_name']} (값: {actualValue})"
        print(f"[createAiAgentAlert] 템플릿 치환 실패: {e}")

    # ── 편차 계산
    deviationPct = None
    try:
        actNum = float(actualValue)
        thrNum = float(rule["threshold_value"])
        if thrNum != 0:
            deviationPct = round((actNum - thrNum) / thrNum * 100, 2)
    except (ValueError, TypeError):
        pass

    # ── Step 2. AI 분석 결과 (실제는 외부 AI Model API 호출)
    aiConfidence    = 92.50  # 신뢰도 (Mock)
    aiReasoning     = f"{partnerName}의 {rule['metric_key']} 값 {actualValue}{rule.get('unit','')}이(가) " \
                      f"기준값 {rule['threshold_value']}{rule.get('unit','')}을(를) {rule['operator']} 조건으로 위반함."
    aiRecommendation = rule.get("action_required", "관련 부서 검토 필요")

    # ── Step 3. AI_AGENT_ALERT INSERT
    insertSql = """
        INSERT INTO `AI_AGENT_ALERT` (
            rule_id, partner_id, indicator_no,
            metric_key, actual_value, threshold_value, deviation_pct,
            severity, ai_confidence, ai_reasoning, ai_recommendation,
            alert_title, alert_content, regulation,
            status, detected_at, run_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', NOW(), ?)
    """
    alertTitle = f"{rule['rule_name']} — {partnerName}"
    params = (
        rule["rule_id"], partner["partner_id"], rule.get("indicator_no"),
        rule["metric_key"], str(actualValue), str(rule["threshold_value"]), deviationPct,
        severity, aiConfidence, aiReasoning, aiRecommendation,
        alertTitle, content, rule.get("regulation"),
        runId,
    )
    result = addKey(insertSql, params)
    if not result[0]:
        print(f"[createAiAgentAlert] AI_AGENT_ALERT INSERT 실패")
        return {"status": False}
    alertId = result[1]

    # ── Step 4. notify.py sendNotify() 호출 → ALARM + 웹소켓 푸시
    # ※ notify.py NOTIFY_CONFIG에 AI_AGENT 타입 사전 등록 필요
    await sendNotify(
    notifyType = aiAgentNotifyType.AI_AGENT,
    userId     = partner["partner_id"],  # ★ user_id 자리에 partner_id를 매핑하여 유저로 취급
    companyId  = partner["id"],          # 내부 일련번호(PK) 등 지정 구조 유지
    meta       = {
        "alertId"   : alertId,
        "partnerId" : partner["partner_id"],
        "partner"   : partnerName,
        "severity"  : severity,
        "value"     : actualValue,
        "title"     : alertTitle,
        "content"   : content,
        },
    )

    # ── Step 5. AI_AGENT_ALERT.alarm_id 업데이트
    #    (sendNotify가 ALARM INSERT 후 ID 반환하지 않으므로 최신 ALARM 조회)
    latestAlarm = findOne(
        "SELECT id FROM `ALARM` WHERE user_id = ? AND type = 'AI_AGENT' ORDER BY id DESC LIMIT 1",
        (partner.get("user_id", 1),)
    )
    if latestAlarm:
        save(
            "UPDATE `AI_AGENT_ALERT` SET alarm_id = ? WHERE alert_id = ?",
            (latestAlarm["id"], alertId)
        )

    print(f"[AI Alert] {alertTitle} — severity={severity}, confidence={aiConfidence}%")

    return {
        "status"   : True,
        "alertId"  : alertId,
        "severity" : severity,
        "title"    : alertTitle,
    }


# ============================================================
# ■ AI Agent 분석 실행 (메인 엔트리포인트)
# ============================================================

async def runAiAgentAnalysis(
    triggeredBy : Optional[int] = None,
    triggerType : str = "MANUAL",
    scope       : str = "ALL",
    scopeTarget : Optional[str] = None,
    aiModel     : str = "GPT-4-Turbo",
) -> dict:
    """
    [역할] AI Agent 전체 분석 실행
    [호출 시점]
      - MainDashboard "🤖 AI 전체 분석" 버튼 클릭
      - 스케줄러 (매일 09:00 정기 분석)
      - 이벤트 트리거 (자가진단 제출, 현장실사 완료 등)

    [처리 흐름]
      1. AI_AGENT_RUN_LOG INSERT (status=RUNNING)
      2. 활성 룰 + 평가 대상 협력사 조회
      3. 각 룰 × 협력사 매트릭스 평가
      4. 위반 감지 시 createAiAgentAlert() 호출
      5. AI_AGENT_RUN_LOG UPDATE (집계 + status=SUCCESS)
      6. AI 종합 요약 텍스트 생성
    """
    startedAt = datetime.now()
    startMs   = int(time.time() * 1000)

    # ── Step 1. RUN_LOG INSERT
    runSql = """
        INSERT INTO `AI_AGENT_RUN_LOG`
        (triggered_by, trigger_type, scope, scope_target, ai_model, status, started_at)
        VALUES (?, ?, ?, ?, ?, 'RUNNING', NOW())
    """
    runResult = addKey(runSql, (triggeredBy, triggerType, scope, scopeTarget, aiModel))
    if not runResult[0]:
        return {"status": False, "message": "RUN_LOG INSERT 실패"}
    runId = runResult[1]

    try:
        # ── Step 2. 활성 룰 조회
        ruleSql = """
            SELECT rule_id, indicator_no, rule_code, rule_name, tier_scope,
                   metric_key, operator, threshold_value, warn_threshold, fail_threshold,
                   unit, severity, notify_yn, notify_template, regulation, action_required
            FROM `AI_AGENT_RULE`
            WHERE active_yn = 'Y'
            ORDER BY priority ASC
        """
        rules = findAll(ruleSql, ())

        # ── 평가 대상 협력사 조회
        if scope == "PARTNER" and scopeTarget:
            companies = findAll("SELECT * FROM `COMPANY` WHERE partner_id = ?", (scopeTarget,))
        elif scope == "TIER" and scopeTarget:
            companies = findAll("SELECT * FROM `COMPANY` WHERE tier_label = ?", (scopeTarget,))
        else:
            companies = findAll("SELECT * FROM `COMPANY` WHERE delete_yn = 0", ())

        # ── Step 3. 매트릭스 평가
        alertsGenerated = 0
        criticalCount   = 0
        failCount       = 0
        warnCount       = 0

        for rule in rules:
            tierScope = rule.get("tier_scope")
            metricKey = rule["metric_key"]

            for partner in companies:
                # 차수 필터링 (tier_scope가 지정된 경우)
                if tierScope and tierScope != "전체":
                    pTier = partner.get("tier_label", "")
                    if tierScope not in pTier:
                        continue

                # metric_key 값 추출
                actualValue = partner.get(metricKey)
                if actualValue is None:
                    continue

                # 룰 평가
                isViolation = evaluateRule(actualValue, rule["operator"], rule["threshold_value"])
                if not isViolation:
                    continue

                # 알림 발송 (notify_yn = Y인 경우만)
                if rule.get("notify_yn") == "Y":
                    alertResult = await createAiAgentAlert(rule, partner, actualValue, runId)
                    if alertResult.get("status"):
                        alertsGenerated += 1
                        sev = rule["severity"]
                        if   sev == "CRITICAL": criticalCount += 1
                        elif sev == "FAIL":     failCount     += 1
                        elif sev == "WARN":     warnCount     += 1

        # ── Step 4. AI 종합 요약
        aiSummary = (
            f"{len(rules)}개 룰 × {len(companies)}개사 평가 완료. "
            f"즉시 조치(Critical) {criticalCount}건, 부적합(Fail) {failCount}건, 주의(Warn) {warnCount}건 감지."
        )

        # ── Step 5. RUN_LOG UPDATE
        endedAt    = datetime.now()
        durationMs = int(time.time() * 1000) - startMs

        save("""
            UPDATE `AI_AGENT_RUN_LOG`
            SET rules_evaluated = ?, alerts_generated = ?,
                critical_count = ?, fail_count = ?, warn_count = ?,
                ai_summary = ?, ended_at = NOW(), duration_ms = ?, status = 'SUCCESS'
            WHERE run_id = ?
        """, (len(rules), alertsGenerated, criticalCount, failCount, warnCount,
              aiSummary, durationMs, runId))

        return {
            "status"   : True,
            "message"  : "AI 분석 완료",
            "runId"    : runId,
            "summary"  : aiSummary,
            "stats"    : {
                "rulesEvaluated"  : len(rules),
                "alertsGenerated" : alertsGenerated,
                "criticalCount"   : criticalCount,
                "failCount"       : failCount,
                "warnCount"       : warnCount,
                "durationMs"      : durationMs,
            }
        }

    except Exception as e:
        errMsg = str(e)
        save("""
            UPDATE `AI_AGENT_RUN_LOG`
            SET status = 'FAILED', error_message = ?, ended_at = NOW()
            WHERE run_id = ?
        """, (errMsg, runId))
        print(f"[runAiAgentAnalysis ERROR] {errMsg}")
        return {"status": False, "message": f"AI 분석 실패: {errMsg}", "runId": runId}


# ============================================================
# ■ AI Agent Alert 조회/관리
# ============================================================

def getAiAgentAlertList(
    partnerId : Optional[str] = None,
    severity  : Optional[str] = None,
    status    : Optional[str] = "OPEN",
    limit     : int = 50,
) -> List[dict]:
    """[역할] AI Agent 알림 목록 조회"""
    conditions = ["delete_yn = 0"]
    params     = []

    if partnerId:
        conditions.append("partner_id = ?")
        params.append(partnerId)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if status:
        conditions.append("status = ?")
        params.append(status)

    whereClause = " AND ".join(conditions)
    params.append(limit)

    sql = f"""
        SELECT alert_id, rule_id, partner_id, indicator_no, metric_key,
               actual_value, threshold_value, deviation_pct, severity,
               ai_confidence, ai_reasoning, ai_recommendation,
               alert_title, alert_content, regulation, status,
               detected_at, alarm_id
        FROM `AI_AGENT_ALERT`
        WHERE {whereClause}
        ORDER BY detected_at DESC
        LIMIT ?
    """
    return findAll(sql, tuple(params))


def acknowledgeAiAgentAlert(alertId: int, userId: int) -> dict:
    """[역할] 알림 확인 처리 (ACKNOWLEDGED)"""
    save("""
        UPDATE `AI_AGENT_ALERT`
        SET status = 'ACKNOWLEDGED', acknowledged_by = ?, acknowledged_at = NOW()
        WHERE alert_id = ? AND delete_yn = 0
    """, (userId, alertId))
    return {"status": True, "alertId": alertId}


def resolveAiAgentAlert(alertId: int, userId: int, resolutionNote: str) -> dict:
    """[역할] 알림 해소 처리 (RESOLVED)"""
    save("""
        UPDATE `AI_AGENT_ALERT`
        SET status = 'RESOLVED', resolved_by = ?, resolved_at = NOW(), resolution_note = ?
        WHERE alert_id = ? AND delete_yn = 0
    """, (userId, resolutionNote, alertId))
    return {"status": True, "alertId": alertId}


def getAiAgentRunLogList(limit: int = 20) -> List[dict]:
    """[역할] AI 분석 실행 로그 조회 (최근 N개)"""
    sql = """
        SELECT run_id, triggered_by, trigger_type, scope, scope_target,
               rules_evaluated, alerts_generated, critical_count, fail_count, warn_count,
               ai_model, ai_summary, started_at, ended_at, duration_ms, status
        FROM `AI_AGENT_RUN_LOG`
        ORDER BY started_at DESC
        LIMIT ?
    """
    return findAll(sql, (limit,))
