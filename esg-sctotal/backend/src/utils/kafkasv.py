import json
import asyncio
import threading
from src.utils.htmltem import getHtml
from kafka import KafkaProducer, KafkaConsumer
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from src.utils.settings import settings, safePrint
import src.utils.dbClient as db

# agentPipeline.py 모듈로부터 수치 정제 엔진 및 독립 분리된 두 함수 임포트
from src.utils.agentPipeline import (
    buildSupplierAnswers, 
    executeComplianceAudit, 
    generateSelfAssessReport
)

# Kafka Producer 설정
kafkaProducer = KafkaProducer(
  bootstrap_servers=settings.kafka_server,
  value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# mail config 설정
mailConf = ConnectionConfig(
  MAIL_USERNAME = settings.mail_username,
  MAIL_PASSWORD = settings.mail_password,
  MAIL_FROM = settings.mail_from,
  MAIL_PORT = settings.mail_port,
  MAIL_SERVER = settings.mail_server,
  MAIL_FROM_NAME = settings.mail_from_name,
  MAIL_STARTTLS = settings.mail_starttls,
  MAIL_SSL_TLS = settings.mail_ssl_tls,
  USE_CREDENTIALS = settings.use_credentials,
  VALIDATE_CERTS = settings.validate_certs
)
fastMail = FastMail(mailConf)

# Producer 함수 
def sendToKafka(data):
    """API 서버에서 메시지를 보낼 때 사용"""
    kafkaProducer.send(settings.kafka_topic, data)
    kafkaProducer.flush()

def sendSelfAssessToKafka(data):
    """자가진단 데이터를 Kafka에 전송"""
    kafkaProducer.send(settings.kafka_self_assess_topic, data)
    kafkaProducer.flush()

# Consumer 이메일 발송 함수
# html1: 사내 직원 초대
# html2: 컨설턴트 초대 (신규: type 2, 기존: type 3)
# html3: 임시 비밀번호 발송
# html4: 협력사 초대 메일 발송

async def handleEmailJob(data):
    """
    이메일 발송 핸들러
    data 예시: 
    {"type": 1, "email": "user@example.com", "companyName": "회사명"}
    {"type": 2, "email": "user@example.com", "companyName": "회사명"}
    {"type": 3, "email": "user@example.com", "companyName": "회사명"}
    {"type": 4, "email": "user@example.com", "tempPwd": "임시비밀번호"}
    {"type": 5, "email": "user@example.com", "authCode": code, "companyName": "회사명"} 
    """

    # 1. 타입에 따른 제목 및 본문 설정
    subject, body, email = getHtml(data)
    if subject:
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=body,
            subtype=MessageType.html
        )
        await fastMail.send_message(message)
    else:
        print(f"알 수 없는 이메일: {email}")

def handleSelfAssessJob(payload: dict):
    """
    FastAPI(Swagger) 업로드 API가 던진 이벤트를 Kafka 토픽에서 감지하여
    E2E 백그라운드 AI 감사 파이프라인과 종합 서술 보고서 작성을 원스톱으로 처리합니다.
    """
    partner_id = payload.get("partner_id")
    version = payload.get("version", 1)
    
    safePrint(f"\n[⚡ Kafka Consumer Engine] 협력사 [{partner_id}] (v{version}) 자가진단 파일 분석 트리거 포착.")
    
    if not partner_id:
        safePrint("[!] 경고: payload 구조 내에 partner_id 누락으로 잡 실행이 불가합니다.")
        return

    try:
        # 1. dbClient를 활용해 사용자가 업로드하고 OCR이 완료한 실제 답변셋 전체 수집
        select_answers_sql = """
            SELECT indicator_no, answer_text 
            FROM `SELF_ASSESS_ANSWER` 
            WHERE partner_id = %s AND version = %s AND delete_yn = 0
        """
        raw_answers = db.findAll(select_answers_sql, (partner_id, version))
        
        if not raw_answers:
            safePrint(f"[!] 경고: DB 내에 협력사 [{partner_id}]의 자가진단 응답 데이터가 식별되지 않아 프로세스를 마감합니다.")
            return
            
        safePrint(f"[*] DB 마스터로부터 {len(raw_answers)}개의 문항 답변 셋 로드 완료. 가드레일 정제 진입.")

        # 2. load.py 알고리즘 기반 서술형 문맥 수치 클렌징 (예: 문장 전체 -> float(1.25) 단일 추출)
        cleaned_supplier_answers = buildSupplierAnswers(raw_answers)

        # ─────────────────────────────────────────────────────────────
        # 🚀 [기능 1 호출]: agentPipeline 고유 규칙 감사 파이프라인 가동
        # ─────────────────────────────────────────────────────────────
        # 내부적으로 위반 검출, AI_AGENT_ALERT/ALARM 적재, 위험군 업데이트, WebSocket 푸시 전동 가동
        run_id = executeComplianceAudit(partner_id, cleaned_supplier_answers)
        
        # ─────────────────────────────────────────────────────────────
        # 🚀 [기능 2 호출]: 기존 main.py 고유 자연어 서술 요약 종합 보고서 생성
        # ─────────────────────────────────────────────────────────────
        markdown_report = generateSelfAssessReport(partner_id, cleaned_supplier_answers)
        
        # 3. 생성된 종합 보고서 활용부 (콘솔 출력 및 시스템 아카이빙 로깅)
        safePrint(f"\n====================================================================")
        safePrint(f"🎉 [AI 에이전트 분석 완료 - Run ID: {run_id}] 실전 데이터 종합 리포팅 요약")
        safePrint(f"====================================================================")
        # 앞부분 400자만 요약 뷰 로깅 출력
        safePrint(markdown_report[:400] + "\n\n... (이하 생략) ...")
        safePrint(f"====================================================================\n")

    except Exception as err:
        safePrint(f"[!] Kafka 백그라운드 핸들러 실행 과정 중 치명적 예외 발생: {err}")

# Consumer 함수
def runEmailConsumer():
    """이메일 토픽 컨슈머 루프"""
    consumer = KafkaConsumer(
        settings.kafka_topic, 
        bootstrap_servers=settings.kafka_server,
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )
    for message in consumer:
        asyncio.run(handleEmailJob(message.value))

def runSelfAssessConsumer():
    """자가진단 토픽 컨슈머 루프"""
    try:
        consumer = KafkaConsumer(
            settings.kafka_self_assess_topic, 
            bootstrap_servers=settings.kafka_server,
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8"))
        )
        for message in consumer:
            asyncio.run(handleSelfAssessJob(message.value))
    except Exception as e:
        print(f"[runSelfAssessConsumer 장애] {e}")

def startConsumer():
    """컨슈머 시작 함수"""
    emailThread = threading.Thread(target=runEmailConsumer, daemon=True)
    emailThread.start()
    
    selfAssessThread = threading.Thread(target=runSelfAssessConsumer, daemon=True)
    selfAssessThread.start()

# src/utils/kafkasv.py 맨 아래 실행부 예시
if __name__ == "__main__":
    from src.utils.agentPipeline import syncOntologyRulesToDb
    
    safePrint("=========================================================")
    safePrint("🚀 Kafka 백그라운드 워커 데몬 가동 프로세스 시작")
    safePrint("=========================================================")
    
    # [정리된 함수 호출] 서버 켜질 때 로컬의 최신 룰셋 파일(.jsonl)을 DB에 동기화
    syncOntologyRulesToDb("./esgOntologyTemplate.jsonl")
    
    # Kafka 컨슈머 루프 가동
    # runSelfAssessConsumer()
