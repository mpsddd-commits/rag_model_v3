import os
import sys
import re
from config.settings import settings

def safe_print(*args, **kwargs):
    """
    Windows console encoding safety wrapper to prevent UnicodeEncodeError
    when printing special characters or non-ASCII characters to standard output.
    """
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    file = kwargs.get('file', sys.stdout)
    
    text = sep.join(str(arg) for arg in args)
    try:
        file.write(text + end)
        file.flush()
    except UnicodeEncodeError:
        encoding = getattr(file, 'encoding', 'utf-8') or 'utf-8'
        safe_text = text.encode(encoding, errors='replace').decode(encoding)
        file.write(safe_text + end)
        file.flush()

def simple_tokenizer(text):
    """
    Strips special characters and punctuation from a given text string,
    converting it to lowercase and splitting it into tokens by whitespace.
    Used for consistent BM25 tokenization.
    """
    if not text:
        return []
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    return clean_text.split()

def check_and_pull_ollama_model(ollama_client, model_name):
    """
    Checks if a target Ollama model exists in the local Ollama instance,
    and automatically issues a pull command if it is missing.
    """
    safe_print(f"[조회] Ollama 모델 '{model_name}' 로컬 설치 상태 검사 중...")
    try:
        models_list = ollama_client.list()
        downloaded_models = []
        for m in models_list.get('models', []):
            name = m.get('model', m.get('name', ''))
            downloaded_models.append(name)
            if ':' in name:
                downloaded_models.append(name.split(':')[0])
                
        exists = any(model_name == m or model_name in m or m in model_name for m in downloaded_models)
        
        if not exists:
            safe_print(f"[다운로드] 로컬에서 '{model_name}' 모델을 찾을 수 없습니다. 자동 다운로드(pull)를 시작합니다...")
            ollama_client.pull(model_name)
            safe_print(f"[성공] 모델 '{model_name}' 다운로드 완료!")
        else:
            safe_print(f"[성공] 모델 '{model_name}' 확인 완료 (사용 가능)")
    except Exception as e:
        safe_print(f"[경고] Ollama 서비스 모델 조회/다운로드 실패: {e}")
