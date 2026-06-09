// src/components/Layout/HeaderNav.jsx
// ────────────────────────────────────────────────────────
// [v1.5] 2026-06-04 — 셀렉트박스 제거, 로그아웃 버튼 추가, loginData 표시
// [v1.0] 초기 버전 — 역할 셀렉트 박스 + 알림 제어
// ────────────────────────────────────────────────────────

import { useState, useRef, useEffect } from "react";

const HeaderNav = ({
  userRole,
  setUserRole,
  showNotif,
  setShowNotif,
  notifications,
  setNotifications,
  unread,
  setMobileMenuOpen,
  setPage,
  setSelPartner,
  setSelBom,
  setUrgentRM,
  setIsRequestingRM,
  /* [v1.5] 로그아웃 핸들러 + 로그인 데이터 */
  handleLogout,
  loginData,
}) => {
  const notifRef = useRef(null);

  useEffect(() => {
    const handleClick = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotif(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      {/* 좌측: 시스템 타이틀 */}
      <div className="flex items-center gap-3">
        <button onClick={() => setMobileMenuOpen(true)} className="md:hidden text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <h1 className="text-base font-black text-gray-800 hidden md:block">ESG 공급망 관리 시스템</h1>
      </div>

      {/* 우측: 알림 + 회사명/역할 + 로그아웃 */}
      <div className="flex items-center gap-4">
        {/* 알림 아이콘 */}
        <div className="relative" ref={notifRef}>
          <button onClick={() => setShowNotif(!showNotif)} className="relative text-gray-500 hover:text-gray-700">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            {unread > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                {unread}
              </span>
            )}
          </button>
          {showNotif && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-xl border border-gray-100 z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
                <span className="font-bold text-sm text-gray-800">알림 센터</span>
                <button onClick={markAllRead} className="text-xs text-[#03a94d] font-bold">전체 읽음</button>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {notifications.length > 0 ? notifications.slice(0, 5).map((n, i) => (
                  <div key={i} className={"px-4 py-3 border-b border-gray-50 text-xs " + (n.read ? "bg-white" : "bg-emerald-50")}>
                    <p className="font-bold text-gray-700">{n.title}</p>
                    <p className="text-gray-400 mt-0.5">{n.time}</p>
                  </div>
                )) : (
                  <p className="text-center text-gray-400 text-xs py-6">알림이 없습니다.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* [v1.5] 회사명/역할 표시 — 셀렉트박스 제거 */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-gray-700">
            {loginData?.company_name || userRole}
            <span className="text-xs text-gray-400 ml-1">
              ({loginData?.tier_label || (loginData?.tier === 0 ? "원청사 관리자" : userRole)})
            </span>
          </span>

          {/* [v1.5] 로그아웃 버튼 */}
          <button
            onClick={() => {
              if (confirm("로그아웃 하시겠습니까?")) {
                if (typeof handleLogout === "function") handleLogout();
              }
            }}
            className="px-3 py-1.5 text-xs font-bold text-gray-500 border border-gray-200 bg-white hover:bg-gray-50 rounded-lg transition"
          >
            로그아웃
          </button>
        </div>
      </div>
    </header>
  );
};

export default HeaderNav;
