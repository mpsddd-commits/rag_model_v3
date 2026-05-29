"""
Main Runner: Executes concurrent ingestion, ontology caching, Hugging Face upload, and hybrid search.
"""
import os
import json
from settings import safe_print
from engine import run_concurrent_ingestion_pipeline, process_esg_compliance_query

if __name__ == "__main__":
    # 로컬 테스트 디렉토리 보장
    os.makedirs("./esg_pdf_files", exist_ok=True)
    os.makedirs("./esg_excel_files", exist_ok=True)
    
    print("=" * 70)
    print("💡 [Step 1] PDF/Excel 동시 적재 + 온톨로지 사전 빌드 + 허깅페이스 원격 백업")
    print("=" * 70)
    
    # 동시 다발 파이프라인 기동 (HuggingFace 저장소 ID를 전달하면 실시간 자동 업로드 실행)
    run_concurrent_ingestion_pipeline(
        pdf_dir="./esg_pdf_files", 
        excel_dir="./esg_excel_files",
        hf_repo="Makesols/esg-vector-dataset"
    )
    
    print("\n" + "=" * 70)
    print("💡 [Step 2] 복원된 온톨로지 규칙 룰 & 하이브리드 검색 기반 연산 추론 검증")
    print("=" * 70)
    
    # 공급망 오염 검증 실사 시나리오 구동 (3차 협력사 Comilog 아동노동 1건 검출)
    sample_query = "저희 보크사이트 채굴 현장에서 아동노동 1건이 현장 감사에서 확인되었습니다."
    sample_partner = "Comilog"
    
    try:
        response_payload = process_esg_compliance_query(
            user_query=sample_query,
            partner_name=sample_partner
        )
        
        print("\n[백엔드 API 엔드포인트 수신 최종 JSON Payload]")
        print("-" * 70)
        print(json.dumps(response_payload, indent=4, ensure_ascii=False))
        print("-" * 70)
        
    except Exception as e:
        safe_print(f"[테스트 실패] 메인 스트림 엔진 구동 중 예외 발생: {e}")