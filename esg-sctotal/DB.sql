-- ╔══════════════════════════════════════════════════════════════════╗
-- ║  Alu-ESG Platform — DB 스키마 v0.5 (통합 최신판)                   ║
-- ║  2026-06-05 · App.jsx (2,629줄) 기준 · 전체 30개 테이블            ║
-- ║                                                                  ║
-- ║  ── 명명 규칙 ──                                                   ║
-- ║  DB  : 테이블=UPPER_CASE / 컬럼=snake_case + COMMENT 필수         ║
-- ║        COLLATE=utf8mb4_unicode_ci (한국어 지원)                    ║
-- ║  BE  : 변수·함수=camelCase / 모듈화(Class 지양) / 파일=소문자 단수   ║
-- ║  FE  : 변수·함수=camelCase / 파일=PascalCase 단수 / 컴포넌트=2회↑   ║
-- ║                                                                  ║
-- ║  ── 변경 이력 ──                                                   ║
-- ║  v0.1 ROLE 매핑, ROLE_MENU_ACCESS, NODE_HISTORY                   ║
-- ║  v0.2 전체 컬럼 COMMENT 추가                                       ║
-- ║  v0.3 SELF_ASSESS_ANSWER/CHECKLIST/RISK_CLASS 신규                ║
-- ║  v0.4 ★ 산림파괴 삭제, risk_level='평가중', 명명 규칙 적용           ║
-- ║      ESG_CHECKLIST·ESG_RISK_CRITERIA 신규 (UPPER_CASE 변환)       ║
-- ║      LICENSE_FILE·SUPPORTING_FILE 신규 (파일 관리)                ║
-- ║      RISK_CLASSIFICATION 제거 (ESG_RISK_CRITERIA와 중복)          ║
-- ║  v0.5 TOKEN 테이블 추가 및 AI_AGENT_RULE 컬럼 추가 및 수정           ║
-- ║                                                                  ║
-- ╚══════════════════════════════════════════════════════════════════╝

CREATE DATABASE IF NOT EXISTS `triplevalues`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `triplevalues`;
SET FOREIGN_KEY_CHECKS = 0;

-- ══════════════════════════════════════════════════════════
-- S1. 사용자 · 권한 · 메뉴접근 · 알림 (5)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `USER`;
CREATE TABLE `USER` (
  id         BIGINT       NOT NULL AUTO_INCREMENT COMMENT '사용자 고유 ID (PK)',
  email      VARCHAR(255) NOT NULL                COMMENT '이메일 (로그인 ID, UNIQUE)',
  password   VARCHAR(255) NOT NULL                COMMENT '비밀번호 (BCrypt 암호화)',
  name       VARCHAR(100) NOT NULL                COMMENT '사용자 이름',
  phone      VARCHAR(20)                          COMMENT '휴대폰 번호',
  delete_yn  TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부 (0=활성, 1=삭제)',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id), UNIQUE KEY uq_email (email)
) ENGINE=InnoDB COMMENT='사용자 마스터';

DROP TABLE IF EXISTS `ROLE`;
CREATE TABLE `ROLE` (
  id          INT         NOT NULL AUTO_INCREMENT COMMENT '권한 고유 ID (PK)',
  role_code   VARCHAR(20) NOT NULL                COMMENT '권한 코드 (OEM/TIER1/TIER2/TIER3)',
  role_name   VARCHAR(50) NOT NULL                COMMENT '권한명 — App.jsx select value (현대모비스/1차 협력사/2차 협력사/3차 협력사)',
  tier_level  TINYINT                             COMMENT '공급망 차수 (0=원청사, 1~3)',
  menu_scope  VARCHAR(30)                         COMMENT '메뉴 범위 (FULL=8메뉴 / PARTNER=2메뉴)',
  description VARCHAR(200)                        COMMENT '권한 설명',
  PRIMARY KEY (id), UNIQUE KEY uq_role_code (role_code)
) ENGINE=InnoDB COMMENT='권한 마스터 — App.jsx 역할 전환 매핑';

INSERT INTO `ROLE` (id,role_code,role_name,tier_level,menu_scope,description) VALUES
(1,'OEM','현대모비스',0,'FULL','원청사 — 8개 메뉴 전체'),
(2,'TIER1','1차 협력사',1,'PARTNER','1차 합금 — 2개 메뉴'),
(3,'TIER2','2차 협력사',2,'PARTNER','2차 제련 — 2개 메뉴'),
(4,'TIER3','3차 협력사',3,'PARTNER','3차 채굴 — 2개 메뉴');

DROP TABLE IF EXISTS `USER_ROLE`;
CREATE TABLE `USER_ROLE` (
  id         BIGINT   NOT NULL AUTO_INCREMENT COMMENT '매핑 ID (PK)',
  user_id    BIGINT   NOT NULL                COMMENT '사용자 ID (FK→USER.id)',
  company_id BIGINT   NOT NULL                COMMENT '기업 ID (FK→COMPANY.id)',
  role_id    INT      NOT NULL                COMMENT '권한 ID (FK→ROLE.id)',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  PRIMARY KEY (id), UNIQUE KEY uq_user_company (user_id,company_id)
) ENGINE=InnoDB COMMENT='사용자-기업-권한 매핑';

DROP TABLE IF EXISTS `ROLE_MENU_ACCESS`;
CREATE TABLE `ROLE_MENU_ACCESS` (
  id         INT         NOT NULL AUTO_INCREMENT COMMENT '접근 권한 ID (PK)',
  role_id    INT         NOT NULL                COMMENT '권한 ID (FK→ROLE.id)',
  menu_key   VARCHAR(30) NOT NULL                COMMENT 'App.jsx pages 키 (dashboard/partner/bom/po/rawmat/risk/inspection/selfassess)',
  menu_label VARCHAR(50) NOT NULL                COMMENT '메뉴 표시명',
  nav_group  VARCHAR(50)                         COMMENT 'NAV 카테고리 그룹명',
  sort_order INT         DEFAULT 0               COMMENT '정렬 순서',
  PRIMARY KEY (id), UNIQUE KEY uq_role_menu (role_id,menu_key)
) ENGINE=InnoDB COMMENT='역할별 메뉴 접근 제어';

INSERT INTO `ROLE_MENU_ACCESS` (role_id,menu_key,menu_label,nav_group,sort_order) VALUES
(1,'dashboard','메인 대시보드','기준 및 협력사 정보',1),(1,'partner','협력사 정보','기준 및 협력사 정보',2),
(1,'bom','BOM 관리','기준 및 협력사 정보',3),(1,'po','PO 관리','구매 및 자재 관리',4),
(1,'rawmat','원자재 관리','구매 및 자재 관리',5),(1,'risk','리스크 현황','실사 및 평가',6),
(1,'inspection','현장 실사','실사 및 평가',7),(1,'selfassess','자가진단 보고서','실사 및 평가',8),
(2,'partner','협력사 정보','협력사 전용 메뉴',1),(2,'rawmat','원자재 관리','협력사 전용 메뉴',2),
(3,'partner','협력사 정보','협력사 전용 메뉴',1),(3,'rawmat','원자재 관리','협력사 전용 메뉴',2),
(4,'partner','협력사 정보','협력사 전용 메뉴',1),(4,'rawmat','원자재 관리','협력사 전용 메뉴',2);

DROP TABLE IF EXISTS `ALARM`;
CREATE TABLE `ALARM` (
  id         BIGINT       NOT NULL AUTO_INCREMENT COMMENT '알림 ID (PK)',
  partner_id VARCHAR(20)  NOT NULL                COMMENT '협력사 코드 (FK→COMPANY.partner_id)',
  type       VARCHAR(30)  NOT NULL                COMMENT '유형 (RISK/URGENT/INSPECT/SELF/INVITE/AI_AGENT)',
  level      VARCHAR(10)                          COMMENT '수준 (fail/warn/info)',
  title      VARCHAR(200) NOT NULL                COMMENT '제목',
  content    TEXT                                 COMMENT '본문',
  path       VARCHAR(300)                         COMMENT '클릭 시 이동 경로',
  meta_json  JSON                                 COMMENT '메타 데이터',
  is_read    TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '읽음 여부 (0=안읽음)',
  delete_yn  TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  PRIMARY KEY (id), KEY idx_user_read (user_id,is_read,delete_yn)
) ENGINE=InnoDB COMMENT='알림 — NotificationPanel / notify.py 호환';

-- ══════════════════════════════════════════════════════════
-- S2. 기업 · 초대 (2) — ★ 산림파괴 컬럼 삭제
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `COMPANY`;
CREATE TABLE `COMPANY` (
  id             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '기업 내부 ID (PK)',
  partner_id     VARCHAR(20)  NOT NULL                COMMENT '협력사 코드 — COMPANIES.id',
  company_name   VARCHAR(200) NOT NULL                COMMENT '기업명 — COMPANIES.company_name',
  short_name     VARCHAR(50)                          COMMENT '약어명 — COMPANIES.short',
  ceo_name       VARCHAR(50)                          COMMENT '대표자명',
  biz_no         VARCHAR(30)                          COMMENT '사업자등록번호',
  founded        DATE                                 COMMENT '설립일',
  address        VARCHAR(500)                         COMMENT '소재지',
  size           VARCHAR(20)                          COMMENT '규모 (대기업/중견/중소)',
  country        VARCHAR(50)                          COMMENT '국가',
  email          VARCHAR(255)                         COMMENT '대표 이메일',
  tier           TINYINT      NOT NULL DEFAULT 0      COMMENT '차수 (0=원청사, 1~3)',
  tier_label     VARCHAR(20)                          COMMENT '차수 표시명',
  parent_id      VARCHAR(20)                          COMMENT '상위 협력사 코드',
  risk_level     VARCHAR(10)                          COMMENT '리스크 등급 (저위험/중위험/고위험)',
  employees      INT                                  COMMENT '임직원 수',
  revenue        BIGINT                               COMMENT '매출액 (백만원)',
  assets         BIGINT                               COMMENT '자산총계 (백만원)',
  scope1         BIGINT                               COMMENT 'Scope 1 GHG (tCO₂e)',
  scope2         BIGINT                               COMMENT 'Scope 2 GHG (tCO₂e)',
  feoc_ratio     DECIMAL(5,2)                         COMMENT 'FEOC 원료 비중 (%)',
  trir           DECIMAL(5,2)                         COMMENT '산업안전 TRIR',
  cmrt           CHAR(1) DEFAULT 'N'                  COMMENT 'CMRT 인증 (Y/N)',
  emat           CHAR(1) DEFAULT 'N'                  COMMENT 'EMAT 인증 (Y/N)',
  iso14001       CHAR(1) DEFAULT 'N'                  COMMENT 'ISO 14001 인증',
  iso45001       CHAR(1) DEFAULT 'N'                  COMMENT 'ISO 45001 인증',
  iatf           CHAR(1) DEFAULT 'N'                  COMMENT 'IATF 16949 인증',
  rba            CHAR(1) DEFAULT 'N'                  COMMENT 'RBA 인증',
  rmap           CHAR(1) DEFAULT 'N'                  COMMENT 'RMAP 인증',
  -- ✗ deforest_yn 삭제 (v0.4)
  -- ✗ deforest_note 삭제 (v0.4)
  cert_count     INT          DEFAULT 0               COMMENT '보유 인증 수',
  status         VARCHAR(20)  DEFAULT 'ACTIVE'        COMMENT '상태',
  is_registered  TINYINT(1)   NOT NULL DEFAULT 0        COMMENT '등록 완료 여부 (0=초대만, 1=등록 완료→재접속 시 2차 인증)',
  delete_yn      TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id), UNIQUE KEY uq_partner (partner_id), KEY idx_tier (tier)
) ENGINE=InnoDB COMMENT='기업 마스터 — E/S/G·re_ratio·산림파괴 삭제';

DROP TABLE IF EXISTS `INVITE`;
CREATE TABLE `INVITE` (
  id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '초대 ID (PK)',
  company_id  BIGINT       NOT NULL                COMMENT '발송 기업 ID',
  user_id     BIGINT       NOT NULL                COMMENT '발송자 ID',
  role_id     INT          NOT NULL                COMMENT '초대 권한 (FK→ROLE.id)',
  project_id  BIGINT                               COMMENT '프로젝트 ID',
  email       VARCHAR(255) NOT NULL                COMMENT '수신자 이메일',
  uuid        VARCHAR(100)                         COMMENT 'JWE 토큰 UUID',
  status      VARCHAR(20)  DEFAULT 'PENDING'       COMMENT '상태 (PENDING/ACCEPTED/EXPIRED)',
  accepted_at DATETIME                             COMMENT '수락 일시',
  expired_at  DATETIME                             COMMENT '만료 일시',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  PRIMARY KEY (id), KEY idx_email (email)
) ENGINE=InnoDB COMMENT='초대 — PartnerInfo';

-- ══════════════════════════════════════════════════════════
-- S3. PO 관리 (1)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `PURCHASE_ORDER`;
CREATE TABLE `PURCHASE_ORDER` (
  id          BIGINT        NOT NULL AUTO_INCREMENT COMMENT 'PO 내부 ID (PK)',
  po_id       VARCHAR(30)   NOT NULL                COMMENT 'PO 번호 — PO_LIST.id',
  partner_id  VARCHAR(20)   NOT NULL                COMMENT '협력사 코드',
  product     VARCHAR(200)  NOT NULL                COMMENT '제품명',
  width       DECIMAL(10,2)                         COMMENT '폭 (mm)',
  length      DECIMAL(10,2)                         COMMENT '길이 (mm)',
  weight      DECIMAL(10,2)                         COMMENT '중량',
  volume      DECIMAL(10,2)                         COMMENT '부피 (L)',
  diameter    DECIMAL(10,2)                         COMMENT '지름 (mm)',
  material    VARCHAR(100)                          COMMENT '재질',
  qty         DECIMAL(12,2) NOT NULL                COMMENT '수량 (ton)',
  unit_price  DECIMAL(12,2)                         COMMENT '단가 (USD)',
  total       DECIMAL(15,2)                         COMMENT '총액 (USD)',
  delivery    DATE                                  COMMENT '납기일',
  status      VARCHAR(20)   DEFAULT 'PENDING'       COMMENT '상태',
  delete_yn   TINYINT(1)    NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id), UNIQUE KEY uq_po (po_id), KEY idx_partner (partner_id)
) ENGINE=InnoDB COMMENT='발주서 — PO_LIST 매핑';

-- ══════════════════════════════════════════════════════════
-- S4. 원자재 · 결재 (4)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `RAW_MATERIAL`;
CREATE TABLE `RAW_MATERIAL` (
  id           BIGINT        NOT NULL AUTO_INCREMENT COMMENT '원자재 ID (PK)',
  raw_id       VARCHAR(30)   NOT NULL                COMMENT '원자재 코드 — RAW_MATERIALS.id',
  po_id        VARCHAR(30)                           COMMENT 'PO 번호',
  partner_id   VARCHAR(20)                           COMMENT '협력사 코드',
  name         VARCHAR(200)  NOT NULL                COMMENT '원자재명',
  width        DECIMAL(10,2)                         COMMENT '폭 (mm)',
  length       DECIMAL(10,2)                         COMMENT '길이 (mm)',
  weight_kg    DECIMAL(10,2)                         COMMENT '중량 (kg)',
  diameter_mm  DECIMAL(10,2)                         COMMENT '지름 (mm)',
  components   TEXT                                  COMMENT '구성 요소 (성분 비율)',
  origin       VARCHAR(200)                          COMMENT '원산지',
  status       VARCHAR(20)   DEFAULT 'DRAFT'         COMMENT '상태',
  requested_at DATETIME                              COMMENT '요청일',
  approved_at  DATETIME                              COMMENT '승인일',
  delete_yn    TINYINT(1)    NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id), UNIQUE KEY uq_raw (raw_id), KEY idx_po (po_id)
) ENGINE=InnoDB COMMENT='원자재 — RAW_MATERIALS 매핑';

DROP TABLE IF EXISTS `RM_TIER_TREE`;
CREATE TABLE `RM_TIER_TREE` (
  id         BIGINT        NOT NULL AUTO_INCREMENT COMMENT '트리 노드 ID (PK)',
  raw_id     VARCHAR(30)   NOT NULL                COMMENT '원자재 코드 (FK)',
  tier       TINYINT       NOT NULL                COMMENT '차수 (1~3)',
  short_name VARCHAR(50)                           COMMENT '협력사 약어명',
  item_name  VARCHAR(200)                          COMMENT '품목명',
  comp       VARCHAR(500)                          COMMENT '성분 표기',
  qty_kg     DECIMAL(12,3)                         COMMENT '수량 (kg)',
  sort_order INT           DEFAULT 0               COMMENT '정렬 순서',
  PRIMARY KEY (id), KEY idx_raw (raw_id)
) ENGINE=InnoDB COMMENT='원자재 공급망 트리';

DROP TABLE IF EXISTS `RM_APPROVAL`;
CREATE TABLE `RM_APPROVAL` (
  approval_id       BIGINT   NOT NULL AUTO_INCREMENT COMMENT '결재 ID (PK)',
  raw_material_id   VARCHAR(30) NOT NULL             COMMENT '원자재 코드 (FK)',
  request_type      VARCHAR(20) NOT NULL DEFAULT 'NORMAL' COMMENT '유형 (NORMAL/URGENT)',
  requester_id      BIGINT                           COMMENT '요청자 ID',
  requester_partner VARCHAR(20)                      COMMENT '요청 협력사',
  request_title     VARCHAR(200)                     COMMENT '제목',
  request_content   TEXT                             COMMENT '내용',
  deadline          DATETIME                         COMMENT '기한',
  approval_yn       CHAR(1)  DEFAULT NULL            COMMENT '승인 (Y/N/NULL)',
  approval_reason   TEXT                             COMMENT '승인/반려 사유',
  approval_dt       DATETIME                         COMMENT '승인 일시',
  approver_id       BIGINT                           COMMENT '승인자 ID',
  approver_partner  VARCHAR(20)                      COMMENT '승인 협력사',
  status            VARCHAR(20) DEFAULT 'PENDING'    COMMENT '상태',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  delete_yn  TINYINT(1) NOT NULL DEFAULT 0           COMMENT '삭제 여부',
  PRIMARY KEY (approval_id), KEY idx_raw (raw_material_id)
) ENGINE=InnoDB COMMENT='원자재 결재 ★ 유지';

DROP TABLE IF EXISTS `RM_APPROVAL_STEP`;
CREATE TABLE `RM_APPROVAL_STEP` (
  step_id       BIGINT   NOT NULL AUTO_INCREMENT COMMENT '단계 ID (PK)',
  approval_id   BIGINT   NOT NULL                COMMENT '결재 ID (FK)',
  step_order    TINYINT  NOT NULL                COMMENT '순서',
  tier_level    TINYINT  NOT NULL                COMMENT '차수 (0~3)',
  partner_id    VARCHAR(20)                      COMMENT '협력사 코드',
  status        VARCHAR(20) DEFAULT 'WAITING'    COMMENT '상태',
  approved_at   DATETIME                         COMMENT '승인 일시',
  approved_by   BIGINT                           COMMENT '승인자 ID',
  reject_reason TEXT                             COMMENT '반려 사유',
  note          TEXT                             COMMENT '비고',
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  PRIMARY KEY (step_id), KEY idx_approval (approval_id)
) ENGINE=InnoDB COMMENT='원자재 결재선 ★ 유지';

-- ══════════════════════════════════════════════════════════
-- S5. BOM (2)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `BOM`;
CREATE TABLE `BOM` (
  id          BIGINT        NOT NULL AUTO_INCREMENT COMMENT 'BOM ID (PK)',
  bom_id      VARCHAR(30)   NOT NULL                COMMENT 'BOM 코드',
  category    VARCHAR(50)                           COMMENT '제품군',
  product     VARCHAR(200)  NOT NULL                COMMENT '제품명',
  item_no     VARCHAR(50)                           COMMENT '품번',
  item_name   VARCHAR(200)                          COMMENT '품목명',
  qty         DECIMAL(12,3)                         COMMENT '수량',
  unit        VARCHAR(20)                           COMMENT '단위',
  weight_g    DECIMAL(10,2)                         COMMENT '중량 (g)',
  supplier_id VARCHAR(20)                           COMMENT '공급사 코드',
  lead_time   INT                                   COMMENT '리드타임 (일)',
  price       DECIMAL(12,2)                         COMMENT '단가',
  components  VARCHAR(500)                          COMMENT '구성 요소',
  status      VARCHAR(20)   DEFAULT 'ACTIVE'        COMMENT '상태',
  delete_yn   TINYINT(1)    NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  PRIMARY KEY (id), UNIQUE KEY uq_bom (bom_id)
) ENGINE=InnoDB COMMENT='BOM — BOM_LIST 매핑';

DROP TABLE IF EXISTS `BOM_TIER_TREE`;
CREATE TABLE `BOM_TIER_TREE` (
  id         BIGINT      NOT NULL AUTO_INCREMENT COMMENT '트리 ID (PK)',
  bom_id     VARCHAR(30) NOT NULL                COMMENT 'BOM 코드 (FK)',
  tier       TINYINT     NOT NULL                COMMENT '차수',
  short_name VARCHAR(50)                         COMMENT '약어명',
  item_name  VARCHAR(200)                        COMMENT '품목명',
  qty_kg     DECIMAL(12,4)                       COMMENT '수량 (kg)',
  sort_order INT         DEFAULT 0               COMMENT '정렬 순서',
  PRIMARY KEY (id), KEY idx_bom (bom_id)
) ENGINE=InnoDB COMMENT='BOM 공급망 트리';

-- ══════════════════════════════════════════════════════════
-- S6. ESG 지표 · 자가진단 · 실사 (3) — ★ forest_risk 삭제
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `ESG_INDICATOR`;
CREATE TABLE `ESG_INDICATOR` (
  id           INT          NOT NULL AUTO_INCREMENT COMMENT '지표 ID (PK)',
  indicator_no INT          NOT NULL                COMMENT '지표 번호 (1~72)',
  tier_scope   VARCHAR(50)  NOT NULL                COMMENT '적용 차수',
  cat          VARCHAR(50)                          COMMENT '카테고리',
  name         VARCHAR(300) NOT NULL                COMMENT '지표명',
  priority     VARCHAR(20)                          COMMENT '우선순위 (Critical/High/Medium)',
  regs         JSON                                 COMMENT '관련 규제 (JSON 배열)',
  actual_value VARCHAR(200)                         COMMENT '실적값',
  status       VARCHAR(10)                          COMMENT '달성 상태 (pass/warn/fail)',
  PRIMARY KEY (id), KEY idx_tier (tier_scope)
) ENGINE=InnoDB COMMENT='ESG 지표 — RiskAssessment';

DROP TABLE IF EXISTS `SELF_ASSESS_REPORT`;
CREATE TABLE `SELF_ASSESS_REPORT` (
  id              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '보고서 ID (PK)',
  report_no       VARCHAR(30)  NOT NULL                COMMENT '보고서 번호',
  partner_name    VARCHAR(200)                         COMMENT '협력사명',
  partner_id      VARCHAR(20)  NOT NULL                COMMENT '협력사 코드',
  tier_scope      VARCHAR(30)                          COMMENT '차수 표시',
  report_year     INT          NOT NULL                COMMENT '보고 연도',
  report_quarter  TINYINT                              COMMENT '분기 (1~4, NULL=연간)',
  status          VARCHAR(20)  DEFAULT 'DRAFT'         COMMENT '상태',
  scope1_text     VARCHAR(50)                          COMMENT 'Scope 1 GHG 텍스트',
  trir_text       VARCHAR(50)                          COMMENT 'TRIR 텍스트',
  forced_labor    VARCHAR(50)                          COMMENT '강제노동 여부',
  feoc_text       VARCHAR(50)                          COMMENT 'FEOC 비중',
  -- ✗ forest_risk 삭제 (v0.4)
  anti_corrupt    VARCHAR(50)                          COMMENT '반부패 정책',
  detail_created_at DATE                               COMMENT '작성일',
  delete_yn       TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id), UNIQUE KEY uq_report (report_no), KEY idx_partner (partner_id)
) ENGINE=InnoDB COMMENT='자가진단 보고서 — re_ratio·forest_risk 삭제';

DROP TABLE IF EXISTS `FIELD_INSPECTION`;
CREATE TABLE `FIELD_INSPECTION` (
  id              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '실사 ID (PK)',
  inspection_no   INT                                  COMMENT '실사 번호',
  target_partner  VARCHAR(200) NOT NULL                COMMENT '대상 협력사',
  inspection_type VARCHAR(50)                          COMMENT '실사 유형',
  phase           VARCHAR(30)                          COMMENT '단계',
  risk_level      VARCHAR(10)                          COMMENT '리스크 등급',
  scheduled_date  DATE                                 COMMENT '예정일',
  actual_date     DATE                                 COMMENT '실시일',
  findings        TEXT                                 COMMENT '발견사항',
  improvements    TEXT                                 COMMENT '개선 요청',
  deadline        DATE                                 COMMENT '기한',
  rba_grade       CHAR(1)                              COMMENT 'RBA 등급',
  csddd_status    VARCHAR(20)                          COMMENT 'CSDDD 이행 상태',
  urgent_action   TEXT                                 COMMENT '긴급 조치',
  action_plan     TEXT                                 COMMENT '개선 계획',
  status          VARCHAR(20)  DEFAULT 'IN_PROGRESS'   COMMENT '상태',
  delete_yn       TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id), KEY idx_target (target_partner)
) ENGINE=InnoDB COMMENT='현장 실사';

-- ══════════════════════════════════════════════════════════
-- S7. 노드 이력 (1) — ★ 산림파괴 컬럼 삭제
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `NODE_HISTORY`;
CREATE TABLE `NODE_HISTORY` (
  id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '이력 ID (PK)',
  partner_id    VARCHAR(20)  NOT NULL                COMMENT '협력사 코드 (FK)',
  record_date   DATE         NOT NULL                COMMENT '기록 일자',
  scope1        BIGINT                               COMMENT 'Scope 1 (tCO₂e)',
  scope2        BIGINT                               COMMENT 'Scope 2 (tCO₂e)',
  feoc_ratio    DECIMAL(5,2)                         COMMENT 'FEOC (%)',
  trir          DECIMAL(5,2)                         COMMENT 'TRIR',
  risk_level    VARCHAR(10)                          COMMENT '리스크 등급',
  -- ✗ deforest_yn 삭제 (v0.4)
  -- ✗ deforest_note 삭제 (v0.4)
  origin        VARCHAR(200)                         COMMENT '원산지',
  name          VARCHAR(200)                         COMMENT '원자재/제품명',
  weight_kg     DECIMAL(12,3)                        COMMENT '중량 (kg)',
  components    VARCHAR(500)                         COMMENT '구성 요소',
  width         DECIMAL(10,2)                        COMMENT '폭 (mm)',
  length        DECIMAL(10,2)                        COMMENT '길이 (mm)',
  diameter_mm   DECIMAL(10,2)                        COMMENT '지름 (mm)',
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  PRIMARY KEY (id), KEY idx_partner_date (partner_id,record_date)
) ENGINE=InnoDB COMMENT='공급망 노드 이력 — 산림파괴 컬럼 삭제';

-- ══════════════════════════════════════════════════════════
-- S8. AI Agent (3)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `AI_AGENT_RULE`;
CREATE TABLE `AI_AGENT_RULE` (
  rule_id         int(11)         NOT NULL          AUTO_INCREMENT               COMMENT '자동 생성 규칙 식별자',
  indicator_no    int(11)         NOT NULL                                       COMMENT '원천 자가진단 문항 지표 번호',
  sub_id          varchar(50)     NOT NULL          DEFAULT 'MAIN'               COMMENT '서브 지표 식별자 (예: PAH, DIOXIN, MAIN)',
  rule_code       varchar(30)     NOT NULL                                       COMMENT '규칙 코드 (예: RULE_040)',
  rule_name       varchar(255)    NOT NULL                                       COMMENT '규칙 이름',
  category        varchar(50)     DEFAULT NULL                                   COMMENT '카테고리 (인권노동, 에너지기후, 공정품질 등)',
  tier_scope      varchar(100)                                                   COMMENT '적용 차수',
  metric_key      varchar(30)     NOT NULL                                       COMMENT '평가 대상 컬럼 키',
  operator        varchar(10)     NOT NULL                                       COMMENT '비교 연산자 규칙',
  threshold_value varchar(255)    NOT NULL                                       COMMENT '통과 임계값/합격기준 범위',
  fail_threshold  varchar(255)    DEFAULT NULL                                   COMMENT '실패 기준 정의 문구',
  severity        varchar(20)     NOT NULL DEFAULT 'WARN'                        COMMENT '리스크 심각도 (CRITICAL, FAIL, WARN)',
  notify_yn       CHAR(1)         DEFAULT 'Y'                                    COMMENT '알림 발송 여부',
  notify_template text            DEFAULT NULL                                   COMMENT '알림 가이드 템플릿',
  regulation      varchar(255)    DEFAULT NULL                                   COMMENT '연계 글로벌 ESG 규제',
  action_required text            DEFAULT NULL                                   COMMENT '불합격 시 권장 조치 방안 명세',
  active_yn       char(1)         DEFAULT 'Y'                                    COMMENT '활성화 여부',
  priority        int(11)         DEFAULT 50                                     COMMENT '알림 표출 우선순위 가중치',
  created_at      timestamp       NOT NULL DEFAULT current_timestamp()           COMMENT '최초 생성 일시',
  updated_at      timestamp       NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정 일시',
  PRIMARY KEY (rule_id),
  UNIQUE KEY uq_indicator_sub (indicator_no, sub_id) -- 💡 indicator_no와 sub_id 조합으로 복합 유니크 키 생성
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 자동 감사 엔진용 마스터 룰셋 규격 테이블';

DROP TABLE IF EXISTS `AI_AGENT_ALERT`;
CREATE TABLE `AI_AGENT_ALERT` (
  alert_id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '알림 ID (PK)',
  rule_id           BIGINT       NOT NULL                COMMENT '룰 ID (FK)',
  partner_id        VARCHAR(20)  NOT NULL                COMMENT '협력사 코드',
  indicator_no      INT                                  COMMENT '지표 번호',
  metric_key        VARCHAR(50)                          COMMENT '평가 키',
  actual_value      VARCHAR(200)                         COMMENT '실제값',
  threshold_value   VARCHAR(100)                         COMMENT '기준값',
  deviation_pct     DECIMAL(8,2)                         COMMENT '편차 (%)',
  severity          VARCHAR(20)  NOT NULL                COMMENT '심각도',
  ai_confidence     DECIMAL(5,2)                         COMMENT 'AI 신뢰도',
  ai_reasoning      TEXT                                 COMMENT 'AI 판단 근거',
  ai_recommendation TEXT                                 COMMENT 'AI 권장 조치',
  alert_title       VARCHAR(200) NOT NULL                COMMENT '알림 제목',
  alert_content     TEXT                                 COMMENT '알림 본문',
  regulation        VARCHAR(100)                         COMMENT '관련 규제',
  status            VARCHAR(20)  DEFAULT 'OPEN'          COMMENT '상태',
  acknowledged_by   VARCHAR(20)                          COMMENT '확인 본사/원청사 코드',
  acknowledged_at   DATETIME                             COMMENT '확인 일시',
  resolved_by       VARCHAR(20)                          COMMENT '해소 본사/원청사 코드',
  resolved_at       DATETIME                             COMMENT '해소 일시',
  resolution_note   TEXT                                 COMMENT '해소 비고',
  alarm_id          BIGINT                               COMMENT 'ALARM 연동 ID',
  detected_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '감지 시각',
  run_id            BIGINT                               COMMENT '실행 로그 ID',
  delete_yn         TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  PRIMARY KEY (alert_id), KEY idx_partner (partner_id), KEY idx_severity (severity)
) ENGINE=InnoDB COMMENT='AI Agent 위반 알림';

DROP TABLE IF EXISTS `AI_AGENT_RUN_LOG`;
CREATE TABLE `AI_AGENT_RUN_LOG` (
  run_id           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '실행 ID (PK)',
  triggered_by     BIGINT                               COMMENT '실행자 ID',
  trigger_type     VARCHAR(30)  DEFAULT 'MANUAL'        COMMENT '실행 유형',
  scope            VARCHAR(30)                          COMMENT '범위',
  scope_target     VARCHAR(50)                          COMMENT '대상',
  rules_evaluated  INT          DEFAULT 0               COMMENT '평가 룰 수',
  alerts_generated INT          DEFAULT 0               COMMENT '생성 알림 수',
  critical_count   INT          DEFAULT 0               COMMENT 'Critical 수',
  fail_count       INT          DEFAULT 0               COMMENT 'Fail 수',
  warn_count       INT          DEFAULT 0               COMMENT 'Warn 수',
  ai_model         VARCHAR(50)                          COMMENT 'AI 모델',
  ai_summary       TEXT                                 COMMENT 'AI 요약',
  started_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '시작 시각',
  ended_at         DATETIME                             COMMENT '종료 시각',
  duration_ms      INT                                  COMMENT '소요 시간 (ms)',
  status           VARCHAR(20)  DEFAULT 'RUNNING'       COMMENT '상태',
  error_message    TEXT                                 COMMENT '에러 메시지',
  PRIMARY KEY (run_id)
) ENGINE=InnoDB COMMENT='AI Agent 실행 로그';

-- ══════════════════════════════════════════════════════════
-- S9. 자가진단 OCR (2) — ★ risk_level DEFAULT '평가중'
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `SELF_ASSESS_ANSWER`;
CREATE TABLE `SELF_ASSESS_ANSWER` (
  id              BIGINT       NOT NULL AUTO_INCREMENT COMMENT '답변 ID (PK)',
  partner_type    VARCHAR(30)  NOT NULL                COMMENT '협력사 구분 (1차/2차/3차-A/3차-B)',
  partner_id      VARCHAR(20)  NOT NULL                COMMENT '협력사 ID (FK→COMPANY.partner_id)',
  indicator_no    INT          NOT NULL                COMMENT '지표 번호 (1~72)',
  category        VARCHAR(50)                          COMMENT '카테고리',
  answer_text     TEXT         NOT NULL                COMMENT '답변 내용 (OCR 추출)',
  risk_level      VARCHAR(10)  DEFAULT '평가중'         COMMENT '리스크 등급 — AI 평가 전 기본값 "평가중"',
  evidence_yn     CHAR(1)      DEFAULT 'N'             COMMENT '증빙 필요 여부',
  source_file_id  BIGINT                               COMMENT '원본 PDF 파일 ID',
  version         INT          NOT NULL DEFAULT 1      COMMENT '자가진단 버전 (파일 재업로드 시 자동 증가)',
  delete_yn       TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id), KEY idx_partner (partner_type,partner_id), KEY idx_indicator (indicator_no)
) ENGINE=InnoDB COMMENT='자가진단 답변 — PDF OCR 추출 (risk_level AI 평가)';

DROP TABLE IF EXISTS `SELF_ASSESS_CHECKLIST`;
CREATE TABLE `SELF_ASSESS_CHECKLIST` (
  id               BIGINT       NOT NULL AUTO_INCREMENT COMMENT '체크리스트 ID (PK)',
  partner_type     VARCHAR(30)  NOT NULL                COMMENT '협력사 구분',
  indicator_no     INT          NOT NULL                COMMENT '지표 번호',
  category         VARCHAR(50)                          COMMENT '카테고리',
  indicator_name   VARCHAR(300) NOT NULL                COMMENT '지표명',
  priority         VARCHAR(20)                          COMMENT '우선순위',
  star_yn          CHAR(1)      DEFAULT 'N'             COMMENT '★ 핵심 지표',
  question         TEXT                                 COMMENT '질문',
  pass_answer      TEXT                                 COMMENT '합격 기준 답변',
  fail_answer      TEXT                                 COMMENT '불합격 기준 답변',
  risk_level       VARCHAR(10)                          COMMENT '리스크 등급 (AI 평가용 유지)',
  evidence_yn      CHAR(1)      DEFAULT 'N'             COMMENT '증빙 필요',
  evidence_list    TEXT                                 COMMENT '증빙 목록',
  action_plan      TEXT                                 COMMENT '대처방안',
  delete_yn        TINYINT(1)   NOT NULL DEFAULT 0      COMMENT '삭제 여부',
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  PRIMARY KEY (id), KEY idx_partner_type (partner_type)
) ENGINE=InnoDB COMMENT='자가진단 체크리스트 마스터';

-- ✗ RISK_CLASSIFICATION 삭제 (v0.4) — ESG_RISK_CRITERIA와 중복되어 제거

-- ══════════════════════════════════════════════════════════
-- S10. ★ v0.4 신규: ESG 실사 체크리스트 + 리스크 기준 (2)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `ESG_CHECKLIST`;
CREATE TABLE `ESG_CHECKLIST` (
  indicator_no        VARCHAR(50)   NOT NULL                  COMMENT 'ESG 평가 지표 고유 번호 (예: ENV-40 또는 순번 코드)',
  category            VARCHAR(100)  NOT NULL                  COMMENT '지표 카테고리 (예: 공정·품질, 환경, 안전 등)',
  indicator_name      VARCHAR(255)  NOT NULL                  COMMENT '지표명 (예: Al 3003 합금 Mn 함량 실측)',
  priority            VARCHAR(20)   NOT NULL DEFAULT 'High'   COMMENT '우선순위 (Critical, High, Medium, Low)',
  is_essential        CHAR(1)       NOT NULL DEFAULT 'N'      COMMENT '★ 중요 지표 여부 (Y/N) - 신규 지표/Critical 불합격 직결 여부',
  question            TEXT          NOT NULL                  COMMENT '실사 항목 질문 및 수치 기준 (BM25 검색 대상)',
  pass_example        TEXT          DEFAULT NULL              COMMENT '합격 판정 기준 예시 또는 가이드라인',
  fail_example        TEXT          DEFAULT NULL              COMMENT '불합격 판정 기준 예시',
  risk_level          VARCHAR(20)   DEFAULT NULL              COMMENT '불합격 시 리스크 등급 (고위험, 중위험, 저위험)',
  evidence_required   CHAR(1)       NOT NULL DEFAULT 'N'      COMMENT '증빙자료 필요 여부 (Y/N)',
  evidence_list       TEXT          DEFAULT NULL              COMMENT '필요 증빙자료 목록 (예: 성분 분석 성적서, 열처리 로그 데이터)',
  action_plan         TEXT          DEFAULT NULL              COMMENT '규격 이탈/불합격 시 협력사 대처 방안 및 조치 지침',
  created_at          TIMESTAMP NULL DEFAULT current_timestamp() COMMENT '지표 등록 일시',
  updated_at          TIMESTAMP NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '지표 수정 일시',
  PRIMARY KEY (`indicator_no`),
  KEY idx_category_indicator (category, indicator_name),
  KEY idx_priority_risk (priority, risk_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='알루미늄 공급망 ESG/품질 실사 체크리스트 마스터';

DROP TABLE IF EXISTS `ESG_RISK_CRITERIA`;
CREATE TABLE `ESG_RISK_CRITERIA` (
  criterion_id      INT(11)       NOT NULL AUTO_INCREMENT   COMMENT '리스크 기준 고유 ID',
  item_name         VARCHAR(100)  NOT NULL                  COMMENT '리스크 평가 분류 항목 (예: 우선순위 기준, 규제 영향 등)',
  high_risk         TEXT          DEFAULT NULL              COMMENT '고위험 (High Risk) 판단 기준 및 사례',
  medium_risk       TEXT          DEFAULT NULL              COMMENT '중위험 (Medium Risk) 판단 기준',
  low_risk          TEXT          DEFAULT NULL              COMMENT '저위험 (Low Risk) 판단 기준',
  created_at        TIMESTAMP     NULL DEFAULT current_timestamp() COMMENT '등록 일시',
  updated_at        TIMESTAMP     NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정 일시',
  PRIMARY KEY (criterion_id),
  UNIQUE KEY ux_item_name (item_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 자가진단 리스크 등급별 분류 기준 마스터';

-- ══════════════════════════════════════════════════════════
-- S11. ★ v0.4 신규: 파일 관리 (2)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `LICENSE_FILE`;
CREATE TABLE `LICENSE_FILE` (
  id         BIGINT(20)   NOT NULL AUTO_INCREMENT           COMMENT '고유ID',
  origin     VARCHAR(255) NOT NULL                          COMMENT '파일명'           COLLATE 'utf8mb4_unicode_ci',
  filename   VARCHAR(255) NOT NULL                          COMMENT '암호화된 파일명'   COLLATE 'utf8mb4_unicode_ci',
  ext        VARCHAR(50)  NOT NULL                          COMMENT '파일타입'         COLLATE 'utf8mb4_unicode_ci',
  dir        VARCHAR(255) NOT NULL                          COMMENT '파일경로'         COLLATE 'utf8mb4_unicode_ci',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP                          COMMENT '등록일자',
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
  delete_yn  TINYINT(1)   NOT NULL DEFAULT '0'              COMMENT '삭제여부',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='사업자등록증 등록 파일 정보 — ocr.py/ocrs.py file.py licenseFile() 연동';

DROP TABLE IF EXISTS `SUPPORTING_FILE`;
CREATE TABLE `SUPPORTING_FILE` (
  id         BIGINT(20)   NOT NULL AUTO_INCREMENT           COMMENT '고유ID',
  partner_id VARCHAR(20)  NOT NULL DEFAULT ''               COMMENT '협력사 코드 (FK→COMPANY.partner_id)',
  file_type  VARCHAR(30)  NOT NULL DEFAULT 'evidence'       COMMENT '파일 구분 (coc/selfassess/evidence/cert)',
  origin     VARCHAR(255) NOT NULL                          COMMENT '파일명'           COLLATE 'utf8mb4_unicode_ci',
  filename   VARCHAR(255) NOT NULL                          COMMENT '암호화된 파일명'   COLLATE 'utf8mb4_unicode_ci',
  ext        VARCHAR(50)  NOT NULL                          COMMENT '파일 타입'        COLLATE 'utf8mb4_unicode_ci',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP                          COMMENT '등록일자',
  updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일자',
  delete_yn  TINYINT(1)   NOT NULL DEFAULT '0'              COMMENT '삭제여부',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_partner_type` (`partner_id`, `file_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='첨부파일 통합 관리 — coc(서약서)/selfassess(자가진단)/evidence(증빙)/cert(인증증빙)';

-- ══════════════════════════════════════════════════════════
-- S12. ★ v0.4 신규: AI 판정 로그 (1)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `AI_LOGS`;
CREATE TABLE `AI_LOGS` (
  id               BIGINT(20)    NOT NULL AUTO_INCREMENT           COMMENT '로그 고유 ID (PK)',
  user_query       TEXT          NOT NULL                          COMMENT '사용자가 입력한 자연어 질문 내용',
  indicator_no     INT(11)       NOT NULL                          COMMENT '매칭된 체크리스트 지표 번호',
  detected_value   DECIMAL(10,4) DEFAULT 0.0000                    COMMENT '사용자 질문에서 추출된 현재 측정 수치',
  threshold_value  DECIMAL(10,4) DEFAULT NULL                      COMMENT 'LLM이 지표 질문에서 추출한 합격 기준 수치',
  judgement_status VARCHAR(20)   NOT NULL                          COMMENT '최종 AI 판정 결과 (합격 / 불합격 / ERROR)',
  judgement_time   DECIMAL(7,3)  NOT NULL DEFAULT 0.000            COMMENT 'AI 판단 처리 소요 시간 (초 단위, 밀리초 포함)',
  execution_time   DECIMAL(7,3)  NOT NULL DEFAULT 0.000            COMMENT 'AI 로직 처리 소요 시간 (초 단위, 밀리초 포함)',
  created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '로그 생성 일시',
  PRIMARY KEY (id),
  KEY idx_indicator_no (indicator_no),
  KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='AI 수치 판정 및 매칭 이력 로그';

-- ══════════════════════════════════════════════════════════
-- S14. ★ 초대 메시지 관리 (1)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `INVITATION_MESSAGE`;
CREATE TABLE `INVITATION_MESSAGE` (
    `id`              BIGINT(20)    NOT NULL AUTO_INCREMENT   COMMENT '고유 ID',
    `role_code`       VARCHAR(20)   NOT NULL                  COMMENT '초대사 권한 코드 (OEM/TIER1/TIER2)',
    `message_subject` VARCHAR(50)   NOT NULL                  COMMENT '협력사별 초대 제목',
    `sent_message`    TEXT          NULL                      COMMENT '초대사 화면 노출용 안내 메시지'      COLLATE 'utf8mb4_unicode_ci',
    `message_content` TEXT          NOT NULL                  COMMENT '피초대 협력사 수신용 메시지 본문'    COLLATE 'utf8mb4_unicode_ci',
    `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP                                    COMMENT '생성일시',
    `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP        COMMENT '수정일시',
    `delete_yn`       TINYINT(1)    NULL     DEFAULT '0'      COMMENT '삭제여부',
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `FK_IM_ROLE` (`role_code`) USING BTREE
) COMMENT='초대 메시지 관리 — 권한별 초대 제목·본문 마스터'
COLLATE='utf8mb4_unicode_ci' ENGINE=InnoDB;


-- ══════════════════════════════════════════════════════════
-- S15. ★ 공장 관리 (1)
-- ══════════════════════════════════════════════════════════

DROP TABLE IF EXISTS `FACTORY`;
CREATE TABLE `FACTORY` (
  id                    BIGINT       NOT NULL AUTO_INCREMENT           COMMENT '공장 고유 ID (PK)',
  partner_id            VARCHAR(20)  NOT NULL                          COMMENT '협력사 코드 (FK→COMPANY.partner_id)',
  factory_name          VARCHAR(200) NOT NULL                          COMMENT '공장명',
  factory_owner         VARCHAR(50)  NOT NULL                          COMMENT '공장 대표자명',
  factory_location      VARCHAR(500)                                   COMMENT '공장 소재지',
  operation_status      VARCHAR(20)  NOT NULL DEFAULT '가동중'          COMMENT '가동 상태 (가동중/중단/폐쇄)',
  utilization_rate      DECIMAL(5,2) NOT NULL DEFAULT 0.00             COMMENT '공장 이용 비율 (%, 기업 내 합계 100%)',
  scope1_emissions      BIGINT       DEFAULT 0                         COMMENT 'Scope 1 GHG 배출량 (tCO₂e)',
  scope2_emissions      BIGINT       DEFAULT 0                         COMMENT 'Scope 2 GHG 배출량 (tCO₂e)',
  feoc_raw_material_ratio DECIMAL(5,2) DEFAULT 0.00                    COMMENT 'FEOC 원료 비중 (%)',
  trir_safety_rate      DECIMAL(5,2) DEFAULT 0.00                      COMMENT 'TRIR 산업안전율',
  note                  TEXT                                           COMMENT '비고',
  delete_yn             TINYINT(1)   NOT NULL DEFAULT 0                COMMENT '삭제 여부',
  created_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '생성일시',
  updated_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
  PRIMARY KEY (id),
  KEY idx_partner (partner_id),
  KEY idx_status (operation_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='공장 정보 — 협력사별 다수 공장 등록, 가중합산 로직 연동';

-- ══════════════════════════════════════════════════════════
-- TOKEN 테이블 (로그인 토큰 관리)
-- [v1.0] 2026-06-04 — partner_id 기준, COMPANY FK 연결
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS `TOKEN` (
    `id`            BIGINT(20)    NOT NULL AUTO_INCREMENT   COMMENT '고유 ID (PK)',
    `partner_id`    VARCHAR(20)   NOT NULL                  COMMENT '협력사 코드 — COMPANY.partner_id',
    `refresh_token` TEXT          NOT NULL                  COMMENT '리프레시 토큰'   COLLATE 'utf8mb4_unicode_ci',
    `uuid`          VARCHAR(100)  NOT NULL                  COMMENT '세션 식별 UUID'  COLLATE 'utf8mb4_unicode_ci',
    `created_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP                 COMMENT '생성일시',
    `updated_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정일시',
    `delete_yn`     TINYINT(1)    NULL     DEFAULT '0'      COMMENT '삭제여부 (0=활성, 1=로그아웃)',
    PRIMARY KEY (`id`) USING BTREE,
    INDEX `IDX_TOKEN_PARTNER` (`partner_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='로그인 토큰 관리 — partner_id 기준 JWT refresh token 저장';

-- 10.14 INVITATION_MESSAGE 더미 데이터 (티어별 초대 메시지)
INSERT INTO `INVITATION_MESSAGE` (`role_code`, `message_subject`, `sent_message`, `message_content`) VALUES
-- 원청사(OEM) → 1차 협력사 초대
('OEM',
 '공급망 맵 초대',
 '원청사(가공·알루미늄 부품 제조) 기준에 부합하는 1차 협력사를 초대해 주시면 됩니다. 알루미늄 합금(Al 3003) 가공, 압연, 열처리 등의 공정 역량을 보유한 기업을 대상으로 해주세요.',
 '귀사는 1차(알루미늄(3003) 합금 주조·가공·압연) 협력사로 초대되었습니다. ESG 공급망 관리 시스템에 접속하셔서 기업 기본 정보, Scope 1·2 GHG 배출량, 글로벌 인증(ISO 14001, IATF 16949 등) 현황, 자가진단 체크리스트 및 관련 증빙 서류를 등록하여 주시기 바랍니다.'
),
-- 1차 협력사(TIER1) → 2차 협력사 초대
('TIER1',
 '협력사 및 공급망 맵 초대',
 '1차 협력사(알루미늄(3003) 합금 주조) 기준에 부합하는 2차 협력사를 초대해 주시면 됩니다. 알루미늄 1차 잉곳 제련, Hall-Héroult 전해 제련 역량을 보유한 기업을 대상으로 해주세요.',
 '귀사는 2차(알루미늄 1차 잉곳 제련·Hall-Héroult 전해 공정) 협력사로 초대되었습니다. ESG 공급망 관리 시스템에 접속하셔서 전력 탄소집약도, PFC 가스 배출량, 에너지 원단위, FEOC 제련소 지분 구조 등의 ESG 항목과 자가진단 체크리스트 및 필요한 증빙 서류를 등록하여 주시기 바랍니다.'
),
-- 2차 협력사(TIER2) → 3차 협력사 초대
('TIER2',
 '협력사 및 공급망 맵 초대',
 '2차 협력사(알루미늄 1차 잉곳 제련) 기준에 부합하는 3차 협력사를 초대해 주시면 됩니다. 보크사이트(Al) 채굴, 알루미나(Al₂O₃) 정제, 망간(Mn) 광석 채굴 역량을 보유한 기업을 대상으로 해주세요.',
 '귀사는 3차(보크사이트(Al) 채굴, 알루미나(Al₂O₃) 정제, 파이롤루사이트(Mn) 채굴) 협력사로 초대되었습니다. ESG 공급망 관리 시스템에 접속하셔서 아동·강제노동 Zero 현황, 산업안전 TRIR, FPIC 원주민 동의, 수질 중금속 농도, 토양 복원 계획 등의 ESG 항목과 자가진단 체크리스트 및 필요한 증빙 서류를 등록하여 주시기 바랍니다.'
);

-- 10.15 기존 COMPANY 더미 데이터 is_registered=1 업데이트
UPDATE `COMPANY` SET is_registered = 1 WHERE delete_yn = 0;


SET FOREIGN_KEY_CHECKS = 1;


-- ══════════════════════════════════════════════════════════
-- SECTION 10. 샘플 데이터
-- ══════════════════════════════════════════════════════════

-- 10.1 COMPANY 
INSERT INTO `COMPANY`
  (partner_id,company_name,short_name,ceo_name,biz_no,founded,address,size,country,email,
   tier,tier_label,parent_id,risk_level,employees,revenue,assets,scope1,scope2,
   feoc_ratio,trir,cmrt,emat,iso14001,iso45001,iatf,rba,rmap,cert_count)
VALUES
('HMOS-001','현대모비스(주)','현대모비스','이규석','264-81-00498','1977-06-24','서울특별시 강남구 테헤란로 521','대기업','대한민국','esg@mobis.co.kr',0,'원청사',NULL,'저위험',46947,572000,665000,180000,105000,3.20,0.38,'Y','N','Y','Y','Y','Y','N',5),
('NOV-001','(주)노벨리스코리아','노벨리스코리아','박진수','128-81-33210','1999-03-15','경기도 시흥시 공단1대로 200','대기업','대한민국','esg@novelis.co.kr',1,'1차 협력사','HMOS-001','저위험',1850,84200,216000,82000,60000,8.10,0.62,'N','N','Y','N','N','N','Y',2),
('NSM-001','(주)남성알루미늄','남성알루미늄','최병훈','310-81-12345','2001-05-10','경상남도 창원시 성산구 공단로 120','중견기업','대한민국','esg@nsm.co.kr',1,'1차 협력사','HMOS-001','저위험',780,38500,95000,45000,32000,6.30,0.78,'N','N','Y','Y','Y','N','N',3),
('KRM-001','(주)케이알엠','케이알엠','이성훈','402-81-45123','2003-07-20','인천광역시 남동구 앵고개로 490','중견기업','대한민국','esg@krm.co.kr',2,'2차 협력사','NOV-001','중위험',420,21800,56400,58000,40000,12.50,1.12,'N','N','Y','N','N','N','N',1),
('HMC-002','현대머티리얼(주)','현대머티리얼','정민수','501-81-67890','2005-09-01','충청남도 아산시 둔포면 산업단지로 55','중소기업','대한민국','esg@hmc.co.kr',2,'2차 협력사','NSM-001','중위험',280,15200,38000,42000,28000,9.80,0.95,'N','N','Y','N','N','N','N',1),
('COM-001','Comilog Gabon S.A.','Comilog','Jean-Pierre M.','GAB-20031200','1962-08-10','Moanda, Haut-Ogooué, Gabon','대기업','가봉','esg@comilog.ga',3,'3차-A','KRM-001','중위험',5200,123000,387000,52000,0,0.00,2.15,'N','N','Y','N','N','N','N',1),
('WIN-001','Windalco Jamaica Ltd.','Windalco','Michael Thompson','JAM-19801045','1980-04-22','Ewarton, Saint Catherine, Jamaica','대기업','자메이카','esg@windalco.jm',3,'3차-B','KRM-001','중위험',3800,89000,224000,68000,0,0.00,1.85,'N','N','N','N','N','N','N',0),
('COD-001','Codelco Norte S.A.','Codelco','Carlos Mendez','CHL-19761009','1976-04-01','Calama, Antofagasta, Chile','대기업','칠레','esg@codelco.cl',3,'3차-C','KRM-001','중위험',18400,482000,1250000,112000,0,0.00,1.42,'N','Y','Y','Y','N','N','N',2),
('EMG-002','Electro Manganese Brasil Ltda','EMG Brasil','Fernando Lima','BRA-20101055','2010-03-20','Pará, Brazil','중견기업','브라질','esg@emg.com.br',3,'3차-A','HMC-002','중위험',2100,65000,180000,38000,0,0.00,1.92,'N','N','Y','N','N','N','N',1),
('ALU-002','Alunorte Alumina S.A.','AluNorte','Rodrigo Ferreira','BRA-19980822','1998-08-22','Barcarena, Pará, Brazil','대기업','브라질','esg@alunorte.com.br',3,'3차-B','HMC-002','중위험',4500,98000,310000,72000,0,0.00,1.65,'N','N','Y','N','N','N','N',1);

-- 10.2 NODE_HISTORY 
INSERT INTO `NODE_HISTORY` (partner_id,record_date,scope1,scope2,feoc_ratio,trir,risk_level,origin,name,weight_kg,components,width,length,diameter_mm) VALUES
('NOV-001','2026-05-15',82000,60000,8.10,0.62,'저위험','울산','Al 3003-H14 튜브',0.22,'Al 97.9%, Mn 1.25%, Cu 0.12%',16,2000,16),
('NOV-001','2026-01-15',79000,57000,7.50,0.57,'저위험','울산','Al 3003 슬라브',1520,'Al 97.9%, Mn 1.25%',600,3000,NULL),
('KRM-001','2026-05-15',58000,40000,12.50,1.12,'중위험','인천','P1020 잉곳',1020,'Al 99.7%',200,800,NULL),
('COM-001','2026-05-15',52000,0,0.00,2.15,'중위험','가봉 Moanda','Mn 정광(MnO₂)',62,'MnO₂ 82%',NULL,NULL,NULL),
('WIN-001','2026-05-15',68000,0,0.00,1.85,'중위험','자메이카','알루미나(Al₂O₃)',2930,'Al₂O₃ 99.4%',NULL,NULL,NULL),
('COD-001','2026-05-15',112000,0,0.00,1.42,'중위험','칠레 Calama','황동광(Cu)',6,'Cu 28%',NULL,NULL,NULL);

-- 10.3 PURCHASE_ORDER
INSERT INTO `PURCHASE_ORDER` (po_id,partner_id,product,width,length,weight,volume,diameter,material,qty,unit_price,total,delivery,status) VALUES
('PO-2025-3003-001','NOV-001','Al 3003-H14 판재',1000,2000,1.2,2.4,NULL,'Al-Mn 합금',45.0,3150,141750,'2025-03-28','COMPLETED'),
('PO-2026-3003-001','NOV-001','Al 3003-H16 박판',1000,NULL,0.5,NULL,NULL,'Al-Mn 합금',55.0,3020,166100,'2026-04-05','CONFIRMED'),
('PO-2026-3003-002','NSM-001','Al 3003-H14 판재',1500,3000,1.5,6.75,NULL,'Al-Mn 합금',42.0,3180,133560,'2026-07-30','PENDING');

-- 10.4 RAW_MATERIAL + RM_TIER_TREE
INSERT INTO `RAW_MATERIAL` (raw_id,po_id,partner_id,name,width,length,weight_kg,diameter_mm,components,origin,status,requested_at,approved_at) VALUES
('RM-001','PO-2025-3003-001','NOV-001','Al 3003 슬라브',600,3000,1520,NULL,'Al 97.9%, Mn 1.25%, Cu 0.12%','KRM-001','APPROVED','2026-01-10','2026-01-15'),
('RM-003','PO-2025-3003-001','KRM-001','전해망간(EMD) — 긴급',NULL,NULL,5,NULL,'Mn 99.7%','COM-001','REQUESTED','2026-01-05',NULL);

INSERT INTO `RM_TIER_TREE` (raw_id,tier,short_name,item_name,comp,qty_kg,sort_order) VALUES
('RM-001',1,'노벨리스코리아','Al 3003 슬라브','Al 97.9%+Mn 1.25%',1520,1),
('RM-001',2,'케이알엠','P1020 잉곳','Al 99.7%',1570,2),
('RM-001',3,'Windalco','알루미나(Al₂O₃)','Al₂O₃ 99.4%',2930,3),
('RM-001',3,'Comilog','Mn 정광(MnO₂)','MnO₂ 82%',62,4),
('RM-001',3,'Codelco','황동광(Cu)','Cu 28%',6,5);

-- 10.5 RM_APPROVAL + STEP
INSERT INTO `RM_APPROVAL` (raw_material_id,request_type,requester_partner,request_title,request_content,deadline,approval_yn,approval_reason,approval_dt,approver_partner,status) VALUES
('RM-001','NORMAL','NOV-001','Al 3003 슬라브 원산지 증명','원산지 및 성분 분석서 승인 요청.','2026-01-20 18:00:00','Y','ASTM B209 만족.','2026-01-15 14:30:00','HMOS-001','APPROVED'),
('RM-003','URGENT','KRM-001','[긴급] 전해망간 FEOC 원산지','IRA 45X D-7 대응.','2026-05-20 18:00:00',NULL,NULL,NULL,NULL,'PENDING');

INSERT INTO `RM_APPROVAL_STEP` (approval_id,step_order,tier_level,partner_id,status,approved_at) VALUES
(1,1,1,'NOV-001','APPROVED','2026-01-13 10:00:00'),
(1,2,0,'HMOS-001','APPROVED','2026-01-15 14:30:00'),
(2,1,3,'COM-001','IN_PROGRESS',NULL),
(2,2,2,'KRM-001','WAITING',NULL),
(2,3,1,'NOV-001','WAITING',NULL),
(2,4,0,'HMOS-001','WAITING',NULL);

-- 10.6 BOM + BOM_TIER_TREE
INSERT INTO `BOM` (bom_id,category,product,item_no,item_name,qty,unit,weight_g,supplier_id,lead_time,price,components,status) VALUES
('BOM-001','열 차폐판','Al 3003-H14 판재 1.5T 400×300mm','HSP-400-300-001','Al 3003-H14 판재 1.5T',1.02,'pcs/pcs',491,'NOV-001',14,280,'Al 97.9%, Mn 1.25%, Cu 0.12%','ACTIVE'),
('BOM-003','휠','Al 3003-H16 판재 3.0T 17인치','WHL-17-001','Al 3003-H16 판재 3.0T',2.15,'pcs/pcs',1347,'NOV-001',21,850,'Al 97.8%, Mn 1.32%, Cu 0.15%','ACTIVE');

INSERT INTO `BOM_TIER_TREE` (bom_id,tier,short_name,item_name,qty_kg,sort_order) VALUES
('BOM-001',1,'노벨리스코리아','Al 3003-H14 판재 1.5T',0.4950,1),
('BOM-001',2,'케이알엠','P1020 잉곳+EMD',0.5120,2),
('BOM-001',3,'Windalco','알루미나(Al₂O₃)',0.9560,3),
('BOM-001',3,'Comilog','Mn 정광(MnO₂)',0.0610,4),
('BOM-001',3,'Codelco','황동광(Cu)',0.0060,5);

-- 10.7 ESG_INDICATOR
INSERT INTO `ESG_INDICATOR` (indicator_no,tier_scope,cat,name,priority,regs,actual_value,status) VALUES
(1,'3차 협력사 (채굴)','인권·노동','아동·강제노동 Zero','Critical',JSON_ARRAY('CSDDD','UFLPA'),'확인서 완비','pass'),
(40,'1차 협력사 (합금)','공정·품질','Mn 함량 1.0~1.5%','Critical',JSON_ARRAY('ASTM'),'1.25%','pass'),
(50,'1차 협력사 (합금)','거버넌스','FEOC Mn·Cu 공급사','Critical',JSON_ARRAY('IRA','FEOC'),'8.1%','warn');

-- 10.8 SELF_ASSESS_REPORT (forest_risk 제거)
INSERT INTO `SELF_ASSESS_REPORT` (report_no,partner_name,partner_id,tier_scope,report_year,report_quarter,status,scope1_text,trir_text,forced_labor,feoc_text,anti_corrupt,detail_created_at) VALUES
('SAR-2025-0001','Comilog Gabon','COM-001','3차-A',2025,NULL,'SUBMITTED','52,000 tCO₂e','2.15 ⚠️','없음 ✅','0%','보유 ✅','2026-01-10'),
('SAR-2025-0003','(주)케이알엠','KRM-001','2차',2025,NULL,'APPROVED','98,000 tCO₂e','1.12 ✅','없음 ✅','12.5% ⚠️','보유 ✅','2025-12-15');

-- 10.9 FIELD_INSPECTION
INSERT INTO `FIELD_INSPECTION` (inspection_no,target_partner,inspection_type,phase,risk_level,scheduled_date,actual_date,findings,improvements,deadline) VALUES
(1,'(주)케이알엠 (2차)','특별현장실사','IMPROVEMENT','중위험','2026-03-15','2026-03-18','FEOC 원료 12.5% 초과','1. FEOC 비해당 소싱\n2. RE 40% 로드맵','2026-09-30'),
(2,'Comilog Gabon (3차-A)','정기현장실사','MONITORING','중위험','2026-01-20','2026-01-23','TRIR 2.15 CSDDD Art.8 초과','1. 산업안전 개선계획서','2026-06-30');

-- 10.10 ALARM
INSERT INTO `ALARM` (partner_id,type,level,title,content,is_read,created_at) VALUES
('NOV-001','RISK','fail','FEOC 초과 — (주)케이알엠','FEOC 원료 12.5% IRA 위험.',0,'2026-05-19 09:15:00'),
('KRM-001','URGENT','warn','긴급 요청 — RM-003','전해망간 원산지 증명서 제출.',0,'2026-05-18 16:30:00'),
('COM-001','SELF','info','자가진단 제출 — Comilog','SAR-2025-0001 제출.',1,'2026-05-17 14:05:00');

-- 10.11 AI_AGENT_RULE (핵심 5개)
INSERT INTO `AI_AGENT_RULE` (indicator_no,rule_code,rule_name,tier_scope,metric_key,operator,threshold_value,unit,severity,regulation,action_required,priority) VALUES
(18,'FEOC_RATIO_ZERO','FEOC 0% 위반','3차-A','feoc_ratio','>','0','%','CRITICAL','IRA/FEOC','대안 소싱 (D+7)',10),
(1,'FORCED_LABOR_ZERO','강제노동 Zero','전체','forced_labor_yn','=','Y','Y/N','CRITICAL','CSDDD/UFLPA','감사 시정 (D+3)',5),
(5,'TRIR_LIMIT','TRIR 한도','3차-A','trir','>','2.0','건/백만h','FAIL','CSDDD','안전 개선 (D+14)',20),
(50,'FEOC_TIER1_LIMIT','1차 FEOC 한도','1차','feoc_ratio','>=','10','%','FAIL','IRA/FEOC','FEOC 비해당 소싱',15),
(15,'MERCURY_ZERO','수은 사용 금지','3차-A','mercury_yn','=','Y','Y/N','CRITICAL','CSDDD/REACH','수은 즉시 중단',5);

-- 10.13 ESG_RISK_CRITERIA
INSERT INTO `ESG_RISK_CRITERIA` (item_name,high_risk,medium_risk,low_risk) VALUES
('우선순위 기준','Critical 불합격 → 반드시 고위험','High 불합격','Medium 불합격 또는 High 경미 편차'),
('규제 영향','CSDDD/UFLPA/FEOC 직접 위반','CSRD/IRA/RoHS 미이행','REACH/CSRD 문서 미비'),
('재무 리스크','매출 5%↑ 손실, 수출 금지','매출 1~5% 손실','매출 1%↓'),
('조치 기한','즉시 (D+3~7)','30일 내 개선 계획','60일 내 보완'),
('점수 환산','0~39점 (Critical 불합격 자동)','40~69점','70~100점'),
('결정 규칙','① Critical 1개라도 불합격 → 고위험 확정\n② FEOC/강제노동 즉시','① High 50%↑ 불합격\n② 40~69점\n③ Critical 전부 합격','① 70%↑ 합격\n② Critical·High 전부 합격\n③ 70점↑');


-- ╔══════════════════════════════════════════════════════════════════╗
-- ║  📊 DB v0.5 통계 — 총 31개 테이블 (UPPER_CASE 통일)                ║
-- ║  ─────────────────────────────────────────────                    ║
-- ║  S1. 사용자·권한·메뉴·알림     : 5개                               ║
-- ║  S2. 기업·초대                 : 2개                               ║
-- ║  S3. PO                        : 1개                               ║
-- ║  S4. 원자재·결재               : 4개                               ║
-- ║  S5. BOM                       : 2개                               ║
-- ║  S6. ESG·자가진단·실사         : 3개                               ║
-- ║  S7. 노드 이력                 : 1개                               ║
-- ║  S8. AI Agent                  : 3개                               ║
-- ║  S9. 자가진단 OCR              : 2개 (risk_level='평가중')         ║
-- ║  S10. ESG 실사 체크리스트      : 2개 (ESG_CHECKLIST/RISK_CRITERIA) ║
-- ║  S11. 파일 관리                : 2개 (LICENSE_FILE/SUPPORTING)     ║
-- ║  S12. ★ AI 판정 로그           : 1개 (AI_LOGS)                    ║
-- ║  S13. ★ 공장관리               : 1개 (FACTORY)                    ║
-- ║  S14. ★ 초대 메시지 관리         : 1개 (INVITATION_MESSAGE)         ║
-- ║  S15. 토큰(로그인 기록)          : 1개 (TOKEN)                      ║
-- ║                                                                  ║
-- ╚══════════════════════════════════════════════════════════════════╝