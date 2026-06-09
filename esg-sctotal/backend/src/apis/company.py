# src/apis/company.py
# [v1.3] 2026-06-04 — 원본명 다운로드(Content-Disposition), 파일 개별 삭제 엔드포인트 추가
# ────────────────────────────────────────────────────────────────────────────
# [역할] HTTP 요청 수신 후 models/company.py에 위임
# [라우트 순서] 고정 경로 → 동적 경로 (FastAPI 매칭 안전)
# ────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, UploadFile, File, Form, Query
from typing import Optional, List
from src.models.company import (
    registerCompanyProcess, updateCompanyProcess, getCompanyDetailProcess,
    getCompanyListProcess, deleteCompanyProcess,
    uploadCocFileProcess, uploadEvidenceProcess, uploadCertProcess,
    uploadSelfAssessProcess, getSelfAssessProcess,
    deleteFileProcess, fileDownloadProcess,
    getFilesByPartnerProcess,
    registerFactoryProcess, updateFactoryProcess, deleteFactoryProcess,
    getFactoryListProcess, getFactoryDetailProcess,
)
from src.models.model import (
    companyRegisterModel, companyUpdateModel, companyListModel,
    factoryRegisterModel, factoryUpdateModel,
)

router = APIRouter()


# ══ 고정 경로 먼저 배치 ══

# ── POST — 기업 등록
@router.post("",
    summary="기업 정보 등록",
    description="협력사 기업 기본정보, ESG 지표, 7대 인증 등록")
def registerCompany(companyRegisterModel: companyRegisterModel):
    return registerCompanyProcess(companyRegisterModel)


# ── POST — 기업 목록
@router.post("/list",
    summary="기업 목록 조회",
    description="검색/필터 기반 기업 목록")
def companyList(companyListModel: companyListModel):
    return getCompanyListProcess(companyListModel)


# ── 파일 업로드 (고정 경로) ──

# ── POST — 글로벌 인증 증빙 다중 업로드
@router.post("/file/cert",
    summary="글로벌 인증 증빙 다중 업로드",
    description="글로벌 증빙자료 → SUPPORTING_FILE 등록")
def certUpload(
    partnerId: str = Form(...), 
    files: List[UploadFile] = File(...)):
    return uploadCertProcess(partnerId, files)


# ── POST — 자가진단 OCR 업로드
@router.post("/file/selfassess",
    summary="자가진단 체크리스트 업로드(버전 자동 증가)",
    description="자가진단 PDF → OCR → 답변 추출 → SELF_ASSESS_ANSWER 저장")
async def selfAssessUpload(
    partnerId: str = Form(...),
    file: UploadFile = File(...)):
    return await uploadSelfAssessProcess(partnerId, file)


# ── POST — 자가진단 증빙자료 다중 업로드
@router.post("/file/evidence", 
    summary="증빙자료 다중 업로드",
    description="자가진단 증빙자료 → SUPPORTING_FILE 등록")
def evidenceUpload(
    partnerId: str = Form(...), 
    files: List[UploadFile] = File(...)):
    return uploadEvidenceProcess(partnerId, files)


# ── POST — CoC 서약서 업로드
@router.post("/file/coc",
    summary="행동강령 서약서 업로드",
    description="CoC 서약서 PDF 업로드 → SUPPORTING_FILE 등록")
def cocUpload(
    partnerId: str = Form(...),
    file: UploadFile = File(...)):
    return uploadCocFileProcess(partnerId, file)


# ── 파일 다운로드 (고정 경로) ──

@router.get("/file/download/{filename}", 
    summary="파일 다운로드 (원본명)",
    description="DB origin 컬럼으로 원본 파일명 변환")
def fileDownload(filename: str):
    return fileDownloadProcess(filename)


{"status": False, "message": "파일을 찾을 수 없습니다."}


# ── 파일 개별 삭제 (Soft Delete — 상세 화면 삭제 버튼용)
@router.delete("/file/{fileId}", 
    summary="파일 개별 삭제 (Soft Delete)",
    description="Soft Delete — 상세 화면 삭제 버튼")
def fileDelete(fileId: int):
    return deleteFileProcess(fileId)


# ══ 공장 관리 (고정 경로) ══

@router.post("/factory",
    summary="공장 등록",        
    description="공장 정보 등록 + 가중합산 업데이트")
def registerFactory(model: factoryRegisterModel):
    return registerFactoryProcess(model)

@router.put("/factory/{factoryId}",
    summary="공장 수정",        
    description="공장 정보 수정 + 가중합산 재계산")
def updateFactory(factoryId: int, model: factoryUpdateModel):
    return updateFactoryProcess(factoryId, model)

@router.delete("/factory/{factoryId}",
    summary="공장 삭제",        
    description="공장 삭제 + 가중합산 재계산")
def deleteFactory(factoryId: int):
    return deleteFactoryProcess(factoryId)

@router.get("/factory/{factoryId}",
    summary="공장 상세",        
    description="공장 정보 조회 + 가중합산 재계산")
def factoryDetail(factoryId: int):
    return getFactoryDetailProcess(factoryId)

# ══ 동적 경로 (하위 경로 먼저) ══

# ── GET — 자가진단 답변 조회 (/{partnerId}/selfassess 먼저!)
@router.get("/{partnerId}/selfassess",
    summary="자가진단 답변 (버전별)",        
    description="협력사별 자가진단 답변 목록")
def selfAssessDetail(partnerId: str, version: Optional[int] = Query(None, description="버전 (None=최신)")):
    return getSelfAssessProcess(partnerId, version)

@router.get("/{partnerId}/factories", 
    summary="협력사 공장 목록",
    description="협력사 공장 목록 조회")
def factoryList(partnerId: str):
    return getFactoryListProcess(partnerId)

@router.get("/{partnerId}/files", 
    summary="협력사 파일 목록 (4영역 분류)",
    description="협력사별 등록된 증빙 자료 관련 파일 목록 조회")
def fileList(partnerId: str):
    return getFilesByPartnerProcess(partnerId)

# ── GET — 기업 상세
@router.get("/{partnerId}",
    summary="기업 상세 조회",
    description="협력사 단건 상세 (기업정보 + 자가진단 답변)")
def companyDetail(partnerId: str):
    return getCompanyDetailProcess(partnerId)


# ── PUT — 기업 수정
@router.put("/{partnerId}",
    summary="기업 정보 수정",
    description="협력사 기업 정보 수정")
def updateCompany(partnerId: str, companyUpdateModel: companyUpdateModel):
    return updateCompanyProcess(partnerId, companyUpdateModel)


# ── DELETE — 기업 삭제
@router.delete("/{partnerId}",
    summary="기업 삭제",
    description="기업 soft delete")
def companyDelete(partnerId: str):
    return deleteCompanyProcess(partnerId)
