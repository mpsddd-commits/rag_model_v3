import React from "react";

const Kpi = ({ icon, accent, label, value, sub }) => {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex items-center gap-4">
      {icon && (
        <div className={(accent || "bg-[#03a94d]") + " w-12 h-12 rounded-xl flex items-center justify-center text-white text-2xl shrink-0"}>
          {icon}
        </div>
      )}
      <div className="flex-1">
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-xl font-black text-gray-900 leading-tight">{value}</p>
        <p className="text-xs text-gray-400 mt-0.5">{sub}</p>
      </div>
    </div>
  );
};

export default Kpi;
