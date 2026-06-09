# test_ai_agent.py
import asyncio
import json
import requests
import websockets

# 테스트 설정 (환경에 맞게 호스트/포트 수정)
API_BASE_URL = "http://localhost:8000/ai-agent"
WS_URL = "ws://localhost:8000/ws/alarm"

# 실제 테스트용으로 Redis 세션에 등록되어 있다고 가정할 가짜 UUID와 마스터 계정 코드
TEST_UUID = "mock_session_uuid_1234"
TEST_PARTNER_ID = "P0001"  # 가드레일 위반을 테스트할 대상 협력사 코드


async def test_websocket_listener():
    """단계 3: 분석 도중 실시간 웹소켓 알림이 대시보드로 브로드캐스팅되는지 감시"""
    print("\n[테스트 3] Real-time 웹소켓 알림 리스너 가동...")
    # 실제 환경에서는 authenticateWS(token) 검증 프로세스용 토큰 파라미터 전달 필요
    ws_uri = f"{WS_URL}?token={TEST_UUID}"
    
    try:
        async with websockets.connect(ws_uri) as websocket:
            print(" -> [성공] 대시보드 웹소켓 채널 연결 완료. AI 푸시 대기 중...")
            
            # 메인 분석 API가 트리거되어 sendNotify()가 실행될 때까지 대기
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"\n🔥 [웹소켓 실시간 수신 알림 포착!!]")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                if data.get("type") == "AI_AGENT":
                    print(" -> [검증 완료] AI Agent 위반 알림이 실시간으로 대시보드 UI에 전송되었습니다.")
                    break
    except Exception as e:
        print(f" -> [웹소켓 커넥션 생략 또는 실패]: {e} (서버가 켜져 있고 토큰이 유효해야 합니다)")


def trigger_ai_analysis():
    """단계 1: AI Agent 전체 분석 마스터 엔진 작동 엔드포인트 호출"""
    print("\n[테스트 1] POST /ai-agent/analyze 호출 (AI 엔진 가동)...")
    payload = {
        "uuid": TEST_UUID,
        "triggerType": "MANUAL",
        "scope": "PARTNER",
        "scopeTarget": TEST_PARTNER_ID,
        "aiModel": "gemma4:e2b"
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/analyze", json=payload)
        print(f" -> Response Status: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result.get("status", False)
    except Exception as e:
        print(f" -> API 호출 실패: {e}")
        return False


def check_dashboard_alerts():
    """단계 2: AI 위반 경고가 AI_AGENT_ALERT 테이블 규격에 맞춰 누적되었는지 GET API 확인"""
    print(f"\n[테스트 2] GET /ai-agent/alerts 필터링 조회 테스트...")
    params = {
        "partnerId": TEST_PARTNER_ID,
        "status": "OPEN",
        "limit": 5
    }
    
    try:
        response = requests.get(f"{API_BASE_URL}/alerts", params=params)
        print(f" -> Response Status: {response.status_code}")
        result = response.json()
        
        alerts = result.get("data", {}).get("alerts", [])
        print(f" -> 총 {len(alerts)}건의 실시간 미확인(OPEN) 리스크 내역 추출 완료.")
        if alerts:
            target_alert = alerts[0]
            print(f"    - 최신 알림 제목: {target_alert.get('alert_title')}")
            print(f"    - 위험 심각도 (Severity): {target_alert.get('severity')}")
            print(f"    - AI 판단 근거 요약: {target_alert.get('ai_reasoning')[:60]}...")
            return target_alert.get("alert_id")
    except Exception as e:
        print(f" -> 알림 목록 API 확인 실패: {e}")
    return None


def patch_acknowledge_alert(alert_id):
    """단계 4: 원청사 매니저 계정 코드로 알림 확인(ACK) 처리 조작"""
    print(f"\n[테스트 4] PATCH /ai-agent/alerts/{alert_id}/ack 처리...")
    payload = {"uuid": TEST_UUID}
    
    try:
        response = requests.patch(f"{API_BASE_URL}/alerts/{alert_id}/ack", json=payload)
        result = response.json()
        print(f" -> 결과: {result.get('message')} (Status: {result.get('status')})")
    except Exception as e:
        print(f" -> ACK API 호출 실패: {e}")


async def main():
    print("=====================================================================")
    print("🚀 ESG 공급망 AI Agent 마스터 통합 파이프라인 기능 백엔드 테스트 시작")
    print("=====================================================================")
    
    # 1. 비동기 웹소켓 리스너를 백그라운드 태스크로 먼저 구동
    ws_task = asyncio.create_task(test_websocket_listener())
    await asyncio.sleep(1) # 리스너 안정화 대기
    
    # 2. 메인 AI 분석 엔진 API 수동 트리거
    success = trigger_ai_analysis()
    
    if success:
        # 3. DB 적재 및 리스트 API 출력 검증
        alert_id = check_dashboard_alerts()
        
        # 4. 웹소켓 이벤트 수신 대기 및 ACK API 마무리 테스트
        if alert_id:
            await asyncio.sleep(2)  # 웹소켓 메시지 도착 시간 확보
            patch_acknowledge_alert(alert_id)
            
    # 웹소켓 리스너 태스크 종료 처리
    ws_task.cancel()
    print("\n=====================================================================")
    print("🏁 [종합 평가] 파이프라인 기능 진단 프로세스 종료")
    print("=====================================================================")


if __name__ == "__main__":
    # 백엔드 API 서버(Uvicorn 등)가 켜진 상태에서 실행해야 합니다.
    asyncio.run(main())