import React, { useState } from "react";
import { COMPANIES } from "@assets/data/masterData";
import Kpi from "@components/Common/Kpi";
import Card from "@components/Common/Card";
import { RChip } from "@components/Common/Chip";

const MainDashboard = () => {
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const certCount = COMPANIES.reduce((a, c) => a + (c.cert_count || 0), 0);
  const midRisk = COMPANIES.filter((c) => c.risk === "중위험").length;

  const runAi = () => {
    setAiLoading(true);
    setAiResult(null);
    setTimeout(() => {
      setAiLoading(false);
      setAiResult("[AI 분석 완료 (2026-05-19)]\n\n[즉시 조치 (2건)]\n1. 케이알엠 FEOC 12.5% - IRA 세액공제 위험\n2. Comilog 산림파괴 리스크 - EUDR 비준수\n\n[모니터링 (2건)]\n3. Comilog TRIR 2.15 초과\n4. 실사 완료율 94%");
    }, 2000);
  };

  const alerts = [
    { id: 1, type: "고위험", tier: "2차 협력사", company: "(주)케이알엠", message: "FEOC 원료 비중 12.5% 검출 - IRA 45X 세액공제 위험 임계점 초과.", date: "2026-05-28", status: "조사중" },
    { id: 2, type: "고위험", tier: "3차 협력사", company: "Comilog Gabon", message: "산림파괴 리스크 - IUCN 보호지역 인접 및 생물다양성 영향 발생 우려로 복원계획 제출 필요.", date: "2026-05-27", status: "검토대기" },
    { id: 3, type: "중위험", tier: "3차 협력사", company: "Comilog Gabon", message: "TRIR(총기록재해율) 2.15건/백만시간 발생 - CSDDD Art.8 기준(≤2.0) 초과로 모니터링 강화 필요.", date: "2026-05-26", status: "검토중" },
    { id: 4, type: "고위험", tier: "2차 협력사", company: "(주)한성정밀", message: "EU CBAM(탄소국경조정제도) 전환 기간 보고서 내 알루미늄 제품군 내재 탄소 배출량 산정 데이터 누락 발생. 과태료 및 원청사 연대 리스크 '높음'.", date: "2026-05-28", status: "검토대기" },
    { id: 5, type: "중위험", tier: "1차 협력사", company: "노벨리스코리아", message: "공급망 실사 지침(CSDDD) 실사 프로세스 내 하위 3차 재활용 스크랩 공급처의 아동노동/인권 부문 리스크 모니터링 데이터 업데이트 지연.", date: "2026-05-27", status: "조사중" },
    { id: 6, type: "고위험", tier: "3차 협력사", company: "삼우강업", message: "원자재 회수 가공 라인 내 폐수 처리 시설의 화학적 산소요구량(COD) 허용 기준치 일시적 초과 감지. 지자체 환경 규제 위반 우려로 긴급 실사 필요.", date: "2026-05-26", status: "검토대기" }
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-gray-900">ESG 공급망 메인 대시보드</h1>
        <p className="text-sm text-gray-400 mt-1">현대모비스 · 3003 합금 · 원청사→1·2차→3차 · CSRD/CSDDD/Net-Zero 2045</p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Kpi label="공급망 등록 기업" value={(COMPANIES.length - 1) + "개사"} sub={"1차 " + COMPANIES.filter((c) => c.tier === 1).length + "·2차 " + COMPANIES.filter((c) => c.tier === 2).length + "·3차 " + COMPANIES.filter((c) => c.tier === 3).length + "개사"} accent="bg-slate-700" />
        <Kpi label="인증 완료 기업" value={certCount + "개 인증"} sub="공급망 전체 보유 인증 합계" accent="bg-emerald-600" />
        <Kpi label="리스크 관리" value={midRisk + "개사"} sub="중위험 (실사 지표 기준)" accent="bg-amber-500" />
        <Kpi label="Net-Zero 목표" value="2045년" sub="Green Supply 로드맵" accent="bg-[#03a94d]" />
      </div>
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-gray-800 text-sm">AI Agent 리스크 실시간 알림</h3>
          <button onClick={runAi} disabled={aiLoading}
            className={"px-4 py-2 text-xs rounded-lg font-bold " + (aiLoading ? "bg-gray-200 text-gray-400" : "bg-[#03a94d] text-white hover:bg-[#02823b]")}>
            {aiLoading ? "분석 중..." : "AI 전체 분석"}
          </button>
        </div>
        {aiResult && <div className="mb-3 p-3 bg-emerald-50 border border-emerald-150 rounded-xl text-xs text-[#03a94d] whitespace-pre-line">{aiResult}</div>}
        <div className="space-y-3">
          {alerts.map((alert) => {
            const isHigh = alert.type === "고위험";
            const borderCls = isHigh ? "border-red-500 bg-red-50/50" : "border-amber-400 bg-amber-50/50";
            const dotCls = isHigh ? "text-red-500" : "text-amber-500";
            
            return (
              <div key={alert.id} className={"flex items-start gap-3 p-3 rounded-lg border-l-4 " + borderCls}>
                <span className={"text-lg font-black shrink-0 " + dotCls}>●</span>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="font-bold text-sm text-gray-900">{alert.company}</span>
                    <span className="text-xs text-gray-400">·</span>
                    <span className="text-xs text-gray-500">{alert.tier}</span>
                    <span className="text-xs text-gray-400">·</span>
                    <span className="text-xs text-gray-500">{alert.date}</span>
                    <span className="ml-auto text-xs px-2 py-0.5 rounded-full font-bold bg-white border border-gray-200 text-gray-600">{alert.status}</span>
                  </div>
                  <p className="text-xs text-gray-600 leading-relaxed">{alert.message}</p>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

export default MainDashboard;
