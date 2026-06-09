import json
import asyncio
import threading
from src.utils.htmltem import getHtml
from kafka import KafkaProducer, KafkaConsumer
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from src.utils.settings import settings, safePrint
import src.utils.dbClient as db
from src.utils.agentPipeline import buildSupplierAnswers, runComplianceAuditAgent

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

async def handleSelfAssessJob(data):
    """
    자가진단 처리 핸들러
    data 예시: {"partner_id": "AL-001", "version": 2, "answers": [...]}
    """
    partnerId = data.get("partner_id")
    answers = data.get("answers", [])
    if not partnerId or not answers:
        print(f"[handleSelfAssessJob] 유효하지 않은 데이터 누락: partnerId={partnerId}, answers={len(answers)}")
        return

    try:
        from agentPipeline import buildSupplierAnswers, runComplianceAuditAgent
        # answers 리스트 구조를 dictionary 구조로 정제
        supplierAnswers = buildSupplierAnswers(answers)
        
        # 동적 AI 지표 실사 및 알림 발송 에이전트 구동
        runComplianceAuditAgent(partnerId, supplierAnswers)
        print(f"[handleSelfAssessJob 성공] partnerId={partnerId} AI 자가진단 평가 완료.")
    except Exception as ex:
        print(f"[handleSelfAssessJob 오류] {ex}")

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
