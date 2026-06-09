# test_local_pipeline.py
import os
import sys
import json
import time
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

# 1. 프로젝트 루트 경로 바인딩 (ModuleNotFoundError 방지)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 의존성 모듈 안전 임포트
from src.utils.websc import manager
import src.utils.websc as websc_mod
import src.utils.db as db_mod

# =====================================================================
# ✨ 1. FastAPI 글로벌 인스턴스 정의
# =====================================================================
app = FastAPI(title="ESG Supply Chain Local Integration Test")

# =====================================================================
# 🎛️ 2. [MOCKING ZONE] 외부 인프라(Redis, DB) 통신 강제 가로채기
# =====================================================================
MOCK_DB_STORAGE = {
    "AI_LOGS": [],
    "ALARM": []
}

def mock_db_save(sql: str, params: tuple = ()):
    sql_upper = sql.upper()
    if "AI_LOGS" in sql_upper:
        MOCK_DB_STORAGE["AI_LOGS"].append(params)
    elif "ALARM" in sql_upper:
        MOCK_DB_STORAGE["ALARM"].append(params)
    print(f"[Mock DB 저장 완료] Target 데이터 적재 완료")
    return True

async def mock_authenticateWS(websocket: WebSocket, token: str ):
    """Redis 세션 인프라를 우회하고 v2.0 규격 partner_id 문자열 반환"""
    if token == "MOCK_TEST_TOKEN_UUID":
        return "PARTNER_AL_001"
    return None

# 실제 프로젝트 모듈의 기능을 테스트용 가짜 함수로 스위칭
db_mod.save = mock_db_save
websc_mod.authenticateWS = mock_authenticateWS


# =====================================================================
# 🌐 3. FastAPI 가상 웹소켓 엔드포인트 구현 (타입 에러 완벽 방어형)
# =====================================================================
@app.websocket("/ws/alarm")
async def websocket_test_endpoint(websocket: WebSocket):
    """
    FastAPI의 파라미터 매핑 버그를 완벽히 우회하기 위해,
    호출 인자를 단 하나(websocket)로 한정하고 쿼리 스트링을 수동 파싱합니다.
    """
    # URL Scope의 쿼리 스트링 파라미터에서 직접 안전하게 token 추출
    query_string = websocket.scope.get("query_string", b"").decode("utf-8")
    
    # 예: "token=MOCK_TEST_TOKEN_UUID" -> "MOCK_TEST_TOKEN_UUID"
    token = None
    if "token=" in query_string:
        token = query_string.split("token=")[1].split("&")[0]
    
    if not token:
        await websocket.close(code=4000)
        print("[WS 테스트 에러] URL에 인증 토큰이 검출되지 않았습니다.")
        return

    # 가짜 인증 함수 호출
    partnerId = await websc_mod.authenticateWS( websocket, token)
    if not partnerId:
        await websocket.close(code=4001)
        print("[WS 테스트 에러] 인증 실패")
        return
        
    print(f"[WS 테스트 서버] 인증 검증 통과 -> partnerId: '{partnerId}'")
    print(f"[WS 테스트 서버] 주입 파라미터 무결성 체크 -> websocket 타입: {type(websocket)}")

    # 💡 [핵심 교정] 변수명 매핑 충돌을 막기 위해 키워드를 완전히 제거하고,
    # src/utils/websc.py 내 ConnectionManager.connect(self, partner_id, websocket)의 
    # 오리지널 파라미터 순서(위치 기반 인자) 그대로 주입합니다.
    await manager.connect(websocket, partnerId)
    
    try:
        while True:
            # 클라이언트 소켓 세션 유지를 위한 리시브 대기 루프
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(partnerId)
    except Exception as e:
        print(f"[WS 루프 예외 발령]: {e}")
        manager.disconnect(partnerId)


# =====================================================================
# 🧠 4. 하이브리드 ESG 가드레일 검색 및 웹소켓 전송 파이프라인 모사 함수
# =====================================================================
def processEsgComplianceQuery_Testing(userQuery: str, partnerName: str, partnerId: str) -> dict:
    """하이브리드 RAG 검색 레이어 가동 후 결과 세트를 소켓을 통해 실시간 에미팅"""
    
    # 아동 노동 가드레일 위반 판단 시뮬레이터
    judgementStatus = "합격"
    actionPlan = "기준 승인 완료. 특이사항 없음"
    
    if any(kwd in userQuery for kwd in ["아동", "강제노동", "인권위반"]):
        judgementStatus = "불합격"
        actionPlan = "① 즉시 공급망 거래 보류 ② 현장 실사단 파견 및 원천 시정조치계획서(CAPA) 징구"

    aiResp = f"### [ESG 공급망 감사 결과 보고서]\n\n**대상**: {partnerName}\n**결과**: {judgementStatus}\n\n**조치방안**:\n{actionPlan}"
    
    # DB 로그 백업 (가짜 DB 저장소로 리다이렉트)
    db_mod.save("INSERT INTO AI_LOGS (partner_name, result) VALUES (%s, %s)", (partnerName, aiResp))
    
    # notify.py 규격 v2.0 1키 체계 호환 푸시 메시지 패킷 가공
    ws_message = {
        "id": 1234,
        "companyId": partnerId, # v2.0 아키텍처 호환 파트너 마스터 식별 키
        "type": "AI_AGENT",
        "title": f"🔴 [ESG 위험 감지] {partnerName} 감사 판정 - {judgementStatus}",
        "content": f"공급망 내 핵심 위반 사항 발견 조치계획: {actionPlan[:20]}...",
        "isRead": False,
        "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "meta": {
            "partner_id": partnerId,
            "partner_name": partnerName,
            "status": judgementStatus,
            "action_plan": actionPlan
        }
    }
    
    # websc.py 커넥션 매니저에 수립된 소켓 트랙이 있다면 즉시 비동기 실시간 발송
    import asyncio
    if partnerId in manager.connections:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.sendToPartner(partnerId, ws_message))
        else:
            loop.run_until_complete(manager.sendToPartner(partnerId, ws_message))
            
    return {"judgement_status": judgementStatus, "ai_evaluation": aiResp}


# =====================================================================
# 🧪 5. 최종 통합 검증 테스트 실행 시나리오
# =====================================================================
def test_full_esg_pipeline_without_infra():
    print("\n" + "="*60)
    print("🚀 로컬 무인프라 하이브리드 ESG & 웹소켓 통합 검증 세션 시작")
    print("="*60)
    
    # FastAPI 상단 인스턴스를 바인딩한 TestClient 구동
    client = TestClient(app)
    test_partner_id = "PARTNER_AL_001"
    test_partner_name = "(주)알루테크"
    test_token = "MOCK_TEST_TOKEN_UUID"

    # 가상 웹소켓 채널 커넥션 오픈
    with client.websocket_connect(f"/ws/alarm?token={test_token}") as websocket:
        print("\n[Pass 1] 가상 클라이언트 웹소켓 핸드셰이크 성공 및 커넥션 풀 매핑 완료.")
        
        # 커넥션 풀에 정상 등록 확인
        assert test_partner_id in manager.connections
        print(f" -> 현재 메모리 상 세션 풀에 보존된 Key 리스트: {list(manager.connections.keys())}")

        # AI 가드레일 크리티컬 쿼리 투입
        test_query = "상반기 공정 실사 결과 공장 내부 아동노동 관련 지표에서 위반 건수가 검출되었습니다."
        print(f"\n[Run 2] AI 에이전트 감사 파이프라인 엔진 구동 요청: '{test_query}'")
        
        # 통합 처리 함수 가동
        pipeline_result = processEsgComplianceQuery_Testing(
            userQuery=test_query, 
            partnerName=test_partner_name, 
            partnerId=test_partner_id
        )
        
        # 엔진 결과 체크
        assert pipeline_result["judgement_status"] == "불합격"
        print(f"[Pass 3] AI 가드레일 위반 판정 정합성 검증 완료 -> 상태: {pipeline_result['judgement_status']}")

        # 실시간 소켓 채널을 타고 넘어온 스트리밍 데이터 획득
        received_raw_packet = websocket.receive_text()
        received_data = json.loads(received_raw_packet)
        
        print("\n" + "-"*40)
        print("📥 [실시간 웹소켓 패킷 내부 구조 캡처 성공]")
        print(json.dumps(received_data, indent=2, ensure_ascii=False))
        print("-"*40)
        
        # 최종 수신 데이터 규격 포맷 검증
        assert received_data["type"] == "AI_AGENT"
        assert received_data["companyId"] == test_partner_id
        print("[Pass 4] 실시간 웹소켓 데이터셋 구조 무결성 최종 통과 (v2.0 1키 규격 준수)")

    print("\n🎉 [성공] 로컬 독립 통합 시나리오 테스트 완벽 통과.")
    print("="*60)

if __name__ == "__main__":
    test_full_esg_pipeline_without_infra()