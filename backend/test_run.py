import asyncio
import sys
import os

# 현재 디렉토리를 path에 추가하여 src 패키지를 인식하게 합니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 비즈니스 로직 함수 임포트
from src.models.aiAgentNotify import runAiAgentAnalysis

async def main():
    print("🚀 AI Agent 전체 분석 엔진 가동...")
    
    # runAiAgentAnalysis는 async 함수이므로 await로 호출합니다.
    # 테스트용 파라미터 전달 (유저 ID 1이 실행한 것으로 가정)
    result = await runAiAgentAnalysis(
        triggeredBy=1,
        triggerType="MANUAL",
        scope="ALL",
        aiModel="GPT-4-Turbo"
    )
    
    print("\n================ [분석 결과 리턴값] ================")
    import pprint
    pprint.pprint(result)
    print("====================================================")

if __name__ == "__main__":
    # 비동기 함수 실행
    asyncio.run(main())