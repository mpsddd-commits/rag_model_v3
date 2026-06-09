import React, { useState } from "react";
import { RAW_MATERIALS, COMPANIES, PO_LIST, NOTIFICATIONS } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { FI, FS } from "@components/Common/Form";

const RawMaterialRequest = ({ setIsRequestingRM }) => {
  const [reqForm, setReqForm] = useState({
    poId: "",
    partner: "",
    origin: "",
    materialName: "",
    weight: "",
    width: "",
    length: "",
    diameter: "",
    components: "",
    deadline: "",
    content: ""
  });

  const matchedPO = PO_LIST.find((p) => p.id === reqForm.poId);
  let matchedPartner = "";
  if (matchedPO) {
    const comp = COMPANIES.find((c) => c.id === matchedPO.partner_id);
    matchedPartner = comp ? comp.company_name : matchedPO.partner_id;
  }

  const handlePOChange = (e) => {
    const nextPoId = e.target.value;
    const po = PO_LIST.find((p) => p.id === nextPoId);
    let partnerName = "";
    if (po) {
      const comp = COMPANIES.find((c) => c.id === po.partner_id);
      partnerName = comp ? comp.company_name : po.partner_id;
    }

    setReqForm((prev) => {
      return Object.assign({}, prev, {
        poId: nextPoId,
        partner: partnerName,
        materialName: po ? po.product : "",
        width: po && po.width ? po.width.toString() : "",
        length: po && po.length ? po.length.toString() : "",
        weight: po && po.weight ? (po.weight * 1000).toString() : "",
        diameter: po && po.diameter ? po.diameter.toString() : "",
        components: po ? po.material : ""
      });
    });
  };

  const handleFieldChange = (field) => (e) => {
    const val = e.target.value;
    setReqForm((prev) => {
      const next = Object.assign({}, prev);
      next[field] = val;
      return next;
    });
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div><h1 className="text-2xl font-black text-gray-900">원자재 요청</h1></div>
        <button onClick={() => { setIsRequestingRM(false); }} className="px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 transition">← 목록으로</button>
      </div>

      {/* 1. 요청 협력사 선택 카드 */}
      <Card className="p-4 border border-slate-200 bg-slate-50/50">
        <div className="flex items-center gap-2 mb-2.5"><h3 className="font-bold text-gray-800">요청 협력사 선택</h3></div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-bold text-gray-600 block mb-1">PO ID 선택 <span className="text-red-500">*</span></label>
            <select
              value={reqForm.poId}
              onChange={handlePOChange}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
            >
              <option value="">-- PO ID를 선택하세요 --</option>
              {PO_LIST.map((po) => {
                return <option key={po.id} value={po.id}>{po.id} ({po.product})</option>;
              })}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold text-gray-600 block mb-1">협력사</label>
            <input
              type="text"
              value={matchedPartner || "PO ID를 먼저 선택해주세요"}
              disabled
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-100 text-gray-500 font-semibold"
            />
          </div>
        </div>
      </Card>

      {/* 2. 요청 항목 상세 입력 카드 */}
      <Card className="p-4 border border-[#03a94d]/20 bg-white">
        <div className="flex items-center gap-2 mb-1"><h3 className="font-bold text-gray-800">요청 항목 상세 입력</h3></div>
        <p className="text-xs text-gray-500 mb-3">각 협력사 원자재 스펙 정보를 입력해 주세요.</p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 입력 폼 필드 */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1">원산지 <span className="text-red-500">*</span></label>
              <input
                type="text"
                placeholder="예: 대한민국 울산, 가봉 등"
                value={reqForm.origin}
                onChange={handleFieldChange("origin")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1">원자재명 (1차 협력사 원자재명) <span className="text-red-500">*</span></label>
              <input
                type="text"
                placeholder="예: Al 3003 슬라브"
                value={reqForm.materialName}
                onChange={handleFieldChange("materialName")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1">중량 (kg) <span className="text-red-500">*</span></label>
              <input
                type="number"
                placeholder="예: 1500"
                value={reqForm.weight}
                onChange={handleFieldChange("weight")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1">폭 (mm)</label>
              <input
                type="number"
                placeholder="예: 600"
                value={reqForm.width}
                onChange={handleFieldChange("width")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1">길이 (mm)</label>
              <input
                type="number"
                placeholder="예: 3000"
                value={reqForm.length}
                onChange={handleFieldChange("length")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              />
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1">지름 (mm)</label>
              <input
                type="number"
                placeholder="예: 25.4"
                value={reqForm.diameter}
                onChange={handleFieldChange("diameter")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs font-bold text-gray-600 block mb-1">구성 요소 <span className="text-red-500">*</span></label>
              <input
                type="text"
                placeholder="예: Al 97.9%, Mn 1.25%, Cu 0.12%"
                value={reqForm.components}
                onChange={handleFieldChange("components")}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              />
              <p className="text-[11px] text-gray-400 mt-1">※ 협력사 측에서 상세 입력을 진행하지만, 원청사 관리 화면에서는 합산 및 전체 사양이 표출됩니다.</p>
            </div>
          </div>

          {/* 실시간 전체 데이터 프리뷰 카드 */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-col justify-between">
            <div>
              <h4 className="font-bold text-xs text-slate-700 border-b pb-2 mb-3">실시간 요청 데이터 (전체 데이터)</h4>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between border-b border-dashed border-gray-200 pb-1.5">
                  <span className="text-gray-400 font-semibold">PO ID</span>
                  <span className="font-bold text-gray-800">{reqForm.poId || "-"}</span>
                </div>
                <div className="flex justify-between border-b border-dashed border-gray-200 pb-1.5">
                  <span className="text-gray-400 font-semibold">대상 협력사</span>
                  <span className="font-bold text-gray-800">{matchedPartner || "-"}</span>
                </div>
                <div className="flex justify-between border-b border-dashed border-gray-200 pb-1.5">
                  <span className="text-gray-400 font-semibold">원자재명</span>
                  <span className="font-bold text-gray-800 text-right max-w-[150px] truncate">{reqForm.materialName || "-"}</span>
                </div>
                <div className="flex justify-between border-b border-dashed border-gray-200 pb-1.5">
                  <span className="text-gray-400 font-semibold">원산지</span>
                  <span className="font-bold text-gray-800">{reqForm.origin || "-"}</span>
                </div>
                <div className="flex justify-between border-b border-dashed border-gray-200 pb-1.5">
                  <span className="text-gray-400 font-semibold">중량</span>
                  <span className="font-bold text-gray-800">{reqForm.weight ? Number(reqForm.weight).toLocaleString() + " kg" : "-"}</span>
                </div>
                <div className="flex justify-between border-b border-dashed border-gray-200 pb-1.5">
                  <span className="text-gray-400 font-semibold">규격 (폭 × 길이 × 지름)</span>
                  <span className="font-bold text-gray-800">
                    {reqForm.width || "-"}mm × {reqForm.length || "-"}mm × {reqForm.diameter || "-"}mm
                  </span>
                </div>
                <div className="flex flex-col">
                  <span className="text-gray-400 font-semibold mb-1">구성 요소 전체 내역</span>
                  <div className="bg-white border border-gray-200 rounded p-2 text-[11px] font-mono text-gray-700 min-h-[48px] break-all leading-normal">
                    {reqForm.components || "입력된 구성 요소 정보가 없습니다."}
                  </div>
                </div>
              </div>
            </div>
            <div className="text-[10px] text-gray-400 mt-4 leading-normal">
              * 상기 입력 데이터는 승인 완료 시 ESG 공급망 맵 및 실사 등급 산출 데이터로 연동됩니다.
            </div>
          </div>
        </div>
      </Card>

      {/* 3. 요청 내용 입력 카드 */}
      <Card className="p-5 bg-white">
        <h4 className="font-bold text-gray-800 mb-4">요청 내용 입력</h4>
        <div className="space-y-4">
          <FI
            label="제출기한"
            type="date"
            value={reqForm.deadline}
            onChange={handleFieldChange("deadline")}
            req
          />
          <div>
            <label className="text-xs font-bold text-gray-600 block mb-1">요청 내용</label>
            <textarea
              rows={6}
              value={reqForm.content}
              onChange={handleFieldChange("content")}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
              placeholder="세부 내용을 입력해주세요."
            />
          </div>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            원자재 정보 요청이 발송되면 대상 협력사에게 즉시 알림이 발송되며, 신규 원자재 임시 레코드가 등록되어 결재 진행 대기 상태가 됩니다.
          </div>
          <div className="flex gap-2">
            <button onClick={() => { setIsRequestingRM(false); }} className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg">취소</button>
            <button onClick={() => {
              if (!reqForm.poId) {
                alert("PO ID를 선택해주세요.");
                return;
              }
              if (!reqForm.origin) {
                alert("원산지를 입력해주세요.");
                return;
              }
              if (!reqForm.materialName) {
                alert("원자재명을 입력해주세요.");
                return;
              }
              if (!reqForm.weight) {
                alert("중량을 입력해주세요.");
                return;
              }
              if (!reqForm.components) {
                alert("구성 요소를 입력해주세요.");
                return;
              }
              if (!reqForm.deadline) {
                alert("제출기한을 입력해주세요.");
                return;
              }

              const newRM = {
                id: "RM-00" + (RAW_MATERIALS.length + 1),
                po_id: reqForm.poId,
                partner_id: matchedPO ? matchedPO.partner_id : "NOV-001",
                name: reqForm.materialName,
                width: reqForm.width ? parseInt(reqForm.width) : null,
                length: reqForm.length ? parseInt(reqForm.length) : null,
                weight_kg: parseInt(reqForm.weight),
                diameter_mm: reqForm.diameter ? parseFloat(reqForm.diameter) : null,
                components: reqForm.components,
                origin: reqForm.origin,
                status: "REQUESTED",
                requested_at: new Date().toISOString().split('T')[0],
                approved_at: null,
                tier_tree: [
                  {
                    tier: 1,
                    short: COMPANIES.find((c) => c.id === (matchedPO ? matchedPO.partner_id : "NOV-001"))?.short || "협력사",
                    item: reqForm.materialName,
                    comp: reqForm.components,
                    qty_kg: parseInt(reqForm.weight)
                  }
                ]
              };

              RAW_MATERIALS.push(newRM);

              const newNotif = {
                id: NOTIFICATIONS.length + 1,
                type: "URGENT",
                level: "warn",
                title: "원자재 요청 발송 완료 — " + newRM.id,
                msg: (matchedPartner) + "에 " + newRM.name + " 정보 요청이 발송되었습니다. 제출 기한: " + reqForm.deadline,
                time: new Date().toISOString().replace('T', ' ').substring(0, 16),
                read: false
              };
              NOTIFICATIONS.unshift(newNotif);

              alert("원자재 요청이 발송되었습니다.\n협력사 알림이 전송되고 신규 레코드가 생성되었습니다.");
              setIsRequestingRM(false);
            }}
              className="px-6 py-2 text-white text-sm rounded-lg font-bold hover:opacity-90 transition shadow-sm"
              style={{ backgroundColor: "#03a94d" }}>요청하기</button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default RawMaterialRequest;
