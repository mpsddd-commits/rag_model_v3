"""
ESG Data Loading Pipeline Module (load.py)
- MariaDB Excel Master Data Ingestion
- PostgreSQL pgvector PDF Chunking & Vector Ingestion
- Hugging Face Dataset Remote Backup
"""
import os
import re
import json
import datetime
import hashlib
import glob
import time
import numpy as np
import pandas as pd
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from datasets import Dataset  
from langchain_text_splitters import RecursiveCharacterTextSplitter
from psycopg2.extras import execute_values

import src.utils.dbClient as db
from src.utils.settings import settings, safePrint, simpleTokenizer

# ======================================================================
# 0. PDF 텍스트 추출 및 슬라이딩 윈도우 청킹 (langchain splitter + 메타데이터 적용)
# ======================================================================
def extractAndChunkPdf(pdfPath: str, chunkSize: int = 1200, chunkOverlap: int = 300) -> list:
    """
    langchain-text-splitters를 활용하여 문맥(마침표, 줄바꿈)이 끊기지 않도록 가드레일을 치고,
    각 청크마다 [파일명 / Page 번호] 메타데이터를 본문에 주입하여 청킹을 수행합니다.
    """
    chunks = []
    fileName = os.path.basename(pdfPath)
    
    try:
        reader = PdfReader(pdfPath)
        
        # 1. 문장 단위 가드레일 분할기 정의
        textSplitter = RecursiveCharacterTextSplitter(
            chunk_size=chunkSize,        # 1200자
            chunk_overlap=chunkOverlap,  # 300자
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""] # 줄바꿈과 마침표를 우선순위로 조절
        )
        
        # 2. 누락 방지 및 페이지별 트래킹을 위해 페이지 단위 루프 실행
        for idx, page in enumerate(reader.pages):
            pageNo = idx + 1 # 1페이지부터 시작하도록 보정
            pageText = page.extract_text()
            
            if not pageText or not pageText.strip():
                continue # 스캔된 이미지 등으로 인해 텍스트가 없는 페이지 가드 스킵
            
            # 3. 해당 페이지의 텍스트를 슬라이딩 윈도우로 분할
            pageChunks = textSplitter.split_text(pageText)
            
            # 4. 분할된 각 청크에 출처 메타데이터 바인딩 및 정제
            for i, chunkSlice in enumerate(pageChunks):
                if not chunkSlice.strip():
                    continue
                
                # 연속된 줄바꿈 및 불필요한 공백 제거
                cleanSlice = " ".join(chunkSlice.split())
                
                # LLM(Gemma)이 출처를 완벽히 인지하도록 텍스트 헤더에 메타데이터 강제 주입
                formattedContent = f"[{fileName} / Page {pageNo}] {cleanSlice}"
                
                # 고유 식별 해시값 생성 (페이지 정보와 인덱스를 결합하여 고유성 보장)
                chunkId = hashlib.md5(f"{fileName}_P{pageNo}_I{i}_{cleanSlice[:20]}".encode()).hexdigest()
                
                chunks.append({
                    "chunk_id": chunkId,
                    "file_name": fileName,
                    "content": formattedContent, # 메타데이터가 접두사로 붙은 텍스트
                    "doc_type": "PDF",
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
        safePrint(f"[정밀 청킹 완료] 파일명: {fileName} -> 생성된 총 청크 수: {len(chunks)}개")
                
    except Exception as e:
        safePrint(f"[오류] PDF 정밀 파싱 실패 ({fileName}): {e}")
        
    return chunks

# ════════════════════════════════════════════════════════
# 1. 마리아 DB 엑셀 적재 및 온톨로지 빌드 영역
# ════════════════════════════════════════════════════════
def parseComplexCriteria(questionText: str) -> dict:
    """
    [개선된 버전] 불필요한 제품명/규격번호 숫자를 필터링하고 
    물결표(~) 구조를 인식하여 정교한 RANGE 및 NUMERIC 마스터 기준값을 추출합니다.
    """
    result = {
        "criteria_type": "BOOL",
        "operator": "== Y",
        "threshold_value": None,
        "min_value": None,
        "max_value": None
    }
    
    if not questionText:
        return result

    # 1. 전처리 가드레일: 의도치 않은 메타 숫자(4자리 제품명, ASTM 규격 번호 등)를 임시 제거
    # 예: Al 3003 -> Al , ASTM B209 -> ASTM B 로 변경하여 수치 인식 방지
    cleanText = re.sub(r"\b\d{4}\b", "", questionText)  # 4자리 숫자(3003 등) 제거
    cleanText = re.sub(r"B\d+", "B", cleanText)         # B209 등 규격명 뒤의 숫자 제거

    # 2. 범위형 분석 (문장에 '범위 내'가 있거나 숫자~숫자 구조가 명시적인 경우)
    # 정규식으로 [숫자][공백이나 물결][숫자] 형태를 직접 타겟팅 (예: 1.00~1.50)
    rangeMatch = re.search(r"(\d+\.\d+|\d+)\s*[~-]\s*(\d+\.\d+|\d+)", cleanText)
    
    if "범위 내" in questionText or rangeMatch:
        if rangeMatch:
            result["criteria_type"] = "RANGE"
            result["min_value"] = float(rangeMatch.group(1))
            result["max_value"] = float(rangeMatch.group(2))
            result["operator"] = "BETWEEN"
            return result
        else:
            # 물결표는 없지만 '범위 내' 키워드가 있는 경우 폴백 처리
            nums = re.findall(r"\d+\.\d+|\d+", cleanText)
            if len(nums) >= 2:
                result["criteria_type"] = "RANGE"
                result["min_value"] = float(nums[0])
                result["max_value"] = float(nums[1])
                result["operator"] = "BETWEEN"
                return result

    # 3. 단일 수치 비교형 분석 ('이하', '미만', '초과', '이상')
    nums = re.findall(r"\d+\.\d+|\d+", cleanText)
    
    if "Zero" in questionText or "zero" in questionText or "0건" in questionText:
        result["criteria_type"] = "NUMERIC"
        result["operator"] = "<="
        result["threshold_value"] = 0.0
        return result

    if nums:
        val = float(nums[0])
        if "이하" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = "<="
            result["threshold_value"] = val
        elif "미만" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = "<"
            result["threshold_value"] = val
        elif "초과" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">"
            result["threshold_value"] = val
        elif "이상" in questionText or "충족" in questionText:
            result["criteria_type"] = "NUMERIC"
            result["operator"] = ">="
            result["threshold_value"] = val

    # 4. 상태 확인형 불리언 가드
    if "않습니까" in questionText:
        result["operator"] = "== N"
        
    return result

def loadSelfAssessChecklistToMariadb(excelDir: str):
    """엑셀의 각 시트(탭) 이름을 기반으로 마스터 데이터를 SELF_ASSESS_CHECKLIST 테이블에 적재합니다."""
    db.save("SET FOREIGN_KEY_CHECKS = 0;")
    db.save("TRUNCATE TABLE SELF_ASSESS_CHECKLIST;")
    db.save("SET FOREIGN_KEY_CHECKS = 1;")
    
    checklistRows = []
    for pattern in ("*.xlsx", "*.xls"):
        for excelPath in glob.glob(os.path.join(excelDir, pattern)):
            try:
                xlDict = pd.read_excel(excelPath, sheet_name=None, header=0)
                for sheetName, df in xlDict.items():
                    sheetNameClean = sheetName.strip()
                    match = re.search(r"^(\d+차\s*협력사|\d+차-[A-Z])", sheetNameClean)
                    partnerType = match.group(1).strip() if match else sheetNameClean[:10]
                    
                    safePrint(f"[파싱 진행] 시트명: '{sheetName}' -> 확정 partner_type: '{partnerType}'")
                    
                    for idx, row in df.iterrows():
                        rowVals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                        if len(rowVals) >= 3:
                            indicatorNoRaw = rowVals[0]
                            if not indicatorNoRaw.replace('.0', '').isdigit():
                                continue
                            
                            checklistRows.append((
                                partnerType, int(indicatorNoRaw), 
                                rowVals[1] if len(rowVals) > 1 else "공통",
                                rowVals[2] if len(rowVals) > 2 else "미지정 지표",
                                rowVals[3] if len(rowVals) > 3 else "Normal",
                                rowVals[4] if len(rowVals) > 4 else "N",
                                rowVals[5] if len(rowVals) > 5 else "",
                                rowVals[6] if len(rowVals) > 6 else "",
                                rowVals[7] if len(rowVals) > 7 else "",
                                rowVals[8] if len(rowVals) > 8 else "중",
                                rowVals[9] if len(rowVals) > 9 else "N",
                                rowVals[10] if len(rowVals) > 10 else "",
                                rowVals[11] if len(rowVals) > 11 else "즉시 시정조치 가이드라인 가동",
                                0
                            ))
            except Exception as e:
                safePrint(f"[오류] '{os.path.basename(excelPath)}' 처리 중 크리티컬 예외 발생: {e}")
                
    if checklistRows:
        sql = """
            INSERT INTO SELF_ASSESS_CHECKLIST (
                partner_type, indicator_no, category, indicator_name, priority, 
                star_yn, question, pass_answer, fail_answer, risk_level, 
                evidence_yn, evidence_list, action_plan, delete_yn
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.saveMany(sql, checklistRows)
        safePrint(f"\n[MariaDB 성공] 시트별 등급 분기 적용 완료 -> 총 {len(checklistRows)}개 핵심 지표 마스터 적재 완료.")

def loadRiskCriteriaToMariadb(excelDir: str):
    """'자가진단_리스크_분류_기준.xlsx' 파일을 읽어 ESG_RISK_CRITERIA 테이블에 전수 적재합니다."""
    db.save("SET FOREIGN_KEY_CHECKS = 0;")
    db.save("TRUNCATE TABLE ESG_RISK_CRITERIA;")
    db.save("SET FOREIGN_KEY_CHECKS = 1;")
    
    riskCriteriaRows = []
    seenItems = set()
    
    for pattern in ("*리스크*분류*.xlsx", "*리스크*분류*.xls", "자가진단_리스크_분류_기준.xlsx"):
        for excelPath in glob.glob(os.path.join(excelDir, pattern)):
            try:
                xlDict = pd.read_excel(excelPath, sheet_name=None, header=1)
                for sheetName, df in xlDict.items():
                    safePrint(f"[리스크 분류 파싱] 파일: {os.path.basename(excelPath)} / 시트명: '{sheetName}'")
                    for idx, row in df.iterrows():
                        rowVals = [str(v).strip() if pd.notna(v) else "" for v in row.values]
                        if len(rowVals) >= 4:
                            itemName, highRisk, mediumRisk, lowRisk = rowVals[0], rowVals[1], rowVals[2], rowVals[3]
                            if not itemName or itemName == "항목" or "기준 추천" in itemName:
                                continue
                            if itemName not in seenItems:
                                riskCriteriaRows.append((itemName, highRisk, mediumRisk, lowRisk))
                                seenItems.add(itemName)
            except Exception as e:
                safePrint(f"[오류] '{os.path.basename(excelPath)}' 리스크 기준 파싱 중 크리티컬 예외 발생: {e}")

    if riskCriteriaRows:
        sqlRisk = """
            INSERT INTO ESG_RISK_CRITERIA (item_name, high_risk, medium_risk, low_risk) VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE high_risk = VALUES(high_risk), medium_risk = VALUES(medium_risk), low_risk = VALUES(low_risk);
        """
        db.saveMany(sqlRisk, riskCriteriaRows)
        safePrint(f"[MariaDB 성공] ESG_RISK_CRITERIA 테이블에 총 {len(riskCriteriaRows)}건의 마스터 기준 적재 완료.")


def buildOntologyRegistry():
    """MariaDB 데이터를 기반으로 사전 구축 후 로컬로 1차 백업을 수행합니다."""
    import engine  
    engine.buildOntologyRegistry() # 기존 MariaDB 빌더 트리거 호출

def exportOntologyToJsonl(outputFilename: str = "esgOntologyTemplate.jsonl"):
    """구축된 온톨로지 리스트를 파인튜닝 지식 데이터 백업용 JSONL 파일로 출력합니다."""
    import engine
    if not engine._ONTOLOGY_TEMPLATE_LIST: engine.buildOntologyRegistry()

    try:
        with open(outputFilename, "w", encoding="utf-8") as f:
            for item in engine._ONTOLOGY_TEMPLATE_LIST:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        safePrint(f"[온톨로지 백업] 엑셀/DB 파싱 데이터 1차 JSONL 추출 완료: {outputFilename}")
    except Exception as e:
        safePrint(f"[온톨로지 백업 실패] : {e}")


# ════════════════════════════════════════════════════════
# 2. pgvector (PostgreSQL) 벡터 적재 및 허깅페이스 이관 영역
# ════════════════════════════════════════════════════════
def initAndSaveToPgvectorAutoOntology(chunks: list, pgTable: str = "ESG_PDF_VECTORS"):
    """
    MariaDB 마스터 지표와 코사인 유사도가 0.5 이상인 청크만 선별하여 pgvector에 적재합니다.
    중복 및 유사도 미달로 제외된 청크들의 상세 내역을 수집하여 하단에 상세 분석 리포트를 출력합니다.
    """
    from engine import ollamaClient  # 💡 engine에 싱글톤으로 선언된 클라이언트 공유 참조
    
    conn = db.getPostgresConn()
    if not conn: 
        return
    
    try:
        # [단계 1] 마리아DB 마스터 지표 텍스트 및 임베딩 로드
        sql = "SELECT question FROM SELF_ASSESS_CHECKLIST WHERE question IS NOT NULL AND question != ''"
        masterRows = db.findAll(sql)
        
        masterVectors = []
        for row in masterRows:
            try:
                resp = ollamaClient.embeddings(model=settings.embed_model, prompt=row["question"])
                vec = np.array(resp["embedding"])
                norm = np.linalg.norm(vec)
                if norm > 0: 
                    masterVectors.append((row["question"], vec, norm)) # 문항 텍스트도 함께 보관
            except Exception:
                continue

        with conn, conn.cursor() as cur:
            # [단계 2] PostgreSQL pgvector 테이블 구성 및 확장 기능 체크
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {pgTable} (
                    id SERIAL PRIMARY KEY, chunk_id TEXT UNIQUE, file_name TEXT,
                    content TEXT, embedding vector(1024), timestamp TEXT
                );
            """)
            
            dataToInsert = []
            totalChunks = len(chunks)
            startTime = time.time()
            
            # 🌟 제외 대상 트래킹을 위한 특수 저장소 레이어
            excludedByDuplicate = []
            excludedBySimilarity = []
            
            safePrint(f"\n[자동 온톨로지 매칭] 총 {totalChunks}개 청크 검증 가동 (마스터 기준 문항 수: {len(masterVectors)}개)")

            for idx, chunk in enumerate(chunks, 1):
                try:
                    # 실시간 모니터링 주기용 출력
                    if idx % 20 == 0 or idx == totalChunks:
                        elapsed = time.time() - startTime
                        safePrint(f" -> 유사도 분석 및 임베딩 연산 중... [{idx}/{totalChunks}] ({idx/totalChunks*100:.1f}%) | 경과시간: {elapsed:.1f}초")
                    
                    cid = chunk["chunk_id"]
                    cText = chunk["content"]
                    fName = chunk["file_name"]
                    
                    # 🛡️ 1) 데이터베이스 내부 중복 체크 가드레일 (1차 제외 원인)
                    sqlCheck = f"SELECT 1 FROM {pgTable} WHERE chunk_id = %s LIMIT 1"
                    cur.execute(sqlCheck, (cid,))
                    if cur.fetchone():
                        # 줄바꿈 정제 후 중복 리스트에 바인딩
                        cleanText = " ".join(cText.split())
                        excludedByDuplicate.append(f"[{fName}] {cleanText[:50]}...")
                        continue
                        
                    # 2) Ollama 기반 청크 데이터 벡터 변환
                    resp = ollamaClient.embeddings(model=settings.embed_model, prompt=cText)
                    currVec = np.array(resp["embedding"])
                    currNorm = np.linalg.norm(currVec)
                    if currNorm == 0: 
                        continue
                        
                    # 📉 3) 코사인 유사도 분석 가드레일 (2차 제외 원인)
                    isValidChunk = False if masterVectors else True
                    maxSimilarity = -1.0
                    
                    for qText, refVec, refNorm in masterVectors:
                        similarity = np.dot(refVec, currVec) / (refNorm * currNorm)
                        if similarity > maxSimilarity:
                            maxSimilarity = similarity
                        
                        if similarity >= 0.55:
                            isValidChunk = True
                            # 조기 종료(Break) 처리하지 않고, 최고 유사도를 기록하기 위해 마저 순회할 수도 있으나, 
                            # 속도를 위해 합격선 도달 시 루프를 탈출하도록 유지하되 최고 점수만 기록 보정
                            break
                    
                    if isValidChunk:
                        dataToInsert.append((cid, fName, cText, resp["embedding"], chunk["timestamp"]))
                    else:
                        # 기준 미달로 탈락한 청크 데이터의 세부 수치 바인딩
                        cleanText = " ".join(cText.split())
                        excludedBySimilarity.append({
                            "file_name": fName,
                            "score": maxSimilarity,
                            "text": cleanText[:60]
                        })
                        
                except Exception as ce:
                    safePrint(f"\n[경고] {idx}번째 청크 처리 예외 스킵: {ce}")
                    continue
            
            # ════════════════════════════════════════════════════════
            # 📊 [추가된 레이어] 제외된 청크 원인 규명 상세 분석 리포트 출력
            # ════════════════════════════════════════════════════════
            totalExcluded = len(excludedByDuplicate) + len(excludedBySimilarity)
            if totalExcluded > 0:
                safePrint("\n" + "="*75)
                safePrint(f"🔍 [제외된 청크 상세 리포트 - 총 {totalExcluded}개 청크 진단 완료]")
                safePrint("="*75)
                
                # 원인 1 출력 (중복)
                safePrint(f"1️⃣ [기존 데이터베이스 중복 가드레일 필터링] 총 {len(excludedByDuplicate)}개")
                if excludedByDuplicate:
                    for row in excludedByDuplicate[:5]: # 너무 많으면 화면을 덮으므로 상위 5개 샘플링 출력
                        safePrint(f"  - {row}")
                    if len(excludedByDuplicate) > 5:
                        safePrint(f"  ...외 {len(excludedByDuplicate) - 5}개 청크 중복으로 적재 제외됨")
                else:
                    safePrint("  - 해당 사항 없음")
                
                # 원인 2 출력 (유사도 미달)
                safePrint(f"\n2️⃣ [ESG 마스터 지표 유사도 기준치 미달 ( < 0.55 ) 필터 탈락] 총 {len(excludedBySimilarity)}개")
                if excludedBySimilarity:
                    # 탈락 청크 중 아까운 순서(유사도 점수가 높았던 순서)로 정렬하여 상위 10개 출력
                    excludedBySimilarity.sort(key=lambda x: x["score"], reverse=True)
                    for row in excludedBySimilarity[:10]:
                        safePrint(f"  - [{row['file_name']}] (최고 유사도: {row['score']:.4f}) {row['text']}...")
                    if len(excludedBySimilarity) > 10:
                        safePrint(f"  ...외 {len(excludedBySimilarity) - 10}개 데이터 ESG 무관 텍스트(노이즈) 가드로 차단 처리")
                else:
                    safePrint("  - 해당 사항 없음")
                safePrint("="*75 + "\n")

            # [단계 4] 최종 필터 통과 데이터가 존재할 경우 벌크 인서트(execute_values) 단일 트랜잭션 수행
            if dataToInsert:
                safePrint(f"[PostgreSQL] 필터 통과한 {len(dataToInsert)}개 신규 청크 적재 (제외: {totalExcluded}개)")
                executeValues(cur, f"""
                    INSERT INTO {pgTable} (chunk_id, file_name, content, embedding, timestamp)
                    VALUES %s ON CONFLICT (chunk_id) DO NOTHING;
                """, dataToInsert)
                conn.commit()
                safePrint(f"[PostgreSQL] pgvector 추가 적재 완료! (최종 소요시간: {time.time() - startTime:.1f}초)\n")
            else:
                safePrint(f"[PostgreSQL 알림] 기준(0.6) 만족 신규 청크 없음. (최종 소요시간: {time.time() - startTime:.1f}초)\n")
                
    except Exception as e:
        safePrint(f"[PostgreSQL 오류] 파이프라인 처리 실패: {e}")

def exportPgvectorToHf(repoId: str):
    """PostgreSQL pgvector 테이블 전체를 원격 Hugging Face Hub 데이터셋으로 밀어 올려 백업합니다."""
    conn = db.getPostgresConn()
    if not conn: return
    safePrint(f"[HuggingFace 백업] '{repoId}' 허브 데이터셋 업로드 가동...")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT chunk_id, file_name, content, embedding, timestamp FROM ESG_PDF_VECTORS;")
            rows = cur.fetchall()
            
        if not rows:
            safePrint("[HuggingFace 백업 경고] 업로드할 원천 DB 데이터가 존재하지 않습니다.")
            return
            
        df = pd.DataFrame(rows, columns=["chunk_id", "file_name", "content", "embedding", "timestamp"])
        dataset = Dataset.from_pandas(df)
        dataset.push_to_hub(repoId, private=False)
        safePrint(f"[HuggingFace 성공] 원격 업로드 완료 -> {repoId}")
    except Exception as e:
        safePrint(f"[HuggingFace 오류] 원격 백업 실패: {e}")


# ════════════════════════════════════════════════════════
# 3. 통합 파이프라인 제어 진입점 (Orchestrator)
# ════════════════════════════════════════════════════════
def runConcurrentIngestionPipeline(pdfDir: str, excelDir: str, hfRepo: str = None):
    """Excel 및 PDF 통합 파이프라인 가동 시 로컬 완성본 JSONL의 상태 가드라인을 최우선 연동합니다."""
    import engine 
    
    safePrint("\n=== 🚀 [통합 파이프라인] 전처리 및 기준 기반 순차 적재 가동 ===")
    
    # [단계 1] 데이터베이스 기초 마스터 싱크
    loadSelfAssessChecklistToMariadb(excelDir)
    loadRiskCriteriaToMariadb(excelDir)

    # 🌟 만약 이미 수정한 로컬 'esgOntologyTemplate.jsonl' 파일이 있다면 
    #     DB 데이터로 덮어쓰지 않고 로컬 파일의 최종 수정본 규칙을 그대로 캐시 엔진에 주입합니다.
    if os.path.exists("esgOntologyTemplate.jsonl"):
        safePrint("[파이프라인 레이어 알림] 기존 가공 완료된 esgOntologyTemplate.jsonl 검증판이 발견되어 로컬 로더를 실행합니다.")
        engine.buildOntologyRegistryFromJsonl("esgOntologyTemplate.jsonl")
    else:
        # 파일이 아예 존재하지 않는 최초 빌드 시에만 기본 Export 프로세스 작동
        engine.buildOntologyRegistry()
        # 로컬 백업용 원본 내보내기 함수 호출
        exportOntologyToJsonl("esgOntologyTemplate.jsonl")

    # [단계 2] PDF 로드 및 마스터 매칭 기반 PostgreSQL pgvector 데이터 저장
    safePrint("[파이프라인 단계 2] PDF 가공 및 마스터 지표 기반 코사인 유사도(>=0.5) 적재 필터링 가동...")
    pdfChunks = []
    for pdfPath in glob.glob(os.path.join(pdfDir, "*.pdf")):
        pdfChunks.extend(extractAndChunkPdf(pdfPath))
        
    if pdfChunks:
        initAndSaveToPgvectorAutoOntology(pdfChunks)
        
        # 💡 [핵심 교정]: engine.py의 Retriever 상태 변수를 직접 덮어씌워 유실을 원천 차단합니다.
        engine.globalChunksPool = pdfChunks
        tokenizedCorpus = [simpleTokenizer(c["content"]) for c in pdfChunks]
        engine.bm25Index = BM25Okapi(tokenizedCorpus)
        safePrint("[인메모리 동기화] 하이브리드 검색용 글로벌 인덱스(BM25Okapi) 실시간 결합 완료.")
        
    # [단계 3] 클라우드 백업용 허깅페이스 전송
    if hfRepo:
        safePrint("[파이프라인 단계 3] Hugging Face 벡터 데이터셋 원격 백업 트리거 가동...")
        exportPgvectorToHf(repoId=hfRepo)