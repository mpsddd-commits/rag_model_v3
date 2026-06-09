// src/homes/App.jsx
// ────────────────────────────────────────────────────────
// [v1.6] 2026-06-05 — 원청사 권한 오매핑 수정(tier=0→현대모비스), 세션 유지(localStorage)
// [v1.5] 2026-06-04 — 원청사 라우팅 수정(tier==0), 로그아웃, 셀렉트박스 제거
// [v1.4] 2026-06-04 — 첫 화면을 로그인으로 변경, 로그인 성공 시 메인 레이아웃 진입
// [v1.3] 2026-06-04 — pageKey 추가(사이드 메뉴 동일 클릭 시 리프레시), navigateTo 콜백
// ────────────────────────────────────────────────────────
import { useState, useEffect } from "react";
import '@styles/App.css';
import {
  PO_LIST, RAW_MATERIALS, BOM_LIST, NODE_HISTORY,
  INSPECTIONS_DATA, NOTIFICATIONS, NET_ZERO, ESG_INDICATORS
} from "@assets/data/masterData";
import { Chip, RChip, SChip } from "@components/Common/Chip";
import Kpi from "@components/Common/Kpi";
import Card from "@components/Common/Card";

import MainDashboard from "@admin/MainDashboard";
import PartnerList from "@admin/partners/PartnerList";
import PartnerDetail from "@admin/partners/PartnerDetail";
import BomList from "@admin/boms/BomList";
import BomDetail from "@admin/boms/BomDetail";
import POManagement from "@admin/pos/POManagement";
import RawMaterialList from "@admin/materials/RawMaterialList";
import RawMaterialRequest from "@admin/materials/RawMaterialRequest";
import UrgentRequest from "@admin/materials/UrgentRequest";
import RiskAssessment from "@admin/risks/RiskAssessment";
import FieldInspection from "@admin/inspections/FieldInspection";
import CompanyInfo from "@partners/CompanyInfo";
import PartnerSubList from "@partners/PartnerSubList";
import MaterialManage from "@partners/MaterialManage";
import HeaderNav from "@components/Layout/HeaderNav";
import SidebarNav from "@components/Layout/SidebarNav";
/* [v1.4] 로그인 컴포넌트 import */
import Login from "@/homes/logins/Login";

const App = () => {
  /* [v1.4] 로그인 상태 — false면 로그인 화면, true면 메인 레이아웃 */
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginData, setLoginData] = useState(null);

  const [page, setPage] = useState("dashboard");
  const [pageKey, setPageKey] = useState(0);
  const [showNotif, setShowNotif] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userRole, setUserRole] = useState("현대모비스");
  const [partnerRegistration, setPartnerRegistration] = useState({});
  const [selPartner, setSelPartner] = useState(null);
  const [selBom, setSelBom] = useState(null);
  const [isRequestingRM, setIsRequestingRM] = useState(false);
  const [urgentRM, setUrgentRM] = useState(null);
  const [notifications, setNotifications] = useState(NOTIFICATIONS);
  const [apiCompanies, setApiCompanies] = useState([]);

  /* [v1.4] 로그인 성공 핸들러 — 로그인 응답 데이터로 역할 설정 후 메인 진입 */
  const handleLoginSuccess = (data) => {
    setLoginData(data);
    /* [v1.6] 버그1 수정: tier=0이면 반드시 "현대모비스" (DB tier_label='원청사'와 무관) */
    const isOem = Number(data?.tier) === 0;
    if (isOem) {
      setUserRole("현대모비스");
    } else if (data?.tier_label) {
      setUserRole(data.tier_label);
    }
    setPage(isOem ? "dashboard" : "company_info");

    /* [v1.6] 버그2 수정: localStorage에 로그인 데이터 저장 → 새로고침 시 복원 */
    try {
      localStorage.setItem("esg_login", JSON.stringify({
        ...data,
        userRole: isOem ? "현대모비스" : (data?.tier_label || ""),
        page: isOem ? "dashboard" : "company_info",
      }));
    } catch(e) { console.error("localStorage 저장 실패:", e); }

    setIsLoggedIn(true);
  };

  /* [v1.5] 로그아웃 핸들러 — Redis/Cookie 초기화 후 로그인 화면 이동 */
  const handleLogout = () => {
    fetch("/api/auth/logout", { method: "POST" })
      .then(() => {
        // 브라우저 쿠키 삭제
        document.cookie.split(";").forEach((c) => {
          document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
      })
      .catch(() => {})
      .finally(() => {
        setIsLoggedIn(false);
        localStorage.removeItem("esg_login");
        setLoginData(null);
        setPage("dashboard");
        setUserRole("현대모비스");
      });
  };

  const navigateTo = (targetPage) => {
    setPage(targetPage);
    setPageKey(prev => prev + 1);
    setSelPartner(null);
    setSelBom(null);
    setUrgentRM(null);
    setIsRequestingRM(false);
    setMobileMenuOpen(false);
  };

  /* [v1.6] 버그2 수정: 앱 마운트 시 localStorage에서 세션 복원 (새로고침 대응) */
  useEffect(() => {
    if (isLoggedIn) return; // 이미 로그인 상태면 스킵
    try {
      const saved = localStorage.getItem("esg_login");
      if (saved) {
        const data = JSON.parse(saved);
        setLoginData(data);
        setUserRole(data.userRole || "현대모비스");
        setPage(data.page || "dashboard");
        setIsLoggedIn(true);
      }
    } catch(e) { console.error("세션 복원 실패:", e); }
  }, []);

  useEffect(() => {
    if (!isLoggedIn) return;
    fetch("/api/company/list", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userRole: userRole }),
    })
      .then((res) => res.json())
      .then((json) => {
        if (json.status && json.data?.companies) setApiCompanies(json.data.companies);
        else setApiCompanies([]);
      })
      .catch(() => setApiCompanies([]));
  }, [userRole, isLoggedIn]);

  /* [v1.4] 로그인 전이면 로그인 화면 표시 */
  if (!isLoggedIn) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  /* ── 로그인 후 메인 레이아웃 ── */
  const unread = notifications.filter((n) => !n.read).length;
  const displayPage = () => (userRole === "3차 협력사" && page === "partner_list") ? "company_info" : page;
  const dp = displayPage();

  const pages = {
    dashboard: <MainDashboard key={pageKey} />,
    partner: selPartner === null ? (
      <PartnerList key={pageKey} userRole={userRole} partnerRegistration={partnerRegistration}
        setSelPartner={setSelPartner} apiCompanies={apiCompanies} />
    ) : (
      <PartnerDetail partner={selPartner} partnerRegistration={partnerRegistration}
        onBack={() => setSelPartner(null)} />
    ),
    company_info: (
      <CompanyInfo key={pageKey} userRole={userRole} partnerRegistration={partnerRegistration}
        setPartnerRegistration={setPartnerRegistration} />
    ),
    po: <POManagement key={pageKey} />,
    rawmat: urgentRM ? (
      <UrgentRequest urgentRM={urgentRM} setUrgentRM={setUrgentRM} />
    ) : isRequestingRM ? (
      <RawMaterialRequest setIsRequestingRM={setIsRequestingRM}
          handleLogout={handleLogout}
          loginData={loginData} />
    ) : (
      <RawMaterialList key={pageKey} userRole={userRole} setIsRequestingRM={setIsRequestingRM} setUrgentRM={setUrgentRM} />
    ),
    risk: <RiskAssessment key={pageKey} />,
    inspection: <FieldInspection key={pageKey} />,
    bom: selBom === null ? <BomList key={pageKey} setSelBom={setSelBom} /> : <BomDetail selBom={selBom} setSelBom={setSelBom} />,
    partner_list: (
      <PartnerSubList key={pageKey} userRole={userRole} partnerRegistration={partnerRegistration} apiCompanies={apiCompanies} />
    ),
    partner_rawmat: <MaterialManage key={pageKey} userRole={userRole} />,
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans">
      {mobileMenuOpen && <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={() => setMobileMenuOpen(false)} />}
      <SidebarNav page={page} setPage={setPage} userRole={userRole}
        mobileMenuOpen={mobileMenuOpen} setMobileMenuOpen={setMobileMenuOpen}
        setSelPartner={setSelPartner} setSelBom={setSelBom}
        setUrgentRM={setUrgentRM} setIsRequestingRM={setIsRequestingRM}
        displayPage={dp}
        navigateTo={navigateTo} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <HeaderNav userRole={userRole} setUserRole={setUserRole}
          showNotif={showNotif} setShowNotif={setShowNotif}
          notifications={notifications} setNotifications={setNotifications}
          unread={unread} setMobileMenuOpen={setMobileMenuOpen}
          setPage={setPage} setSelPartner={setSelPartner}
          setSelBom={setSelBom} setUrgentRM={setUrgentRM}
          setIsRequestingRM={setIsRequestingRM}
          handleLogout={handleLogout}
          loginData={loginData} />
        <main className="flex-1 overflow-y-auto p-6" onClick={() => { if (showNotif) setShowNotif(false); }}>
          {pages[dp]}
        </main>
      </div>
    </div>
  );
};

export default App;
