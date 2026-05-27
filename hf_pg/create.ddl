CREATE TABLE `esg_checklist` (
  `indicator_no` varchar(50) NOT NULL COMMENT 'ESG 평가 지표 고유 번호 (예: ENV-40 또는 순번 코드)',
  `category` varchar(100) NOT NULL COMMENT '지표 카테고리 (예: 공정·품질, 환경, 안전 등)',
  `indicator_name` varchar(255) NOT NULL COMMENT '지표명 (예: Al 3003 합금 Mn 함량 실측)',
  `priority` varchar(20) NOT NULL DEFAULT 'High' COMMENT '우선순위 (Critical, High, Medium, Low)',
  `is_essential` char(1) NOT NULL DEFAULT 'N' COMMENT '★ 중요 지표 여부 (Y/N) - 신규 지표/Critical 불합격 직결 여부',
  `question` text NOT NULL COMMENT '실사 항목 질문 및 수치 기준 (BM25 검색 대상)',
  `pass_example` text DEFAULT NULL COMMENT '합격 판정 기준 예시 또는 가이드라인',
  `fail_example` text DEFAULT NULL COMMENT '불합격 판정 기준 예시',
  `risk_level` varchar(20) DEFAULT NULL COMMENT '불합격 시 리스크 등급 (고위험, 중위험, 저위험)',
  `evidence_required` char(1) NOT NULL DEFAULT 'N' COMMENT '증빙자료 필요 여부 (Y/N)',
  `evidence_list` text DEFAULT NULL COMMENT '필요 증빙자료 목록 (예: 성분 분석 성적서, 열처리 로그 데이터)',
  `action_plan` text DEFAULT NULL COMMENT '규격 이탈/불합격 시 협력사 대처 방안 및 조치 지침',
  `created_at` timestamp NULL DEFAULT current_timestamp() COMMENT '지표 등록 일시',
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '지표 수정 일시',
  PRIMARY KEY (`indicator_no`),
  KEY `idx_category_indicator` (`category`, `indicator_name`),
  KEY `idx_priority_risk` (`priority`, `risk_level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='알루미늄 공급망 ESG/품질 실사 체크리스트 마스터';

CREATE TABLE `esg_risk_criteria` (
  `criterion_id` int(11) NOT NULL AUTO_INCREMENT COMMENT '리스크 기준 고유 ID',
  `item_name` varchar(100) NOT NULL COMMENT '리스크 평가 분류 항목 (예: 우선순위 기준, 규제 영향 등)',
  `high_risk` text DEFAULT NULL COMMENT '고위험 (High Risk) 판단 기준 및 사례',
  `medium_risk` text DEFAULT NULL COMMENT '중위험 (Medium Risk) 판단 기준',
  `low_risk` text DEFAULT NULL COMMENT '저위험 (Low Risk) 판단 기준',
  `created_at` timestamp NULL DEFAULT current_timestamp() COMMENT '등록 일시',
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '수정 일시',
  PRIMARY KEY (`criterion_id`),
  UNIQUE KEY `ux_item_name` (`item_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ESG 자가진단 리스크 등급별 분류 기준 마스터';