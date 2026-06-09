# test_ai_alarm.py (최종 수정 버전)
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from agentPipeline import runComplianceAuditAgent
except ImportError:
    from src.models.aiAgentNotify import createAiAgentAlert as runComplianceAuditAgent

async def test_main():
    test_partner_id = "NSM-001" 
    
    # 📌 [핵심 고침] metric_key 이름 대신 실제 온톨로지 지표 번호(indicator_no)를 키로 주입합니다.
    # (예시 지표 번호입니다. 실제 AI_AGENT_RULE 테이블의 indicator_no와 맞춰주세요)
    mock_answers = {
        34: 15.0,         # TRIR 지표 번호가 2번인 경우
        50: 85.5,         # feocRatio 지표 번호가 3번인 경우
        
        # 만약 서브 지표 룰(PAH 등)을 테스트 하려면 문자열 키 사용 가능
        "PAH": 85.5,
        "DIOXIN": 0.99
    }
    
    print("[*] AI 에이전트 알람 스키마 연동 테스트 시작...")
    
    try:
        if asyncio.iscoroutinefunction(runComplianceAuditAgent):
            await runComplianceAuditAgent(test_partner_id, mock_answers)
        else:
            runComplianceAuditAgent(test_partner_id, mock_answers)
        print("[*] 테스트 함수 호출 완료. DB를 확인하세요.")
    except Exception as e:
        print(f"[!] 가동 중 오류 발생: {e}")

if __name__ == "__main__":
    asyncio.run(test_main())