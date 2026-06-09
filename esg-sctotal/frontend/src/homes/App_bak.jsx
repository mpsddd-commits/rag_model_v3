// [v1.3] 2026-06-04 — pageKey 추가(사이드 메뉴 동일 클릭 시 리프레시), navigateTo 콜백
import { useState, useEffect } from "react";
/* [이슈] CSS import 경로 변경: src/styles/ (PASTED 구조 반영) */
import '@styles/App.css';
import {
  /* [이슈] COMPANIES 더미 삭제 — 셀렉트박스 전환 시 DB에서 조회 */
  /* COMPANIES, */
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

const App = () => {
  const [page, setPage] = useState("dashboard");
  /* [v1.3] pageKey: 동일 메뉴 재클릭 시 컴포넌트 강제 리마운트 */
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

  /* [이슈] API 연동 state — 셀렉트박스 전환 시 DB 협력사 목록 조회 */
  const [apiCompanies, setApiCompanies] = useState([]);

  /* [v1.3] 사이드 메뉴 클릭 시 호출 — 모든 하위 상태 초기화 + pageKey 증가 */
  const navigateTo = (targetPage) => {
    setPage(targetPage);
    setPageKey(prev => prev + 1);
    setSelPartner(null);
    setSelBom(null);
    setUrgentRM(null);
    setIsRequestingRM(false);
    setMobileMenuOpen(false);
  };

  /* [이슈] 역할 변경 시 DB에서 협력사 목록 조회 (api.js 미사용, 직접 fetch) */
  useEffect(() => {
    fetch("/api/company/list", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userRole: userRole }),
    })
      .then((res) => res.json())
      .then((json) => {
        if (json.status && json.data?.companies) {
          setApiCompanies(json.data.companies);
        } else {
          setApiCompanies([]);
        }
      })
      .catch(() => setApiCompanies([]));
  }, [userRole]);

  const unread = notifications.filter((n) => !n.read).length;
  const displayPage = () => {
    return userRole === "3차 협력사" && page === "partner_list" ? "company_info" : page;
  };

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
      <RawMaterialRequest setIsRequestingRM={setIsRequestingRM} />
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
        displayPage={displayPage()}
        navigateTo={navigateTo} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <HeaderNav userRole={userRole} setUserRole={setUserRole}
          showNotif={showNotif} setShowNotif={setShowNotif}
          notifications={notifications} setNotifications={setNotifications}
          unread={unread} setMobileMenuOpen={setMobileMenuOpen}
          setPage={setPage} setSelPartner={setSelPartner}
          setSelBom={setSelBom} setUrgentRM={setUrgentRM}
          setIsRequestingRM={setIsRequestingRM} />
        <main className="flex-1 overflow-y-auto p-6" onClick={() => { if (showNotif) setShowNotif(false); }}>
          {pages[displayPage()]}
        </main>
      </div>
    </div>
  );
};

export default App;
