"""
Main Runner: Executes concurrent ingestion, ontology caching, Hugging Face upload, and hybrid search.
"""
import os
import json
from settings import safePrint
from load import runConcurrentIngestionPipeline
from engine import processEsgComplianceQuery, buildOntologyRegistryFromJsonl

if __name__ == "__main__":
    # 로컬 테스트 디렉토리 보장
    os.makedirs("./esgPdfFiles", exist_ok=True)
    os.makedirs("./esgExcelFiles", exist_ok=True)
    
    # # ====================================================================
    # # 🔄 [선택] 새 PDF/Excel 파일이 추가되어 데이터베이스 및 벡터 적재가 필요할 때만 주석 해제
    # # ====================================================================
    # print("=" * 70)
    # print("💡 [Step 1] PDF/Excel 동시 적재 + 온톨로지 사전 빌드 + 허깅페이스 원격 백업")
    # print("=" * 70)
    runConcurrentIngestionPipeline(
        pdfDir="./esgPdfFiles", 
        excelDir="./esgExcelFiles",
        # hfRepo="Makesols/esg-vector-dataset"
    )
    
    # ====================================================================
    # 🚀 [상시 실행] 수정 완료된 완성본 jsonl 기반으로 온톨로지 규칙을 초고속 로드 (서빙 레이어)
    # ====================================================================
    # print("\n" + "=" * 70)
    # print("💡 [Step 2] 완성본 온톨로지 규칙 룰 & 하이브리드 검색 기반 연산 추론 검증")
    # print("=" * 70)
    
    # # 파이프라인을 돌렸든 안 돌렸든, 수정된 완성본 JSONL을 최종 가드레일 규칙으로 바인딩합니다.
    # buildOntologyRegistryFromJsonl(jsonlPath="./esgOntologyTemplate.jsonl")
    
    # # 실시간 하이브리드 추론 검증 테스트
    # sampleQuery = "보크사이트 채굴 현장에서 아동노동 및 강제노동 1건 확인"
    # samplePartner = "Windalco"
    
    # try:
    #     responsePayload = processEsgComplianceQuery(
    #         userQuery=sampleQuery,
    #         partnerName=samplePartner
    #     )
        
    #     print("\n[백엔드 수신 최종 검증 완결형 JSON 응답 페이로드]")
    #     print("-" * 70)
    #     print(json.dumps(responsePayload, indent=4, ensure_ascii=False))
    #     print("-" * 70)
        
    # except Exception as e:
    #     safePrint(f"[런타임 테스트 실패] 가드레일 추론 처리 엔진 구동 오류: {e}")