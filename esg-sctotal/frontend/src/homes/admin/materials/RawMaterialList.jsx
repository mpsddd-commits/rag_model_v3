import React, { useState } from "react";
import { RAW_MATERIALS, COMPANIES } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { SChip } from "@components/Common/Chip";
import SupplyChainMap from "@components/UI/SupplyChainMap";

const TierTree = ({ rows = [] }) => {
  const tierBg = { 1: "bg-[#03a94d]", 2: "bg-[#0ea5e9]", 3: "bg-[#8b5cf6]" };
  return (
    <div className="space-y-1 py-2">
      {rows.map((row, i) => {
        const bg = tierBg[row.tier] || "bg-gray-400";
        return (
          <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 border border-gray-100"
            style={{ marginLeft: (row.tier - 1) * 16 + "px" }}>
            <span className={"text-white text-xs font-bold px-1.5 py-0.5 rounded " + bg}>{row.tier}차</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-gray-800">{row.short}</p>
              <p className="text-xs text-gray-500">{row.item}</p>
              {row.comp && <p className="text-xs text-gray-400">{row.comp}</p>}
            </div>
            {row.qty_kg && <span className="text-xs font-mono font-bold text-[#03a94d] shrink-0">{row.qty_kg} kg</span>}
          </div>
        );
      })}
    </div>
  );
};

const RawMaterialList = ({ userRole, setIsRequestingRM, setUrgentRM }) => {
  const [openPO, setOpenPO] = useState(null);   // PO ID 드롭다운 열림
  const [selRM, setSelRM] = useState(null);   // 행 클릭 → 상세
  const [search, setSearch] = useState("");     // 협력사명 검색
  const [statusFilter, setStatusFilter] = useState("all"); // 상태 필터

  // Filter RAW_MATERIALS based on search and statusFilter
  const filteredRM = RAW_MATERIALS.filter((r) => {
    // 하위 티어 필터링 제약 (선택된 협력사의 아래 단계 티어 원자재 정보만 보이도록)
    const partnerCo = COMPANIES.find((c) => c.id === r.partner_id);
    const tier = partnerCo ? partnerCo.tier : 0;
    if (userRole === "1차 협력사" && tier <= 1) return false;
    if (userRole === "2차 협력사" && tier <= 2) return false;
    if (userRole === "3차 협력사" && tier <= 3) return false;

    if (search.trim() !== "") {
      const s = search.toLowerCase();
      const company = COMPANIES.find((c) => c.id === r.partner_id);
      const companyName = company ? company.company_name.toLowerCase() : "";
      const companyShort = company ? company.short.toLowerCase() : "";
      const partnerId = r.partner_id.toLowerCase();

      const match = companyName.indexOf(s) !== -1 || companyShort.indexOf(s) !== -1 || partnerId.indexOf(s) !== -1;
      if (!match) return false;
    }
    if (statusFilter !== "all" && r.status !== statusFilter) {
      return false;
    }
    return true;
  });

  if (selRM) {
    return (
      <div className="space-y-5">
        <div className="flex items-start justify-between">
          <div><h1 className="text-2xl font-black text-gray-900">원자재 상세</h1></div>
          <button onClick={() => { setSelRM(null); }} className="px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 transition">← 목록으로</button>
        </div>
        <Card className="p-5 bg-white">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-lg text-gray-900">{selRM.name}</h3>
            <SChip s={selRM.status} type="rawmat" />
          </div>
          <div className="grid grid-cols-2 gap-3 mb-4">
            {[[ "PO ID", selRM.po_id ], [ "협력사", COMPANIES.find((c) => c.id === selRM.partner_id)?.company_name || selRM.partner_id ], [ "폭(mm)", selRM.width || "-" ], [ "길이(mm)", selRM.length || "-" ], [ "중량(kg)", selRM.weight_kg || "-" ], [ "지름(mm)", selRM.diameter_mm || "-" ], [ "원산지", selRM.origin ], [ "구성요소", selRM.components ], [ "요청일", selRM.requested_at ], [ "승인일", selRM.approved_at || "-" ]].map((pair, i) => {
              return <div key={i} className="bg-gray-50 rounded p-2"><p className="text-xs text-gray-400 font-semibold">{pair[0]}</p><p className="text-sm font-bold text-gray-900 mt-0.5">{pair[1]}</p></div>;
            })}
          </div>

          <div className="mt-6 border-t pt-6">
            <p className="text-sm font-bold text-gray-700 mb-3">공급망 맵 트리 (연결된 공급망만 표시)</p>
            <SupplyChainMap hideTitle={true} filterPartnerId={selRM.partner_id} approvedAt={selRM.approved_at} />
          </div>
          {selRM.status === "APPROVED" && (
            <div className="mt-4 flex gap-2 border-t pt-4">
              <button onClick={() => { setUrgentRM(selRM); setSelRM(null); }}
                className="px-4 py-2 text-white text-sm rounded-lg font-bold transition hover:opacity-90 shadow-sm"
                style={{ backgroundColor: "#03a94d" }}>요청하기</button>
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div><h1 className="text-2xl font-black text-gray-900">원자재 관리</h1><p className="text-sm text-gray-400 mt-1">PO ID 클릭 → 공급망 트리 드롭다운 / 행 클릭 → 상세</p></div>
        <button
          onClick={() => {
            setIsRequestingRM(true);
          }}
          className="px-4 py-2 text-white text-sm rounded-lg font-bold hover:opacity-90 transition shadow-sm"
          style={{ backgroundColor: "#03a94d" }}
        >
          + 원자재 요청
        </button>
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

          {/* 상태 필터 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-500">상태:</span>
            <div className="flex gap-1.5 flex-wrap">
              {[
                { key: "all", label: "전체" },
                { key: "APPROVED", label: "승인 완료" },
                { key: "PENDING", label: "승인 대기" },
                { key: "IN_PROGRESS", label: "진행중" },
                { key: "REJECTED", label: "반려" },
                { key: "REQUESTED", label: "요청중" }
              ].map((opt) => {
                const active = statusFilter === opt.key;
                return (
                  <button
                    key={opt.key}
                    onClick={() => { setStatusFilter(opt.key); }}
                    className={"px-2.5 py-1 text-xs rounded-lg border font-medium transition duration-150 " + (active ? "bg-slate-800 text-white border-slate-800 shadow-sm" : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50")}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Card>

      <Card className="overflow-hidden bg-white">
        <div className="p-4 border-b"><h3 className="font-bold text-gray-800 text-sm">원자재 목록</h3></div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50">
                {["PO ID", "협력사", "원자재명", "폭(mm)", "길이(mm)", "중량(kg)", "지름(mm)", "구성 요소", "원산지", "상태", "긴급 요청"].map((h, i) => {
                  return <th key={i} className="px-2 py-2 text-left font-bold text-gray-500">{h}</th>;
                })}
              </tr>
            </thead>
            <tbody>
              {filteredRM.length > 0 ? (
                filteredRM.map((r) => {
                  const isPOOpen = openPO === r.po_id;
                  return [
                    <tr key={r.id} className={"border-t hover:bg-gray-50 cursor-pointer" + (selRM && selRM.id === r.id ? " bg-emerald-50/30" : "")}
                      onClick={() => { setSelRM(r); }}>
                      <td className="px-2 py-2" onClick={(e) => { e.stopPropagation(); setOpenPO(isPOOpen ? null : r.po_id); }}>
                        <span className="font-mono text-[#03a94d] font-bold underline cursor-pointer">{r.po_id}</span>
                        <span className="ml-1 text-gray-400">{isPOOpen ? "▲" : "▼"}</span>
                      </td>
                      <td className="px-2 py-2">{COMPANIES.find((c) => c.id === r.partner_id)?.short || r.partner_id}</td>
                      <td className="px-2 py-2 font-medium">{r.name}</td>
                      <td className="px-2 py-2 font-mono">{r.width || "-"}</td>
                      <td className="px-2 py-2 font-mono">{r.length || "-"}</td>
                      <td className="px-2 py-2 font-mono">{r.weight_kg || "-"}</td>
                      <td className="px-2 py-2 font-mono">{r.diameter_mm || "-"}</td>
                      <td className="px-2 py-2 text-gray-500" style={{ maxWidth: "120px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.components}</td>
                      <td className="px-2 py-2">{r.origin}</td>
                      <td className="px-2 py-2"><SChip s={r.status} type="rawmat" /></td>
                      <td className="px-2 py-2" onClick={(e) => { e.stopPropagation(); }}>
                        {r.status === "APPROVED" && (
                          <button onClick={() => { setUrgentRM(r); }}
                            className="px-2 py-1 text-white rounded text-xs font-bold transition hover:opacity-90 shadow-sm"
                            style={{ backgroundColor: "#03a94d" }}>요청하기</button>
                        )}
                      </td>
                    </tr>,
                    // PO ID 드롭다운 트리
                    isPOOpen && r.tier_tree && r.tier_tree.length > 0 ? (
                      <tr key={r.id + "-tree"} className="bg-emerald-50/30">
                        <td colSpan={11} className="px-4 py-3">
                          <p className="text-xs font-bold text-[#03a94d] mb-2">{r.po_id} — 공급망 재료·광물 트리</p>
                          <TierTree rows={r.tier_tree} />
                        </td>
                      </tr>
                    ) : null
                  ];
                })
              ) : (
                <tr>
                  <td colSpan={11} className="text-center py-10 bg-white text-gray-400 text-sm">
                    검색 결과에 해당하는 원자재가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-400 p-3">PO ID 클릭 → 공급망 트리 드롭다운 / 행 클릭 → 원자재 상세</p>
      </Card>
    </div>
  );
};

export default RawMaterialList;
export { TierTree };
