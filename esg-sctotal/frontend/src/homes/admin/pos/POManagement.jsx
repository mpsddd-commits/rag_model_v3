import React from "react";
import { PO_LIST } from "@assets/data/masterData";
import Card from "@components/Common/Card";
import { SChip } from "@components/Common/Chip";

const POManagement = () => {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-black text-gray-900">PO 관리</h1>
        <p className="text-sm text-gray-400 mt-1">Al 3003 합금 영업용 PO · 규격 상세 관리</p>
      </div>
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50">
                {["PO 번호", "제품", "폭(mm)", "길이(mm)", "중량(mm)", "부피(L)", "지름(mm)", "재질", "수량", "총액($)", "납기", "상태"].map((h, i) => {
                  return (
                    <th key={i} className="px-2 py-2 text-left font-bold text-gray-500">
                      {h}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {PO_LIST.map((p, i) => {
                return (
                  <tr key={i} className="border-t hover:bg-gray-50">
                    <td className="px-2 py-2 font-mono text-[#03a94d] font-bold">{p.id}</td>
                    <td className="px-2 py-2">{p.product}</td>
                    <td className="px-2 py-2 font-mono">{p.width || "-"}</td>
                    <td className="px-2 py-2 font-mono">{p.length || "-"}</td>
                    <td className="px-2 py-2 font-mono">{p.weight || "-"}</td>
                    <td className="px-2 py-2 font-mono">{p.volume || "-"}</td>
                    <td className="px-2 py-2 font-mono">{p.diameter || "-"}</td>
                    <td className="px-2 py-2">{p.material}</td>
                    <td className="px-2 py-2 font-bold">{p.qty}</td>
                    <td className="px-2 py-2">${p.total.toLocaleString()}</td>
                    <td className="px-2 py-2">{p.delivery}</td>
                    <td className="px-2 py-2">
                      <SChip s={p.status} type="po" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default POManagement;
