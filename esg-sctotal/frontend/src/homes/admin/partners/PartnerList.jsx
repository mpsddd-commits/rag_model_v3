import React, { useState } from "react";
/* [이슈] COMPANIES 더미 삭제 — App.jsx에서 apiCompanies prop으로 전달받음 */
/* import { COMPANIES } from "@assets/data/masterData"; */
import Card from "@components/Common/Card";
import { RChip } from "@components/Common/Chip";

/* [이슈] apiCompanies prop 추가 — DB에서 조회된 협력사 목록 수신 */
const PartnerList = ({ userRole, partnerRegistration, setSelPartner, apiCompanies }) => {
  const [selCo, setSelCo] = useState(null);
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");

  /* [이슈] COMPANIES 상수 → apiCompanies prop으로 교체 (빈 배열 fallback) */
  const companies = apiCompanies || [];

  /* [이슈] 필드명 호환 함수 — DB(partner_id/risk_level/short_name/tier_label) vs 더미(id/risk/short/tierLabel) */
  const g = (c, key) => {
    if (key === "id") return c.id || c.partner_id;
    if (key === "risk") return c.risk || c.risk_level || "";
    if (key === "short") return c.short || c.short_name || "";
    if (key === "tierLabel") return c.tierLabel || c.tier_label || "";
    return c[key];
  };

  const isSubTierOf = (company, targetParentId) => {
    let curr = company;
    while (curr && curr.parent_id) {
      if (curr.parent_id === targetParentId) return true;
      /* [이슈] COMPANIES → companies 교체 */
      curr = companies.find((co) => g(co, "id") === curr.parent_id);
    }
    return false;
  };

  /* [이슈] COMPANIES → companies 교체 */
  const filtered = companies.filter((c) => {
    if (c.tier === 0) return false;
    if (userRole === "1차 협력사" && c.tier <= 1) return false;
    if (userRole === "2차 협력사" && c.tier <= 2) return false;
    if (userRole === "3차 협력사" && c.tier <= 3) return false;

    if (userRole !== "현대모비스") {
      let currentPartnerId = "NOV-001";
      if (userRole === "2차 협력사") currentPartnerId = "KRM-001";
      if (userRole === "3차 협력사") currentPartnerId = "COM-001";
      if (!isSubTierOf(c, currentPartnerId)) return false;
    }

    if (search.trim() !== "") {
      const s = search.toLowerCase();
      /* [이슈] c.short → g(c, "short") 필드명 호환 */
      const nameMatch = c.company_name.toLowerCase().includes(s) || g(c, "short").toLowerCase().includes(s);
      if (!nameMatch) return false;
    }
    if (tierFilter !== "all" && c.tier !== tierFilter) return false;
    /* [이슈] c.risk → g(c, "risk") 필드명 호환 */
    if (riskFilter !== "all" && g(c, "risk") !== riskFilter) return false;
    return true;
  });

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-black text-gray-900">협력사 정보</h1>
          <p className="text-sm text-gray-400 mt-1">협력사 마스터 · 계층별 직접 연결</p>
        </div>
      </div>

      {/* 검색 및 필터 패널 — 디자인 원본 유지 */}
      <Card className="p-4 space-y-4 bg-white">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
          <div className="w-full md:w-72 relative">
            <input type="text" placeholder="협력사명 검색..." value={search}
              onChange={(e) => { setSearch(e.target.value); }}
              className="w-full pl-9 pr-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-[#03a94d]" />
            <span className="absolute left-3 top-2.5 text-gray-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
          </div>
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-gray-500">계층:</span>
              <div className="flex gap-1.5">
                {[{ key: "all", label: "전체" }, { key: 1, label: "1차 협력사 (합금)" }, { key: 2, label: "2차 협력사 (제련)" }, { key: 3, label: "3차 협력사 (채굴)" }].map((opt) => {
                  const active = tierFilter === opt.key;
                  return (<button key={opt.key} onClick={() => { setTierFilter(opt.key); }}
                    className={"px-2.5 py-1 text-xs rounded-lg border font-medium " + (active ? "bg-slate-800 text-white border-slate-800" : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50")}>{opt.label}</button>);
                })}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-gray-500">리스크:</span>
              <div className="flex gap-1.5">
                {[{ key: "all", label: "전체" }, { key: "저위험", label: "저위험" }, { key: "중위험", label: "중위험" }, { key: "고위험", label: "고위험" }].map((opt) => {
                  const active = riskFilter === opt.key;
                  return (<button key={opt.key} onClick={() => { setRiskFilter(opt.key); }}
                    className={"px-2.5 py-1 text-xs rounded-lg border font-medium " + (active ? "bg-slate-800 text-white border-slate-800" : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50")}>{opt.label}</button>);
                })}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="space-y-3">
        {filtered.length > 0 ? (
          filtered.map((c) => {
            const canOpenAccordion = userRole !== "현대모비스";
            /* [이슈] c.id → g(c, "id") 필드명 호환 */
            const cId = g(c, "id");
            const isOpen = canOpenAccordion && selCo && g(selCo, "id") === cId;
            const displayCo = c;

            return (
              /* [이슈] key={c.id} → key={cId} */
              <Card key={cId} className="overflow-hidden">
                <div className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
                  onClick={() => {
                    if (userRole === "현대모비스") {
                      /* [이슈] 호환 필드 추가하여 PartnerDetail에 전달 */
                      setSelPartner(Object.assign({}, displayCo, {
                        id: cId, partner_id: cId,
                        risk: g(displayCo, "risk"), short: g(displayCo, "short"),
                        tierLabel: g(displayCo, "tierLabel")
                      }));
                    } else {
                      setSelCo(isOpen ? null : displayCo);
                    }
                  }}>
                  <div className="flex items-center gap-3">
                    <div className={"w-2 h-10 rounded-full " + (displayCo.tier === 0 ? "bg-slate-800" : displayCo.tier === 1 ? "bg-[#03a94d]" : displayCo.tier === 2 ? "bg-[#0ea5e9]" : "bg-[#8b5cf6]")} />
                    <div>
                      <p className="font-bold text-gray-900">{displayCo.company_name}</p>
                      {/* [이슈] displayCo.tierLabel → g(displayCo, "tierLabel"), displayCo.id → cId */}
                      <p className="text-xs text-gray-500">{g(displayCo, "tierLabel")} · {displayCo.country} · {cId}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* [이슈] displayCo.risk → g(displayCo, "risk") */}
                    <RChip v={g(displayCo, "risk")} />
                    <span className="text-gray-400">{userRole === "현대모비스" ? "→" : (isOpen ? "▲" : "▼")}</span>
                  </div>
                </div>
                {isOpen && (
                  <div className="border-t p-4 space-y-4">
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      {[["대표자명", displayCo.ceo_name], ["사업자등록번호", displayCo.biz_no], ["설립일", displayCo.founded], ["대표 이메일 주소", displayCo.email || "-"], ["기업 규모", displayCo.size], ["국가", displayCo.country]].map((pair, i) => {
                        return <div key={i}><span className="text-xs text-gray-400">{pair[0]}</span><p className="font-medium text-gray-800">{pair[1]}</p></div>;
                      })}
                      <div className="col-span-2"><span className="text-xs text-gray-400">소재지</span><p className="font-medium text-gray-800">{displayCo.address}</p></div>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                      {[["Scope 1", (displayCo.scope1 || 0).toLocaleString() + " tCO₂e"], ["Scope 2", (displayCo.scope2 || 0).toLocaleString() + " tCO₂e"], ["FEOC 비중", (displayCo.feoc_ratio || 0) + "%"], ["TRIR", displayCo.trir || 0]].map((pair, i) => {
                        return <div key={i} className="bg-gray-50 rounded p-2 text-xs"><p className="text-gray-400">{pair[0]}</p><p className="font-bold text-gray-900">{pair[1]}</p></div>;
                      })}
                    </div>
                    <div className="border-t pt-3 space-y-2">
                      <p className="text-xs font-bold text-gray-700">글로벌 인증 및 이니셔티브 준수 현황</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                        {[["ISO 14001 환경경영", displayCo.iso14001], ["ISO 45001 안전보건", displayCo.iso45001], ["IATF 16949 자동차 품질", displayCo.iatf], ["RBA 책임 비즈니스", displayCo.rba], ["CMRT 분쟁광물 보고", displayCo.cmrt], ["RMAP 책임 광물 보증", displayCo.rmap], ["EMAT 전기차 광물 추적", displayCo.emat]].map((pair, i) => {
                          const val = pair[1] || "N";
                          const isY = val === "Y";
                          return (<div key={i} className="bg-gray-50 rounded p-2 text-xs flex flex-col justify-between">
                            <p className="text-gray-400 font-semibold mb-1">{pair[0]}</p>
                            <span className={"inline-block text-[10px] px-1.5 py-0.5 rounded font-bold border " + (isY ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-slate-100 text-slate-500 border-slate-200")}>{isY ? "Y (준수)" : "N (미준수)"}</span>
                          </div>);
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
            {/* [이슈] API 미연결 시 안내 메시지 추가 */}
            {companies.length === 0 ? "API 서버에서 데이터를 불러오는 중입니다..." : "검색 결과에 해당하는 협력사가 없습니다."}
          </div>
        )}
      </div>
    </div>
  );
};

export default PartnerList;
