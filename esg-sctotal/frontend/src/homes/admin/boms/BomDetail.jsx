import React from "react";
import { COMPANIES } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { SChip } from "@components/Common/Chip";
import SupplyChainMap from "@components/UI/SupplyChainMap";

const BomDetail = ({ selBom, setSelBom }) => {
  if (!selBom) return null;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-black text-gray-900">BOM 상세</h1>
        </div>
        <button
          onClick={() => { setSelBom(null); }}
          className="px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 transition"
        >
          ← 목록으로
        </button>
      </div>
      <Card className="p-5 bg-white">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-black text-lg text-gray-900">{selBom.product}</h3>
            <p className="text-sm text-gray-500 mt-0.5">{selBom.category} · {selBom.item_no}</p>
          </div>
          <SChip s={selBom.status} type="bom" />
        </div>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {[
            ["품목명", selBom.item_name],
            ["계산 중량", selBom.weight_g + "g"],
            ["수량", selBom.qty + " " + selBom.unit],
            ["단가", selBom.price + "원"],
            ["리드타임", selBom.lead_time + "일"],
            ["구성요소", selBom.components]
          ].map((pair, i) => {
            return (
              <div key={i} className="bg-gray-50 rounded p-2.5 border border-gray-100">
                <p className="text-xs text-gray-400 font-semibold">{pair[0]}</p>
                <p className="text-sm font-semibold text-gray-800 mt-0.5">{pair[1]}</p>
              </div>
            );
          })}
        </div>
        <div className="mt-6 border-t pt-6">
          <p className="text-sm font-bold text-gray-700 mb-3">공급망 지도(Supply Chain Map)</p>
          <SupplyChainMap
            hideTitle={true}
            filterPartnerId={selBom.supplier_id}
            bom={selBom}
            approvedAt={selBom.approved_at}
          />
        </div>
      </Card>
    </div>
  );
};

export default BomDetail;
