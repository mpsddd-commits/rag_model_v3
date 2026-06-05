from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, Union, List
from datetime import date

# BaseModel 안에 있는 변수의 class type별 description 작성하는 방법  
# str인 경우 field에 (..., description="") 선언
# float인 경우 field에 (0.0, description="") 선언
# bool인 경우 field에 (True, description="") 선언

# --------------------------
# 공통 응답 모델 및 요청 모델 정의
# --------------------------
def responseModel(status: bool, message: str="", data: dict={}):
    """ 응답 모델 """
    return {
        "status": status,
        "message": message,
        "data": data
    }

# --------------------------
# 각 API별 요청 모델 정의
# --------------------------
class emailModel(BaseModel):
   email: EmailStr = Field(..., description="비밀번호 찾기에 사용되는 이메일 모델")

class loginModel(BaseModel):
  """ auth.py post 로그인 모델 """
  email: EmailStr = Field(..., description="로그인에서 사용되는 이메일 모델")
  password: str = Field(..., description="로그인에서 사용하는 pwd 모델")

class logoutModel(BaseModel):
   """ auth.py delete 로그아웃 모델"""
   uuid: str = Field(..., description="로그아웃에서 사용되는 uuid 모델")

class pwdCheckModel(BaseModel):
   """ auth.py patch 비밀번호 확인 모델"""
   uuid: str = Field(..., description="비밀번호 확인에서 사용되는 uuid 모델")
   password: str = Field(..., description="비밀번호 확인에서 사용하는 pwd 모델")

class SignUpModel(BaseModel):
  """user.py 회원가입 통합 요청 모델"""

  # ── USER 테이블 필드
  email: EmailStr                          = Field(...,  description="USER.email")
  password: str                            = Field(...,  description="USER.password")
  userName: str                            = Field(...,  description="USER.name")
  agreed: bool                             = Field(...,  description="개인정보 수집 및 이용 동의 여부")
  
  # ── COMPANY 테이블 필드
  licensefileId: int                       = Field(...,  description="COMPANY.license_file_id")
  businessNumber: int                      = Field(...,  description="COMPANY.business_number")
  companyName: str                         = Field(...,  description="COMPANY.company_name")
  ceoName: str                             = Field(...,  description="COMPANY.ceo_name")
  openingDate: Optional[Union[str, date]]  = Field(None, description="COMPANY.company_establishment 'YYYY-MM-DD'")
  corporateNumber: int                     = Field(...,  description="COMPANY.corporate_number")
  headOffice: str                          = Field(...,  description="COMPANY.company_address")
  taxName: str                             = Field(...,  description="COMPANY.tax_name")
  issueDate: Optional[Union[str, date]]    = Field(None, description="COMPANY.issue_date 'YYYY-MM-DD'")
  companySize: Optional[str]               = Field(None, description="COMPANY.company_size")
  
  # ── INDUSTRY_DETAIL 테이블 필드
  # [FK] industry_id → INDUSTRY_CODE.id (배열 수신 → saveMany 일괄 INSERT)
  # [FK] company_id  → COMPANY.id       (signUpProcess 내부 주입)
  industryList: List[str]                 = Field(...,  description="INDUSTRY_DETAIL.industry_id 배열")
  
  # ── USER_ROLE 테이블 필드
  # [FK] role_id → ROLE.id
  roleId: int                              = Field(2,    description="USER_ROLE.role_id (기본값: 2)")

class userUpdateModel(BaseModel):
    """ user.py patch 회원 수정 페이지 전용 모델 (화면 항목: 새 비밀번호, 확인, 이름) """
    uuid: str = Field(..., description="회원정보 수정시 사용되는 uuid 모델")
    name: Optional[str] = Field(None, description="변경할 이름")
    newPassword: Optional[str] = Field(None, description="변경할 비밀번호")
    newPasswordConfirm: Optional[str] = Field(None, description="변경할 비밀번호 확인")

    # Pydantic 라이브러리에서 정의한 이름이라 카멜케이스 안 됨
    @model_validator(mode='after')
    def checkPasswordsMatch(self) -> 'userUpdateModel':
        # 비밀번호 변경 값이 들어온 경우에만 두 값이 일치하는지 검증
        if self.newPassword or self.newPasswordConfirm:
            if self.newPassword != self.newPasswordConfirm:
                raise ValueError("변경할 비밀번호가 서로 일치하지 않습니다.")
        return self
    
class duplicateCheckModel(BaseModel):
  """ user.py get email,사업자 등록 번호 중복 체크 인증 모델 """
  # 이메일: 형식 검증은 EmailStr이 담당, 설명 추가
  email: Optional[EmailStr] =  Field(
      None,
      description="회원가입에서 사용되는 이메일 모델"
      )
  # 사업자 번호: 10자리 숫자 패턴 검증 및 길이 제한, 설명 추가
  businessNumber: Optional[str] = Field(
      None,
      min_length=10, 
      max_length=10,
      pattern=r"^\d{10}$",  # 숫자 10자리 정규표현식
      description="회원가입에서 사용되는 사업자 등록 번호 모델"
      )
  
class userDeleteModel(BaseModel):
    """ user.py delete 회원 탈퇴 페이지 전용 모델 (uuid 이용) """
    uuid: str = Field(..., description="회원탈퇴시 사용되는 uuid 모델")

class inviteMemberModel(BaseModel):
    """ inviteMember.py 내부 직원 초대 API 모델 """
    uuid: str = Field(..., description="내부 직원 초대 API에서 사용되는 uuid")
    email: List[EmailStr] = Field(..., description="초대할 내부 직원의 이메일")
    issue: List[int]= Field(..., description="이슈 그룹 리스트")
    role: int = Field(..., description="권한 모델(Consultant, Employee)")
    projectId: int = Field(..., description="프로젝트 id")

class inviteConsultantModel(BaseModel):
    """ inviteConsultant.py 컨설턴트 초대 API 모델 """
    uuid: str = Field(..., description="컨설턴트 초대 API에서 사용되는 uuid 모델")
    email: List[EmailStr] = Field(..., description="초대할 컨설턴트의 이메일 모델")
    role: int = Field(..., description="권한 모델(3)")
    projectId: int = Field(..., description="프로젝트 id")

class inviteSignUpUserInfo(BaseModel):
  """ invite.py 초대 링크로 회원가입 API 모델 """
  companyName: str = Field(..., description="초대 링크로 회원가입 시 사용되는 회사명")
  email: EmailStr = Field(..., description="초대 링크로 회원가입 시 사용되는 이메일")
  name: str = Field(..., description="초대 링크로 회원가입 시 사용되는 이름")
  password: str = Field(..., description="초대 링크로 회원가입 시 사용되는 비밀번호")

class alarmListModel(BaseModel):
    """alarm.py POST 알림 목록 조회 요청 모델"""
    uuid   : str            = Field(...,  description="Redis uuid — user_id 조회용")
    type   : Optional[str]  = Field(None, description="단일 알림 유형 필터 (예: USER)")
    types  : Optional[str]  = Field(None, description="복수 알림 유형 필터 (예: CHART,LEAF)")
    isRead : Optional[bool] = Field(None, description="읽음 여부 필터")
    page   : Optional[int]  = Field(1,    description="페이지 번호 (기본값: 1)")
    size   : Optional[int]  = Field(20,   description="페이지 크기 (기본값: 20)")


class alarmReadModel(BaseModel):
    """alarm.py PATCH 알림 읽음 처리 요청 모델"""
    uuid  : str                  = Field(...,  description="Redis uuid — user_id 조회용")
    types : Optional[List[str]]  = Field(None, description="읽음 처리할 유형 리스트. null/빈배열 → 전체")


class alarmSendModel(BaseModel):
    """alarm.py POST 알림 전송 요청 모델"""
    notifyType : str            = Field(..., description="NotifyType — USER/CHECK/CHART/LEAF/CUBE")
    userId     : int            = Field(..., description="FK → USER.id — 수신자")
    companyId  : int            = Field(..., description="FK → COMPANY.id")
    meta       : Optional[dict] = Field({},  description="타입별 치환 변수 및 추가 메타데이터")


class alarmResponse(BaseModel):
    """alarm.py 알림 공통 응답 모델"""
    status  : bool
    message : str
    data    : Optional[dict] = None

