from pydantic import BaseModel, Field
from typing import Optional, List

# --------------------------
# 공통 응답 모델
# --------------------------
def responseModel(status: bool, message: str="", data: dict={}):
    return {"status": status, "message": message, "data": data}

# --------------------------
# 로그인용 요청 모델 (ESG 공급망 전용)
# --------------------------
class EsgLoginModel(BaseModel):
    """원청사/N차 협력사 공통 로그인 모델"""
    email:      str = Field(..., description="로그인 이메일")
    loginType:  str = Field("oem", description="로그인 유형 (oem=원청사, supplier=N차 협력사)")
    authCode:   Optional[str] = Field(None, description="2차 인증 코드 (협력사만 필수, 6자리)")
 
class AuthCodeModel(BaseModel):
    """2차 인증 코드 발송 요청 모델"""
    email: str = Field(..., description="인증 코드를 받을 이메일")
 
class UserModel(BaseModel):
    """로그인 세션 사용자 모델 (토큰 페이로드용)"""
    uuid:       str = Field(..., description="세션 UUID")
    partnerId:  str = Field(..., description="partner_id — COMPANY 테이블 식별자")
    name:       str = Field(..., description="기업명")
    email:      str = Field(..., description="담당자 이메일")
    role:       str = Field(..., description="권한 (원청사/1차/2차/3차)")
    role_name:  str = Field(..., description="권한 표시명")

# --------------------------
# 기업 정보 요청 모델
# --------------------------
class companyRegisterModel(BaseModel):
    """기업 정보 등록 모델"""
    partnerId:   str = Field(..., description="협력사 코드 (HMOS-001 등)")
    companyName: str = Field(..., description="기업명")
    ceoName:     str = Field(..., description="대표자명")
    bizNo:       str = Field(..., description="사업자등록번호")
    founded:     str = Field("",  description="설립일")
    address:     str = Field("",  description="소재지")
    size:        str = Field("",  description="규모 (대기업/중견/중소)")
    country:     str = Field("",  description="국가")
    tier:        int = Field(0,   description="차수 (0=원청사, 1~3)")
    tierLabel:   str = Field("",  description="차수 표시명")
    parentId:    str = Field("",  description="상위 협력사 코드")
    scope1:      int = Field(0,   description="Scope 1 GHG")
    scope2:      int = Field(0,   description="Scope 2 GHG")
    feocRatio:   float = Field(0.0, description="FEOC 비중 (%)")
    trir:        float = Field(0.0, description="TRIR")
    iso14001:    str = Field("N", description="ISO 14001")
    iso45001:    str = Field("N", description="ISO 45001")
    iatf:        str = Field("N", description="IATF 16949")
    rba:         str = Field("N", description="RBA")
    rmap:        str = Field("N", description="RMAP")
    cmrt:        str = Field("N", description="CMRT")
    emat:        str = Field("N", description="EMAT")

class companyUpdateModel(BaseModel):
    """기업 정보 수정 모델"""
    companyName: Optional[str] = Field(None, description="기업명")
    ceoName:     Optional[str] = Field(None, description="대표자명")
    bizNo:       Optional[str] = Field(None, description="사업자등록번호")
    founded:     Optional[str] = Field(None, description="설립일")
    address:     Optional[str] = Field(None, description="소재지")
    size:        Optional[str] = Field(None, description="규모")
    country:     Optional[str] = Field(None, description="국가")
    scope1:      Optional[int] = Field(None, description="Scope 1")
    scope2:      Optional[int] = Field(None, description="Scope 2")
    feocRatio:   Optional[float] = Field(None, description="FEOC")
    trir:        Optional[float] = Field(None, description="TRIR")
    iso14001:    Optional[str] = Field(None, description="ISO 14001")
    iso45001:    Optional[str] = Field(None, description="ISO 45001")
    iatf:        Optional[str] = Field(None, description="IATF")
    rba:         Optional[str] = Field(None, description="RBA")
    rmap:        Optional[str] = Field(None, description="RMAP")
    cmrt:        Optional[str] = Field(None, description="CMRT")
    emat:        Optional[str] = Field(None, description="EMAT")

class companyListModel(BaseModel):
    """기업 목록 조회 모델"""
    search:   Optional[str] = Field(None, description="검색어")
    tier:     Optional[int] = Field(None, description="차수 필터")
    risk:     Optional[str] = Field(None, description="리스크 필터")
    parentId: Optional[str] = Field(None, description="상위 협력사")
    userRole: Optional[str] = Field(None, description="현재 역할")


# --------------------------
# 공장 정보 요청 모델
# --------------------------
class factoryRegisterModel(BaseModel):
    """공장 등록 모델"""
    partnerId:          str   = Field(..., description="협력사 코드")
    factoryName:        str   = Field(..., description="공장명")
    factoryOwner:       str   = Field("",  description="공장주명")
    factoryLocation:    str   = Field("",  description="공장 소재지")
    operationStatus:    str   = Field("가동중", description="가동 상태 (가동중/중단/폐쇄)")
    utilizationRate:    float = Field(0.0, description="공장 이용 비율 (%)")
    scope1Emissions:    int   = Field(0,   description="Scope 1 배출량")
    scope2Emissions:    int   = Field(0,   description="Scope 2 배출량")
    feocRawMaterialRatio: float = Field(0.0, description="FEOC 원료 비중 (%)")
    trirSafetyRate:     float = Field(0.0, description="TRIR 산업안전율")
    note:               str   = Field("",  description="비고")

class factoryUpdateModel(BaseModel):
    """공장 수정 모델"""
    factoryName:        Optional[str]   = Field(None, description="공장명")
    factoryOwner:       Optional[str]   = Field(None, description="공장주명")
    factoryLocation:    Optional[str]   = Field(None, description="소재지")
    operationStatus:    Optional[str]   = Field(None, description="가동 상태")
    utilizationRate:    Optional[float] = Field(None, description="이용 비율 (%)")
    scope1Emissions:    Optional[int]   = Field(None, description="Scope 1")
    scope2Emissions:    Optional[int]   = Field(None, description="Scope 2")
    feocRawMaterialRatio: Optional[float] = Field(None, description="FEOC")
    trirSafetyRate:     Optional[float] = Field(None, description="TRIR")
    note:               Optional[str]   = Field(None, description="비고")

# --------------------------
# 자가진단 버전 조회 모델
# --------------------------
class selfAssessVersionModel(BaseModel):
    """자가진단 버전별 조회 모델"""
    partnerId: str = Field(..., description="협력사 코드")
    version:   Optional[int] = Field(None, description="조회할 버전 (None=최신)")

class alarmListModel(BaseModel):
    """alarm.py POST 알림 목록 조회 요청 모델"""
    uuid   : str            = Field(...,  description="Redis uuid — partner_id 조회용")
    type   : Optional[str]  = Field(None, description="단일 알림 유형 필터 (예: USER)")
    types  : Optional[str]  = Field(None, description="복수 알림 유형 필터 (예: CHART,LEAF)")
    isRead : Optional[bool] = Field(None, description="읽음 여부 필터")
    page   : Optional[int]  = Field(1,    description="페이지 번호 (기본값: 1)")
    size   : Optional[int]  = Field(20,   description="페이지 크기 (기본값: 20)")


class alarmReadModel(BaseModel):
    """alarm.py PATCH 알림 읽음 처리 요청 모델"""
    uuid  : str                  = Field(...,  description="Redis uuid — partner_id 조회용")
    types : Optional[List[str]]  = Field(None, description="읽음 처리할 유형 리스트. null/빈배열 → 전체")


class alarmSendModel(BaseModel):
    """alarm.py POST 알림 전송 요청 모델"""
    notifyType : str            = Field(..., description="NotifyType — USER/CHECK/CHART/LEAF/CUBE")
    partnerId  : str            = Field(..., description="FK → COMPANY.partner_id")
    meta       : Optional[dict] = Field({},  description="타입별 치환 변수 및 추가 메타데이터")


class alarmResponse(BaseModel):
    """alarm.py 알림 공통 응답 모델"""
    status  : bool
    message : str
    data    : Optional[dict] = None