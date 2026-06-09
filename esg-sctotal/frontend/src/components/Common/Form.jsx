import React from "react";

export const FI = ({ label, req, type = "text", value = "", onChange = (() => {}), ph }) => {
  return (
    <div>
      <label className="text-xs font-bold text-gray-600 block mb-1">
        {label}
        {req && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={ph}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
      />
    </div>
  );
};

export const FS = ({ label, req, value, onChange = (() => {}), opts = [] }) => {
  return (
    <div>
      <label className="text-xs font-bold text-gray-600 block mb-1">
        {label}
        {req && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <select
        value={value}
        onChange={onChange}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30 bg-white"
      >
        {opts.map((o, i) => {
          const v = typeof o === "object" ? o.value : o;
          const l = typeof o === "object" ? o.label : o;
          return (
            <option key={i} value={v}>
              {l}
            </option>
          );
        })}
      </select>
    </div>
  );
};
