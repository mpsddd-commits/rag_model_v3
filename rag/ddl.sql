CREATE TABLE AI_LOGS (
    log_id INT AUTO_INCREMENT PRIMARY KEY,          -- 로그 고유 고유 ID (자동 증가)
    partner_name VARCHAR(100) NOT NULL,             -- 협력사명
    user_query TEXT NOT NULL,                       -- 사용자 질의 내용
    ai_evaluation LONGTEXT NOT NULL,                -- AI가 최종 생성한 감사 리포트 (Markdown)
    judgement_status VARCHAR(50) NOT NULL,          -- 온톨로지 가드레일 최종 판정 상태 (합격/불합격 등)
    risk_chain_json LONGTEXT,                       -- 공급망 리스크 전파 트리 데이터 (JSON 스트링)
    ai_model VARCHAR(100) NOT NULL,                 -- 추론에 사용된 Ollama LLM 모델명 (추가 🌟)
    inference_duration DECIMAL(5, 2) NOT NULL,      -- AI 추론 순수 소요 시간 (초 단위, 예: 3.45초) (추가 🌟)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 로그 생성 및 판단 시간
    -- 조회 성능 최적화를 위한 인덱스 추가
    INDEX idx_partner_status (partner_name, judgement_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE `SELF_ASSESS_CHECKLIST` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '체크리스트 ID (PK)',
  `partner_type` varchar(30) NOT NULL COMMENT '협력사 구분',
  `indicator_no` int(11) NOT NULL COMMENT '지표 번호',
  `category` varchar(50) DEFAULT NULL COMMENT '카테고리',
  `indicator_name` varchar(300) NOT NULL COMMENT '지표명',
  `priority` varchar(20) DEFAULT NULL COMMENT '우선순위',
  `star_yn` char(1) DEFAULT 'N' COMMENT '★ 핵심 지표',
  `question` text DEFAULT NULL COMMENT '질문',
  `pass_answer` text DEFAULT NULL COMMENT '합격 기준 답변',
  `fail_answer` text DEFAULT NULL COMMENT '불합격 기준 답변',
  `risk_level` varchar(10) DEFAULT NULL COMMENT '리스크 등급 (AI 평가용 유지)',
  `evidence_yn` char(1) DEFAULT 'N' COMMENT '증빙 필요',
  `evidence_list` text DEFAULT NULL COMMENT '증빙 목록',
  `action_plan` text DEFAULT NULL COMMENT '대처방안',
  `delete_yn` tinyint(1) NOT NULL DEFAULT 0 COMMENT '삭제 여부',
  `created_at` datetime NOT NULL DEFAULT current_timestamp() COMMENT '생성일시',
  PRIMARY KEY (`id`),
  KEY `idx_partner_type` (`partner_type`),
  UNIQUE KEY `uq_indicator_no` (`indicator_no`) -- 지표 번호 고유 식별을 위해 권장
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='자가진단 체크리스트 마스터';

CREATE TABLE `ESG_RISK_CRITERIA` (
  `criterion_id` int(11) NOT NULL AUTO_INCREMENT COMMENT '리스크 기준 고유 ID',
  `item_name` varchar(100) NOT NULL COMMENT '리스크 평가 분류 항목 (예: 우선순위 기준, 규제 영향 등)',
  `high_risk` text DEFAULT NULL COMMENT '고위험 (High Risk) 판단 기준 및 사례',
  `medium_risk` text DEFAULT NULL COMMENT '중위험 (Medium Risk) 판단 기준',
  `low_risk` text DEFAULT NULL COMMENT '저위험 (Low Risk) 판단 기준',
  `created_at` timestamp NULL DEFAULT current_timestamp() COMMENT '등록 일시',
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정 일시',
  PRIMARY KEY (`criterion_id`),
  UNIQUE KEY `ux_item_name` (`item_name`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 자가진단 리스크 등급별 분류 기준 마스터';
