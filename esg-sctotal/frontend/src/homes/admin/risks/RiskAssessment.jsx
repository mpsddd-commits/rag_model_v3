import React, { useState } from "react";
import { ESG_INDICATORS } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { Chip, RChip } from "@components/Common/Chip";

const RiskAssessment = () => {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("all"); // "all", 1, 2, 3
  const [riskFilter, setRiskFilter] = useState("all"); // "all", "저위험", "중위험", "고위험"

  // Gather all indicators with their respective tier values
  const allInds = [];
  ["1차 협력사 (합금)", "2차 협력사 (제련)", "3차 협력사 (채굴)"].forEach((key) => {
    let tierVal = 3;
    if (key.indexOf("1차") !== -1) tierVal = 1;
    if (key.indexOf("2차") !== -1) tierVal = 2;

    const items = ESG_INDICATORS[key] || [];
    items.forEach((item) => {
      allInds.push(Object.assign({}, item, { tier: tierVal }));
    });
  });

  // Filter indicators
  const filteredInds = allInds.filter((ind) => {
    // 1. Search filter (match partner name)
    if (search.trim() !== "") {
      const s = search.toLowerCase();
      const partnerMatch = (ind.partner || "").toLowerCase().includes(s);
      if (!partnerMatch) return false;
    }

    // 2. Tier filter
    if (tierFilter !== "all" && ind.tier !== tierFilter) {
      return false;
    }

    // 3. Risk filter (priority mapped to 저위험, 중위험, 고위험)
    let mappedPrio = "저위험";
    if (ind.priority === "Critical") mappedPrio = "고위험";
    else if (ind.priority === "High") mappedPrio = "중위험";
    else if (ind.priority === "Low") mappedPrio = "저위험";

    if (riskFilter !== "all" && mappedPrio !== riskFilter) {
      return false;
    }

    return true;
  });

  const passCount = filteredInds.filter((i) => i.status === "pass").length;
  const warnCount = filteredInds.filter((i) => i.status === "warn").length;
  const failCount = filteredInds.filter((i) => i.status === "fail").length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-black text-gray-900">리스크 현황</h1>
        <p className="text-sm text-gray-400 mt-1">CSDDD/CSRD/UFLPA/IRA/FEOC 기반</p>
      </div>

      {/* 검색 및 필터 패널 */}
      <Card className="p-4 space-y-4 bg-white">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
          {/* 검색창 */}
          <div className="w-full md:w-72 relative">
            <input
              type="text"
              placeholder="협력사명 검색..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); }}
              className="w-full pl-9 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <span className="absolute left-3 top-2.5 text-gray-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
          </div>

          <div className="flex flex-wrap gap-4 items-center">
            {/* 티어 필터 */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-gray-500">계층:</span>
              <div className="flex gap-1.5">
                {[
                  { key: "all", label: "전체" },
                  { key: 1, label: "1차 협력사 (합금)" },
                  { key: 2, label: "2차 협력사 (제련)" },
                  { key: 3, label: "3차 협력사 (채굴)" }
                ].map((opt) => {
                  const active = tierFilter === opt.key;
                  return (
                    <button
                      key={opt.key}
                      onClick={() => { setTierFilter(opt.key); }}
                      className={"px-2.5 py-1 text-xs rounded-lg border font-medium " + (active ? "bg-slate-800 text-white border-slate-800" : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50")}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 리스크 필터 */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-gray-500">리스크:</span>
              <div className="flex gap-1.5">
                {[
                  { key: "all", label: "전체" },
                  { key: "저위험", label: "저위험" },
                  { key: "중위험", label: "중위험" },
                  { key: "고위험", label: "고위험" }
                ].map((opt) => {
                  const active = riskFilter === opt.key;
                  return (
                    <button
                      key={opt.key}
                      onClick={() => { setRiskFilter(opt.key); }}
                      className={"px-2.5 py-1 text-xs rounded-lg border font-medium " + (active ? "bg-slate-800 text-white border-slate-800" : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50")}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* KPI 지표 현황 */}
      <div className="grid grid-cols-3 gap-4">
        {[[ "저위험", passCount, "green" ], [ "중위험", warnCount, "yellow" ], [ "고위험", failCount, "red" ]].map((item, i) => {
          const cls = "bg-white rounded-xl p-4 shadow-sm border-l-4 " + (item[2] === "green" ? "border-green-400" : item[2] === "yellow" ? "border-yellow-400" : "border-red-400");
          return (
            <div key={i} className={cls}>
              <p className="text-xs text-gray-500">{item[0]}</p>
              <p className={"text-3xl font-bold " + (item[2] === "green" ? "text-green-600" : item[2] === "yellow" ? "text-yellow-600" : "text-red-600")}>{item[1]}</p>
            </div>
          );
        })}
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          {filteredInds.length > 0 ? (
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50">
                  {["No.", "협력사", "지표명", "규제", "실적값", "리스크 등급"].map((h, i) => {
                    return <th key={i} className="px-3 py-2 text-left font-bold text-gray-500">{h}</th>;
                  })}
                </tr>
              </thead>
              <tbody>
                {filteredInds.map((ind, i) => {
                  let mappedPrio = "저위험";
                  if (ind.priority === "Critical") mappedPrio = "고위험";
                  else if (ind.priority === "High") mappedPrio = "중위험";
                  else if (ind.priority === "Low") mappedPrio = "저위험";

                  return (
                    <tr key={i} className={"border-t " + (ind.status === "fail" ? "bg-red-50" : ind.status === "warn" ? "bg-yellow-50" : "")}>
                      <td className="px-3 py-2 font-mono text-gray-400">{i + 1}</td>
                      <td className="px-3 py-2 font-bold text-gray-900">{ind.partner}</td>
                      <td className="px-3 py-2 font-medium">{ind.name}</td>
                      <td className="px-3 py-2">{ind.regs.join(", ")}</td>
                      <td className="px-3 py-2 font-mono">{ind.value}</td>
                      <td className="px-3 py-2">
                        <RChip v={mappedPrio} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-10 bg-white rounded-xl text-gray-400 text-sm">
              검색 결과에 해당하는 리스크 현황이 없습니다.
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default RiskAssessment;
