import React, { useState } from "react";
import { RAW_MATERIALS, COMPANIES, NOTIFICATIONS } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { FI } from "@components/Common/Form";

const UrgentRequest = ({ urgentRM, setUrgentRM }) => {
  const [urgentForm, setUrgentForm] = useState({ deadline: "", content: "" });
  const [selectedItems, setSelectedItems] = useState([]); // 선택된 요청 항목들

  if (!urgentRM) return null;

  const u = (k) => (e) => {
    setUrgentForm((p) => {
      const n = Object.assign({}, p);
      n[k] = e.target.value;
      return n;
    });
  };

  const handleItemToggle = (label) => {
    setSelectedItems((prev) => {
      if (prev.indexOf(label) !== -1) {
        return prev.filter((x) => x !== label);
      } else {
        return prev.concat(label);
      }
    });
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div><h1 className="text-2xl font-black text-gray-900">긴급 요청</h1></div>
        <button onClick={() => { setUrgentRM(null); setSelectedItems([]); }} className="px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 transition">← 목록으로</button>
      </div>

      {/* 요청 대상 정보 (읽기 전용) */}
      <Card className="p-4 border border-slate-200 bg-slate-50/50">
        <div className="flex items-center gap-2 mb-2.5"><h3 className="font-bold text-gray-800">요청 대상 정보</h3></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {[
            ["PO ID", urgentRM.po_id],
            ["협력사", COMPANIES.find((c) => c.id === urgentRM.partner_id)?.company_name || urgentRM.partner_id],
            ["원자재명", urgentRM.name]
          ].map((pair, i) => {
            return (
              <div key={i} className="bg-white rounded-lg p-2.5 border border-gray-150 shadow-sm flex flex-col justify-between">
                <p className="text-gray-400 text-[10px] font-semibold uppercase tracking-wider">{pair[0]}</p>
                <p className="font-semibold text-gray-800 mt-1">{pair[1]}</p>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 요청 항목 선택 (선택 가능) */}
      <Card className="p-4 border border-[#03a94d]/20 bg-white">
        <div className="flex items-center gap-2 mb-1"><h3 className="font-bold text-gray-800">요청 항목 선택</h3></div>
        <p className="text-xs text-gray-500 mb-3">각 항목을 클릭하면 요청할 항목으로 선택됩니다.</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
          {[
            ["폭(mm)", urgentRM.width || "-"],
            ["길이(mm)", urgentRM.length || "-"],
            ["지름(mm)", urgentRM.diameter_mm || "-"],
            ["중량(kg)", urgentRM.weight_kg || "-"],
            ["원산지", urgentRM.origin],
            ["구성요소", urgentRM.components]
          ].map((pair, i) => {
            const label = pair[0];
            const value = pair[1];
            const isSelected = selectedItems.indexOf(label) !== -1;
            return (
              <div
                key={i}
                onClick={() => { handleItemToggle(label); }}
                className={"rounded p-2.5 border transition duration-150 cursor-pointer relative group flex flex-col justify-between " + (isSelected ? "bg-[#03a94d]/10 border-[#03a94d] ring-1 ring-[#03a94d]/30 shadow-sm" : "bg-gray-50 border-gray-150 hover:bg-[#03a94d]/5 hover:border-[#03a94d]/20")}
                title="클릭 시 요청 항목으로 선택됩니다"
              >
                <div className="text-gray-400 flex justify-between items-center text-[10px] font-semibold uppercase tracking-wider">
                  <span>{label}</span>
                  {isSelected ? (
                    <span className="text-[#03a94d] font-bold flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                  ) : (
                    <span className="text-gray-300 opacity-0 group-hover:opacity-100 transition duration-150 text-[10px] font-bold">+ 선택</span>
                  )}
                </div>
                <p className="font-semibold text-gray-800 mt-1">{value}</p>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 요청 내용 입력 */}
      <Card className="p-5 bg-white">
        <h4 className="font-bold text-gray-800 mb-4">요청 내용 입력</h4>
        <div className="space-y-4">
          <div>
            <label className="text-xs font-bold text-gray-600 block mb-1.5">요청 항목 <span className="text-red-500">*</span></label>
            {selectedItems.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 mb-1">
                {selectedItems.map((item) => {
                  return (
                    <span key={item} className="inline-flex items-center gap-1.5 bg-[#03a94d]/10 text-[#03a94d] border border-[#03a94d]/20 rounded-full px-2.5 py-1 text-xs font-semibold shadow-sm">
                      {item}
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleItemToggle(item); }}
                        className="hover:bg-emerald-200 hover:text-emerald-950 rounded-full p-0.5 transition duration-100"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </span>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-gray-400 mb-1">선택된 항목이 없습니다. 상단에서 요청할 항목을 선택해주세요.</p>
            )}
          </div>

          <FI label="제출기한" type="date" value={urgentForm.deadline} onChange={u("deadline")} req />
          <div>
            <label className="text-xs font-bold text-gray-600 block mb-1">요청 내용</label>
            <textarea rows={6} value={urgentForm.content} onChange={u("content")}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              placeholder="세부 내용을 입력해주세요." />
          </div>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">요청 시 해당 협력사에 즉시 알림이 발송되며, RAW_MATERIAL_APPROVAL 결재선이 생성됩니다.</div>
          <div className="flex gap-2">
            <button onClick={() => { setUrgentRM(null); setSelectedItems([]); }} className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg">취소</button>
            <button onClick={() => {
              if (selectedItems.length === 0) {
                alert("요청 항목을 하나 이상 선택해주세요.");
                return;
              }
              if (!urgentForm.deadline) {
                alert("제출기한을 입력해주세요.");
                return;
              }
              
              const newNotif = {
                id: NOTIFICATIONS.length + 1,
                type: "URGENT",
                level: "warn",
                title: "긴급 원자재 요청 — " + urgentRM.id,
                msg: (COMPANIES.find((c) => c.id === urgentRM.partner_id)?.short || urgentRM.partner_id) + "에 " + urgentRM.name + " 정보 보완이 긴급 요청되었습니다. (요청 항목: " + selectedItems.join(", ") + ")",
                time: new Date().toISOString().replace('T', ' ').substring(0, 16),
                read: false
              };
              NOTIFICATIONS.unshift(newNotif);

              alert("요청이 발송되었습니다.\n결재선이 생성되었습니다.");
              setUrgentRM(null);
              setUrgentForm({ deadline: "", content: "" });
              setSelectedItems([]);
            }}
              className="px-6 py-2 text-white text-sm rounded-lg font-bold hover:opacity-90 transition shadow-sm"
              style={{ backgroundColor: "#03a94d" }}>요청 하기</button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default UrgentRequest;
