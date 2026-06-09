import React, { useState, useEffect } from "react";
import { COMPANIES, NODE_HISTORY, RAW_MATERIALS } from "@assets/data/masterData";
import { RChip } from "@components/Common/Chip";
import Card from "@components/Common/Card";

const SupplyChainMap = (p) => {
  const [sel, setSel] = useState(null);
  const [selectedYear, setSelectedYear] = useState("");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [selectedDay, setSelectedDay] = useState("");

  var rCls = { "저위험": "border-green-400 bg-green-50", "중위험": "border-yellow-400 bg-yellow-50", "고위험": "border-red-400 bg-red-50" };

  // 세트별 구성
  var set1 = {
    tier1: COMPANIES.find(c => c.id === "NOV-001"),
    tier2: COMPANIES.find(c => c.id === "KRM-001"),
    tier3: COMPANIES.filter(c => c.tier === 3 && c.parent_id === "KRM-001"),
  };
  var set2 = {
    tier1: COMPANIES.find(c => c.id === "NSM-001"),
    tier2: COMPANIES.find(c => c.id === "HMC-002"),
    tier3: COMPANIES.filter(c => c.tier === 3 && c.parent_id === "HMC-002"),
  };
  var origin = COMPANIES.find(c => c.tier === 0);

  var isSet1Related = true;
  var isSet2Related = true;

  if (p?.filterPartnerId) {
    var set1Ids = ["NOV-001", "KRM-001", "COM-001", "WIN-001", "COD-001"];
    var set2Ids = ["NSM-001", "HMC-002", "EMG-002", "ALU-002"];

    isSet1Related = set1Ids.includes(p.filterPartnerId);
    isSet2Related = set2Ids.includes(p.filterPartnerId);
  }

  // 노드 선택(sel) 또는 부모의 approvedAt 변경 시 선택 날짜를 초기화
  useEffect(() => {
    if (sel) {
      var historyList = NODE_HISTORY.filter(h => h.partner_id === sel.id);
      if (historyList.length > 0) {
        var baseDate = p.approvedAt;
        var hasBaseDate = historyList.some(h => h.date === baseDate);

        if (!hasBaseDate || !baseDate) {
          var dates = historyList.map(h => h.date).sort().reverse();
          baseDate = dates[0];
        }

        var parts = baseDate.split("-");
        setSelectedYear(parts[0]);
        setSelectedMonth(parts[1]);
        setSelectedDay(parts[2]);
      } else {
        setSelectedYear("");
        setSelectedMonth("");
        setSelectedDay("");
      }
    } else {
      setSelectedYear("");
      setSelectedMonth("");
      setSelectedDay("");
    }
  }, [sel, p.approvedAt]);

  // 연쇄 날짜 업데이트 핸들러
  const handleYearChange = (e) => {
    var y = e.target.value;
    setSelectedYear(y);

    var historyList = NODE_HISTORY.filter(h => h.partner_id === sel.id);
    var months = [...new Set(
      historyList
        .filter(h => h.date.startsWith(y + "-"))
        .map(h => h.date.split("-")[1])
    )].sort().reverse();

    var nextM = months[0] || "";
    setSelectedMonth(nextM);

    if (nextM) {
      var days = [...new Set(
        historyList
          .filter(h => h.date.startsWith(y + "-" + nextM + "-"))
          .map(h => h.date.split("-")[2])
      )].sort().reverse();
      setSelectedDay(days[0] || "");
    } else {
      setSelectedDay("");
    }
  };

  const handleMonthChange = (e) => {
    var m = e.target.value;
    setSelectedMonth(m);

    var historyList = NODE_HISTORY.filter(h => h.partner_id === sel.id);
    var days = [...new Set(
      historyList
        .filter(h => h.date.startsWith(selectedYear + "-" + m + "-"))
        .map(h => h.date.split("-")[2])
    )].sort().reverse();
    setSelectedDay(days[0] || "");
  };

  var historyList = sel ? NODE_HISTORY.filter(h => h.partner_id === sel.id) : [];
  var targetDate = (selectedYear && selectedMonth && selectedDay) ? (selectedYear + "-" + selectedMonth + "-" + selectedDay) : null;
  var matchedHistory = targetDate ? historyList.find(h => h.date === targetDate) : null;

  // matchedHistory가 있다면 sel의 필드들을 history 데이터로 오버라이드하여 렌더링에 사용
  var displayCo = sel;
  if (sel && matchedHistory) {
    displayCo = Object.assign({}, sel, {
      scope1: matchedHistory.scope1,
      scope2: matchedHistory.scope2,
      feoc_ratio: matchedHistory.feoc_ratio,
      trir: matchedHistory.trir,
      risk: matchedHistory.risk,
      deforest_yn: matchedHistory.deforest_yn,
      deforest_note: matchedHistory.deforest_note
    });
  }

  // Cascading select options
  var years = [...new Set(historyList.map(h => h.date.split("-")[0]))].sort().reverse();
  var months = [...new Set(
    historyList
      .filter(h => h.date.startsWith(selectedYear + "-"))
      .map(h => h.date.split("-")[1])
  )].sort().reverse();
  var days = [...new Set(
    historyList
      .filter(h => h.date.startsWith(selectedYear + "-" + selectedMonth + "-"))
      .map(h => h.date.split("-")[2])
  )].sort().reverse();

  const CompBox = (bp) => {
    var c = bp.c;
    if (!c) return null;
    var isActive = sel && sel.id === c.id;
    var baseCls = "cursor-pointer rounded-xl border-2 p-2.5 transition hover:shadow-md text-center " +
      (rCls[c.risk] || "border-gray-200") + (isActive ? " ring-2 ring-[#03a94d]" : "");
    return (
      <div className={baseCls} style={{ minWidth: "130px" }} onClick={() => setSel(isActive ? null : c)}>
        <div className={"text-white text-xs font-bold px-2 py-0.5 rounded-full mb-1 " +
          (c.tier === 0 ? "bg-slate-800" : c.tier === 1 ? "bg-[#03a94d]" : c.tier === 2 ? "bg-[#0ea5e9]" : "bg-[#8b5cf6]")}>
          {c.tierLabel}
        </div>
        <p className="text-xs font-bold text-gray-800 leading-tight">{c.short}</p>
        <p className="text-xs text-gray-400">{c.country}</p>
        <div className="flex justify-center mt-1"><RChip v={c.risk} /></div>
      </div>
    );
  };

  // 3차 그룹 (수평 연결선 포함)
  const Tier3Group = (gp) => {
    var comps = gp.comps || [];
    if (comps.length === 0) return null;
    return (
      <div className="flex flex-col items-center">
        {/* 수직선 (2차→3차) */}
        <div className="w-px h-8 bg-emerald-400" />
        {/* 수평 연결선 + 3차 세트 */}
        <div className="relative flex items-start">
          {/* 수평선 전체 너비 */}
          <div className="absolute top-0 left-0 right-0 h-px bg-emerald-300" style={{ top: "0px" }} />
          {comps.map((c, i) => {
            return (
              <div key={c.id} className="flex flex-col items-center mx-3">
                <div className="w-px h-8 bg-emerald-300" />
                <CompBox c={c} />
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const SupplySet = (sp) => {
    var t1 = sp.t1;
    var t2 = sp.t2;
    var t3 = sp.t3 || [];
    return (
      <div className="flex flex-col items-center">
        <CompBox c={t1} />
        <div className="w-px h-8 bg-emerald-400" />
        <CompBox c={t2} />
        <Tier3Group comps={t3} />
      </div>
    );
  };

  return (
    <div className="space-y-5">
      {!p?.hideTitle && (
        <div>
          <h1 className="text-2xl font-black text-gray-900">공급망 맵</h1>
          <p className="text-sm text-gray-400 mt-1">원청사 → 1차 → 2차 → 3차 트리 구조 · 세트 2개</p>
        </div>
      )}
      <Card className="p-6 overflow-x-auto">
        <div className="flex flex-col items-center min-w-max">
          <div className="relative flex items-start justify-center">
            {/* 세트 1 */}
            {isSet1Related && (
              <div className={isSet2Related ? "mx-8" : ""}>
                <SupplySet t1={set1.tier1} t2={set1.tier2} t3={set1.tier3} />
              </div>
            )}
            {/* 세트 2 */}
            {isSet2Related && (
              <div className={isSet1Related ? "mx-8" : ""}>
                <SupplySet t1={set2.tier1} t2={set2.tier2} t3={set2.tier3} />
              </div>
            )}
          </div>
        </div>
        {/* 범례 */}
        <div className="flex gap-4 mt-5 justify-center flex-wrap text-xs text-gray-500">
          {[["bg-[#03a94d]", "1차"], ["bg-[#0ea5e9]", "2차"], ["bg-[#8b5cf6]", "3차"]].map((item, i) => {
            return <span key={i} className="flex items-center gap-1"><span className={"w-3 h-3 rounded-full " + item[0]} />{item[1]}</span>;
          })}
        </div>
      </Card>
      {sel && (
        <Card className="p-5 border border-[#03a94d]/20">
          {/* 과거 이력 조회 셀렉트 박스 */}
          {historyList.length > 0 && (
            <div className="mb-4 p-3 bg-gray-50 rounded-xl border border-gray-200/60">
              <p className="text-xs text-gray-500 font-bold mb-1.5 flex items-center gap-1">
                <span>💡</span> 정보 조회하기: 이력 시점의 연도, 월, 일을 선택하시면 해당 일자의 상세 정보를 즉시 조회할 수 있습니다.
              </p>
              <div className="flex gap-2">
                <div className="flex-1">
                  <select value={selectedYear} onChange={handleYearChange}
                    className="w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#03a94d]">
                    {years.map(y => <option key={y} value={y}>{y}년</option>)}
                  </select>
                </div>
                <div className="flex-1">
                  <select value={selectedMonth} onChange={handleMonthChange}
                    className="w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#03a94d]">
                    {months.map(m => <option key={m} value={m}>{parseInt(m)}월</option>)}
                  </select>
                </div>
                <div className="flex-1">
                  <select value={selectedDay} onChange={e => setSelectedDay(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-[#03a94d]">
                    {days.map(d => <option key={d} value={d}>{parseInt(d)}일</option>)}
                  </select>
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-between items-start mb-3">
            <div>
              <h3 className="font-black text-lg">{displayCo.company_name}</h3>
              <p className="text-sm text-gray-500">{displayCo.tierLabel} · {displayCo.country}</p>
              {displayCo.deforest_yn === "Y" && <p className="text-xs text-green-700 mt-1">🌲 {displayCo.deforest_note}</p>}
            </div>
            <div className="shrink-0 ml-4">
              <RChip v={displayCo.risk} />
            </div>
          </div>
          {(() => {
            var activeMat;
            var isBomMode = !!p.bom;
            var weightLabel = isBomMode ? "계산 중량" : "중량";
            var formattedWeight = "-";

            if (isBomMode) {
              var bom = p.bom;
              var W1 = (bom.weight_g * bom.qty) / 1000; // in kg

              var partnerWeight = 0;
              var materialName = "";
              var origin = displayCo.country;
              var components = "";
              var width = null;
              var length = null;
              var diameter = null;

              var parsedDims = { width: null, length: null, diameter: null };
              var prod = bom.product || "";
              if (prod.includes("400×300mm")) {
                parsedDims.width = 400; parsedDims.length = 300;
              } else if (prod.includes("600×400mm")) {
                parsedDims.width = 600; parsedDims.length = 400;
              } else if (prod.includes("D432mm") || prod.includes("17인치")) {
                parsedDims.diameter = 432;
              } else if (prod.includes("D457mm") || prod.includes("18인치")) {
                parsedDims.diameter = 457;
              } else if (prod.includes("Ø12")) {
                parsedDims.diameter = 12; parsedDims.length = 3000;
              } else if (prod.includes("Ø25")) {
                parsedDims.diameter = 25; parsedDims.length = 3000;
              } else if (prod.includes("Ø8")) {
                parsedDims.diameter = 8; parsedDims.length = 2000;
              } else if (prod.includes("Ø16")) {
                parsedDims.diameter = 16; parsedDims.length = 2000;
              }

              if (displayCo.id === "NOV-001" || displayCo.id === "NSM-001") {
                partnerWeight = W1;
                materialName = bom.item_name;
                components = bom.components || "Al 97.9%, Mn 1.25%, Cu 0.12%";
                width = parsedDims.width;
                length = parsedDims.length;
                diameter = parsedDims.diameter;
              } else if (displayCo.id === "KRM-001" || displayCo.id === "HMC-002") {
                partnerWeight = W1 * 0.979;
                materialName = "P1020 알루미늄 잉곳";
                components = "Al 99.7%";
                width = 200;
                length = 800;
              } else if (displayCo.id === "COM-001" || displayCo.id === "EMG-002") {
                partnerWeight = W1 * 0.0125;
                materialName = "망간 정광(MnO₂)";
                components = "MnO₂ 82%, Fe 5%";
              } else if (displayCo.id === "WIN-001") {
                partnerWeight = W1 * 0.0073;
                materialName = "알루미나(Al₂O₃)";
                components = "Al₂O₃ 99.4%";
              } else if (displayCo.id === "ALU-002") {
                partnerWeight = W1 * 0.0085;
                materialName = "알루미나(Al₂O₃)";
                components = "Al₂O₃ 99.3%";
              } else if (displayCo.id === "COD-001") {
                partnerWeight = W1 * 0.0012;
                materialName = "황동광(Cu)";
                components = "Cu 28%, Fe 30%";
              }

              if (matchedHistory) {
                activeMat = {
                  company_id: displayCo.id,
                  name: matchedHistory.name || materialName,
                  width: matchedHistory.width !== undefined ? matchedHistory.width : width,
                  length: matchedHistory.length !== undefined ? matchedHistory.length : length,
                  diameter_mm: matchedHistory.diameter_mm !== undefined ? matchedHistory.diameter_mm : diameter,
                  weight_kg: partnerWeight,
                  components: matchedHistory.components || components,
                  origin: matchedHistory.origin || (origin === "대한민국" ? (displayCo.id === "NOV-001" ? "울산" : "창원") : origin)
                };
              } else {
                activeMat = {
                  company_id: displayCo.id,
                  name: materialName,
                  width: width,
                  length: length,
                  diameter_mm: diameter,
                  weight_kg: partnerWeight,
                  components: components,
                  origin: origin === "대한민국" ? (displayCo.id === "NOV-001" ? "울산" : "창원") : origin
                };
              }

              if (activeMat.weight_kg < 0.1) {
                formattedWeight = activeMat.weight_kg.toFixed(5).replace(/\.?0+$/, "") + " kg";
              } else {
                formattedWeight = activeMat.weight_kg.toFixed(3).replace(/\.?0+$/, "") + " kg";
              }
            } else {
              var mat = RAW_MATERIALS.find(r => r.partner_id === displayCo.id);
              var dummyMaterials = {
                "COM-001": { name: "망간 정광(MnO₂)", width: null, length: null, weight_kg: 62, diameter_mm: null, components: "MnO₂ 82%, Fe 5%", origin: "가봉 Moanda" },
                "WIN-001": { name: "알루미나(Al₂O₃)", width: null, length: null, weight_kg: 2930, diameter_mm: null, components: "Al₂O₃ 99.4%", origin: "자메이카 Ewarton" },
                "COD-001": { name: "황동광(Cu)", width: null, length: null, weight_kg: 6, diameter_mm: null, components: "Cu 28%, Fe 30%", origin: "칠레 Calama" },
                "HMC-002": { name: "알루미늄 잉곳 P1020", width: 200, length: 800, weight_kg: 25, diameter_mm: null, components: "Al 99.7%", origin: "브라질 (AluNorte)" },
                "EMG-002": { name: "Mn 정광", width: null, length: null, weight_kg: 59, diameter_mm: null, components: "MnO₂ 80%", origin: "브라질 Pará" },
                "ALU-002": { name: "알루미나", width: null, length: null, weight_kg: 1890, diameter_mm: null, components: "Al₂O₃ 99.3%", origin: "브라질 Barcarena" }
              };

              var baseMat = mat || dummyMaterials[displayCo.id] || {
                name: "일반 알루미늄 슬라브", width: 500, length: 2500, weight_kg: 1200, diameter_mm: null, components: "Al 99.5%", origin: "대한민국"
              };

              if (matchedHistory) {
                activeMat = {
                  company_id: displayCo.id,
                  name: matchedHistory.name || baseMat.name,
                  width: matchedHistory.width !== undefined ? matchedHistory.width : baseMat.width,
                  length: matchedHistory.length !== undefined ? matchedHistory.length : baseMat.length,
                  diameter_mm: matchedHistory.diameter_mm !== undefined ? matchedHistory.diameter_mm : baseMat.diameter_mm,
                  weight_kg: matchedHistory.weight_kg !== undefined ? matchedHistory.weight_kg : baseMat.weight_kg,
                  components: matchedHistory.components || baseMat.components,
                  origin: matchedHistory.origin || baseMat.origin
                };
              } else {
                activeMat = Object.assign({ company_id: displayCo.id }, baseMat);
              }

              formattedWeight = activeMat.weight_kg ? activeMat.weight_kg.toLocaleString() + " kg" : "-";
            }

            const targetCompany = (displayCo && displayCo.id === activeMat.company_id) ? displayCo : COMPANIES.find(co => co.id === activeMat.company_id);

            return (
              <div className="grid grid-cols-2 gap-3 mt-4 text-xs border-t pt-4">
                {[
                  ["원자재명", activeMat.name || "-"],
                  ["원산지", activeMat.origin || "-"],
                  [weightLabel, formattedWeight],
                  ["폭", activeMat.width ? activeMat.width + " mm" : "-"],
                  ["길이", activeMat.length ? activeMat.length + " mm" : "-"],
                  ["지름", activeMat.diameter_mm ? activeMat.diameter_mm + " mm" : "-"],
                  ["Scope 1", targetCompany?.scope1 ? targetCompany.scope1.toLocaleString() + " tCO₂eq" : "-"],
                  ["Scope 2", targetCompany?.scope2 ? targetCompany.scope2.toLocaleString() + " tCO₂eq" : "-"],
                  ["FEOC 비중", targetCompany?.feoc_ratio !== undefined ? targetCompany.feoc_ratio + " %" : "-"],
                  ["TRIR", targetCompany?.trir !== undefined ? targetCompany.trir + " 건/백만h" : "-"],
                ].map((pair, i) => {
                  return <div key={i} className="bg-gray-50 rounded p-2"><p className="text-xs text-gray-400">{pair[0]}</p><p className="text-sm font-bold text-gray-900">{pair[1]}</p></div>;
                })}
                <div className="col-span-2 bg-gray-50 rounded p-2">
                  <p className="text-xs text-gray-400">구성 요소</p>
                  <p className="text-sm font-bold text-gray-900">{activeMat.components || "-"}</p>
                </div>
              </div>
            );
          })()}
        </Card>
      )}
    </div>
  );
};

export default SupplyChainMap;
