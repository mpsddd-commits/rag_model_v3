"""
ESG MariaDB RAG System runner script.
Delegates core matching, validation, and generation to search.checklist_matcher.
"""
from search.checklist_matcher import (
    search_checklist_row,
    extract_and_compare,
    process_esg_query
)
from utils.helpers import safe_print

if __name__ == "__main__":
    # Note: MariaDB must have the 'esg_checklist' table populated before running this test.
    safe_print("====== ESG MariaDB RAG 시스템 독립 실행 테스트 ======")
    
    # Virtual user query leading to a fail condition test
    test_query = "현재 공정에서 발생한 Cu 함량이 0.28%로 집계되었습니다. 어떻게 대처해야 하죠?"
    
    # Run pipeline
    answer = process_esg_query(test_query)
    
    safe_print("\n" + "="*50)
    safe_print("🤖 AI 최종 답변 가이드라인:")
    safe_print("="*50)
    safe_print(answer)
    safe_print("="*50)