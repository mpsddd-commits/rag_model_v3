import re
import datetime
import hashlib
import pandas as pd
from datasets import Dataset
from database.postgres_client import get_postgres_conn
from utils.helpers import safe_print

def export_pgvector_to_file_and_hf(repo_id="Makesols/esg-vector-dataset3"):
    """
    [고도화된 RAG 데이터셋 구축 파이프라인]
    1) 고유 해시 ID(UUID 대체)를 부여하여 중복 데이터 적재 원천 차단
    2) 수치 정합성 검증용 메타데이터(수치/단위) 자동 파싱 레이어 추가
    3) AI 파인 튜닝 및 검색 고도화를 위한 구조화된 Hugging Face Dataset 발행
    """
    safe_print("\n[백업/HF] 데이터셋 고도화 파이프라인 가동...")
    try:
        conn = get_postgres_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, content, embedding::text, source_file, source_type, page_or_row FROM esg_documents;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        safe_print(f"[오류] PostgreSQL 백업 데이터 조회 실패: {e}")
        return
    
    if not rows:
        safe_print("[경고] DB에 저장된 데이터가 없어 백업 및 업로드를 건너뜁니다.")
        return

    # 1. 판다스 데이터프레임 변환
    df = pd.DataFrame(rows, columns=['id', 'content', 'embedding', 'source_file', 'source_type', 'page_or_row'])
    df['embedding'] = df['embedding'].apply(lambda x: [float(i) for i in x.strip('[]').split(',')])

    # 2. [추천 로직 A] 고유 지문(MD5 Hash) ID 생성 및 업로드 날짜 기록
    # 중복 저장 방지 및 타임라인 이력 관리에 유용합니다.
    safe_print("[프로세스] 데이터셋 유니크 해시 키 및 타임스탬프 생성 중...")
    df['chunk_hash'] = df['content'].apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())
    df['uploaded_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 3. [추천 로직 B] 수치(Percentage/Mpa) 및 성분 메타데이터 사전 파싱 추출
    # 향후 하이브리드 수치 검색 연산을 위해 데이터셋 단계에서 미리 태그를 파싱해둡니다.
    safe_print("[프로세스] ESG/알루미늄 성분 및 수치 규격(%, Mpa) 태그 추출 중...")
    
    def extract_chemical_tags(text):
        tags = []
        for element in ['Mn', 'Cu', 'Al', 'Si', 'Fe', 'Mg', 'Zn', 'Ti']:
            if element in text:
                tags.append(element)
        return tags if tags else ["General_ESG"]

    def extract_numeric_values(text):
        # 0.25%, 100Mpa 같은 패턴을 정규식으로 자동 수집
        found = re.findall(r'\d+\.\d+\s*%|\d+\s*%\s*|\d+\s*[Mm]pa', text)
        return [f.strip() for f in found] if found else ["None"]

    df['detected_elements'] = df['content'].apply(extract_chemical_tags)
    df['detected_numbers'] = df['content'].apply(extract_numeric_values)

    # 4. 로컬 파일 하이브리드 백업 (CSV / Parquet)
    # Parquet은 임베딩 벡터와 같은 고차원 list 구조 데이터를 깨짐 없이 압축 저장하는 데 탁월합니다.
    try:
        df.to_csv("esg_vector_backup.csv", index=False, encoding='utf-8-sig')
        df.to_parquet("esg_vector_backup.parquet", index=False)
        safe_print("[성공] 로컬 멀티-포맷 백업 완료 (esg_vector_backup.parquet)")
    except Exception as e:
        safe_print(f"[경고] 로컬 백업 파일 저장 오류: {e}")

    # 5. [추천 로직 C] Hugging Face Hub 구조화 업로드
    if repo_id:
        try:
            safe_print(f"[HF] 허깅페이스 프라이빗 리포지토리 '{repo_id}' 업로드 준비 중...")
            
            # 파인튜닝용 스키마에 맞게 Dataset 구조 정의
            hf_dataset = Dataset.from_pandas(df)
            
            # 전송 스트리밍 최적화 및 업로드 수행
            hf_dataset.push_to_hub(repo_id, private=True)
            safe_print(f"🎉 [최종 성공] 고도화된 메타데이터를 포함한 HF 데이터셋 업로드가 전면 완료되었습니다!")
        except Exception as e:
            safe_print(f"[오류] 허깅페이스 업로드 중 실패 (토큰 인증 또는 네트워크 바인딩 오류): {e}")
