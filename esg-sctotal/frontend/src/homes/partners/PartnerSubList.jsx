import React, { useState } from "react";
/* [이슈] companies 더미 삭제 — App.jsx에서 apiCompanies prop으로 전달받음 */
/* import { COMPANIES } from "@assets/data/masterData"; */
import Card from "@components/Common/Card";
import { Chip, RChip } from "@components/Common/Chip";

/* [이슈] apiCompanies prop 추가 */
const PartnerSubList = ({ userRole, partnerRegistration, apiCompanies }) => {
  const [selCo, setSelCo] = useState(null);
  /* [이슈] companies → apiCompanies prop 사용 */
  const companies = apiCompanies || [];
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");

  const isSubTierOf = (company, targetParentId) => {
    let curr = company;
    while (curr && curr.parent_id) {
      if (curr.parent_id === targetParentId) {
        return true;
      }
      curr = companies.find((co) => (co.id || co.partner_id) === curr.parent_id);
    }
    return false;
  };

  const filtered = companies.filter((c) => {
    if (c.tier === 0) return false;

    // 하위 티어 필터링 제약
    if (userRole === "1차 협력사" && c.tier <= 1) return false;
    if (userRole === "2차 협력사" && c.tier <= 2) return false;
    if (userRole === "3차 협력사" && c.tier <= 3) return false;

    // 연결된 하위 공급망 노드 필터링
    let currentPartnerId = "NOV-001";
    if (userRole === "2차 협력사") currentPartnerId = "KRM-001";
    if (userRole === "3차 협력사") currentPartnerId = "COM-001";

    if (!isSubTierOf(c, currentPartnerId)) {
      return false;
    }

    // 검색 필터
    if (search.trim() !== "") {
      const s = search.toLowerCase();
      const nameMatch = c.company_name.toLowerCase().includes(s) || ((c.short || c.short_name || "")).toLowerCase().includes(s);
      if (!nameMatch) return false;
    }

    // 티어 필터
    if (tierFilter !== "all" && c.tier !== tierFilter) {
      return false;
    }

    // 리스크 필터
    if (riskFilter !== "all" && (c.risk || c.risk_level || "") !== riskFilter) {
      return false;
    }

    return true;
  });

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-black text-gray-900">하위 협력사 정보 조회</h1>
          <p className="text-sm text-gray-400 mt-1">하위 계층 협력사 정보 및 준수 현황</p>
        </div>
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
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-[#03a94d]"
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
                      onClick={() => setTierFilter(opt.key)}
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
                      onClick={() => setRiskFilter(opt.key)}
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

      <div className="space-y-3">
        {filtered.length > 0 ? (
          filtered.map((c) => {
            /* [이슈] selCo.id → partner_id 호환 */
            const isOpen = selCo && (selCo.id || selCo.partner_id) === (c.id || c.partner_id);
            /* [이슈] c.tierLabel → tier_label 호환 */
            let regKey = c.tierLabel || c.tier_label;
            /* [이슈] c.short → short_name 호환 */
            if (c.tier === 3 && (c.short || c.short_name) === "Comilog") {
              regKey = "3차 협력사";
            }
            const regData = partnerRegistration ? partnerRegistration[regKey] : null;
            let displayCo = c;
            if (regData) {
              displayCo = Object.assign({}, c, {
                company_name: regData.companyName || c.company_name,
                ceo_name: regData.ceoName || c.ceo_name,
                biz_no: regData.bizNo || c.biz_no,
                founded: regData.founded || c.founded,
                email: regData.email || c.email,
                size: regData.size || c.size,
                country: regData.country || c.country,
                address: regData.address || c.address,
                scope1: regData.scope1 || c.scope1,
                scope2: regData.scope2 || c.scope2,
                feoc_ratio: regData.feocRatio || c.feoc_ratio,
                trir: regData.trir || c.trir,
                iso14001: regData.iso14001 || c.iso14001,
                iso45001: regData.iso45001 || c.iso45001,
                iatf: regData.iatf || c.iatf,
                rba: regData.rba || c.rba,
                cmrt: regData.cmrt || c.cmrt,
                rmap: regData.rmap || c.rmap,
                emat: regData.emat || c.emat
              });
            }

            return (
              <Card
                /* [이슈] key={displayCo.id} → partner_id 호환 */
                key={displayCo.id || displayCo.partner_id} className="overflow-hidden">
                <div className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                  onClick={() => setSelCo(isOpen ? null : displayCo)}>
                  <div className="flex items-center gap-3">
                    <div className={"w-2 h-10 rounded-full " + (displayCo.tier === 0 ? "bg-slate-800" : displayCo.tier === 1 ? "bg-[#03a94d]" : displayCo.tier === 2 ? "bg-[#0ea5e9]" : "bg-[#8b5cf6]")} />
                    <div>
                      <p className="font-bold text-gray-900">{displayCo.company_name}</p>
                      {/* [이슈] displayCo.id → partner_id 호환 */}
                      <p className="text-xs text-gray-500">{(displayCo.tierLabel || displayCo.tier_label || "")} · {displayCo.country} · {displayCo.id || displayCo.partner_id}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <RChip v={(displayCo.risk || displayCo.risk_level || "중위험")} />
                    <span className="text-gray-400">
                      {isOpen ? "▲" : "▼"}
                    </span>
                  </div>
                </div>
                {isOpen && (
                  <div className="border-t p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      {[[ "대표자명", displayCo.ceo_name ], [ "사업자등록번호", displayCo.biz_no ], [ "설립일", displayCo.founded ], [ "대표 이메일 주소", displayCo.email || "-" ], [ "기업 규모", displayCo.size ], [ "국가", displayCo.country ]].map((pair, i) => {
                        return <div key={i}><span className="text-xs text-gray-400">{pair[0]}</span><p className="font-medium text-gray-800">{pair[1]}</p></div>;
                      })}
                      <div className="col-span-2"><span className="text-xs text-gray-400">소재지</span><p className="font-medium text-gray-800">{displayCo.address}</p></div>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                      {[
                        [ "Scope 1", (displayCo.scope1 || 0).toLocaleString() + " tCO₂e" ],
                        [ "Scope 2", (displayCo.scope2 || 0).toLocaleString() + " tCO₂e" ],
                        [ "FEOC 비중", displayCo.feoc_ratio + "%" ],
                        [ "TRIR", displayCo.trir ]
                      ].map((pair, i) => {
                        return <div key={i} className="bg-gray-50 rounded p-2 text-xs"><p className="text-gray-400">{pair[0]}</p><p className="font-bold text-gray-900">{pair[1]}</p></div>;
                      })}
                    </div>
                    {/* 글로벌 인증 및 이니셔티브 준수 현황 */}
                    <div className="border-t pt-3 space-y-2">
                      <p className="text-xs font-bold text-gray-700">글로벌 인증 및 이니셔티브 준수 현황</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                        {[
                          [ "ISO 14001 환경경영", displayCo.iso14001 ],
                          [ "ISO 45001 안전보건", displayCo.iso45001 ],
                          [ "IATF 16949 자동차 품질", displayCo.iatf ],
                          [ "RBA 책임 비즈니스", displayCo.rba ],
                          [ "CMRT 분쟁광물 보고", displayCo.cmrt ],
                          [ "RMAP 책임 광물 보증", displayCo.rmap ],
                          [ "EMAT 전기차 광물 추적", displayCo.emat ]
                        ].map((pair, i) => {
                          const val = pair[1] || "N";
                          const isY = val === "Y";
                          const badgeCls = "inline-block text-[10px] px-1.5 py-0.5 rounded font-bold border " +
                            (isY ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-slate-100 text-slate-500 border-slate-200");
                          return (
                            <div key={i} className="bg-gray-50 rounded p-2 text-xs flex flex-col justify-between">
                              <p className="text-gray-400 font-semibold mb-1">{pair[0]}</p>
                              <div>
                                <span className={badgeCls}>{isY ? "Y (준수)" : "N (미준수)"}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            );
          })
        ) : (
          <div className="text-center py-10 bg-white rounded-xl border border-gray-150 text-gray-400 text-sm">
            검색 결과에 해당하는 협력사가 없습니다.
          </div>
        )}
      </div>
    </div>
  );
};

export default PartnerSubList;
