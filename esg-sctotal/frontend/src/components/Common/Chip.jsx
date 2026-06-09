import React from "react";

export const Chip = ({ text, color }) => {
  const m = {
    red: "bg-red-50 text-red-600 border border-red-200",
    yellow: "bg-amber-50 text-amber-600 border border-amber-200",
    green: "bg-[#03a94d]/10 text-[#03a94d] border border-[#03a94d]/20 font-medium",
    blue: "bg-blue-50 text-blue-600 border border-blue-200",
    teal: "bg-teal-50 text-teal-600 border border-teal-200",
    indigo: "bg-indigo-50 text-indigo-600 border border-indigo-200",
    slate: "bg-slate-50 text-slate-500 border border-slate-200",
    orange: "bg-orange-50 text-orange-600 border border-orange-200",
    violet: "bg-violet-50 text-violet-600 border border-violet-200",
    pink: "bg-pink-50 text-pink-600 border border-pink-200",
    cyan: "bg-cyan-50 text-cyan-600 border border-cyan-200",
    rose: "bg-rose-50 text-rose-600 border border-rose-200",
  };
  return (
    <span className={"px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap " + (m[color] || m.slate)}>
      {text}
    </span>
  );
};

export const RChip = ({ v }) => {
  if (v === "고위험") return <Chip text="고위험" color="red" />;
  if (v === "중위험") return <Chip text="중위험" color="yellow" />;
  return <Chip text="저위험" color="green" />;
};

export const SChip = ({ s, type }) => {
  // type: "bom" | "po" | "rawmat"
  // 1. BOM 관리 (보라, 회색, 청록, 핑크 계열)
  const bomMap = {
    ACTIVE: ["활성", "violet"],
    INACTIVE: ["비활성", "slate"],
    REGISTERING: ["등록 중", "cyan"],
    DISCONTINUED: ["단종", "pink"]
  };

  // 2. PO 관리 (청록, 파랑, 인디고, 주황 계열)
  const poMap = {
    COMPLETED: ["완료", "teal"],
    SHIPPED: ["출하중", "blue"],
    CONFIRMED: ["확정", "indigo"],
    PENDING: ["승인 대기", "orange"],
  };

  // 3. 원자재 관리 (그린, 옐로, 오렌지, 레드, 로즈 계열)
  const rawmatMap = {
    APPROVED: ["승인 완료", "green"],
    PENDING: ["승인 대기", "yellow"],
    IN_PROGRESS: ["진행중", "orange"],
    REJECTED: ["반려", "red"],
    REQUESTED: ["요청중", "rose"]
  };

  let m = {};
  if (type === "bom") {
    m = bomMap;
  } else if (type === "po") {
    m = poMap;
  } else if (type === "rawmat") {
    m = rawmatMap;
  } else {
    m = Object.assign({}, bomMap, poMap, rawmatMap, {
      DRAFT: ["작성중", "slate"],
      SUBMITTED: ["제출", "blue"],
      WAITING: ["대기중", "slate"],
      CLOSED: ["완료", "green"]
    });
  }

  const pair = m[s] || [s, "slate"];
  return <Chip text={pair[0]} color={pair[1]} />;
};
