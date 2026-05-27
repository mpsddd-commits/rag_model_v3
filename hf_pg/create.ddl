CREATE TABLE `esg_checklist` (
    `indicator_no` VARCHAR(50) NOT NULL COMMENT 'ESG 평가 지표 번호 (예: ENV-01, SOC-02)',
    `indicator_name` VARCHAR(255) NOT NULL COMMENT 'ESG 평가 지표명 (예: 온실가스 배출량 관리, 작업장 안전)',
    `question` TEXT NOT NULL COMMENT '실사 항목 질문 및 수치 기준 (BM25 검색 대상)',
    `pass_example` TEXT DEFAULT NULL COMMENT '합격 판정 기준 예시 또는 가이드라인',
    `fail_example` TEXT DEFAULT NULL COMMENT '불합격 판정 기준 예시',
    `action_plan` TEXT DEFAULT NULL COMMENT '규격 이탈/불합격 시 협력사 대처 방안 및 조치 지침',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '지표 등록 일시',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '지표 수정 일시',
    PRIMARY KEY (`indicator_no`),
    -- 지표명으로 필터링하거나 정렬할 때 성능 향상을 위한 인덱스
    INDEX `idx_indicator_name` (`indicator_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='알루미늄 공급망 ESG 실사 체크리스트 마스터';


💡 DDL 설계 포인트 설명
indicator_no (기본키, PK)

VARCHAR(50)으로 설정하여 ENV-01, GOV-03 같은 표준화된 지표 코드를 기본키로 사용할 수 있게 했습니다. 만약 순번(1, 2, 3...) 형태의 자동 증가 PK가 필요하시다면 INT AUTO_INCREMENT로 변경하셔도 좋습니다.

question, action_plan (TEXT 타입)

파이썬 코드에서 BM25 알고리즘이 문장 전체를 토큰화하여 단어를 추출하는 핵심 필드입니다. 글자 수 제한이 있는 VARCHAR 대신 대용량 텍스트를 저장할 수 있는 TEXT 타입을 채택했습니다.

인코딩 설정 (utf8mb4)

알루미늄 공정 부호, 단위 기호(예: ㎡, ℃, ㎥)나 이모지, 특수 기호 등이 입력되더라도 깨지지 않고 완벽하게 저장되도록 MariaDB 표준인 utf8mb4 문자셋을 지정했습니다.

CREATE TABLE `ai_logs` (
    `log_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '로그 일련번호',
    `user_query` TEXT NOT NULL COMMENT '사용자가 입력한 실제 질문 문장',
    `indicator_no` VARCHAR(50) NOT NULL COMMENT '매칭된 ESG 지표 번호 (FK 역할)',
    `detected_value` DOUBLE DEFAULT NULL COMMENT '사용자 질문에서 추출된 현재 수치',
    `threshold_value` DOUBLE DEFAULT NULL COMMENT '체크리스트의 통과 기준 수치',
    `judgement_status` VARCHAR(50) NOT NULL COMMENT '판정 결과 (합격 / 불합격 / ERROR)',
    `logged_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '로그 기록 일시',
    PRIMARY KEY (`log_id`),
    CONSTRAINT `fk_logs_indicator` FOREIGN KEY (`indicator_no`) REFERENCES `esg_checklist` (`indicator_no`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI RAG 실사 진단 및 수치 비교 로그';

하단부에서 AI 판정 결과 및 사용자의 실제 질문 수치를 저장하는 ai_logs 테이블의 DDL도 함께 필요하실 것 같아 첨부.