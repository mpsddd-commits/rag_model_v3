import React, { useState } from "react";
import { RAW_MATERIALS, COMPANIES, PO_LIST, NOTIFICATIONS } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { SChip } from "@components/Common/Chip";

const ROLE_MAP = {
  "1차 협력사": "NOV-001",
  "2차 협력사": "KRM-001",
  "3차 협력사": "COM-001"
};

// 공통 UI 폼 컴포넌트
const FI = (p) => {
  return (
    <div>
      <label className="text-xs font-bold text-gray-600 block mb-1">
        {p.label}
        {p.req && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        type={p.type || "text"}
        value={p.value || ""}
        onChange={p.onChange || (() => {})}
        placeholder={p.ph}
        disabled={p.disabled}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30 bg-white disabled:bg-gray-100 disabled:text-gray-500"
      />
    </div>
  );
};

const MaterialManage = ({ userRole }) => {
  const partnerId = ROLE_MAP[userRole] || "NOV-001";

  // viewMode: "list" | "form" | "urgent"
  const [viewMode, setViewMode] = useState("list");
  const [selRM, setSelRM] = useState(null);

  // Form State
  const [form, setForm] = useState({
    origin: "",
    name: "",
    weight_kg: "",
    width: "",
    length: "",
    diameter_mm: "",
    components: ""
  });

  const [urgentRM, setUrgentRM] = useState(null);
  const [urgentForm, setUrgentForm] = useState({
    origin: "",
    name: "",
    weight_kg: "",
    width: "",
    length: "",
    diameter_mm: "",
    components: ""
  });

  // 해당 협력사의 원자재 리스트
  const list = RAW_MATERIALS.filter(r => r.partner_id === partnerId);

  // 최근 알림 중 긴급 요청 추출
  const companyShort = COMPANIES.find(c => c.id === partnerId)?.short || partnerId;
  const urgentNotifs = NOTIFICATIONS.filter(n => n.type === "URGENT" && n.msg.includes(companyShort));

  const handleStartSubmit = (rm) => {
    setSelRM(rm);
    setForm({
      origin: rm.origin || "",
      name: rm.name || "",
      weight_kg: rm.weight_kg !== null ? rm.weight_kg.toString() : "",
      width: rm.width !== null ? rm.width.toString() : "",
      length: rm.length !== null ? rm.length.toString() : "",
      diameter_mm: rm.diameter_mm !== null ? rm.diameter_mm.toString() : "",
      components: rm.components || ""
    });
    setViewMode("form");
  };

  const handleStartUrgent = (rm) => {
    setUrgentRM(rm);
    setUrgentForm({
      origin: rm.origin || "",
      name: rm.name || "",
      weight_kg: rm.weight_kg !== null ? rm.weight_kg.toString() : "",
      width: rm.width !== null ? rm.width.toString() : "",
      length: rm.length !== null ? rm.length.toString() : "",
      diameter_mm: rm.diameter_mm !== null ? rm.diameter_mm.toString() : "",
      components: rm.components || ""
    });
    setViewMode("urgent");
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();

    if (!form.origin || !form.name || !form.weight_kg || !form.components) {
      alert("필수 항목(* 표시)을 모두 입력해 주십시오.");
      return;
    }

    // 데이터 업데이트
    setSelRM(prev => {
      const updated = Object.assign({}, prev, {
        origin: form.origin,
        name: form.name,
        weight_kg: parseInt(form.weight_kg),
        width: form.width ? parseInt(form.width) : null,
        length: form.length ? parseInt(form.length) : null,
        diameter_mm: form.diameter_mm ? parseFloat(form.diameter_mm) : null,
        components: form.components,
        status: "PENDING"
      });

      const idx = RAW_MATERIALS.findIndex(r => r.id === prev.id);
      if (idx !== -1) {
        RAW_MATERIALS[idx] = updated;
      }
      return updated;
    });

    const newNotif = {
      id: NOTIFICATIONS.length + 1,
      type: "SELF",
      level: "info",
      title: "원자재 정보 제출 완료 — " + selRM.id,
      msg: companyShort + "에서 " + form.name + "의 원자재 세부 사양 정보를 제출하였습니다. 원청사의 검토 및 승인을 대기합니다.",
      time: new Date().toISOString().replace('T', ' ').substring(0, 16),
      read: false
    };
    NOTIFICATIONS.unshift(newNotif);

    alert("원자재 정보가 제출되었습니다. 원청사의 승인을 기다립니다.");
    setViewMode("list");
    setSelRM(null);
  };

  const handleUrgentSubmit = (e) => {
    e.preventDefault();

    if (!urgentForm.origin || !urgentForm.name || !urgentForm.weight_kg || !urgentForm.components) {
      alert("필수 항목(* 표시)을 모두 입력해 주십시오.");
      return;
    }

    setUrgentRM(prev => {
      const updated = Object.assign({}, prev, {
        origin: urgentForm.origin,
        name: urgentForm.name,
        weight_kg: parseInt(urgentForm.weight_kg),
        width: urgentForm.width ? parseInt(urgentForm.width) : null,
        length: urgentForm.length ? parseInt(urgentForm.length) : null,
        diameter_mm: urgentForm.diameter_mm ? parseFloat(urgentForm.diameter_mm) : null,
        components: urgentForm.components,
        status: "PENDING"
      });

      const idx = RAW_MATERIALS.findIndex(r => r.id === prev.id);
      if (idx !== -1) {
        RAW_MATERIALS[idx] = updated;
      }
      return updated;
    });

    const newNotif = {
      id: NOTIFICATIONS.length + 1,
      type: "SELF",
      level: "info",
      title: "긴급 원자재 정보 보완 완료 — " + urgentRM.id,
      msg: companyShort + "에서 긴급 요청된 " + urgentForm.name + "의 보완 서류 및 상세 정보를 재제출하였습니다.",
      time: new Date().toISOString().replace('T', ' ').substring(0, 16),
      read: false
    };
    NOTIFICATIONS.unshift(newNotif);

    alert("긴급 보완 정보가 제출되었습니다.");
    setViewMode("list");
    setUrgentRM(null);
  };

  if (viewMode === "form" && selRM) {
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-black text-gray-900">원자재 정보 제출</h1>
            <p className="text-sm text-gray-400 mt-1">원청사가 요청한 원자재 사양 상세 정보를 입력합니다.</p>
          </div>
          <button
            onClick={() => { setViewMode("list"); setSelRM(null); }}
            className="px-4 py-2 bg-slate-100 text-slate-700 text-xs rounded-lg hover:bg-slate-200 transition font-bold"
          >
            목록으로
          </button>
        </div>

        <form onSubmit={handleFormSubmit} className="space-y-6">
          <Card className="p-6 bg-white border border-gray-150">
            <div className="flex justify-between items-center border-b pb-3 mb-5">
              <h2 className="text-base font-bold text-gray-900" style={{ fontSize: "16px" }}>원자재 세부 규격 입력</h2>
              <span className="text-xs text-gray-400">PO ID: {selRM.po_id}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FI label="원자재명" req value={form.name} onChange={(e) => setForm(Object.assign({}, form, { name: e.target.value }))} ph="예: 알루미늄 슬라브 3003" />
              <FI label="원산지" req value={form.origin} onChange={(e) => setForm(Object.assign({}, form, { origin: e.target.value }))} ph="예: 대한민국 울산" />
              <FI label="중량 (kg)" req type="number" value={form.weight_kg} onChange={(e) => setForm(Object.assign({}, form, { weight_kg: e.target.value }))} ph="예: 1500" />
              <FI label="폭 (mm)" type="number" value={form.width} onChange={(e) => setForm(Object.assign({}, form, { width: e.target.value }))} ph="예: 600" />
              <FI label="길이 (mm)" type="number" value={form.length} onChange={(e) => setForm(Object.assign({}, form, { length: e.target.value }))} ph="예: 3000" />
              <FI label="지름 (mm)" type="number" value={form.diameter_mm} onChange={(e) => setForm(Object.assign({}, form, { diameter_mm: e.target.value }))} ph="예: 25.4" />
              <div className="md:col-span-2">
                <FI label="구성 요소" req value={form.components} onChange={(e) => setForm(Object.assign({}, form, { components: e.target.value }))} ph="예: Al 97.9%, Mn 1.25%, Cu 0.12%" />
              </div>
            </div>
          </Card>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setViewMode("list"); setSelRM(null); }}
              className="px-5 py-2.5 bg-gray-100 text-gray-700 text-xs font-bold rounded-lg hover:bg-gray-200 transition"
            >
              취소
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 text-white text-xs font-bold rounded-lg hover:opacity-90 transition shadow-sm"
              style={{ backgroundColor: "#03a94d" }}
            >
              제출하기
            </button>
          </div>
        </form>
      </div>
    );
  }

  if (viewMode === "urgent" && urgentRM) {
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-black text-gray-900">긴급 요청 정보 보완</h1>
            <p className="text-sm text-gray-400 mt-1">원청사가 긴급 보완을 요구한 사양 정보를 수정하여 재제출합니다.</p>
          </div>
          <button
            onClick={() => { setViewMode("list"); setUrgentRM(null); }}
            className="px-4 py-2 bg-slate-100 text-slate-700 text-xs rounded-lg hover:bg-slate-200 transition font-bold"
          >
            목록으로
          </button>
        </div>

        <form onSubmit={handleUrgentSubmit} className="space-y-6">
          <Card className="p-6 bg-white border border-gray-150">
            <div className="flex justify-between items-center border-b pb-3 mb-5">
              <h2 className="text-base font-bold text-gray-900" style={{ fontSize: "16px" }}>긴급 원자재 규격 보완</h2>
              <span className="text-xs px-2.5 py-0.5 rounded bg-red-50 text-red-600 border border-red-100 font-bold">긴급 보완</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FI label="원자재명" req value={urgentForm.name} onChange={(e) => setUrgentForm(Object.assign({}, urgentForm, { name: e.target.value }))} />
              <FI label="원산지" req value={urgentForm.origin} onChange={(e) => setUrgentForm(Object.assign({}, urgentForm, { origin: e.target.value }))} />
              <FI label="중량 (kg)" req type="number" value={urgentForm.weight_kg} onChange={(e) => setUrgentForm(Object.assign({}, urgentForm, { weight_kg: e.target.value }))} />
              <FI label="폭 (mm)" type="number" value={urgentForm.width} onChange={(e) => setUrgentForm(Object.assign({}, urgentForm, { width: e.target.value }))} />
              <FI label="길이 (mm)" type="number" value={urgentForm.length} onChange={(e) => setUrgentForm(Object.assign({}, urgentForm, { length: e.target.value }))} />
              <FI label="지름 (mm)" type="number" value={urgentForm.diameter_mm} onChange={(e) => setUrgentForm(Object.assign({}, urgentForm, { diameter_mm: e.target.value }))} />
              <div className="md:col-span-2">
                <FI label="구성 요소" req value={urgentForm.components} onChange={(e) => setUrgentForm(Object.assign({}, urgentForm, { components: e.target.value }))} />
              </div>
            </div>
          </Card>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setViewMode("list"); setUrgentRM(null); }}
              className="px-5 py-2.5 bg-gray-100 text-gray-700 text-xs font-bold rounded-lg hover:bg-gray-200 transition"
            >
              취소
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 text-white text-xs font-bold rounded-lg hover:opacity-90 transition shadow-sm"
              style={{ backgroundColor: "#d32f2f" }}
            >
              긴급 재제출
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-black text-gray-900">원자재 관리</h1>
        <p className="text-sm text-gray-400 mt-1">원청사 정보 요청 내역 조회 및 세부 사양 등록</p>
      </div>

      {/* 긴급 요청 알림 카드 */}
      {urgentNotifs.length > 0 && (
        <Card className="p-4 border border-red-200 bg-red-50/50 space-y-2">
          <h3 className="text-xs font-bold text-red-700 flex items-center gap-1.5">
            긴급 보완 요청 수신 내역
          </h3>
          <div className="divide-y divide-red-100">
            {urgentNotifs.map((n) => {
              const targetRM = list.find(r => n.msg.includes(r.id));
              return (
                <div key={n.id} className="py-2 first:pt-0 last:pb-0 flex items-center justify-between text-xs gap-3">
                  <p className="text-red-800 leading-relaxed font-medium">{n.msg}</p>
                  {targetRM && (
                    <button
                      onClick={() => handleStartUrgent(targetRM)}
                      className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-bold shrink-0 transition"
                    >
                      즉시 보완
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* 원자재 목록 카드 */}
      <Card className="overflow-hidden bg-white">
        <div className="p-4 border-b">
          <h3 className="font-bold text-gray-800 text-sm">요청 및 등록 원자재 목록</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50">
                {["PO ID", "원자재명", "원산지", "폭(mm)", "길이(mm)", "중량(kg)", "지름(mm)", "구성 요소", "요청일", "상태", "작업"].map((h, i) => {
                  return <th key={i} className="px-2 py-2.5 text-left font-bold text-gray-500">{h}</th>;
                })}
              </tr>
            </thead>
            <tbody>
              {list.length > 0 ? (
                list.map((r) => {
                  const canEdit = r.status === "REQUESTED" || r.status === "REJECTED";
                  return (
                    <tr key={r.id} className="border-t hover:bg-gray-50">
                      <td className="px-2 py-3 font-mono text-gray-500 font-bold">{r.po_id}</td>
                      <td className="px-2 py-3 font-medium text-gray-800">{r.name}</td>
                      <td className="px-2 py-3 text-gray-600">{r.origin || "-"}</td>
                      <td className="px-2 py-3 font-mono text-gray-600">{r.width !== null ? r.width : "-"}</td>
                      <td className="px-2 py-3 font-mono text-gray-600">{r.length !== null ? r.length : "-"}</td>
                      <td className="px-2 py-3 font-mono text-gray-600">{r.weight_kg !== null ? r.weight_kg.toLocaleString() : "-"}</td>
                      <td className="px-2 py-3 font-mono text-gray-600">{r.diameter_mm !== null ? r.diameter_mm : "-"}</td>
                      <td className="px-2 py-3 text-gray-500 max-w-[150px] truncate" title={r.components}>{r.components || "-"}</td>
                      <td className="px-2 py-3 text-gray-400 font-mono">{r.requested_at}</td>
                      <td className="px-2 py-3">
                        <SChip s={r.status} type="rawmat" />
                      </td>
                      <td className="px-2 py-3">
                        {canEdit ? (
                          <button
                            onClick={() => handleStartSubmit(r)}
                            className="px-2.5 py-1 text-white rounded text-xs font-bold hover:opacity-90 transition shadow-sm"
                            style={{ backgroundColor: "#03a94d" }}
                          >
                            정보 입력
                          </button>
                        ) : (
                          <span className="text-gray-400 italic">완료됨</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={11} className="text-center py-10 text-gray-400 text-sm">
                    요청 또는 등록된 원자재 내역이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default MaterialManage;
