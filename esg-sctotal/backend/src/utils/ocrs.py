# src/utils/ocrs.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] 자가진단 체크리스트 PDF에서 "답변" 열 데이터를 OCR로 추출
#
# [v0.5 — 유동적 협력사 구분 + 3차 통합(A+B) 지원]
#
#   ✅ 협력사 구분: 유동적 확장 가능 (TIER_RANGES 설정 기반)
#      현재: 1차(40~56), 2차(28~39), 3차-A(1~18), 3차-B(19~27)
#      향후: 2차-B, 3차-D 등 자유롭게 추가 가능
#
#   ✅ 3차 통합: 알루미나 포함 회사는 3차-A(18개) + 3차-B(9개) = 26개 통합
#      partner_type → "3차 협력사" (Windalco, AluNorte)
#
#   ✅ QUESTION_TAILS: 질문 2번째줄 혼입 방지 사전 (전 차수 대응)
#   ✅ risk_level: 추출 제거 (AI 평가, DEFAULT '평가중')
# ────────────────────────────────────────────────────────────────────────────

import os
import io
import re
from fastapi import UploadFile, HTTPException
from google.cloud import vision
from src.utils.settings import settings
from src.utils.db import save, findAll, findOne, addKey
from src.utils.file import licenseFile


# ============================================================
# ■ 협력사 구분 설정 (유동적 확장 가능)
# ============================================================
# 새 차수 추가 시 여기에 range만 추가하면 자동 반영됨
# 예: "2차-B 협력사": range(60, 70) 추가 가능

TIER_RANGES = {
    "1차 협력사":  range(40, 57),   # No.40~56 (17개)
    "2차 협력사":  range(28, 40),   # No.28~39 (12개)
    "3차-A":       range(1, 19),    # No.1~18  (18개)
    "3차-B":       range(19, 28),   # No.19~27 (9개)
}

# 3차 통합 PDF의 경우에도 지표별 개별 차수로 등록
# range(1,19) → "3차-A", range(19,28) → "3차-B"


def _detectPartnerType(indicatorNos: list) -> str:
    """
    [역할] 지표번호 목록으로 협력사 구분을 유동적으로 판별

    [로직]
      단일 차수 매칭: TIER_RANGES에서 가장 많이 매칭되는 차수 선택
      매칭 없음 → "미분류"

    [3차 통합 처리]
      3차-A + 3차-B 모두 존재해도 "3차 협력사"가 아닌
      각 지표별로 range(1,19)→"3차-A", range(19,28)→"3차-B" 개별 등록
      → _detectIndicatorTier() 에서 지표 단위로 판별

    [확장성]
      TIER_RANGES에 새 항목 추가만으로 새 차수 자동 지원
    """
    nosSet = set(indicatorNos)

    # 가장 많이 매칭되는 차수 선택 (전체 PDF의 대표 차수)
    bestType = "미분류"
    bestCount = 0
    for tierName, tierRange in TIER_RANGES.items():
        count = len(nosSet & set(tierRange))
        if count > bestCount:
            bestCount = count
            bestType = tierName

    return bestType


def _detectIndicatorTier(indicatorNo: int) -> str:
    """
    [역할] 개별 지표번호 → 해당 차수 판별 (지표 단위)

    [사용처] saveChecklistAnswers()에서 지표별 partner_type 결정
      → 3차 통합 PDF(1~27)에서도 No.1~18은 "3차-A", No.19~27은 "3차-B"로 개별 등록
    """
    for tierName, tierRange in TIER_RANGES.items():
        if indicatorNo in tierRange:
            return tierName
    return "미분류"


# ============================================================
# ■ 질문 꼬리 패턴 (전 차수 대응)
# ============================================================

QUESTION_TAILS = {
    # ── 1차 협력사 (40~56)
    40: ["히트별 OES/ICP-OES 성분 분석 결과를 제출해 주십시오"],
    41: ["로트별 ICP-OES/XRF 분석 결과를 제출해 주십시오"],
    44: ["열처리 로그 데이터를 제출해 주십시오"],
    46: ["UTM 시험 성적서를 제출해 주십시오"],
    49: ["에너지 사용 현황 보고서를 제출해 주십시오",
         "에너지 사용 현황 보고서를 제출해"],
    50: ["온실가스 배출량 검증 보고서를 제출해 주십시오"],
    51: ["RoHS 시험 성적서를 제출해 주십시오"],
    52: ["SVHC 대조 현황 보고서를 제출해 주십시오"],
    54: ["최근 감사 보고서를 제출해 주십시오"],
    55: ["접수 건수를 공개하고 있습니까"],
    56: ["공급사 지분 구조 확인서를 제출해 주십시오",
         "귀사의 Mn\\(망간\\).*해당 기업이 있습니까"],
    # ── 2차 협력사 (28~39)
    28: ["전력 구매 계약\\(PPA\\).*제출해 주십시오",
         "전력 구매 계약.*제출해 주십시오"],
    32: ["양극효과\\(Anode Effect\\).*보고해 주십시오",
         "양극효과.*보고해 주십시오"],
    37: ["DOE FEOC.*확인서를 제출해 주십시오",
         "DOE FEOC.*제출해 주십시오"],
    # ── 3차-A 채굴 (1~18)
    1:  ["ILO 감사기관\\(SGS/Bureau Veritas\\).*제출해 주십시오",
         "ILO 감사기관.*제출해 주십시오"],
    2:  ["근로계약 유형별 비율 현황 자료를 제출해 주십시오"],
    5:  ["TRIR 산정 기초 자료를 제출해 주십시오"],
    8:  ["\\(As≤0.05.*mg/L\\)",
         "\\(As.*Pb.*mg/L\\)"],
    18: ["FEOC 해당 여부 자체 점검 결과를 제출해 주십시오"],
    # ── 3차-B Bayer (19~27)
    19: ["알루미나 성적서\\(COA\\)를 제출해 주십시오",
         "알루미나 성적서.*제출해 주십시오"],
    21: ["\\(야외 개방형 습식 저장은 불합격\\)"],
    27: ["지분 구조 확인서를 제출해 주십시오"],
}


# ============================================================
# ■ 지표 마스터 (카테고리, 증빙 기준값)
# ============================================================

INDICATOR_MASTER = {
    # 1차 (40~56)
    40:{"cat":"공정·품질","ev":"Y"},41:{"cat":"공정·품질","ev":"Y"},
    42:{"cat":"공정·품질","ev":"Y"},43:{"cat":"공정·품질","ev":"Y"},
    44:{"cat":"공정·품질","ev":"Y"},45:{"cat":"공정·품질","ev":"Y"},
    46:{"cat":"공정·품질","ev":"Y"},47:{"cat":"공정·품질","ev":"Y"},
    48:{"cat":"공정·품질","ev":"Y"},49:{"cat":"에너지·기후","ev":"Y"},
    50:{"cat":"에너지·기후","ev":"Y"},51:{"cat":"화학물질","ev":"Y"},
    52:{"cat":"화학물질","ev":"Y"},53:{"cat":"화학물질","ev":"Y"},
    54:{"cat":"거버넌스","ev":"Y"},55:{"cat":"거버넌스","ev":"N"},
    56:{"cat":"거버넌스","ev":"Y"},
    # 2차 (28~39)
    28:{"cat":"에너지·기후","ev":"Y"},29:{"cat":"에너지·기후","ev":"Y"},
    30:{"cat":"에너지·기후","ev":"Y"},31:{"cat":"에너지·기후","ev":"Y"},
    32:{"cat":"에너지·기후","ev":"Y"},33:{"cat":"화학물질","ev":"Y"},
    34:{"cat":"에너지·기후","ev":"Y"},35:{"cat":"화학물질","ev":"Y"},
    36:{"cat":"화학물질","ev":"Y"},37:{"cat":"거버넌스","ev":"Y"},
    38:{"cat":"거버넌스","ev":"Y"},39:{"cat":"화학물질","ev":"Y"},
    # 3차-A (1~18)
    1:{"cat":"인권·노동","ev":"Y"},2:{"cat":"인권·노동","ev":"Y"},
    3:{"cat":"인권·노동","ev":"Y"},4:{"cat":"인권·노동","ev":"N"},
    5:{"cat":"인권·노동","ev":"Y"},6:{"cat":"인권·노동","ev":"Y"},
    7:{"cat":"인권·노동","ev":"Y"},8:{"cat":"환경","ev":"Y"},
    9:{"cat":"환경","ev":"Y"},10:{"cat":"환경","ev":"Y"},
    11:{"cat":"에너지·기후","ev":"Y"},12:{"cat":"환경","ev":"Y"},
    13:{"cat":"환경","ev":"Y"},14:{"cat":"화학물질","ev":"Y"},
    15:{"cat":"화학물질","ev":"Y"},16:{"cat":"거버넌스","ev":"Y"},
    17:{"cat":"거버넌스","ev":"N"},18:{"cat":"거버넌스","ev":"Y"},
    # 3차-B (19~27)
    19:{"cat":"공정·품질","ev":"Y"},20:{"cat":"공정·품질","ev":"N"},
    21:{"cat":"환경","ev":"Y"},22:{"cat":"에너지·기후","ev":"Y"},
    23:{"cat":"에너지·기후","ev":"Y"},24:{"cat":"화학물질","ev":"Y"},
    25:{"cat":"환경","ev":"Y"},26:{"cat":"화학물질","ev":"Y"},
    27:{"cat":"거버넌스","ev":"Y"},
}


# ============================================================
# ■ PDF → OCR 텍스트 추출
# ============================================================

def extractTextFromPdf(filePath: str) -> str:
    """PDF → Google Cloud Vision API batch_annotate_files로 텍스트 추출"""
    keyPath = settings.ocr_key_path
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keyPath
    client = vision.ImageAnnotatorClient()

    if not os.path.exists(filePath):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    try:
        with io.open(filePath, 'rb') as f:
            content = f.read()

        inputConfig = vision.InputConfig(
            content=content, mime_type="application/pdf"
        )
        feature = vision.Feature(
            type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION
        )
        request = vision.AnnotateFileRequest(
            input_config=inputConfig, features=[feature]
        )
        response = client.batch_annotate_files(requests=[request])

        if not response.responses:
            return ""

        fullText = ""
        for fr in response.responses:
            for pr in fr.responses:
                if pr.error.message:
                    raise HTTPException(
                        status_code=500,
                        detail=f"OCR 에러: {pr.error.message}"
                    )
                if pr.full_text_annotation:
                    fullText += pr.full_text_annotation.text + "\n"

        return fullText.strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"OCR 처리 실패: {str(e)}"
        )


# ============================================================
# ■ 답변 텍스트 정제 (핵심 함수)
# ============================================================

def _cleanAnswer(rawText: str, indicatorNo: int) -> str:
    """
    OCR raw 텍스트에서 순수 답변만 추출

    처리 순서:
      0. 우선순위(Critical/High/Medium) + ★ 마커 제거  ← v0.5 추가
      1. QUESTION_TAILS 질문 꼬리 패턴 제거
      2. 공통 질문 패턴 제거 (귀사의/귀사는...입니까?)
      3. Y/N 접두어 제거 (증빙자료 마커)
      4. 카테고리 헤더 제거 (▶공정·품질 등)
      5. 리스크 등급 텍스트 제거 (AI 평가 전환)
      6. 다음 지표 잔존 제거 ("20 공정품질 Bayer..." 등)
      7. 선두 특수문자 정리
    """
    text = rawText.strip()
    if not text:
        return ""

    # ── 0. 우선순위 + ★ 마커 제거 (v0.5 신규)
    # 패턴: "Critical ★ Y", "High ★Y", "Medium★ Y", "High Y", "Critical" 등
    text = re.sub(
        r'^(?:Critical|High|Medium|Low)\s*★?\s*',
        '', text, flags=re.IGNORECASE
    )
    # 중간에 나타나는 우선순위 + Y/N ("...85%입니다. High Y 계약...")
    text = re.sub(
        r'\.\s+(?:Critical|High|Medium|Low)\s*★?\s*[YN]?\s+',
        '. ', text, flags=re.IGNORECASE
    )
    # 단독 ★ 잔존 제거
    text = re.sub(r'★\s*', '', text)

    # ── 1. QUESTION_TAILS 패턴 제거
    tails = QUESTION_TAILS.get(indicatorNo, [])
    for tail in tails:
        text = re.sub(tail + r'[\.\s]*', '', text, flags=re.IGNORECASE)

    # ── 2. 공통 질문 패턴 제거
    # "귀사의/귀사는/귀사에서/귀사가/귀사 " 등 모든 형태 대응
    text = re.sub(r'귀사(?:의|는|에서|에|가)?\s[^?？]*[?？]\s*', '', text)
    # 질문 뒤 괄호 주석 잔존 제거 "(Pb≤1,000ppm 등)"
    text = re.sub(r'^\s*\([^)]*\)\s*', '', text)
    text = re.sub(r'[^\s]*를?\s*제출해\s*주십시오[\.\s]*', '', text)
    text = re.sub(r'[^\s]*를?\s*제출해\s*$', '', text)
    text = re.sub(r'[^\s]*를?\s*보고해\s*주십시오[\.\s]*', '', text)

    # ── 3. Y/N 접두어 제거
    text = re.sub(r'^\s*[YN]\s+', '', text)
    text = re.sub(r'\.\s+[YN]\s+', '. ', text)

    # ── 4. 카테고리 헤더 제거 (· 포함/미포함, 선두/중간/후미)
    catRe = r'공정·?품질|에너지·?기후|화학물질|거버넌스|인권·?노동|환경|공시'
    # ▶ 접두 카테고리
    text = re.sub(rf'▶\s*(?:{catRe})\s*', '', text)
    # 선두 카테고리명 (OCR에서 카테고리가 답변 앞에 붙는 경우)
    text = re.sub(rf'^\s*(?:{catRe})\s+', '', text)
    # 후미 카테고리명
    text = re.sub(rf'\s+(?:{catRe})\s*$', '', text)
    text = re.sub(rf'(?:{catRe})\s*$', '', text)

    # ── 4-1. ★ 2차 우선순위 제거 (카테고리 제거 후 노출된 경우)
    text = re.sub(r'^\s*(?:Critical|High|Medium|Low)\s*[YN]?\s+', '', text, flags=re.IGNORECASE)

    # ── 5. 리스크 등급 텍스트 제거 (AI 평가)
    text = re.sub(r'(?:고위험|중위험|저위험)\s*', '', text)

    # ── 6. 다음 지표 잔존 제거 ("20 공정품질 Bayer..." 등)
    text = re.sub(rf'\d{{1,3}}\s+(?:{catRe})\s+.*$', '', text, flags=re.DOTALL)

    # ── 7. 특수문자 정리
    text = re.sub(r'•\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[.\?\s]+', '', text).strip()

    return text


# ============================================================
# ■ OCR 텍스트 파싱
# ============================================================

def parseChecklistAnswers(ocrText: str) -> list:
    """
    OCR 텍스트에서 지표별 답변 추출

    전략:
      1단계: 지표번호 + 카테고리 패턴으로 블록 분리
      2단계: _cleanAnswer()로 질문 꼬리 제거
      3단계: 합쳐진 블록 분리
      4단계: INDICATOR_MASTER로 보정
      5단계: 중복 제거 + 정렬
    """
    answers = []

    catNames = '공정·품질|에너지·기후|화학물질|거버넌스|인권·노동|환경|공시'
    pattern = rf'(\d{{1,3}})\s+({catNames})'
    matches = list(re.finditer(pattern, ocrText))

    for i, match in enumerate(matches):
        indicatorNo = int(match.group(1))
        master = INDICATOR_MASTER.get(indicatorNo)
        if not master:
            continue

        # 블록 범위
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(ocrText)
        block = ocrText[start:end].strip()

        category = master["cat"]
        evidenceYn = master["ev"]

        # 지표명 헤더 제거 후 raw 텍스트
        headerPattern = rf'{indicatorNo}\s+{re.escape(category)}\s+\S[^\n]*'
        headerMatch = re.search(headerPattern, block)
        if headerMatch:
            rawAnswer = block[headerMatch.end():].strip()
        else:
            rawAnswer = block[len(match.group(0)):].strip()

        # 정제
        clean = _cleanAnswer(rawAnswer, indicatorNo)

        # 합쳐진 블록 분리 (인접 지표 답변 합쳐진 경우)
        splitMarkers = [
            r'예\.\s+(?:Scope|압연|재생|전력|에너지)',
            r'예\.\s+(?:UTS|균질화|열간)',
            r'예\.\s+(?:CO₂|tCO)',
        ]
        for marker in splitMarkers:
            parts = re.split(f'(?={marker})', clean, maxsplit=1)
            if len(parts) > 1 and len(parts[0]) > 15 and len(parts[1]) > 15:
                clean = parts[0].strip()
                nextNo = indicatorNo + 1
                nextMaster = INDICATOR_MASTER.get(nextNo)
                if nextMaster and nextNo not in {a["indicator_no"] for a in answers}:
                    nextClean = _cleanAnswer(parts[1], nextNo)
                    if nextClean:
                        answers.append({
                            "indicator_no": nextNo,
                            "category": nextMaster["cat"],
                            "answer_text": nextClean,
                            "evidence_yn": nextMaster["ev"],
                        })

        if clean and len(clean) > 3:
            answers.append({
                "indicator_no": indicatorNo,
                "category": category,
                "answer_text": clean,
                "evidence_yn": evidenceYn,
            })

    # 중복 제거 + 정렬
    seen = set()
    unique = []
    for a in sorted(answers, key=lambda x: x["indicator_no"]):
        if a["indicator_no"] not in seen:
            seen.add(a["indicator_no"])
            unique.append(a)

    return unique


# ============================================================
# ■ DB 저장
# ============================================================

def saveChecklistAnswers(partner_type, partner_id, answers, file_id=None):
    """
    파싱된 답변 → SELF_ASSESS_ANSWER INSERT (risk_level 미포함, DEFAULT '평가중')

    [v0.5 변경]
      3차 통합 PDF(No.1~27)의 경우 지표별 개별 차수 등록:
        No.1~18  → partner_type = "3차-A"
        No.19~27 → partner_type = "3차-B"
    """
    saved_count = 0
    for ans in answers:
        # 지표별 개별 차수 판별 (3차 통합 PDF 대응)
        ind_tier = _detectIndicatorTier(ans["indicator_no"])
        actual_type = ind_tier if ind_tier != "미분류" else partner_type

        # dbCount = 0
        # if dbCount == 0:
        #     sqlDB = settings.external_maria_db
        # else:
        #     sqlDB = settings.maria_db_database

        # sql = f"""
        #     INSERT INTO {sqlDB}.`SELF_ASSESS_ANSWER` (
        #         partner_type, partner_id, indicator_no, category,
        #         answer_text, evidence_yn, source_file_id, version
        #     ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        # """

        sql = f"""
            INSERT INTO `SELF_ASSESS_ANSWER` (
                partner_type, partner_id, indicator_no, category,
                answer_text, evidence_yn, source_file_id, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """
        params = (
            actual_type, partner_id,
            ans["indicator_no"], ans["category"],
            ans["answer_text"], ans["evidence_yn"], file_id,
        )
        
        result = save(sql, params)
        if result:
            saved_count += 1
    return {
        "saved_count": saved_count,
        "partner_type": partner_type,
        "partner_id": partner_id,
    }


# ============================================================
# ■ 통합 처리 함수 (API 엔트리포인트)
# ============================================================

async def extractChecklistProcess(file: UploadFile, partnerId: str) -> dict:
    """자가진단 PDF 업로드 → OCR → 답변 파싱 → DB 저장"""
    try:
        # Step 1. 파일 저장
        fileResult = licenseFile(file, partnerId)
        if not fileResult['status']:
            return {"status": False, "message": "파일 저장 실패", "data": None}

        fileUuid = fileResult['data']["fileName"]
        fileExt = fileResult['data']["ext"]
        fileId = (
            fileResult['data']["fileId"]["id"]
            if fileResult['data']["fileId"]
            else None
        )
        filePath = f'licenseFiles/{fileUuid}.{fileExt}'

        # Step 2. OCR
        ocrText = extractTextFromPdf(filePath)
        if not ocrText:
            return {
                "status": False,
                "message": "PDF에서 텍스트를 추출할 수 없습니다.",
                "data": None,
            }

        # Step 3. 파싱
        answers = parseChecklistAnswers(ocrText)
        if not answers:
            return {
                "status": False,
                "message": "답변 데이터를 파싱할 수 없습니다.",
                "data": {
                    "ocr_text_length": len(ocrText),
                    "ocr_text_preview": ocrText[:500],
                },
            }

        # Step 4. 협력사 구분 (유동적 판별)
        indicatorNos = [a["indicator_no"] for a in answers]
        partnerType = _detectPartnerType(indicatorNos)

        # 협력사 ID 추출
        partnerIdMatch = re.search(r'([A-Z]{2,4}-\d{3})', ocrText)
        partnerId = (
            partnerIdMatch.group(1) if partnerIdMatch else "UNKNOWN"
        )

        # Step 5. DB 저장
        saveResult = saveChecklistAnswers(
            partnerType, partnerId, answers, fileId
        )

        # Step 6. 결과 반환
        return {
            "status": True,
            "message": "자가진단 체크리스트 OCR 추출 및 저장 완료",
            "data": {
                "partner_type": partnerType,
                "partner_id": partnerId,
                "total_answers": len(answers),
                "saved_count": saveResult["saved_count"],
                "file_id": fileId,
                "answers": answers,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": False,
            "message": f"OCR 처리 실패: {str(e)}",
            "data": None,
        }