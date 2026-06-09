import React, { useState } from "react";
import { BOM_LIST, COMPANIES } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { Chip, SChip } from "@components/Common/Chip";

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

const BomList = ({ setSelBom }) => {
  const [category, setCategory] = useState("전체");
  const [openBomId, setOpenBomId] = useState(null);  // BOM ID 드롭다운
  const [search, setSearch] = useState("");     // 협력사명 검색
  const [statusFilter, setStatusFilter] = useState("all"); // 상태 필터

  const CATEGORIES = ["전체", "열차폐판", "휠", "파이프", "튜브"];

  // Filter BOM_LIST based on search, category and statusFilter
  const filtered = BOM_LIST.filter((b) => {
    // 1. 제품군 필터 (띄어쓰기 무시하고 비교)
    if (category !== "전체") {
      const normalizedCat = b.category.replace(/\s+/g, "");
      const normalizedFilter = category.replace(/\s+/g, "");
      if (normalizedCat !== normalizedFilter) {
        return false;
      }
    }

    // 2. 협력사명 검색
    if (search.trim() !== "") {
      const s = search.toLowerCase();
      const company = COMPANIES.find((c) => c.id === b.supplier_id);
      const companyName = company ? company.company_name.toLowerCase() : "";
      const companyShort = company ? company.short.toLowerCase() : "";
      const supplierId = b.supplier_id.toLowerCase();

      const match = companyName.indexOf(s) !== -1 || companyShort.indexOf(s) !== -1 || supplierId.indexOf(s) !== -1;
      if (!match) return false;
    }

    // 3. 상태 필터
    if (statusFilter !== "all" && b.status !== statusFilter) {
      return false;
    }

    return true;
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-black text-gray-900">BOM 관리</h1>
        <p className="text-sm text-gray-400 mt-1">Al 3003 제품군별 BOM · BOM ID 클릭 → 드롭다운 트리 / 행 클릭 → 상세</p>
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

          {/* 제품군 필터 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-500">제품군:</span>
            <div className="flex gap-1.5 flex-wrap">
              {CATEGORIES.map((c) => {
                const active = category === c;
                return (
                  <button
                    key={c}
                    onClick={() => { setCategory(c); }}
                    className={"px-2.5 py-1 text-xs rounded-lg border font-medium transition duration-150 " + (active ? "bg-slate-800 text-white border-slate-800 shadow-sm" : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50")}
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 상태 필터 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-500">상태:</span>
            <div className="flex gap-1.5 flex-wrap">
              {[
                { key: "all", label: "전체" },
                { key: "ACTIVE", label: "활성" },
                { key: "INACTIVE", label: "비활성" },
                { key: "REGISTERING", label: "등록 중" },
                { key: "DISCONTINUED", label: "단종" }
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

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50">
                {["BOM ID", "제품군", "제품명", "품번", "품목명", "계산 중량", "수량", "단위", "협력사", "상태"].map((h, i) => {
                  return <th key={i} className="px-2 py-2 text-left font-bold text-gray-500">{h}</th>;
                })}
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map((b) => {
                  const isBomOpen = openBomId === b.id;
                  return [
                    <tr key={b.id} className="border-t hover:bg-gray-50 cursor-pointer" onClick={() => { setSelBom(b); }}>
                      <td className="px-2 py-2" onClick={(e) => { e.stopPropagation(); setOpenBomId(isBomOpen ? null : b.id); }}>
                        <span className="font-mono text-[#03a94d] font-bold underline cursor-pointer">{b.id}</span>
                        <span className="ml-1 text-gray-400">{isBomOpen ? "▲" : "▼"}</span>
                      </td>
                      <td className="px-2 py-2"><Chip text={b.category} color="slate" /></td>
                      <td className="px-2 py-2 font-medium">{b.product}</td>
                      <td className="px-2 py-2 font-mono">{b.item_no}</td>
                      <td className="px-2 py-2">{b.item_name}</td>
                      <td className="px-2 py-2 font-mono font-bold text-emerald-700">{b.weight_g}g</td>
                      <td className="px-2 py-2 font-mono">{b.qty}</td>
                      <td className="px-2 py-2 text-gray-500">{b.unit}</td>
                      <td className="px-2 py-2">{COMPANIES.find((c) => c.id === b.supplier_id)?.short || "-"}</td>
                      <td className="px-2 py-2"><SChip s={b.status} type="bom" /></td>
                    </tr>,
                    // BOM ID 드롭다운 트리
                    isBomOpen && b.tier_tree && b.tier_tree.length > 0 ? (
                      <tr key={b.id + "-tree"} className="bg-emerald-50/30">
                        <td colSpan={10} className="px-4 py-3">
                          <p className="text-xs font-bold text-[#03a94d] mb-2">{b.id} — 공급망 재료·광물 트리 (중량: {b.weight_g}g)</p>
                          <TierTree rows={b.tier_tree} />
                        </td>
                      </tr>
                    ) : null
                  ];
                })
              ) : (
                <tr>
                  <td colSpan={10} className="text-center py-10 bg-white text-gray-400 text-sm">
                    검색 결과에 해당하는 BOM 항목이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-400 p-3">BOM ID 클릭 → 공급망 트리 드롭다운 / 행 클릭 → BOM 상세</p>
      </Card>
    </div>
  );
};

export default BomList;
