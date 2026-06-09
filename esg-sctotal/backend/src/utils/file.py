import uuid
# [v1.3] 2026-06-04 — supportingFile Soft Delete 활성화, softDeleteFileById 신규, 원본명 다운로드 지원
import shutil
from pathlib import Path
import httpx
import json
from src.utils.settings import settings
from src.utils.db import save, findOne
from src.models.model import responseModel

# --------------------------
# 파일명 분리, 암호화 로직
# --------------------------

def licenseFile(file, partnerId):
    UPLOAD_DIR = Path("licenseFiles")
    UPLOAD_DIR.mkdir(exist_ok=True)
    origin = file.filename
    ext = origin.split(".")[-1].lower()
    id = uuid.uuid4().hex
    newName = f"{id}.{ext}"
    folderPath = str(UPLOAD_DIR)

    sql = f"""
        INSERT INTO `LICENSE_FILE` (`origin`, `ext`, `fileName`,`dir`) 
        VALUES (?,?,?,?)
        """
    params = (origin, ext, newName, folderPath)
    result = save(sql, params)

    vrtsion = _getLatestVersion(partnerId)

    # 이전 파일이 존재하는 경우 delete_yn=1 처리 (Soft Delete)
    if vrtsion > 0:
        selectSql = """
            SELECT DISTINCT lf.id
            FROM `LICENSE_FILE` lf
            INNER JOIN `SELF_ASSESS_ANSWER` sa
            ON lf.id = sa.source_file_id AND sa.partner_id = ? AND sa.`version` = ?
            WHERE lf.delete_yn = 0
            ORDER BY lf.created_at DESC
        """    
        delFileId = findOne(selectSql, (partnerId, vrtsion))

        deleteSql = f"""
            UPDATE `LICENSE_FILE`
            SET delete_yn = 1
            WHERE id = ? AND delete_yn = 0
        """
        save(deleteSql, (delFileId.get("id"),))

    fileIdSql = f"""
        SELECT id
        FROM `LICENSE_FILE`
        WHERE fileName = ? AND delete_yn = 0;"""
    fileIdParams = (newName,)
    fileId = findOne(fileIdSql, fileIdParams)
    if result:
        path = UPLOAD_DIR / newName
        # [이슈-수정] UploadFile.file 포인터 초기화 — Starlette 파싱 후 포인터가 끝에 위치하여 0바이트 복사 방지
        file.file.seek(0)
        with path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        return responseModel(result, "성공", {"fileName": id, "ext": ext, "fileId": fileId})
    else:
        return responseModel(result, "실패", None)



# --------------------------
# 증빙파일 통합 저장 (SUPPORTING_FILE 테이블)
# partner_id + file_type(coc/selfassess/evidence/cert)으로 구분
# --------------------------
def supportingFile(file, partnerId, fileType):
    UPLOAD_DIR = Path("supportingFiles")
    UPLOAD_DIR.mkdir(exist_ok=True)
    origin = file.filename
    ext = origin.split(".")[-1].lower()
    fileUuid = uuid.uuid4().hex
    newName = f"{fileUuid}.{ext}"
    folderPath = str(UPLOAD_DIR)

    if fileType == "coc":
        # CoC는 단일 파일만 존재하도록 기존 파일 Soft Delete 처리
        softDeleteSql = f"""
            UPDATE `SUPPORTING_FILE`
            SET delete_yn = 1
            WHERE partner_id = ? AND file_type = ? AND delete_yn = 0
        """
        save(softDeleteSql, (partnerId, fileType))

    # 신규 파일 INSERT
    sql = f"""
        INSERT INTO `SUPPORTING_FILE`
        (`partner_id`, `file_type`, `origin`, `ext`, `dir`, `filename`)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    params = (partnerId, fileType, origin, ext, folderPath, newName)
    result = save(sql, params)

    if result:
        fileIdSql = f"SELECT id FROM `SUPPORTING_FILE` WHERE filename = ? AND delete_yn = 0"
        fileId = findOne(fileIdSql, (newName,))
        path = UPLOAD_DIR / newName
        file.file.seek(0)
        with path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        return responseModel(True, "파일 저장 성공", {
            "fileId": fileId["id"] if fileId else None,
            "fileName": newName,
            "originName": origin,
            "ext": ext,
            "fileType": fileType,
        })
    return responseModel(False, "파일 저장 실패")


def softDeleteFileById(fileId):
    """개별 파일 Soft Delete (수정 화면 삭제 버튼용)"""
    sql = f"UPDATE `SUPPORTING_FILE` SET delete_yn = 1 WHERE id = ? AND delete_yn = 0"
    return save(sql, (fileId,))


# --------------------------
# 공공데이터포털 API 호출 로직 (사업자 등록증 진위여부 확인)
# --------------------------
async def checkBusinessStatus(businessNumber: str):
    serviceKey = settings.service_key
    url = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={serviceKey}"
    payload = {
       "b_no": [businessNumber]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            )
        except Exception as e:
            return responseModel(False, f"네트워크 오류: {str(e)}")

    if response.status_code == 200:
        responseData = response.json()

        if responseData.get("data"):
            businessInfo = responseData["data"][0]

            if not businessInfo.get("tax_type_cd"):
                return responseModel(False, businessInfo.get("tax_type"))

            if businessInfo.get("b_stt_cd") == "03":
                return responseModel(False, "폐업 상태입니다.")

            return responseModel(True, "사업자 정보가 확인되었습니다.")
        
        return responseModel(False, "응답 데이터가 올바르지 않습니다.")
    else:
        return responseModel(False, "API 서버 응답 실패", {"code": response.status_code})
    


# ════════════════════════════════════════════════════════════
# ■ 내부 헬퍼
# ════════════════════════════════════════════════════════════

def _getLatestVersion(partnerId) -> int:
    sql = "SELECT COALESCE(MAX(version), 0) AS v FROM `SELF_ASSESS_ANSWER` WHERE partner_id = ? AND delete_yn = 0"
    row = findOne(sql, (partnerId,))
    return row["v"] if row else 0