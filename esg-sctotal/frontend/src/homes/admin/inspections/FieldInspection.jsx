import React, { useState } from "react";
import { INSPECTIONS_DATA } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { Chip, RChip } from "@components/Common/Chip";
import { FS } from "@components/Common/Form";

const PhaseChip = (p) => {
  const l = { SCHEDULED: "예정", SELF_ASSESS: "자가진단", ON_SITE: "현장방문", IMPROVEMENT: "개선중", MONITORING: "모니터링", COMPLETED: "완료" };
  const c = { SCHEDULED: "slate", SELF_ASSESS: "blue", ON_SITE: "indigo", IMPROVEMENT: "yellow", MONITORING: "orange", COMPLETED: "green" };
  return <Chip text={l[p.v] || p.v} color={c[p.v] || "slate"} />;
};

const FieldInspection = () => {
  const [openId, setOpenId] = useState(null);
  const [reportId, setReportId] = useState(null);
  const [reportForm, setReportForm] = useState({ rba: "B", csddd: "이행중", score_e: "", score_s: "", score_g: "", urgent: "", action_plan: "" });
  
  const ur = (k) => (e) => {
    setReportForm((p) => {
      const n = Object.assign({}, p);
      n[k] = e.target.value;
      return n;
    });
  };

  const PHASES = ["SCHEDULED", "SELF_ASSESS", "ON_SITE", "IMPROVEMENT", "MONITORING", "COMPLETED"];
  const P_LABEL = { SCHEDULED: "예정", SELF_ASSESS: "자가진단", ON_SITE: "현장방문", IMPROVEMENT: "개선중", MONITORING: "모니터링", COMPLETED: "완료" };

  return (
    <div className="space-y-5">
      <div><h1 className="text-2xl font-black text-gray-900">현장 실사</h1><p className="text-sm text-gray-400 mt-1">현장 방문 확인 후 보고서 작성</p></div>
      {/* 프로세스 흐름 */}
      <Card className="p-4">
        <div className="flex items-center gap-1 overflow-x-auto">
          {PHASES.map((p, i) => {
            const cls = "px-3 py-2 rounded-lg text-xs font-bold border text-center " +
              (p === "COMPLETED" ? "bg-emerald-100 border-emerald-300 text-emerald-700" : "bg-slate-100 border-slate-200 text-slate-700");
            const notLast = i < PHASES.length - 1;
            return (
              <div key={p} className="flex items-center gap-1 shrink-0">
                <div className={cls}><div className="font-black">{i + 1}</div><div>{P_LABEL[p]}</div></div>
                {notLast ? <span className="text-gray-300">{"→"}</span> : null}
              </div>
            );
          })}
        </div>
      </Card>
      {/* 실사 카드 목록 */}
      <div className="space-y-3">
        {INSPECTIONS_DATA.map((ins) => {
          const isOpen = openId === ins.id;
          const hasReport = reportId === ins.id;
          return (
            <Card key={ins.id}>
              <div className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                onClick={() => { setOpenId(isOpen ? null : ins.id); setReportId(null); }}>
                <div className="flex items-center gap-3">
                  <span className={ins.risk === "저위험" ? "text-emerald-500 text-xl font-bold" : "text-amber-500 text-xl font-bold"}>●</span>
                  <div>
                    <p className="font-bold text-sm text-gray-900">{ins.target}</p>
                    <p className="text-xs text-gray-500">{ins.type} · 예정: {ins.scheduled} · 실시: {ins.actual}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <PhaseChip v={ins.phase} />
                  <RChip v={ins.risk} />
                  <span>{isOpen ? "▲" : "▼"}</span>
                </div>
              </div>
              {isOpen && !hasReport && (
                <div className="border-t p-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs font-bold text-gray-700 mb-1">주요 발견사항</p>
                      <p className="text-xs text-gray-600 bg-red-50 rounded p-2 leading-relaxed">{ins.findings}</p>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-gray-700 mb-1">개선 요청 사항</p>
                      <p className="text-xs text-gray-600 bg-yellow-50 rounded p-2 whitespace-pre-line">{ins.improvements}</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500">개선 완료 기한: <b>{ins.deadline}</b></p>
                  <div className="flex gap-2">
                    <button onClick={() => { setReportId(ins.id); }} className="text-xs px-3 py-1.5 bg-[#03a94d] hover:bg-[#02823b] text-white rounded-lg font-bold transition">보고서 작성</button>
                    <button className="text-xs px-3 py-1.5 bg-white border border-gray-200 text-gray-700 rounded-lg">개선 요청 발송</button>
                    <button className="text-xs px-3 py-1.5 bg-white border border-gray-200 text-gray-700 rounded-lg">후속 점검 예약</button>
                  </div>
                </div>
              )}
              {isOpen && hasReport && (
                <div className="border-t p-4 space-y-3">
                  <p className="text-sm font-bold text-gray-800">현장 실사 보고서 작성</p>
                  <div className="grid grid-cols-2 gap-3">
                    <FS label="RBA 행동강령 준수 등급" value={reportForm.rba} onChange={ur("rba")}
                      opts={[{ value: "A", label: "A — 우수" }, { value: "B", label: "B — 양호" }, { value: "C", label: "C — 개선필요" }, { value: "D", label: "D — 긴급조치" }]} />
                    <FS label="CSDDD 이행 상태" value={reportForm.csddd} onChange={ur("csddd")}
                      opts={["이행완료", "이행중", "미이행"]} />
                    <div className="col-span-2">
                      <label className="text-xs font-bold text-gray-600 block mb-1">긴급 조치 필요 사항</label>
                      <textarea rows={2} value={reportForm.urgent} onChange={ur("urgent")}
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                        placeholder="FEOC 원료 비중 초과 — 즉시 대안 소싱 계획 요구..." />
                    </div>
                    <div className="col-span-2">
                      <label className="text-xs font-bold text-gray-600 block mb-1">개선 조치 계획 (Action Plan)</label>
                      <textarea rows={3} value={reportForm.action_plan} onChange={ur("action_plan")}
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                        placeholder="FEOC 비해당 알루미나 대체 소싱처 발굴 (6개월 내)" />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => { setReportId(null); }} className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg">취소</button>
                    <button onClick={() => { alert("실사 보고서 임시저장 완료"); }} className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg">임시저장</button>
                    <button onClick={() => { alert("실사 보고서가 승인 요청되었습니다."); setReportId(null); setOpenId(null); }}
                      className="px-6 py-2 bg-[#03a94d] hover:bg-[#02823b] text-white text-sm rounded-lg font-bold transition">승인 요청</button>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default FieldInspection;
