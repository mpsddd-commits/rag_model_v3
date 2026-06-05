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

    # ── Step 2. AI 분석 결과 (Ollama RAG 연동)
    # 2-1. RAG Context 조회: ESG_INDICATOR 규제 기준 조회
    indicator_no = rule.get("indicator_no")
    rag_context = ""
    if indicator_no:
        try:
            # db.py의 findOne 함수를 사용하여 관련 ESG 지표 규제 요건 조회
            indicator = findOne(
                "SELECT indicator_name, pass_criteria, fail_criteria, regulations, tier_scope, category FROM `ESG_INDICATOR` WHERE indicator_no = ?",
                (indicator_no,)
            )
            if indicator:
                rag_context = (
                    f"규제 명칭: {indicator.get('regulations', 'N/A')} (지표 범주: {indicator.get('category', 'N/A')})\n"
                    f"지표 명칭: {indicator.get('indicator_name', 'N/A')}\n"
                    f"적용 차수: {indicator.get('tier_scope', 'N/A')}\n"
                    f"적합 기준 (Pass Criteria): {indicator.get('pass_criteria', 'N/A')}\n"
                    f"부적합/위반 기준 (Fail Criteria): {indicator.get('fail_criteria', 'N/A')}\n"
                )
        except Exception as db_err:
            print(f"[RAG Context Retrieve Error] {db_err}")

    # 기본값 설정 (Ollama API 호출 실패 시 Fallback 대비)
    aiConfidence = 92.50
    aiReasoning = f"{partnerName}의 {rule['metric_key']} 값 {actualValue}{rule.get('unit','')}이(가) " \
                  f"기준값 {rule['threshold_value']}{rule.get('unit','')}을(를) {rule['operator']} 조건으로 위반함."
    aiRecommendation = rule.get("action_required", "관련 부서 검토 필요")

    # 2-2. Ollama 프롬프트 구성 및 로컬 API 호출
    import urllib.request

    # 룰 분석에 사용할 로컬 모델 지정 (기본값: gemma2)
    # runAiAgentAnalysis에서 전달된 모델명(GPT-4-Turbo 등)이 들어오나 로컬에서는 gemma2, llama3 등을 우선 매핑
    ollama_model = "gemma2"
    if runId:
        try:
            run_log = findOne("SELECT ai_model FROM `AI_AGENT_RUN_LOG` WHERE run_id = ?", (runId,))
            if run_log and run_log.get("ai_model"):
                model_name = run_log["ai_model"].lower()
                # 로컬 올라마 모델 매핑 (GPT/Claude로 들어와도 로컬 올라마 구동을 위해 gemma2 등으로 변환 가능)
                if "gpt" not in model_name and "claude" not in model_name:
                    ollama_model = run_log["ai_model"]
        except Exception:
            pass

    system_prompt = (
        "당신은 글로벌 ESG 규제(CSDDD, CSRD, UFLPA, IRA/FEOC 등) 전문 AI 감사관(Compliance Officer)입니다.\n"
        "주어진 규제 기준(RAG 컨텍스트)과 협력사의 실제 데이터를 분석하여, 위반 사항에 대해 신뢰도 점수를 부여하고, "
        "위반 근거 및 구체적이고 실행 가능한 시정 조치(권장사항)를 제시해야 합니다."
    )

    user_prompt = f"""
[retrieved_context]
{rag_context if rag_context else '규제 지침 정보를 DB에서 찾을 수 없음'}

[violation_data]
- 협력사명: {partnerName}
- 위반한 규칙: {rule['rule_name']}
- 평가 대상 지표 (metric_key): {rule['metric_key']}
- 실제 측정값 (actual_value): {actualValue} {rule.get('unit', '')}
- 룰 기준값 (threshold_value): {rule['threshold_value']} {rule.get('unit', '')}
- 비교 연산 조건 (operator): {rule['operator']}
- 기본 권장조치: {rule.get('action_required', 'N/A')}
- 리스크 등급 (severity): {severity}

[instructions]
1. 실제 측정값과 룰 기준값 및 규제 기준(RAG 컨텍스트)을 분석하여 위반 여부를 검증하십시오.
2. 분석 신뢰도 점수 (ai_confidence, 0.00 ~ 100.00 사이의 실수)를 결정하십시오.
3. 분석 근거 (ai_reasoning, 구체적인 규제 지침과 수치를 인용하여 격식 있고 설득력 있는 한국어로 작성하십시오).
4. 시정 권장 사항 (ai_recommendation, 해당 협력사가 즉시 조치해야 할 구체적인 시정 계획 및 대안 소싱 전략 등을 명확한 한국어로 기술하십시오).

반드시 아래 JSON 형식으로만 응답해야 하며, JSON 외의 어떠한 텍스트나 설명, 마크다운 기호(예: ```json)도 포함하지 마십시오.

{{
  "verified_violation": true,
  "ai_confidence": 95.50,
  "ai_reasoning": "위반 원인과 규제 관련 상세 서술",
  "ai_recommendation": "협력사가 해야 할 일 단계별 요약"
}}
"""

    try:
        url = "http://localhost:11434/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": ollama_model,
            "prompt": f"System: {system_prompt}\nUser: {user_prompt}",
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        # 타임아웃 10초 설정하여 외부 호출 지연 차단
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            llm_text = res_json.get("response", "").strip()

            # JSON 데이터만 안전하게 파싱하기 위한 마크다운(```json) 정화 작업
            if "```" in llm_text:
                lines = llm_text.split("\n")
                cleaned_lines = []
                in_block = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_block = not in_block
                        continue
                    cleaned_lines.append(line)
                llm_text = "\n".join(cleaned_lines).strip()

            # JSON 디코딩
            parsed_data = json.loads(llm_text)
            aiConfidence = float(parsed_data.get("ai_confidence", aiConfidence))
            aiReasoning = parsed_data.get("ai_reasoning", aiReasoning)
            aiRecommendation = parsed_data.get("ai_recommendation", aiRecommendation)
            print(f"[Ollama RAG Success] Model={ollama_model}, Confidence={aiConfidence}%")

    except Exception as ollama_err:
        # 로컬 올라마 구동 상태가 아니거나 에러 발생 시 원래의 룰 기반 정보로 안전하게 백업(지연 및 다운 방지)
        print(f"[Ollama RAG Exception - Graceful Fallback Active] Error: {ollama_err}")

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
        userId     = partner.get("user_id", 1),     # 협력사 담당자 또는 관리자
        companyId  = partner["id"],
        meta       = {
            "alertId"   : alertId,
            "partnerId" : partner["partner_id"],
            "partner"   : partnerName,
            "ruleCode"  : rule["rule_code"],
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
