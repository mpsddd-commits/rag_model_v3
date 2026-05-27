import os
import ollama
from search.hybrid_retriever import search_similar_documents, ollama_client
from utils.helpers import safe_print, check_and_pull_ollama_model

def ask_esg_chatbot(model_name, query):
    """
    RAG generation pipeline:
    1) Query the hybrid Dense+Sparse retriever to fetch the top 3 contexts.
    2) Construct standard structured prompts detailing citation protocols.
    3) Invoke Ollama LLM to synthesize the response and return response along with citations.
    """
    check_and_pull_ollama_model(ollama_client, model_name)
    retrieved_contexts = search_similar_documents(query, top_k=3)
    
    if not retrieved_contexts:
        return "[경고] 검색 결과가 존재하지 않아 답변을 구성할 수 없습니다.", []
    
    formatted_context_list = []
    citations = []
    
    for idx, ctx in enumerate(retrieved_contexts):
        source_info = f"{ctx['source_file']} ({ctx['page_or_row']})"
        citations.append(source_info)
        formatted_context_list.append(
            f"[참고 자료 {idx+1}] (출처: {source_info})\n내용: {ctx['content']}"
        )
        
    context = "\n\n".join(formatted_context_list)
    
    prompt = f"""당신은 ESG 공급망 실사 지침 및 글로벌 규제 전문가입니다. 
주어진 [참고 문서]의 핵심 내용을 기반으로 [사용자 질문]에 신뢰할 수 있는 정확한 정보를 제공하세요.
반드시 제공된 문서에 나와 있는 내용만을 토대로 요약 및 분석을 수행해야 합니다.
답변할 때 해당하는 내용이 어떤 참고 자료(예: [참고 자료 1], [참고 자료 2] 등)에서 온 것인지 본문 내에 명시하여 사용자가 출처를 검증할 수 있도록 하세요.

[참고 문서]
{context}

[사용자 질문]
{query}
"""
    
    safe_print(f"\n[AI] [{model_name}] 모델이 답변을 생성하는 중...")
    try:
        response = ollama_client.generate(model=model_name, prompt=prompt)
        return response['response'], citations
    except Exception as e:
        err_msg = f"LLM 답변 생성 중 치명적인 실패가 발생했습니다: {e}"
        return err_msg, citations
