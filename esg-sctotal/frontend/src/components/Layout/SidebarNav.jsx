// [v1.3] 2026-06-04 — navigateTo로 동일 메뉴 클릭 시 리프레시
import React from "react";
import heroLogo from "@assets/logos/TVLogo.png";

const PARTNER_NAV_CATEGORIES = [
  {
    title: "■ 협력사 전용 메뉴",
    items: [
      { key: "company_info", label: "기업 정보 관리", badge: null },
      { key: "partner_list", label: "협력사 정보", badge: null },
      { key: "partner_rawmat", label: "원자재 관리", badge: null },
    ]
  }
];

const NAV_CATEGORIES = [
  {
    title: "■ 기준 및 협력사 정보",
    items: [
      { key: "dashboard", label: "메인 대시보드", badge: null },
      { key: "partner", label: "협력사 정보", badge: null },
      { key: "bom", label: "BOM 관리", badge: null },
    ]
  },
  {
    title: "■ 구매 및 자재 관리",
    items: [
      { key: "po", label: "PO 관리", badge: null },
      { key: "rawmat", label: "원자재 관리", badge: null },
    ]
  },
  {
    title: "■ 실사 및 평가",
    items: [
      { key: "risk", label: "리스크 현황", badge: null },
      { key: "inspection", label: "현장 실사", badge: "3건" },
    ]
  }
];

const SidebarNav = ({
  page,
  setPage,
  userRole,
  mobileMenuOpen,
  setMobileMenuOpen,
  setSelPartner,
  setSelBom,
  setUrgentRM,
  setIsRequestingRM,
  displayPage
}) => {
  return (
    <aside className={"fixed inset-y-0 left-0 z-50 w-56 bg-primary-green text-emerald-100 flex flex-col shrink-0 sidebar-transition md:relative md:translate-x-0 " +
      (mobileMenuOpen ? "translate-x-0" : "-translate-x-full")}>
      <div className="p-4 border-b border-emerald-600/30 flex items-center justify-between">
        <div
          onClick={() => {
            /* [v1.3] navigateTo 사용 — 동일 페이지에서도 리프레시 */
            const target = userRole !== "현대모비스" ? "company_info" : "dashboard";
            if (typeof navigateTo === "function") { navigateTo(target); }
            else { setPage(target); setSelPartner(null); setSelBom(null); setUrgentRM(null); setIsRequestingRM(false); setMobileMenuOpen(false); }
          }}
          style={{ cursor: "pointer" }}
          className="w-full flex items-center justify-center bg-white h-16 rounded-lg shadow-sm overflow-hidden"
        >
          <img src={heroLogo} alt="Triple Values" className="w-full h-full object-contain scale-[1.35]" />
        </div>
      </div>
      <nav className="flex-1 p-2 space-y-6 overflow-y-auto">
        {(userRole !== "현대모비스" ? PARTNER_NAV_CATEGORIES : NAV_CATEGORIES).map((cat, idx) => {
          return (
            <div key={idx} className="space-y-2">
              <p className="px-3 text-xs font-bold text-emerald-200 tracking-wide">{cat.title}</p>
              <div className="space-y-1">
                {cat.items.filter(n => {
                  if (userRole === "3차 협력사" && n.key === "partner_list") return false;
                  return true;
                }).map(n => {
                  const cls = "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition text-left " +
                    (displayPage === n.key ? "bg-primary-dark-green text-white font-bold" : "text-emerald-100 hover:bg-emerald-600/50 hover:text-white");
                  return (
                    <button key={n.key} onClick={() => { /* [v1.3] */ if (typeof navigateTo === "function") { navigateTo(n.key); } else { setPage(n.key); setSelPartner(null); setSelBom(null); setUrgentRM(null); setIsRequestingRM(false); setMobileMenuOpen(false); } }} className={cls}>
                      <span>{n.label}</span>
                      {n.badge && <span className="text-xs px-1.5 py-0.5 rounded-full font-bold bg-amber-400 text-white">{n.badge}</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
};

export default SidebarNav;
