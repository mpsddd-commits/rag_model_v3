# src/models/company.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] 협력사 기업정보 + 공장 관리 + 자가진단 버전 Business Logic
# [스타일] camelCase 함수명, BaseModel 사용
# ────────────────────────────────────────────────────────────────────────────

from pathlib import Path

from src.utils.db import save, findOne, findAll, addKey
from src.utils.file import supportingFile, softDeleteFileById
from src.models.model import responseModel
from pathlib import Path
from urllib.parse import quote
from fastapi.responses import FileResponse
from src.utils.ocrs import extractChecklistProcess



# ════════════════════════════════════════════════════════════
# ■ 기업 정보 CRUD
# ════════════════════════════════════════════════════════════

def registerCompanyProcess(model) -> dict:
    existSql = "SELECT id FROM `COMPANY` WHERE partner_id = ? AND delete_yn = 0"
    exist = findOne(existSql, (model.partnerId,))
    if exist:
        return responseModel(False, "이미 등록된 협력사입니다.")
    certFields = [model.cmrt, model.emat, model.iso14001, model.iso45001, model.iatf, model.rba, model.rmap]
    certCount = sum(1 for v in certFields if v == "Y")
    sql = """
        INSERT INTO `COMPANY` (
            partner_id, company_name, short_name, ceo_name, biz_no, founded,
            address, size, country, tier, tier_label, parent_id,
            scope1, scope2, feoc_ratio, trir,
            cmrt, emat, iso14001, iso45001, iatf, rba, rmap,
            cert_count, status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ACTIVE')
    """
    params = (
        model.partnerId, model.companyName, model.companyName,
        model.ceoName, model.bizNo, model.founded,
        model.address, model.size, model.country,
        model.tier, model.tierLabel, model.parentId,
        model.scope1, model.scope2, model.feocRatio, model.trir,
        model.cmrt, model.emat, model.iso14001, model.iso45001,
        model.iatf, model.rba, model.rmap, certCount,
    )
    result = save(sql, params)
    if result:
        return responseModel(True, "기업 정보가 등록되었습니다.", {"partnerId": model.partnerId})
    return responseModel(False, "기업 정보 등록 실패")


def updateCompanyProcess(partnerId, model) -> dict:
    fieldMap = {
        "companyName": "company_name", "ceoName": "ceo_name",
        "bizNo": "biz_no", "founded": "founded", "address": "address",
        "size": "size", "country": "country",
        "scope1": "scope1", "scope2": "scope2",
        "feocRatio": "feoc_ratio", "trir": "trir",
        "iso14001": "iso14001", "iso45001": "iso45001", "iatf": "iatf",
        "rba": "rba", "rmap": "rmap", "cmrt": "cmrt", "emat": "emat",
    }
    setClauses, params = [], []
    data = model.dict(exclude_none=True)
    for camel, snake in fieldMap.items():
        if camel in data:
            setClauses.append(f"`{snake}` = ?")
            params.append(data[camel])
    if not setClauses:
        return responseModel(False, "수정할 데이터가 없습니다.")
    certFields = ["cmrt", "emat", "iso14001", "iso45001", "iatf", "rba", "rmap"]
    if any(f in data for f in certFields):
        cur = findOne("SELECT cmrt,emat,iso14001,iso45001,iatf,rba,rmap FROM `COMPANY` WHERE partner_id=?", (partnerId,))
        if cur:
            merged = {f: cur.get(f, "N") for f in certFields}
            merged.update({f: data[f] for f in certFields if f in data})
            certCount = sum(1 for f in certFields if merged.get(f) == "Y")
            setClauses.append("`cert_count` = ?")
            params.append(certCount)
    params.append(partnerId)
    sql = f"UPDATE `COMPANY` SET {', '.join(setClauses)} WHERE partner_id = ? AND delete_yn = 0"
    result = save(sql, tuple(params))
    if result:
        return responseModel(True, "기업 정보가 수정되었습니다.", {"partnerId": partnerId})
    return responseModel(False, "수정 실패")


def getCompanyDetailProcess(partnerId) -> dict:
    sql = "SELECT * FROM `COMPANY` WHERE partner_id = ? AND delete_yn = 0"
    company = findOne(sql, (partnerId,))
    if not company:
        return responseModel(False, "기업 정보를 찾을 수 없습니다.")
    # 최신 버전 자가진단
    latestVer = _getLatestVersion(partnerId)
    answersSql = """
        SELECT id, partner_type, indicator_no, category, answer_text,
               risk_level, evidence_yn, version, created_at
        FROM `SELF_ASSESS_ANSWER`
        WHERE partner_id = ? AND version = ?
        ORDER BY indicator_no ASC
    """
    answers = findAll(answersSql, (partnerId, latestVer))
    # 공장 목록
    factories = _getFactoriesByPartnerId(partnerId)
    # 버전 목록
    versions = _getVersionList(partnerId)
    return responseModel(True, "조회 성공", {
        "company": company,
        "selfAssessAnswers": answers or [],
        "factories": factories or [],
        "versions": versions or [],
        "currentVersion": latestVer,
    })


def getCompanyListProcess(model) -> dict:
    conditions = ["delete_yn = 0"]
    params = []
    if model.userRole == "1차 협력사":
        conditions.append("tier > 1")
    elif model.userRole == "2차 협력사":
        conditions.append("tier > 2")
    elif model.userRole == "3차 협력사":
        conditions.append("tier > 3")
    else:
        conditions.append("tier > 0")
    if model.parentId:
        conditions.append("parent_id = ?")
        params.append(model.parentId)
    if model.search:
        conditions.append("(company_name LIKE ? OR short_name LIKE ?)")
        params.extend([f"%{model.search}%", f"%{model.search}%"])
    if model.tier is not None:
        conditions.append("tier = ?")
        params.append(model.tier)
    if model.risk:
        conditions.append("risk_level = ?")
        params.append(model.risk)
    where = " AND ".join(conditions)
    sql = f"""
        SELECT partner_id, company_name, short_name, ceo_name, biz_no,
               founded, address, size, country, email,
               tier, tier_label, parent_id, risk_level,
               scope1, scope2, feoc_ratio, trir,
               cmrt, emat, iso14001, iso45001, iatf, rba, rmap,
               cert_count, status
        FROM `COMPANY` WHERE {where}
        ORDER BY tier ASC, company_name ASC
    """
    rows = findAll(sql, tuple(params))
    return responseModel(True, "조회 성공", {"companies": rows or [], "count": len(rows or [])})


def deleteCompanyProcess(partnerId) -> dict:
    sql = "UPDATE `COMPANY` SET delete_yn = 1 WHERE partner_id = ?"
    result = save(sql, (partnerId,))
    if result:
        return responseModel(True, "삭제되었습니다.")
    return responseModel(False, "삭제 실패")


# ════════════════════════════════════════════════════════════
# ■ 글로벌 인증 증빙 다중 업로드
# ════════════════════════════════════════════════════════════

def uploadCertProcess(partnerId, files) -> dict:
    """글로벌 인증 증빙 다중 업로드 → SUPPORTING_FILE (file_type='cert')"""
    uploaded = []
    for f in files:
        result = supportingFile(f, partnerId, "cert")
        if result["status"]:
            uploaded.append(result["data"])
    return responseModel(True, f"인증 증빙 {len(uploaded)}건 업로드 완료", {"files": uploaded, "count": len(uploaded)})


# ════════════════════════════════════════════════════════════
# ■ 자가진단 관리
# ════════════════════════════════════════════════════════════

# 버전 관리
def getSelfAssessProcess(partnerId, version=None) -> dict:
    """버전별 자가진단 답변 조회 (version=None → 최신)"""
    if version is None:
        version = _getLatestVersion(partnerId)
    sql = """
        SELECT sc.question, sc.indicator_name, sc.priority,
               sa.id, sa.partner_type, sa.partner_id, sa.indicator_no,
               sa.category, sa.answer_text, sa.risk_level, sa.evidence_yn,
               sa.version, sa.created_at
        FROM `SELF_ASSESS_ANSWER` sa
        LEFT JOIN `SELF_ASSESS_CHECKLIST` sc
          ON sa.indicator_no = sc.indicator_no AND sa.partner_type = sc.partner_type
        WHERE sa.partner_id = ? AND sa.version = ?
        ORDER BY sa.indicator_no ASC
    """
    rows = findAll(sql, (partnerId, version))
    versions = _getVersionList(partnerId)
    return responseModel(True, "조회 성공", {
        "answers": rows or [], "count": len(rows or []),
        "currentVersion": version, "versions": versions,
    })

# 자가진단 OCR 업로드 + 자동 버전업 → LICENSE_FILE + SELF_ASSESS_ANSWER
async def uploadSelfAssessProcess(partnerId, file) -> dict:
    """자가진단 OCR 업로드 — 자동 버전업"""
    
    # 최신 버전을가져와 업로드된 파일과 매핑하여 
    # 다음과 같이 Soft Delete 처리 
    # 새 파일 저장 → OCR → 답변 저장 → 버전업 + 이전 버전 답변 Soft Delete
    oldVersion = _getLatestVersion(partnerId)
    result = await extractChecklistProcess(file, partnerId)

    # 혹시 모르니 result 진행 후 다음 버전 계산하여 리턴 데이터에 포함 (프론트에서 최신 버전 정보로 활용)
    # 다음 버전 번호 계산
    nextVersion = oldVersion + 1
    
    if result.get("status") and result.get("data"):
        if result["data"].get("partner_id") == "UNKNOWN":
            result["data"]["partner_id"] = partnerId
        fileId = result["data"].get("file_id")
        # partner_id + version 업데이트
        if fileId:
            updateSql = """
                UPDATE `SELF_ASSESS_ANSWER`
                SET partner_id = ?, version = ?
                WHERE partner_id = 'UNKNOWN' AND source_file_id = ? AND delete_yn = 0
            """
            save(updateSql, (partnerId, nextVersion, fileId))
        result["data"]["version"] = nextVersion
        if oldVersion > 0:
            # 이전 버전 답변은 delete_yn=1 처리 (최신 버전만 조회되도록)
            deleteSql = """
                UPDATE `SELF_ASSESS_ANSWER`
                SET delete_yn = 1
                WHERE partner_id = ? AND version = ? AND delete_yn = 0
            """
            save(deleteSql, (partnerId, oldVersion,))

        # Kafka로 전송하기 위해 새로 적재된 자가진단 리스트 데이터 조회
        try:
            answersSql = """
                SELECT indicator_no, answer_text, category, evidence_yn
                FROM `SELF_ASSESS_ANSWER`
                WHERE partner_id = ? AND version = ? AND delete_yn = 0
            """
            answers = findAll(answersSql, (partnerId, nextVersion))
            
            if answers:
                from src.utils.kafkasv import sendSelfAssessToKafka
                kafkaMessage = {
                    "partner_id": partnerId,
                    "version": nextVersion,
                    "answers": [
                        {
                            "indicator_no": row["indicator_no"],
                            "answer_text": row["answer_text"],
                            "category": row["category"],
                            "evidence_yn": row["evidence_yn"]
                        }
                        for row in answers
                    ]
                }
                sendSelfAssessToKafka(kafkaMessage)
                print(f"[Kafka Publish] partner_id={partnerId}, version={nextVersion}, answers={len(answers)}")
        except Exception as kafka_ex:
            print(f"[Kafka Publish Error] {kafka_ex}")
            
    return result

# 자가진단 증빙자료는 별도 업로드 API로 관리 (evidence 파일 유형) — OCR 결과와 직접 연결된 파일이 아니므로, 자가진단 답변과 1:N 관계로 유연하게 관리
def uploadEvidenceProcess(partnerId, files) -> dict:
    """증빙자료 다중 업로드 → SUPPORTING_FILE (file_type='evidence')"""
    uploaded = []
    for f in files:
        result = supportingFile(f, partnerId, "evidence")
        if result["status"]:
            uploaded.append(result["data"])
    return responseModel(True, f"증빙자료 {len(uploaded)}건 업로드 완료", {"files": uploaded, "count": len(uploaded)})


# ════════════════════════════════════════════════════════════
# ■ 행동강령 서약서 업로드
# ════════════════════════════════════════════════════════════

def uploadCocFileProcess(partnerId, file) -> dict:
    """행동강령 서약서 → SUPPORTING_FILE (file_type='coc')"""
    return supportingFile(file, partnerId, "coc")


# ════════════════════════════════════════════════════════════
# ■ 협력사별 등록된 파일 조회
# ════════════════════════════════════════════════════════════

def getFilesByPartnerProcess(partnerId) -> dict:
    """협력사별 파일 목록 조회 — 4영역 분류 (coc/selfassess/evidence/cert)"""
    sql = """
        SELECT id, partner_id, file_type, origin, filename, ext, created_at
        FROM `SUPPORTING_FILE`
        WHERE partner_id = ? AND delete_yn = 0
        ORDER BY file_type ASC, created_at DESC
    """
    rows = findAll(sql, (partnerId,))
    # 영역별 분류
    categorized = {
        "coc": [],        # 행동강령 준수 서약서
        "selfassess": [], # 자가진단 완료 문서
        "evidence": [],   # 자가진단 증빙 자료
        "cert": [],       # 글로벌 인증 증빙 자료
    }
    for row in (rows or []):
        ft = row.get("file_type", "evidence")
        if ft in categorized:
            categorized[ft].append(row)
        else:
            categorized["evidence"].append(row)
    # LICENSE_FILE(자가진단 OCR PDF)도 추가
    lfSql = """
        SELECT DISTINCT lf.id, lf.origin, lf.filename, lf.ext, lf.dir, lf.created_at
        FROM `LICENSE_FILE` lf
        INNER JOIN `SELF_ASSESS_ANSWER` sa
          ON lf.id = sa.source_file_id AND sa.partner_id = ?
        WHERE lf.delete_yn = 0
        ORDER BY lf.created_at DESC
    """
    licenseFiles = findAll(lfSql, (partnerId,))
    categorized["selfassess"].extend(licenseFiles or [])
    return responseModel(True, "조회 성공", categorized)


# ════════════════════════════════════════════════════════════
# ■ [v1.4] 파일 다운로드 / 삭제 프로세스 (라우터 로직 분리)
# ════════════════════════════════════════════════════════════
 
def fileDownloadProcess(filename: str):
    """파일 다운로드 — DB origin 컬럼으로 원본 파일명 변환 후 FileResponse 반환"""
 
    # DB에서 원본 파일명 조회 (SUPPORTING_FILE → LICENSE_FILE 순)
    originName = filename
    for table in ["SUPPORTING_FILE", "LICENSE_FILE"]:
        row = findOne(f"SELECT origin FROM `{table}` WHERE filename = ?", (filename,))
        if row and row.get("origin"):
            originName = row["origin"]
            break
 
    # 파일 경로 탐색 (supportingFiles/ → licenseFiles/ 순)
    for folder in ["supportingFiles", "licenseFiles"]:
        path = Path(folder) / filename
        if path.exists():
            encoded = quote(originName)
            headers = {"Content-Disposition": f"attachment; filename*=UTF-8\'\'\'{encoded}"}
            return FileResponse(path=str(path), headers=headers, media_type="application/octet-stream")
 
    return responseModel(False, "파일을 찾을 수 없습니다.")


# ════════════════════════════════════════════════════════════
# ■ 파일 개별 삭제 (Soft Delete — 상세 화면 삭제 버튼용)
# ════════════════════════════════════════════════════════════

def deleteFileProcess(fileId) -> dict:
    result = softDeleteFileById(fileId)
    if result:
        return responseModel(True, "파일이 삭제되었습니다.")
    return responseModel(False, "삭제 실패")


# ════════════════════════════════════════════════════════════
# ■ 공장 CRUD + 가중합산
# ════════════════════════════════════════════════════════════

def registerFactoryProcess(model) -> dict:
    """공장 등록 + 가중합산 업데이트"""
    sql = """
        INSERT INTO `FACTORY` (
            partner_id, factory_name, factory_owner, factory_location, operation_status,
            utilization_rate, scope1_emissions, scope2_emissions,
            feoc_raw_material_ratio, trir_safety_rate, note
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """
    params = (
        model.partnerId, model.factoryName, model.factoryOwner, model.factoryLocation,
        model.operationStatus, model.utilizationRate,
        model.scope1Emissions, model.scope2Emissions,
        model.feocRawMaterialRatio, model.trirSafetyRate, model.note,
    )
    factoryId = addKey(sql, params)
    if factoryId:
        # 가중합산 자동 업데이트
        _recalcWeightedSum(model.partnerId)
        return responseModel(True, "공장이 등록되었습니다.", {"factoryId": factoryId})
    return responseModel(False, "공장 등록 실패")


def updateFactoryProcess(factoryId, model) -> dict:
    """공장 수정 + 가중합산 재계산"""
    fieldMap = {
        "factoryName": "factory_name", "factoryOwner": "factory_owner", "factoryLocation": "factory_location",
        "operationStatus": "operation_status", "utilizationRate": "utilization_rate",
        "scope1Emissions": "scope1_emissions", "scope2Emissions": "scope2_emissions",
        "feocRawMaterialRatio": "feoc_raw_material_ratio", "trirSafetyRate": "trir_safety_rate",
        "note": "note",
    }
    setClauses, params = [], []
    data = model.dict(exclude_none=True)
    for camel, snake in fieldMap.items():
        if camel in data:
            setClauses.append(f"`{snake}` = ?")
            params.append(data[camel])
    if not setClauses:
        return responseModel(False, "수정할 데이터가 없습니다.")
    params.append(factoryId)
    sql = f"UPDATE `FACTORY` SET {', '.join(setClauses)} WHERE id = ? AND delete_yn = 0"
    result = save(sql, tuple(params))
    if result:
        # 해당 공장의 partner_id 조회 후 가중합산
        factory = findOne("SELECT partner_id FROM `FACTORY` WHERE id = ?", (factoryId,))
        if factory:
            _recalcWeightedSum(factory["partner_id"])
        return responseModel(True, "공장 정보가 수정되었습니다.", {"factoryId": factoryId})
    return responseModel(False, "수정 실패")


def deleteFactoryProcess(factoryId) -> dict:
    """공장 삭제 + 가중합산 재계산"""
    factory = findOne("SELECT partner_id FROM `FACTORY` WHERE id = ? AND delete_yn = 0", (factoryId,))
    sql = "UPDATE `FACTORY` SET delete_yn = 1 WHERE id = ?"
    result = save(sql, (factoryId,))
    if result and factory:
        _recalcWeightedSum(factory["partner_id"])
        return responseModel(True, "공장이 삭제되었습니다.")
    return responseModel(False, "삭제 실패")


def getFactoryListProcess(partnerId) -> dict:
    """협력사별 공장 목록 + 합산 요약"""
    factories = _getFactoriesByPartnerId(partnerId)
    summary = _getWeightedSummary(partnerId)
    return responseModel(True, "조회 성공", {
        "factories": factories or [],
        "count": len(factories or []),
        "summary": summary,
    })


def getFactoryDetailProcess(factoryId) -> dict:
    sql = "SELECT * FROM `FACTORY` WHERE id = ? AND delete_yn = 0"
    factory = findOne(sql, (factoryId,))
    if not factory:
        return responseModel(False, "공장 정보를 찾을 수 없습니다.")
    return responseModel(True, "조회 성공", {"factory": factory})


# ════════════════════════════════════════════════════════════
# ■ 내부 헬퍼
# ════════════════════════════════════════════════════════════

def _getLatestVersion(partnerId) -> int:
    sql = "SELECT COALESCE(MAX(version), 0) AS v FROM `SELF_ASSESS_ANSWER` WHERE partner_id = ? AND delete_yn = 0"
    row = findOne(sql, (partnerId,))
    return row["v"] if row else 0


def _getVersionList(partnerId) -> list:
    sql = """
        SELECT DISTINCT version, MIN(created_at) AS created_at, COUNT(*) AS answer_count
        FROM `SELF_ASSESS_ANSWER`
        WHERE partner_id = ?
        GROUP BY version ORDER BY version DESC
    """
    return findAll(sql, (partnerId,)) or []


def _getFactoriesByPartnerId(partnerId) -> list:
    sql = """
        SELECT id, factory_name, factory_owner, factory_location, operation_status,
               utilization_rate, scope1_emissions, scope2_emissions,
               feoc_raw_material_ratio, trir_safety_rate, note, created_at
        FROM `FACTORY`
        WHERE partner_id = ? AND delete_yn = 0
        ORDER BY created_at ASC
    """
    return findAll(sql, (partnerId,)) or []


def _getWeightedSummary(partnerId) -> dict:
    """공장별 가중합산 계산"""
    factories = _getFactoriesByPartnerId(partnerId)
    if not factories:
        return {"scope1": 0, "scope2": 0, "feocRatio": 0.0, "trir": 0.0, "factoryCount": 0}
    # [이슈-수정] MariaDB Decimal 타입 → Python float/int 강제 변환
    # DB에서 DECIMAL 컬럼 조회 시 Python Decimal 타입으로 반환되어
    # round(Decimal) → Decimal이 되고, save() 시 BIGINT 컬럼에 Decimal 전달 → 타입 불일치 오류
    totalScope1 = sum(float(f["scope1_emissions"] or 0) * float(f["utilization_rate"] or 0) / 100 for f in factories)
    totalScope2 = sum(float(f["scope2_emissions"] or 0) * float(f["utilization_rate"] or 0) / 100 for f in factories)
    totalFeoc = sum(float(f["feoc_raw_material_ratio"] or 0) * float(f["utilization_rate"] or 0) / 100 for f in factories)
    totalTrir = sum(float(f["trir_safety_rate"] or 0) * float(f["utilization_rate"] or 0) / 100 for f in factories)
    return {
        "scope1": int(round(totalScope1)), "scope2": int(round(totalScope2)),
        "feocRatio": round(totalFeoc, 2), "trir": round(totalTrir, 2),
        "factoryCount": len(factories),
    }


def _recalcWeightedSum(partnerId):
    """공장 가중합산 → COMPANY 테이블 자동 업데이트"""
    summary = _getWeightedSummary(partnerId)
    # [이슈-수정] factoryCount=0 일 때도 COMPANY를 0으로 리셋
    # 기존: factoryCount > 0 일 때만 업데이트 → 마지막 공장 삭제 시 COMPANY 미초기화 버그
    sql = """
        UPDATE `COMPANY`
        SET scope1 = ?, scope2 = ?, feoc_ratio = ?, trir = ?
        WHERE partner_id = ? AND delete_yn = 0
    """
    # [이슈-수정] int/float 명시 변환 — MariaDB Decimal → Python 네이티브 타입 보장
    result = save(sql, (
        int(summary["scope1"]), int(summary["scope2"]),
        float(summary["feocRatio"]), float(summary["trir"]),
        partnerId
    ))
    if result:
        print(f"[가중합산] {partnerId} 업데이트 완료: scope1={summary['scope1']}, scope2={summary['scope2']}, feoc={summary['feocRatio']}, trir={summary['trir']}")
    else:
        print(f"[가중합산] {partnerId} 업데이트 실패")
