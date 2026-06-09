// [v1.3] 2026-06-04 — 상세 화면 삭제 버튼+Confirm, 유효성 검사 기존 파일 합산, 수정 화면 파일 바인딩
import React, { useState, useEffect } from "react";
/* [이슈] COMPANIES 더미 삭제 — API에서 기업정보 조회 */
/* import { COMPANIES } from "@assets/data/masterData"; */
import Card from "@components/Common/Card";
import { Chip } from "@components/Common/Chip";

const ROLE_MAP = {
  "1차 협력사": "NOV-001",
  "2차 협력사": "KRM-001",
  "3차 협력사": "COM-001"
};

const CERT_LABELS = {
  iso14001: "ISO 14001 (환경경영인증)",
  iso45001: "ISO 45001 (안전보건인증)",
  iatf: "IATF 16949 (품질경영인증)",
  rba: "RBA (책임 비즈니스 인증)",
  rmap: "RMAP (책임 광물 보증 인증)",
  cmrt: "CMRT (분쟁광물 보고 인증)",
  emat: "EMAT (배터리·광물 추적 보고 인증)"
};

const CompanyInfo = ({ userRole, partnerRegistration, setPartnerRegistration }) => {
  const partnerId = ROLE_MAP[userRole] || "NOV-001";
  /* [이슈] COMPANIES.find 더미 삭제 — useEffect에서 API 조회로 대체 */
  const [apiCompany, setApiCompany] = useState(null);

  // viewMode: "welcome" | "form" | "detail"
  /* [이슈] API 기업정보 우선 체크, partnerRegistration fallback */
  const hasRegistered = apiCompany !== null || !!partnerRegistration[partnerId];
  const [viewMode, setViewMode] = useState("welcome");

  /* [이슈] Form state 초기값 빈 폼 — useEffect에서 API 결과로 채움 */
  const [form, setForm] = useState({
    company_name: "", ceo_name: "", biz_no: "", founded: "", address: "",
    size: "", country: "",
    scope1: "", scope2: "", feoc_ratio: "", trir: "",
    iso14001: "", iso45001: "", iatf: "", rba: "", rmap: "", cmrt: "", emat: "",
    coc_file: "", self_assess_file: "", evidence_files: [], cert_files: []
  });

  /* [이슈] 파일명 state 초기값 빈 값 — useEffect에서 설정 */
  const [cocFileName, setCocFileName] = useState("");
  const [selfAssessFileName, setSelfAssessFileName] = useState("");
  /* [이슈-수정] 실제 File 객체 보존 state 추가 — 파일명만 저장하던 버그 수정 */
  const [cocFileObj, setCocFileObj] = useState(null);
  const [selfAssessFileObj, setSelfAssessFileObj] = useState(null);
  /* [이슈-수정] 증빙/인증 File 객체 배열 보존 — 다중 업로드용 */
  const [evidenceFileObjs, setEvidenceFileObjs] = useState([]);
  const [certFileObjs, setCertFileObjs] = useState([]);
  /* [이슈] 상세 화면 증빙탭 — API에서 4영역 분류 파일 조회 */
  const [categorizedFiles, setCategorizedFiles] = useState({ coc: [], selfassess: [], evidence: [], cert: [] });
  const [evidenceFileNames, setEvidenceFileNames] = useState([]);
  const [certFileNames, setCertFileNames] = useState([]);
  const [detailTab, setDetailTab] = useState("info"); // "info" | "evidence" | "factory"
  /* [이슈] 공장 관리 state 추가 — 요구사항 3번 */
  const [factories, setFactories] = useState([]);
  const [factoryForm, setFactoryForm] = useState({
    factoryName: "", factoryLocation: "", operationStatus: "가동중",
    utilizationRate: 0, scope1Emissions: 0, scope2Emissions: 0,
    feocRawMaterialRatio: 0, trirSafetyRate: 0, note: ""
  });
  const [factorySummary, setFactorySummary] = useState(null);
  const [editingFactoryId, setEditingFactoryId] = useState(null);
  const [showFactoryForm, setShowFactoryForm] = useState(false);
  /* [이슈] 자가진단 버전 state 추가 — 요구사항 1번 */
  const [selfAssessVersions, setSelfAssessVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [selfAssessAnswers, setSelfAssessAnswers] = useState([]);

  useEffect(() => {
    const nextPartnerId = ROLE_MAP[userRole] || "NOV-001";
    setDetailTab("info");

    /* [이슈] useEffect에서 API 호출 추가 — DB에서 기업정보 조회 */
    fetch(`/api/company/${nextPartnerId}`).then((res) => res.json()).then((json) => {
      if (json.status && json.data && json.data.company) {
        const co = json.data.company;
        setApiCompany(co);
        setViewMode("detail");
        setForm({
          company_name: co.company_name || "", ceo_name: co.ceo_name || "",
          biz_no: co.biz_no || "", founded: co.founded || "",
          address: co.address || "", size: co.size || "", country: co.country || "",
          scope1: co.scope1 || "", scope2: co.scope2 || "",
          feoc_ratio: co.feoc_ratio || "", trir: co.trir || "",
          iso14001: co.iso14001 || "", iso45001: co.iso45001 || "",
          iatf: co.iatf || "", rba: co.rba || "",
          rmap: co.rmap || "", cmrt: co.cmrt || "", emat: co.emat || "",
          coc_file: "", self_assess_file: "", evidence_files: [], cert_files: []
        });
        /* [이슈] 공장 목록 + 자가진단 버전 목록 API 응답에서 추출 */
        setFactories(json.data.factories || []);
        setSelfAssessVersions(json.data.versions || []);
        setSelfAssessAnswers(json.data.selfAssessAnswers || []);
        if (json.data.versions?.length > 0) {
          setSelectedVersion(json.data.currentVersion || json.data.versions[0].version);
        }
        /* [이슈] 상세 화면 증빙탭 — 4영역 분류 파일 목록 조회 */
        fetch(`/api/company/${nextPartnerId}/files`)
          .then(r => r.json())
          .then(fj => { if (fj.status) setCategorizedFiles(fj.data || { coc: [], selfassess: [], evidence: [], cert: [] }); })
          .catch(() => {});
      } else {
        /* [이슈] API에 없으면 partnerRegistration fallback → 없으면 welcome */
        setApiCompany(null);
        const nextHasRegistered = !!partnerRegistration[nextPartnerId];
        if (nextHasRegistered) {
          setViewMode("detail");
          const saved = partnerRegistration[nextPartnerId];
          setForm(Object.assign({
            company_name: "", ceo_name: "", biz_no: "", founded: "", address: "",
            size: "", country: "",
            scope1: "", scope2: "", feoc_ratio: "", trir: "",
            iso14001: "", iso45001: "", iatf: "", rba: "", rmap: "", cmrt: "", emat: "",
            coc_file: saved.cocFileName || "", self_assess_file: saved.selfAssessFileName || "",
            evidence_files: saved.evidenceFileNames || [], cert_files: saved.certFileNames || []
          }, saved));
          setCocFileName(saved.cocFileName || "");
          setSelfAssessFileName(saved.selfAssessFileName || "");
          setEvidenceFileNames(saved.evidenceFileNames || []);
          setCertFileNames(saved.certFileNames || []);
        } else {
          setViewMode("welcome");
          setForm({
            company_name: "", ceo_name: "", biz_no: "", founded: "", address: "",
            size: "", country: "",
            scope1: "", scope2: "", feoc_ratio: "", trir: "",
            iso14001: "", iso45001: "", iatf: "", rba: "", rmap: "", cmrt: "", emat: "",
            coc_file: "", self_assess_file: "", evidence_files: [], cert_files: []
          });
          setCocFileName(""); setSelfAssessFileName(""); setEvidenceFileNames([]); setCertFileNames([]);
        }
      }
    }).catch(() => {
      setApiCompany(null);
      setViewMode("welcome");
    });
  }, [userRole]);

  const handleFieldChange = (field) => (e) => {
    const val = e.target.value;
    setForm(prev => {
      const next = Object.assign({}, prev);
      next[field] = val;
      return next;
    });
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();

    // 유효성 검사
    const requiredFields = [
      "company_name", "ceo_name", "biz_no", "founded", "address",
      "scope1", "scope2", "feoc_ratio", "trir"
    ];
    for (let f of requiredFields) {
      if (!form[f]) {
        alert("모든 기본 정보 및 ESG 지표 항목을 입력해주세요.");
        return;
      }
    }

    // 7대 글로벌 인증 유효성 검사
    const certFields = ["iso14001", "iso45001", "iatf", "rba", "rmap", "cmrt", "emat"];
    for (let c of certFields) {
      if (!form[c]) {
        alert("7대 글로벌 ESG 인증 여부를 모두 선택해주세요.");
        return;
      }
    }

    /* [v1.3] 유효성 검사 — 기존 파일(categorizedFiles) + 신규 파일 합산 체크
       기존 DB 파일이 있거나 새 파일을 선택했으면 통과, 둘 다 없으면 Alert */

    // 글로벌 인증 증빙서류 유효성 검사
    const currentCerts = form.cert_files && form.cert_files.length > 0 ? form.cert_files : certFileNames;
    const existingCerts = (categorizedFiles.cert || []).length;
    if ((!currentCerts || currentCerts.length === 0) && existingCerts === 0) {
      alert("글로벌 인증 증빙서류를 최소 1개 이상 업로드해야 합니다.");
      return;
    }

    // 자가진단 완료 서류 유효성 검사
    const existingSelfAssess = (categorizedFiles.selfassess || []).length;
    if (!form.self_assess_file && !selfAssessFileName && existingSelfAssess === 0) {
      alert("자가진단 완료 서류 파일을 업로드해주세요.");
      return;
    }

    // 증빙자료 유효성 검사
    const currentEvidences = form.evidence_files && form.evidence_files.length > 0 ? form.evidence_files : evidenceFileNames;
    const existingEvidence = (categorizedFiles.evidence || []).length;
    if ((!currentEvidences || currentEvidences.length === 0) && existingEvidence === 0) {
      alert("증빙자료 파일을 1개 이상 업로드해주세요.");
      return;
    }

    // 행동강령 서약서 유효성 검사
    const existingCoc = (categorizedFiles.coc || []).length;
    if (!form.coc_file && !cocFileName && existingCoc === 0) {
      alert("행동강령 준수 서약서 파일을 업로드해주세요.");
      return;
    }

    const updatedData = Object.assign({}, form, {
      cocFileName: form.coc_file || cocFileName,
      selfAssessFileName: form.self_assess_file || selfAssessFileName,
      evidenceFileNames: currentEvidences,
      certFileNames: currentCerts
    });

    /* [이슈] API 호출 추가 — 기업정보 등록/수정을 DB에 저장 */
    const apiData = {
      partnerId: partnerId,
      companyName: form.company_name, ceoName: form.ceo_name,
      bizNo: form.biz_no, founded: form.founded,
      address: form.address, size: form.size, country: form.country,
      scope1: parseInt(form.scope1) || 0, scope2: parseInt(form.scope2) || 0,
      feocRatio: parseFloat(form.feoc_ratio) || 0, trir: parseFloat(form.trir) || 0,
      iso14001: form.iso14001, iso45001: form.iso45001, iatf: form.iatf,
      rba: form.rba, rmap: form.rmap, cmrt: form.cmrt, emat: form.emat,
      tier: ROLE_MAP[userRole] ? (userRole === "1차 협력사" ? 1 : userRole === "2차 협력사" ? 2 : 3) : 0,
      tierLabel: userRole, parentId: "",
    };
    /* [이슈-수정] isEdit 판별도 hasRegistered로 통일 — apiCompany null 경로 대응 */
    const isEdit = hasRegistered;
    /* [이슈] api.js 미사용 — 직접 fetch 호출 */
    const apiUrl = isEdit ? `/api/company/${partnerId}` : `/api/company`;
    const apiMethod = isEdit ? "PUT" : "POST";
    const apiFn = fetch(apiUrl, {
      method: apiMethod,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(apiData),
    }).then((res) => res.json());
    apiFn.then((json) => {
      if (json.status) {
        setPartnerRegistration(prev => {
          const next = Object.assign({}, prev);
          next[partnerId] = updatedData;
          return next;
        });
        setCocFileName(updatedData.coc_file);
        setSelfAssessFileName(updatedData.self_assess_file);
        setEvidenceFileNames(updatedData.evidence_files);
        setCertFileNames(updatedData.cert_files);
        /* [이슈] API 저장 후 apiCompany를 snake_case 키로 설정 — detail 뷰 호환 */
        setApiCompany({
          partner_id: partnerId,
          company_name: form.company_name, ceo_name: form.ceo_name,
          biz_no: form.biz_no, founded: form.founded,
          address: form.address, size: form.size, country: form.country,
          scope1: form.scope1, scope2: form.scope2,
          feoc_ratio: form.feoc_ratio, trir: form.trir,
          iso14001: form.iso14001, iso45001: form.iso45001, iatf: form.iatf,
          rba: form.rba, rmap: form.rmap, cmrt: form.cmrt, emat: form.emat,
          cocFileName: updatedData.cocFileName,
          selfAssessFileName: updatedData.selfAssessFileName,
          evidenceFileNames: updatedData.evidenceFileNames,
          certFileNames: updatedData.certFileNames,
        });
        setViewMode("detail");
        alert("기업 정보가 성공적으로 " + (isEdit ? "수정" : "등록") + "되었습니다.");

        /* [이슈-수정] 파일 업로드를 Promise.all로 처리 → 완료 후 상세 화면 파일 재조회
           등록/수정 화면 모두 동일한 파일 업로드 로직 적용 */
        const uploadPromises = [];

        // CoC 서약서 업로드
        if (cocFileObj) {
          const cocFd = new FormData();
          cocFd.append("partnerId", partnerId);
          cocFd.append("file", cocFileObj);
          uploadPromises.push(
            fetch("/api/company/file/coc", { method: "POST", body: cocFd })
              .then(r => r.json())
              .then(r => { if (r.status) { setCocFileObj(null); } })
          );
        }
        // 자가진단 PDF 업로드 (OCR + 버전업)
        if (selfAssessFileObj) {
          const saFd = new FormData();
          saFd.append("partnerId", partnerId);
          saFd.append("file", selfAssessFileObj);
          uploadPromises.push(
            fetch("/api/company/file/selfassess", { method: "POST", body: saFd })
              .then(r => r.json())
              .then(r => {
                if (r.status) {
                  setSelfAssessFileObj(null);
                  alert("자가진단 OCR 완료 (v" + (r.data?.version || 1) + ", " + (r.data?.total_answers || 0) + "개 답변)");
                } else {
                  alert("자가진단 OCR 실패: " + (r.message || ""));
                }
              })
          );
        }
        // 증빙자료 다중 업로드
        if (evidenceFileObjs.length > 0) {
          const evFd = new FormData();
          evFd.append("partnerId", partnerId);
          evidenceFileObjs.forEach(f => evFd.append("files", f));
          uploadPromises.push(
            fetch("/api/company/file/evidence", { method: "POST", body: evFd })
              .then(r => r.json())
              .then(r => { if (r.status) setEvidenceFileObjs([]); })
          );
        }
        // 글로벌 인증 증빙 다중 업로드
        if (certFileObjs.length > 0) {
          const certFd = new FormData();
          certFd.append("partnerId", partnerId);
          certFileObjs.forEach(f => certFd.append("files", f));
          uploadPromises.push(
            fetch("/api/company/file/cert", { method: "POST", body: certFd })
              .then(r => r.json())
              .then(r => { if (r.status) setCertFileObjs([]); })
          );
        }

        /* [이슈-수정] 모든 파일 업로드 완료 후 상세 화면 파일 목록 재조회
           → 상세 화면 증빙 탭에서 최신 파일 데이터가 바인딩되도록 보장 */
        if (uploadPromises.length > 0) {
          Promise.all(uploadPromises)
            .then(() => {
              fetch(`/api/company/${partnerId}/files`)
                .then(r => r.json())
                .then(fj => {
                  if (fj.status) setCategorizedFiles(fj.data || { coc: [], selfassess: [], evidence: [], cert: [] });
                });
            })
            .catch(e => console.error("파일 업로드 오류:", e));
        }
      } else {
        alert(json.message || "저장 실패. 다시 시도해주세요.");
      }
    }).catch((err) => {
      alert("서버 연결 오류: " + err.message);
    });
  };

  // 1. 웰컴 화면
  if (viewMode === "welcome") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[75vh] w-full text-center px-4">
        <Card className="max-w-2xl p-10 bg-white border border-gray-150 shadow-md rounded-2xl">
          <div className="w-16 h-16 bg-[#03a94d]/10 rounded-full flex items-center justify-center mx-auto mb-6 text-[#03a94d] text-3xl font-bold">
            ✓
          </div>
          <h1 className="text-2xl font-black text-gray-900 mb-4">ESG 공급망 관리 파트너 포털에 오신 것을 환영합니다</h1>
          <p className="text-gray-500 text-sm leading-relaxed mb-8">
            현재 {userRole}의 기업 정보가 등록되어 있지 않습니다.<br />
            플랫폼 내 원자재 관리 및 공급망 대응을 시작하기 위해 기업 기본 정보와 글로벌 ESG 준수 현황을 먼저 등록해주시기 바랍니다.
          </p>
          <button
            onClick={() => setViewMode("form")}
            className="px-8 py-3 text-white text-sm font-bold rounded-lg transition hover:opacity-90 shadow-sm"
            style={{ backgroundColor: "#03a94d" }}
          >
            기업 정보 등록하기
          </button>
        </Card>
      </div>
    );
  }

  // 2. 등록 및 수정 폼 화면
  if (viewMode === "form") {
    const isEditMode = hasRegistered;
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-black text-gray-900">
            {isEditMode ? "기업 정보 수정" : "신규 기업 정보 등록"}
          </h1>
          <button
            onClick={() => {
              if (isEditMode) {
                setViewMode("detail");
              } else {
                setViewMode("welcome");
              }
            }}
            className="px-4 py-2 bg-slate-100 text-slate-700 text-xs rounded-lg hover:bg-slate-200 transition font-bold"
          >
            {isEditMode ? "← 돌아가기" : "취소"}
          </button>
        </div>

        <form onSubmit={handleFormSubmit} className="space-y-6">
          <Card className="p-6 bg-white border border-gray-150">
            <h2 className="text-base font-bold text-gray-900 border-b pb-3 mb-5" style={{ fontSize: "16px" }}>
              기본 정보 및 ESG 성과 지표 입력
            </h2>

            {/* 2열 그리드 레이아웃 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* 기본 정보 그룹 */}
              <div className="space-y-4">
                <h3 className="text-xs font-extrabold text-[#03a94d] uppercase tracking-wider">기본 기업 정보</h3>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">기업명 *</label>
                  <input
                    type="text"
                    placeholder="예: (주)노벨리스코리아"
                    value={form.company_name}
                    onChange={handleFieldChange("company_name")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">대표자명 *</label>
                  <input
                    type="text"
                    placeholder="예: 홍길동"
                    value={form.ceo_name}
                    onChange={handleFieldChange("ceo_name")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">사업자등록번호 *</label>
                  <input
                    type="text"
                    placeholder="예: 128-81-33210"
                    value={form.biz_no}
                    onChange={handleFieldChange("biz_no")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">설립일 *</label>
                  <input
                    type="date"
                    value={form.founded}
                    onChange={handleFieldChange("founded")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">소재지 *</label>
                  <input
                    type="text"
                    placeholder="예: 서울시 강남구 테헤란로 123"
                    value={form.address}
                    onChange={handleFieldChange("address")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-bold text-gray-600 block mb-1">기업 규모 *</label>
                    <select
                      value={form.size}
                      onChange={handleFieldChange("size")}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30 bg-white"
                    >
                      <option value="" disabled>규모 선택</option>
                      <option value="대기업">대기업</option>
                      <option value="중견기업">중견기업</option>
                      <option value="중소기업">중소기업</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-bold text-gray-600 block mb-1">소재 국가 *</label>
                    <input
                      type="text"
                      placeholder="예: 대한민국"
                      value={form.country}
                      onChange={handleFieldChange("country")}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                    />
                  </div>
                </div>

              </div>

              {/* ESG 지표 그룹 */}
              <div className="space-y-4 md:border-l md:pl-5 md:border-gray-100">
                <h3 className="text-xs font-extrabold text-[#03a94d] uppercase tracking-wider">핵심 ESG 지표</h3>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">Scope 1 배출량 (tCO₂e) *</label>
                  <input
                    type="number"
                    placeholder="예: 82000"
                    value={form.scope1}
                    onChange={handleFieldChange("scope1")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">Scope 2 배출량 (tCO₂e) *</label>
                  <input
                    type="number"
                    placeholder="예: 45000"
                    value={form.scope2}
                    onChange={handleFieldChange("scope2")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">FEOC 원료 비중 (%) *</label>
                  <input
                    type="number"
                    step="0.1"
                    placeholder="예: 12.5"
                    value={form.feoc_ratio}
                    onChange={handleFieldChange("feoc_ratio")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-gray-600 block mb-1">TRIR 산업안전율 *</label>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="예: 0.15"
                    value={form.trir}
                    onChange={handleFieldChange("trir")}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30"
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* 1열 세로 배열: 자가진단 및 글로벌 인증 증빙 */}
          <Card className="p-6 bg-white border border-gray-150">
            <h2 className="text-base font-bold text-gray-900 border-b pb-3 mb-5" style={{ fontSize: "16px" }}>
              글로벌 인증 준수 현황
            </h2>
            <div className="space-y-4">
              {Object.keys(CERT_LABELS).map(key => (
                <div key={key} className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                  <span className="text-xs font-bold text-gray-700">{CERT_LABELS[key]} *</span>
                  <div className="flex gap-4 mt-2 sm:mt-0">
                    <label className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
                      <input
                        type="radio"
                        name={key}
                        value="Y"
                        checked={form[key] === "Y"}
                        onChange={handleFieldChange(key)}
                        className="text-[#03a94d] focus:ring-[#03a94d]/30"
                      />
                      취득/이행 (Y)
                    </label>
                    <label className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
                      <input
                        type="radio"
                        name={key}
                        value="N"
                        checked={form[key] === "N"}
                        onChange={handleFieldChange(key)}
                        className="text-[#03a94d] focus:ring-[#03a94d]/30"
                      />
                      미취득/미이행 (N)
                    </label>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-gray-100 mt-5 pt-4">
              <label className="text-xs font-bold text-gray-600 block mb-1">글로벌 인증 증빙서류 업로드 *</label>
              <p className="text-xs text-gray-400 mb-3 leading-normal">
                보유하신 글로벌 인증(환경, 품질, 안전, 분쟁광물 등)의 증빙서류 파일들을 업로드해 주십시오. (다중 선택 가능)
              </p>

              <div className="w-full border border-gray-200 rounded-lg p-2 bg-white flex items-center gap-3 mb-2">
                <button
                  type="button"
                  onClick={() => document.getElementById("cert-file-input").click()}
                  className="text-xs px-3.5 py-1.5 border border-gray-300 bg-white hover:bg-gray-50 rounded-md font-bold text-gray-700 transition shrink-0"
                >
                  파일 선택
                </button>
                <span className="text-xs text-gray-500">
                  파일 선택 파일 {(form.cert_files && form.cert_files.length > 0 ? form.cert_files.length : (certFileNames ? certFileNames.length : 0))}개
                </span>
                <input
                  id="cert-file-input"
                  type="file"
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files);
                    if (files.length > 0) {
                      const newNames = files.map(f => f.name);
                      setForm(prev => {
                        const existing = prev.cert_files || [];
                        const combined = Array.from(new Set([...existing, ...newNames]));
                        return Object.assign({}, prev, { cert_files: combined });
                      });
                      setCertFileNames(prev => Array.from(new Set([...prev, ...newNames])));
                      /* [이슈-수정] 실제 File 객체 보존 — 다중 업로드용 */
                      setCertFileObjs(prev => [...prev, ...files]);
                    }
                  }}
                  className="hidden"
                />
              </div>

              {((form.cert_files && form.cert_files.length > 0) || (certFileNames && certFileNames.length > 0)) && (
                <div className="mt-3 space-y-1.5">
                  <p className="text-xs font-bold text-gray-600">선택된 증빙서류 목록:</p>
                  <div className={(form.cert_files && form.cert_files.length > 0 ? form.cert_files.length : certFileNames.length) >= 7 ? "max-h-48 overflow-y-auto pr-1" : ""}>
                    {(form.cert_files && form.cert_files.length > 0 ? form.cert_files : certFileNames).map((fname, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-gray-200/60 text-xs mb-1.5 last:mb-0">
                        <span className="font-semibold text-gray-700">{fname}</span>
                        <button
                          type="button"
                          onClick={() => {
                            const currentList = form.cert_files && form.cert_files.length > 0 ? form.cert_files : certFileNames;
                            const filtered = currentList.filter((_, i) => i !== idx);
                            setForm(prev => Object.assign({}, prev, { cert_files: filtered }));
                            setCertFileNames(filtered);
                          }}
                          className="text-red-500 hover:text-red-700 font-bold ml-2 text-xs"
                        >
                          삭제
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* 1열 세로 배열: 자가진단 및 증빙 자료 제출 */}
          <Card className="p-6 bg-white border border-gray-150">
            <h2 className="text-base font-bold text-gray-900 border-b pb-3 mb-3" style={{ fontSize: "16px" }}>
              자가진단 및 증빙 자료 제출
            </h2>
            <p className="text-xs text-gray-500 mb-4 leading-normal">
              공급망 내 ESG 규제 리스크 방지를 위해 협력사의 자가진단 및 증빙자료 제출을 필수로 지정하고 있습니다. 양식을 다운로드하여 작성 후 업로드해주십시오.
            </p>
            <div className="p-4 bg-slate-50 rounded-xl border border-gray-200/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <p className="text-xs font-bold text-gray-800">
                  {userRole === "3차 협력사" ? "3차 협력사용 자가진단 파일.xlsx" : userRole === "2차 협력사" ? "2차 협력사용 자가진단 파일.xlsx" : "1차 협력사용 자가진단 파일.xlsx"}
                </p>
                <p className="text-[11px] text-gray-400">Excel 양식 파일</p>
              </div>
              <button
                type="button"
                onClick={() => alert(`${userRole === "3차 협력사" ? "3차 협력사용 자가진단 파일.xlsx" : userRole === "2차 협력사" ? "2차 협력사용 자가진단 파일.xlsx" : "1차 협력사용 자가진단 파일.xlsx"} 양식 파일 다운로드가 완료되었습니다.`)}
                className="text-xs px-3.5 py-2 border border-gray-250 bg-white hover:bg-gray-100 rounded-lg font-bold text-gray-700 transition"
              >
                양식 다운로드
              </button>
            </div>
            <div className="mb-4">
              <label className="text-xs font-bold text-gray-600 block mb-1.5">자가진단 완료 서류 업로드 *</label>
              <div className="w-full border border-gray-200 rounded-lg p-2 bg-white flex items-center gap-3 mb-2">
                <button
                  type="button"
                  onClick={() => document.getElementById("self-assess-file-input").click()}
                  className="text-xs px-3.5 py-1.5 border border-gray-300 bg-white hover:bg-gray-50 rounded-md font-bold text-gray-700 transition shrink-0"
                >
                  파일 선택
                </button>
                <span className="text-xs text-gray-500">
                  파일 선택 파일 {(form.self_assess_file || selfAssessFileName ? 1 : 0)}개
                </span>
                <input
                  id="self-assess-file-input"
                  type="file"
                  accept=".pdf"
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      setForm(prev => Object.assign({}, prev, { self_assess_file: file.name }));
                      setSelfAssessFileName(file.name);
                      /* [이슈-수정] 실제 File 객체 보존 — 폼 제출 시 OCR API 업로드용 */
                      setSelfAssessFileObj(file);
                    }
                  }}
                  className="hidden"
                />
              </div>
              {(form.self_assess_file || selfAssessFileName) && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-xs font-bold text-gray-600">선택된 서류 목록:</p>
                  <div className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-gray-200/60 text-xs">
                    <span className="font-semibold text-gray-700">{form.self_assess_file || selfAssessFileName}</span>
                    <button
                      type="button"
                      onClick={() => {
                        setForm(prev => Object.assign({}, prev, { self_assess_file: "" }));
                        setSelfAssessFileName("");
                      }}
                      className="text-red-500 hover:text-red-700 font-bold ml-2 text-xs"
                    >
                      삭제
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1.5">증빙자료 업로드 (다중 선택 가능) *</label>
              <div className="w-full border border-gray-200 rounded-lg p-2 bg-white flex items-center gap-3 mb-2">
                <button
                  type="button"
                  onClick={() => document.getElementById("evidence-file-input").click()}
                  className="text-xs px-3.5 py-1.5 border border-gray-300 bg-white hover:bg-gray-50 rounded-md font-bold text-gray-700 transition shrink-0"
                >
                  파일 선택
                </button>
                <span className="text-xs text-gray-500">
                  파일 선택 파일 {(form.evidence_files && form.evidence_files.length > 0 ? form.evidence_files.length : (evidenceFileNames ? evidenceFileNames.length : 0))}개
                </span>
                <input
                  id="evidence-file-input"
                  type="file"
                  multiple
                  onChange={(e) => {
                    const files = Array.from(e.target.files);
                    if (files.length > 0) {
                      const newNames = files.map(f => f.name);
                      setForm(prev => {
                        const existing = prev.evidence_files || [];
                        const combined = Array.from(new Set([...existing, ...newNames]));
                        return Object.assign({}, prev, { evidence_files: combined });
                      });
                      setEvidenceFileNames(prev => Array.from(new Set([...prev, ...newNames])));
                      /* [이슈-수정] 실제 File 객체 보존 — 다중 업로드용 */
                      setEvidenceFileObjs(prev => [...prev, ...files]);
                    }
                  }}
                  className="hidden"
                />
              </div>
              {((form.evidence_files && form.evidence_files.length > 0) || (evidenceFileNames && evidenceFileNames.length > 0)) && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-xs font-bold text-gray-600">선택된 증빙서류 목록:</p>
                  <div className={(form.evidence_files && form.evidence_files.length > 0 ? form.evidence_files.length : evidenceFileNames.length) >= 7 ? "max-h-48 overflow-y-auto pr-1" : ""}>
                    {(form.evidence_files && form.evidence_files.length > 0 ? form.evidence_files : evidenceFileNames).map((fname, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-gray-200/60 text-xs mb-1.5 last:mb-0">
                        <span className="font-semibold text-gray-700">{fname}</span>
                        <button
                          type="button"
                          onClick={() => {
                            const currentList = form.evidence_files && form.evidence_files.length > 0 ? form.evidence_files : evidenceFileNames;
                            const filtered = currentList.filter((_, i) => i !== idx);
                            setForm(prev => Object.assign({}, prev, { evidence_files: filtered }));
                            setEvidenceFileNames(filtered);
                          }}
                          className="text-red-500 hover:text-red-700 font-bold ml-2 text-xs"
                        >
                          삭제
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* 1열 세로 배열: 행동강령(CoC) 동의 서약서 */}
          <Card className="p-6 bg-white border border-gray-150">
            <h2 className="text-base font-bold text-gray-900 border-b pb-3 mb-3" style={{ fontSize: "16px" }}>
              협력사 행동강령 준수 서약 및 동의
            </h2>
            <p className="text-xs text-gray-500 mb-4 leading-normal">
              공급망 내 ESG 규제 리스크 방지를 위해 협력사의 행동강령 서약 제출을 필수로 지정하고 있습니다. 양식을 다운로드하여 날인 후 업로드해주십시오.
            </p>
            <div className="p-4 bg-slate-50 rounded-xl border border-gray-200/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <p className="text-xs font-bold text-gray-800">현대모비스 협력사 행동강령 양식</p>
                <p className="text-[11px] text-gray-400">CoC_Agreement_Form.pdf (1.2MB)</p>
              </div>
              <button
                type="button"
                onClick={() => alert("행동강령 서약서 양식 파일 다운로드가 완료되었습니다.")}
                className="text-xs px-3.5 py-2 border border-gray-250 bg-white hover:bg-gray-100 rounded-lg font-bold text-gray-700 transition"
              >
                양식 다운로드
              </button>
            </div>
            <div>
              <label className="text-xs font-bold text-gray-600 block mb-1.5">행동강령 서약서 파일 업로드 *</label>
              <div className="w-full border border-gray-200 rounded-lg p-2 bg-white flex items-center gap-3 mb-2">
                <button
                  type="button"
                  onClick={() => document.getElementById("coc-file-input").click()}
                  className="text-xs px-3.5 py-1.5 border border-gray-300 bg-white hover:bg-gray-50 rounded-md font-bold text-gray-700 transition shrink-0"
                >
                  파일 선택
                </button>
                <span className="text-xs text-gray-500">
                  파일 선택 파일 {(form.coc_file || cocFileName ? 1 : 0)}개
                </span>
                <input
                  id="coc-file-input"
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      setForm(prev => Object.assign({}, prev, { coc_file: file.name }));
                      setCocFileName(file.name);
                      /* [이슈-수정] 실제 File 객체 보존 — 폼 제출 시 API 업로드용 */
                      setCocFileObj(file);
                    }
                  }}
                  className="hidden"
                />
              </div>
              {(form.coc_file || cocFileName) && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-xs font-bold text-gray-600">선택된 서류 목록:</p>
                  <div className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-gray-200/60 text-xs">
                    <span className="font-semibold text-gray-700">{form.coc_file || cocFileName}</span>
                    <button
                      type="button"
                      onClick={() => {
                        setForm(prev => Object.assign({}, prev, { coc_file: "" }));
                        setCocFileName("");
                      }}
                      className="text-red-500 hover:text-red-700 font-bold ml-2 text-xs"
                    >
                      삭제
                    </button>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                if (isEditMode) {
                  setViewMode("detail");
                } else {
                  setViewMode("welcome");
                }
              }}
              className="px-5 py-2.5 bg-gray-100 text-gray-750 text-xs font-bold rounded-lg hover:bg-gray-200 transition"
            >
              취소
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 text-white text-xs font-bold rounded-lg hover:opacity-90 transition shadow-sm"
              style={{ backgroundColor: "#03a94d" }}
            >
              저장 및 제출하기
            </button>
          </div>
        </form>
      </div>
    );
  }

  // 3. 상세 명세 화면 (Detail View)
  /* [이슈] API 데이터(apiCompany) 우선, partnerRegistration fallback */
  const registeredData = apiCompany || partnerRegistration[partnerId] || {};
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black text-gray-900">기업 정보 관리</h1>
        <button
          onClick={() => setViewMode("form")}
          className="px-4 py-2 text-white text-xs font-bold rounded-lg hover:opacity-90 transition shadow-sm"
          style={{ backgroundColor: "#03a94d" }}
        >
          정보 수정하기
        </button>
      </div>

      {/* 2대 탭 네비게이션 */}
      <div className="flex border-b border-gray-200 bg-white rounded-t-xl px-4 pt-2">
        <button
          onClick={() => { setDetailTab("info"); }}
          className={"px-4 py-2.5 text-sm font-bold border-b-2 transition-all " +
            (detailTab === "info" ? "border-[#03a94d] text-[#03a94d]" : "border-transparent text-gray-500 hover:text-gray-700")}
        >
          기업 정보
        </button>
        <button
          onClick={() => { setDetailTab("evidence"); }}
          className={"px-4 py-2.5 text-sm font-bold border-b-2 transition-all " +
            (detailTab === "evidence" ? "border-[#03a94d] text-[#03a94d]" : "border-transparent text-gray-500 hover:text-gray-700")}
        >
          제출 자료
        </button>
        {/* [이슈] 공장 등록 탭 추가 — 요구사항 3번 */}
        <button
          onClick={() => { setDetailTab("factory"); }}
          className={"px-4 py-2.5 text-sm font-bold border-b-2 transition-all " +
            (detailTab === "factory" ? "border-[#03a94d] text-[#03a94d]" : "border-transparent text-gray-500 hover:text-gray-700")}
        >
          공장 등록
        </button>
      </div>

      {/* 탭 콘텐츠 */}
      {detailTab === "info" && (
        <div className="space-y-5">
          {/* 영역 1: 기본 정보 */}
          <Card className="p-6 bg-white border border-gray-150">
            <h2 className="font-bold text-gray-900 border-b pb-3 mb-4" style={{ fontSize: "16px" }}>
              기본 정보
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" style={{ fontSize: "14px" }}>
              {[
                ["회사명", registeredData.company_name],
                ["대표자명", registeredData.ceo_name],
                ["사업자등록번호", registeredData.biz_no],
                ["설립일", registeredData.founded],
                ["회사 주소", registeredData.address],
                ["회사 규모", registeredData.size],
                ["소재 국가", registeredData.country]
              ].map(([label, val], i) => (
                <div key={i} className="bg-slate-50/50 rounded-lg p-3 border border-gray-100 flex flex-col justify-between">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">{label}</span>
                  <span className="font-semibold text-gray-800">{val || "-"}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* 영역 2: ESG 성과 지표 */}
          <Card className="p-6 bg-white border border-gray-150">
            <h2 className="font-bold text-gray-900 border-b pb-3 mb-4" style={{ fontSize: "16px" }}>
              ESG 성과 지표
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" style={{ fontSize: "14px" }}>
              {[
                ["Scope 1 배출량", registeredData.scope1 ? Number(registeredData.scope1).toLocaleString() + " tCO₂e" : "-"],
                ["Scope 2 배출량", registeredData.scope2 ? Number(registeredData.scope2).toLocaleString() + " tCO₂e" : "-"],
                ["FEOC 원료 비중", registeredData.feoc_ratio ? registeredData.feoc_ratio + " %" : "-"],
                ["TRIR 산업안전율", registeredData.trir ? registeredData.trir + " 건" : "-"]
              ].map(([label, val], i) => (
                <div key={i} className="bg-slate-50/50 rounded-lg p-3 border border-gray-100 flex flex-col justify-between">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">{label}</span>
                  <span className="font-bold text-gray-800">{val || "-"}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* 영역 3: 글로벌 인증 현황 */}
          <Card className="p-6 bg-white border border-gray-150">
            <h2 className="font-bold text-gray-900 border-b pb-3 mb-4" style={{ fontSize: "16px" }}>
              글로벌 인증 현황
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {Object.keys(CERT_LABELS).map(key => {
                const val = registeredData[key];
                const isY = val === "Y";
                return (
                  <div key={key} className="flex items-center justify-between p-3 bg-slate-50/50 border border-gray-100 rounded-xl">
                    <span className="text-xs font-bold text-gray-700">{CERT_LABELS[key]}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-bold border ${isY ? "bg-[#03a94d]/10 text-[#03a94d] border-[#03a94d]/20" : "bg-gray-100 text-gray-400 border-gray-200"}`}>
                      {isY ? "준수 (Y)" : "미준수 (N)"}
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* [이슈-수정] 증빙 자료 탭 — API에서 4영역 분류 파일 조회 + 실제 다운로드 */}
      {detailTab === "evidence" && (
        <div className="space-y-6">
          {[
            { key: "selfassess", title: "자가진단 완료 문서" },
            { key: "evidence",   title: "자가진단 증빙 자료" },
            { key: "cert",       title: "글로벌 인증 증빙 자료" },
            { key: "coc",        title: "행동강령 준수 서약서" },
          ].map((section) => {
            const files = categorizedFiles[section.key] || [];
            return (
              <Card key={section.key} className="p-6 space-y-4">
                <h3 className="text-base font-bold text-gray-800 border-b pb-2" style={{ fontSize: "16px" }}>
                  {section.title}
                </h3>
                {files.length > 0 ? (
                  <div className={files.length >= 7 ? "max-h-48 overflow-y-auto pr-1" : ""}>
                    {files.map((file, idx) => (
                      <div key={file.id || idx} className="bg-gray-50 border border-gray-100 p-3 rounded-xl mb-2 last:mb-0 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="bg-gray-100 text-gray-400 rounded-lg w-7 h-7 flex items-center justify-center shrink-0 text-xs font-bold font-mono">
                            {String(idx + 1).padStart(2, "0")}
                          </span>
                          <span className="text-sm font-bold text-gray-800 truncate">{file.origin || file.filename}</span>
                        </div>
                        <div className="flex gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => {
                              /* [이슈-수정] 실제 다운로드 — /api/company/file/download/{filename} */
                              const dl = file.filename || file.origin;
                              const a = document.createElement("a");
                              a.href = `/api/company/file/download/${dl}`;
                              a.download = file.origin || dl;
                              document.body.appendChild(a);
                              a.click();
                              document.body.removeChild(a);
                            }}
                            className="text-xs px-3 py-1.5 border border-gray-250 bg-white hover:bg-gray-100 rounded-lg font-bold text-gray-700 transition"
                          >
                            다운로드
                          </button>
                          {/* 삭제 버튼 + Confirm */}
                          {/* 자가진단 완료 문서 / 행동강령 서약서는 삭제 버튼 제외 (마스터 문서 보호) */}
                          {section.key !== "selfassess" && section.key !== "coc" && (
                          <button
                            type="button"
                            onClick={() => {
                              if (confirm("파일을 정말 삭제하시겠습니까?")) {
                                fetch(`/api/company/file/${file.id}?`, { method: "DELETE" })
                                  .then(r => r.json())
                                  .then(r => {
                                    if (r.status) {
                                      /* 화면에서 즉시 제거 — 새로고침 없이 */
                                      setCategorizedFiles(prev => ({
                                        ...prev,
                                        [section.key]: prev[section.key].filter(f => f.id !== file.id)
                                      }));
                                    } else { alert("삭제에 실패했습니다."); }
                                  });
                              }
                            }}
                            className="text-xs px-3 py-1.5 border border-red-200 bg-white hover:bg-red-50 rounded-lg font-bold text-red-500 transition"
                          >
                            삭제
                          </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">제출된 서류가 없습니다.</p>
                )}
              </Card>
            );
          })}
        </div>
      )}

      {/* [이슈] 공장 등록 탭 콘텐츠 — 요구사항 3번 */}
      {detailTab === "factory" && (
        <div className="space-y-5">
          <Card className="p-6 bg-white border border-gray-150">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-gray-900" style={{ fontSize: "16px" }}>공장 목록</h2>
              <button
                onClick={() => { setShowFactoryForm(true); setEditingFactoryId(null); setFactoryForm({
                  factoryName: "", factoryLocation: "", operationStatus: "가동중",
                  utilizationRate: 0, scope1Emissions: 0, scope2Emissions: 0,
                  feocRawMaterialRatio: 0, trirSafetyRate: 0, note: ""
                }); }}
                className="text-xs px-3 py-1.5 rounded-lg font-bold text-white transition"
                style={{ backgroundColor: "#03a94d" }}
              >+ 공장 추가</button>
            </div>
            {factories.length > 0 ? (
              <div className="space-y-3">
                {factories.map((f) => (
                  <div key={f.id} className="border rounded-lg p-4 bg-gray-50 space-y-2">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-bold text-gray-900">{f.factory_name}</p>
                        <p className="text-xs text-gray-500">{f.factory_location} · {f.operation_status}</p>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => {
                          setEditingFactoryId(f.id);
                          setFactoryForm({
                            factoryName: f.factory_name, factoryOwner: f.factory_owner, factoryLocation: f.factory_location,
                            operationStatus: f.operation_status, utilizationRate: f.utilization_rate,
                            scope1Emissions: f.scope1_emissions, scope2Emissions: f.scope2_emissions,
                            feocRawMaterialRatio: f.feoc_raw_material_ratio, trirSafetyRate: f.trir_safety_rate,
                            note: f.note || ""
                          });
                          setShowFactoryForm(true);
                        }} className="text-xs px-2 py-1 border rounded bg-white hover:bg-gray-100">수정</button>
                        <button onClick={() => {
                          if (confirm("삭제하시겠습니까?")) {
                            fetch(`/api/company/factory/${f.id}`, { method: "DELETE" })
                              .then(r => r.json()).then(() => _loadFactories());
                          }
                        }} className="text-xs px-2 py-1 border rounded bg-white hover:bg-red-50 text-red-500">삭제</button>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
                      <div className="bg-white rounded p-2"><p className="text-gray-400">이용 비율</p><p className="font-bold">{f.utilization_rate}%</p></div>
                      <div className="bg-white rounded p-2"><p className="text-gray-400">Scope 1</p><p className="font-bold">{(f.scope1_emissions || 0).toLocaleString()} tCO₂e</p></div>
                      <div className="bg-white rounded p-2"><p className="text-gray-400">Scope 2</p><p className="font-bold">{(f.scope2_emissions || 0).toLocaleString()} tCO₂e</p></div>
                      <div className="bg-white rounded p-2"><p className="text-gray-400">FEOC</p><p className="font-bold">{f.feoc_raw_material_ratio}%</p></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-6">등록된 공장이 없습니다.</p>
            )}
            {factorySummary && factorySummary.factoryCount > 0 && (
              <div className="mt-4 p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
                <p className="text-xs font-bold text-emerald-700 mb-2">가중합산 요약 (COMPANY 자동 반영)</p>
                <div className="grid grid-cols-4 gap-2 text-xs">
                  <div><span className="text-gray-500">Scope 1</span><p className="font-bold">{factorySummary.scope1?.toLocaleString()}</p></div>
                  <div><span className="text-gray-500">Scope 2</span><p className="font-bold">{factorySummary.scope2?.toLocaleString()}</p></div>
                  <div><span className="text-gray-500">FEOC</span><p className="font-bold">{factorySummary.feocRatio}%</p></div>
                  <div><span className="text-gray-500">TRIR</span><p className="font-bold">{factorySummary.trir}</p></div>
                </div>
              </div>
            )}
          </Card>

          {showFactoryForm && (
            <Card className="p-6 bg-white border border-gray-150">
              <h2 className="font-bold text-gray-900 mb-4" style={{ fontSize: "16px" }}>
                {editingFactoryId ? "공장 수정" : "공장 등록"}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                {[["공장명", "factoryName", "text"],["공장주명", "factoryOwner", "text"], ["소재지", "factoryLocation", "text"],
                  ["이용 비율 (%)", "utilizationRate", "number"], ["Scope 1 (tCO₂e)", "scope1Emissions", "number"],
                  ["Scope 2 (tCO₂e)", "scope2Emissions", "number"], ["FEOC 비중 (%)", "feocRawMaterialRatio", "number"],
                  ["TRIR", "trirSafetyRate", "number"]].map(([label, key, type]) => (
                  <div key={key}>
                    <label className="block text-xs font-bold text-gray-600 mb-1">{label}</label>
                    <input type={type} value={factoryForm[key]}
                      onChange={(e) => setFactoryForm(prev => ({ ...prev, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                  </div>
                ))}
                <div>
                  <label className="block text-xs font-bold text-gray-600 mb-1">가동 상태</label>
                  <select value={factoryForm.operationStatus}
                    onChange={(e) => setFactoryForm(prev => ({ ...prev, operationStatus: e.target.value }))}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                    <option value="가동중">가동중</option><option value="중단">중단</option><option value="폐쇄">폐쇄</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button onClick={() => {
                  const body = { ...factoryForm, partnerId: partnerId };
                  const url = editingFactoryId ? `/api/company/factory/${editingFactoryId}` : "/api/company/factory";
                  const method = editingFactoryId ? "PUT" : "POST";
                  fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
                    .then(r => r.json()).then((json) => {
                      if (json.status) { alert(json.message); setShowFactoryForm(false); _loadFactories(); }
                      else { alert(json.message || "저장 실패"); }
                    });
                }} className="px-4 py-2 text-sm font-bold text-white rounded-lg" style={{ backgroundColor: "#03a94d" }}>
                  {editingFactoryId ? "수정 저장" : "등록"}
                </button>
                <button onClick={() => setShowFactoryForm(false)} className="px-4 py-2 text-sm font-bold text-gray-600 border rounded-lg">취소</button>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );

  /* [이슈] 공장 목록 로드 함수 — 탭 전환 시 호출 */
  function _loadFactories() {
    fetch(`/api/company/${partnerId}/factories`)
      .then(r => r.json()).then((json) => {
        if (json.status) {
          setFactories(json.data.factories || []);
          setFactorySummary(json.data.summary || null);
        }
      });
  }
};

export default CompanyInfo;
