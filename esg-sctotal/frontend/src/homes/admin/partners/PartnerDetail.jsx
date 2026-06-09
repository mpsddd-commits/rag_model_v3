import React, { useState, useEffect } from "react";
import Card from "@components/Common/Card";
import { RChip } from "@components/Common/Chip";

/* [이슈] 자가진단 데이터를 API에서 조회하여 동적으로 표시 */

const PartnerDetail = ({ partner, partnerRegistration, onBack }) => {
  const [activeTab, setActiveTab] = useState("info"); // "info", "selfassess", "evidence", "factory"
  const [openCards, setOpenCards] = useState({});

  /* [이슈] 자가진단 데이터 API fetch 추가 — 더미 데이터 대신 DB 조회 */
  const [checklistData, setChecklistData] = useState([]);
  const [subChecklistData, setSubChecklistData] = useState([]);
  const [checklistA, setChecklistA] = useState([]);
  const [checklistB, setChecklistB] = useState([]);

  /* [이슈] 자가진단 버전 관리 state — 요구사항 1번 */
  const [selfAssessVersions, setSelfAssessVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);

  /* [이슈] 공장 정보 state — 요구사항 5번 */
  const [factories, setFactories] = useState([]);
  const [factorySummary, setFactorySummary] = useState(null);
  const [categorizedFiles, setCategorizedFiles] = useState({ coc: [], selfassess: [], evidence: [], cert: [] });

  // 하단 증빙 자료 탭에서 에러가 나지 않도록 변수 안전화 처리
  const regData = partnerRegistration || {};

  useEffect(() => {
    const pid = partner?.id || partner?.partner_id;
    if (!pid) return;

    /* [이슈] 버전별 자가진단 조회 — version 파라미터 추가 */
    const versionParam = selectedVersion ? `?version=${selectedVersion}` : "";
    fetch(`/api/company/${pid}/selfassess${versionParam}`)
      .then((res) => res.json())
      .then((json) => {
        if (json.status && json.data) {
          const answers = (json.data.answers || []).map((a, idx) => ({
            id: a.indicator_no || idx + 1,
            /* [이슈-수정] indicator=내부 지표명 라벨 */
            indicator: a.indicator_name || "",
            priority: a.priority || "High",
            /* [이슈-수정] fullQuestion=질문전문 */
            question: a.question || "",
            fullQuestion: a.question || "",
            evidenceRequired: a.evidence_yn || "N",
            answer: a.answer_text || "",
            riskGrade: a.risk_level || "평가중",
          }));
          setChecklistData(answers.filter((a) => a.id >= 40 && a.id <= 56));
          setSubChecklistData(answers.filter((a) => a.id >= 28 && a.id <= 39));
          setChecklistA(answers.filter((a) => a.id >= 1 && a.id <= 18));
          setChecklistB(answers.filter((a) => a.id >= 19 && a.id <= 27));
          /* [이슈] 버전 목록 설정 */
          if (json.data.versions) setSelfAssessVersions(json.data.versions);
          if (!selectedVersion && json.data.currentVersion) setSelectedVersion(json.data.currentVersion);
        }
      })
      .catch((err) => console.error("자가진단 조회 실패:", err));

    /* [이슈] 공장 목록 조회 — 요구사항 5번 */
    fetch(`/api/company/${pid}/factories`)
      .then((res) => res.json())
      .then((json) => {
        if (json.status && json.data) {
          setFactories(json.data.factories || []);
          setFactorySummary(json.data.summary || null);
        }
      })
      .catch((err) => console.error("공장 조회 실패:", err));

    fetch(`/api/company/${pid}/files`)
      .then((res) => res.json())
      .then((json) => { if (json.status && json.data) setCategorizedFiles(json.data); })
      .catch(() => { });
  }, [partner, selectedVersion]);

  // 누락되었던 카드 토글 함수 추가
  const toggleCard = (id) => {
    setOpenCards((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-black text-gray-900">협력사 상세 정보</h1>
          <p className="text-sm text-gray-400 mt-1">{partner.company_name} ({partner.tierLabel})</p>
        </div>
        <button onClick={onBack} className="px-4 py-2 bg-slate-100 text-slate-700 text-sm rounded-lg hover:bg-slate-200 transition">← 목록으로</button>
      </div>

      {/* 탭 네비게이션 */}
      <div className="flex border-b border-gray-200 bg-white rounded-t-xl px-4 pt-2">
        <button
          onClick={() => { setActiveTab("info"); }}
          className={"px-4 py-2.5 text-sm font-bold border-b-2 transition-all " +
            (activeTab === "info" ? "border-[#03a94d] text-[#03a94d]" : "border-transparent text-gray-500 hover:text-gray-700")}
        >
          협력사 정보
        </button>
        <button
          onClick={() => { setActiveTab("selfassess"); }}
          className={"px-4 py-2.5 text-sm font-bold border-b-2 transition-all " +
            (activeTab === "selfassess" ? "border-[#03a94d] text-[#03a94d]" : "border-transparent text-gray-500 hover:text-gray-700")}
        >
          자가진단 정보
        </button>
        <button
          onClick={() => { setActiveTab("evidence"); }}
          className={"px-4 py-2.5 text-sm font-bold border-b-2 transition-all " +
            (activeTab === "evidence" ? "border-[#03a94d] text-[#03a94d]" : "border-transparent text-gray-500 hover:text-gray-700")}
        >
          증빙 자료
        </button>
        {/* [이슈] 공장 정보 탭 추가 — 요구사항 5번 */}
        <button
          onClick={() => { setActiveTab("factory"); }}
          className={"px-4 py-2.5 text-sm font-bold border-b-2 transition-all " +
            (activeTab === "factory" ? "border-[#03a94d] text-[#03a94d]" : "border-transparent text-gray-500 hover:text-gray-700")}
        >
          공장 정보
        </button>
      </div>

      {/* 탭 콘텐츠 */}
      {activeTab === "info" && (
        <div className="space-y-6">
          {/* 기본 협력사 정보 */}
          <Card className="p-6 space-y-4">
            <h3 className="text-base font-bold text-gray-800 border-b pb-2" style={{ fontSize: "16px" }}>기본 협력사 정보</h3>
            <div className="grid grid-cols-2 gap-4 text-xs">
              {[
                ["기업명", partner.company_name],
                ["대표자명", partner.ceo_name || "-"],
                ["사업자등록번호", partner.biz_no || "-"],
                ["설립일", partner.founded || "-"],
                ["대표 이메일 주소", partner.email || "-"],
                ["기업 규모", partner.size || "-"],
                ["소재 국가", partner.country || "-"],
                ["소재지", partner.address || "-"],
              ].map((pair, i) => {
                return (
                  <div key={i} className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
                    <span className="text-xs text-gray-400 font-semibold">{pair[0]}</span>
                    <p className="text-sm font-bold text-gray-800 mt-0.5">{pair[1]}</p>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* ESG 주요 지표 데이터 */}
          <Card className="p-6 space-y-4">
            <h3 className="text-base font-bold text-gray-800 border-b pb-2" style={{ fontSize: "16px" }}>ESG 주요 지표 데이터</h3>
            <div className="grid grid-cols-2 gap-4 text-xs">
              {[
                ["Scope 1 (tCO₂e)", partner.scope1 ? Number(partner.scope1).toLocaleString() : "0"],
                ["Scope 2 (tCO₂e)", partner.scope2 ? Number(partner.scope2).toLocaleString() : "0"],
                ["FEOC 원료 비중 (%)", partner.feoc_ratio !== undefined ? partner.feoc_ratio + "%" : "-"],
                ["TRIR 산업안전율", partner.trir !== undefined ? partner.trir : "-"]
              ].map((pair, i) => {
                return (
                  <div key={i} className="bg-gray-50 p-2.5 rounded-lg border border-gray-100">
                    <span className="text-xs text-gray-400 font-semibold">{pair[0]}</span>
                    <p className="text-sm font-bold text-gray-800 mt-0.5">{pair[1]}</p>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* 글로벌 인증 및 이니셔티브 준수 현황 */}
          <Card className="p-6 space-y-4">
            <h3 className="text-base font-bold text-gray-800 border-b pb-2" style={{ fontSize: "16px" }}>글로벌 인증 및 이니셔티브 준수 현황</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {[
                ["CMRT (분쟁광물 보고 인증 여부)", partner.cmrt],
                ["EMAT (배터리·광물 추적 보고 인증 여부)", partner.emat],
                ["ISO 14001 (환경경영 인증 여부)", partner.iso14001],
                ["ISO 45001 (안전보건 인증 여부)", partner.iso45001],
                ["IATF 16949 (품질경영 인증 여부)", partner.iatf],
                ["RBA (책임 비즈니스 인증 여부)", partner.rba],
                ["RMAP (책임 광물 보증 인증 여부)", partner.rmap],
              ].map((pair, i) => {
                var val = pair[1] || "N";
                var isY = val === "Y";
                var badgeCls = "px-2 py-0.5 rounded text-xs font-bold border " +
                  (isY ? "bg-emerald-50 text-emerald-700 border-emerald-100" : "bg-slate-100 text-slate-500 border-slate-200");
                return (
                  <div key={i} className="bg-gray-50 p-2.5 rounded-lg border border-gray-100 flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-700">{pair[0]}</span>
                    <span className={badgeCls}>{isY ? "Y (준수)" : "N (미준수)"}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {activeTab === "selfassess" && (
        <div className="space-y-4">
          {/* [이슈] 자가진단 버전 선택 드롭다운 — 요구사항 1번 */}
          {selfAssessVersions.length > 0 && (
            <div className="flex items-center gap-3 bg-white p-3 rounded-lg border">
              <span className="text-xs font-bold text-gray-600">버전:</span>
              <select
                value={selectedVersion || ""}
                onChange={(e) => setSelectedVersion(Number(e.target.value))}
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
              >
                {selfAssessVersions.map((v) => (
                  <option key={v.version} value={v.version}>
                    v{v.version} ({v.answer_count}건 · {v.created_at ? new Date(v.created_at).toLocaleDateString() : ""})
                  </option>
                ))}
              </select>
            </div>
          )}
          {partner.tier === 1 ? (
            <div className="space-y-4">
              {checklistData.map((item) => {
                const isOpen = !!openCards[item.id];

                let pBadgeColor = "bg-emerald-100 text-emerald-800 border border-emerald-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                if (item.priority === "Critical") {
                  pBadgeColor = "bg-red-100 text-red-800 border border-red-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                } else if (item.priority === "High") {
                  pBadgeColor = "bg-yellow-100 text-yellow-800 border border-yellow-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                }

                let rBadgeColor = "bg-emerald-100 text-emerald-800 border border-emerald-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                if (item.riskGrade === "고위험") {
                  rBadgeColor = "bg-red-100 text-red-800 border border-red-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                } else if (item.riskGrade === "중위험") {
                  rBadgeColor = "bg-yellow-100 text-yellow-800 border border-yellow-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                }

                return (
                  <div key={item.id} className="border border-gray-200 bg-white rounded-xl overflow-hidden shadow-sm">
                    {/* 토글 헤더 */}
                    <div
                      onClick={() => toggleCard(item.id)}
                      className="p-5 flex items-center justify-between gap-4 cursor-pointer hover:bg-gray-50/80 transition-all select-none"
                    >
                      <div className="flex items-center gap-4 flex-1 min-w-0 pr-2">
                        <span className="text-sm font-black text-gray-400 bg-gray-100 rounded-lg w-8 h-8 flex items-center justify-center shrink-0">
                          {String(item.id).padStart(2, '0')}
                        </span>
                        <p className="text-xs md:text-sm font-semibold text-gray-800 leading-relaxed line-clamp-2 md:line-clamp-none">
                          {item.question}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className={pBadgeColor}>
                          우선순위: {item.priority}
                        </span>
                        <span className={rBadgeColor}>
                          평가: {item.riskGrade}
                        </span>
                        <span className="text-gray-400 text-sm font-bold transition-all ml-1 w-4 text-center">
                          {isOpen ? "▲" : "▼"}
                        </span>
                      </div>
                    </div>

                    {/* 토글 콘텐츠 */}
                    {isOpen && (
                      <div className="border-t border-gray-150 p-5 space-y-5 bg-slate-50/40">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">지표명</span>
                            <p className="text-sm font-bold text-gray-800 mt-0.5">{item.indicator}</p>
                          </div>
                          <div>
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">증빙자료 필요 여부</span>
                            {item.evidenceRequired === "Y" ? (
                              <div className="flex items-center gap-1.5 mt-1 text-xs text-amber-800 font-bold bg-amber-50 border border-amber-100 rounded px-2.5 py-1 w-fit">
                                <span>⚠️</span> 증빙서류 필수 제출 대상
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-600 font-bold bg-slate-100 border border-slate-200 rounded px-2.5 py-1 w-fit">
                                <span>✓</span> 증빙서류 선택 제출
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <label className="block text-xs font-bold text-gray-500">협력사 답변 (Partner Answer)</label>
                          <textarea
                            readOnly
                            disabled
                            value={item.answer}
                            className="w-full bg-white border border-gray-200 rounded-lg p-3 text-xs text-gray-700 leading-relaxed focus:outline-none resize-none cursor-not-allowed opacity-90 shadow-inner"
                            rows={3}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : partner.tier === 2 ? (
            <div className="space-y-4">
              {subChecklistData.map((item) => {
                const cardKey = "t2_" + item.id;
                const isOpen = !!openCards[cardKey];

                let pBadgeColor = "bg-emerald-100 text-emerald-800 border border-emerald-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                if (item.priority === "Critical") {
                  pBadgeColor = "bg-red-100 text-red-800 border border-red-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                } else if (item.priority === "High") {
                  pBadgeColor = "bg-yellow-100 text-yellow-800 border border-yellow-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                }

                let rBadgeColor = "bg-emerald-100 text-emerald-800 border border-emerald-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                if (item.riskGrade === "고위험") {
                  rBadgeColor = "bg-red-100 text-red-800 border border-red-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                } else if (item.riskGrade === "중위험") {
                  rBadgeColor = "bg-yellow-100 text-yellow-800 border border-yellow-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                }

                return (
                  <div key={item.id} className="border border-gray-200 bg-white rounded-xl overflow-hidden shadow-sm">
                    {/* 토글 헤더 */}
                    <div
                      onClick={() => toggleCard(cardKey)}
                      className="p-5 flex items-center justify-between gap-4 cursor-pointer hover:bg-gray-50/80 transition-all select-none"
                    >
                      <div className="flex items-center gap-4 flex-1 min-w-0 pr-2">
                        <span className="text-sm font-black text-gray-400 bg-gray-100 rounded-lg w-8 h-8 flex items-center justify-center shrink-0">
                          {String(item.id).padStart(2, '0')}
                        </span>
                        <p className="text-xs md:text-sm font-semibold text-gray-800 leading-relaxed line-clamp-2 md:line-clamp-none">
                          {item.question}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className={pBadgeColor}>
                          우선순위: {item.priority}
                        </span>
                        <span className={rBadgeColor}>
                          평가: {item.riskGrade}
                        </span>
                        <span className="text-gray-400 text-sm font-bold transition-all ml-1 w-4 text-center">
                          {isOpen ? "▲" : "▼"}
                        </span>
                      </div>
                    </div>

                    {/* 토글 콘텐츠 */}
                    {isOpen && (
                      <div className="border-t border-gray-150 p-5 space-y-5 bg-slate-50/40">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">지표명</span>
                            <p className="text-sm font-bold text-gray-800 mt-0.5">{item.indicator}</p>
                          </div>
                          <div>
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">증빙자료 필요 여부</span>
                            {item.evidenceRequired === "Y" ? (
                              <div className="flex items-center gap-1.5 mt-1 text-xs text-amber-800 font-bold bg-amber-50 border border-amber-100 rounded px-2.5 py-1 w-fit">
                                <span>⚠️</span> 증빙서류 필수 제출 대상
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-600 font-bold bg-slate-100 border border-slate-200 rounded px-2.5 py-1 w-fit">
                                <span>✓</span> 증빙서류 선택 제출
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <label className="block text-xs font-bold text-gray-500">협력사 답변 (Partner Answer)</label>
                          <textarea
                            readOnly
                            disabled
                            value={item.answer}
                            className="w-full bg-white border border-gray-200 rounded-lg p-3 text-xs text-gray-700 leading-relaxed focus:outline-none resize-none cursor-not-allowed opacity-90 shadow-inner"
                            rows={3}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : partner.tier === 3 ? (
            <div className="space-y-4">
              {(partner.tierLabel === "3차-B" ? [...checklistA, ...checklistB] : checklistA).map((item, index) => {
                const cardKey = "t3_" + item.id;
                const isOpen = !!openCards[cardKey];

                let pBadgeColor = "bg-emerald-100 text-emerald-800 border border-emerald-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                if (item.priority === "Critical") {
                  pBadgeColor = "bg-red-100 text-red-800 border border-red-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                } else if (item.priority === "High") {
                  pBadgeColor = "bg-yellow-100 text-yellow-800 border border-yellow-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                }

                let rBadgeColor = "bg-emerald-100 text-emerald-800 border border-emerald-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                if (item.riskGrade === "고위험") {
                  rBadgeColor = "bg-red-100 text-red-800 border border-red-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                } else if (item.riskGrade === "중위험") {
                  rBadgeColor = "bg-yellow-100 text-yellow-800 border border-yellow-200 shadow-sm uppercase tracking-wider px-4 py-2 text-xs font-black rounded-full whitespace-nowrap";
                }

                return (
                  <div key={item.id} className="border border-gray-200 bg-white rounded-xl overflow-hidden shadow-sm">
                    {/* 토글 헤더 */}
                    <div
                      onClick={() => toggleCard(cardKey)}
                      className="p-5 flex items-center justify-between gap-4 cursor-pointer hover:bg-gray-50/80 transition-all select-none"
                    >
                      <div className="flex items-center gap-4 flex-1 min-w-0 pr-2">
                        <span className="text-sm font-black text-gray-400 bg-gray-100 rounded-lg w-8 h-8 flex items-center justify-center shrink-0">
                          {String(index + 1).padStart(2, '0')}
                        </span>
                        <p className="text-xs md:text-sm font-semibold text-gray-800 leading-relaxed line-clamp-2 md:line-clamp-none">
                          {item.question}
                        </p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className={pBadgeColor}>
                          우선순위: {item.priority}
                        </span>
                        <span className={rBadgeColor}>
                          평가: {item.riskGrade}
                        </span>
                        <span className="text-gray-400 text-sm font-bold transition-all ml-1 w-4 text-center">
                          {isOpen ? "▲" : "▼"}
                        </span>
                      </div>
                    </div>

                    {/* 토글 콘텐츠 */}
                    {isOpen && (
                      <div className="border-t border-gray-150 p-5 space-y-5 bg-slate-50/40">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">지표명</span>
                            <p className="text-sm font-bold text-gray-800 mt-0.5">{item.indicator}</p>
                          </div>
                          <div>
                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">증빙자료 필요 여부</span>
                            {item.evidenceRequired === "Y" ? (
                              <div className="flex items-center gap-1.5 mt-1 text-xs text-amber-800 font-bold bg-amber-50 border border-amber-100 rounded px-2.5 py-1 w-fit">
                                <span>⚠️</span> 증빙서류 필수 제출 대상
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-600 font-bold bg-slate-100 border border-slate-200 rounded px-2.5 py-1 w-fit">
                                <span>✓</span> 증빙서류 선택 제출
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <label className="block text-xs font-bold text-gray-500">협력사 답변 (Partner Answer)</label>
                          <textarea
                            readOnly
                            disabled
                            value={item.answer}
                            className="w-full bg-white border border-gray-200 rounded-lg p-3 text-xs text-gray-700 leading-relaxed focus:outline-none resize-none cursor-not-allowed opacity-90 shadow-inner"
                            rows={3}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <Card className="p-12 text-center text-gray-400 bg-white">
              <p className="text-sm">자가진단 정보 세부내용은 추후 구성될 예정입니다.</p>
            </Card>
          )}
        </div>
      )}

      {activeTab === "evidence" && (
        <div className="space-y-6">
          {[
            { key: "selfassess", title: "자가진단 완료 문서" },
            { key: "evidence", title: "자가진단 증빙 자료" },
            { key: "cert", title: "글로벌 인증 증빙 자료" },
            { key: "coc", title: "행동강령 준수 서약서" },
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
                        <button type="button" onClick={() => {
                          const dl = file.filename || file.origin;
                          const a = document.createElement("a");
                          a.href = `/api/company/file/download/${dl}`;
                          a.download = file.origin || dl;
                          document.body.appendChild(a); a.click(); document.body.removeChild(a);
                        }}
                          className="text-xs px-3 py-1.5 border border-gray-250 bg-white hover:bg-gray-100 rounded-lg font-bold text-gray-700 transition shrink-0">
                          다운로드
                        </button>
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

      {/* [이슈] 공장 정보 탭 — 요구사항 5번: 원청사가 협력사 공장 정보 조회 */}
      {activeTab === "factory" && (
        <div className="space-y-5">
          {factorySummary && factorySummary.factoryCount > 0 && (
            <Card className="p-4 bg-emerald-50 border border-emerald-100">
              <p className="text-xs font-bold text-emerald-700 mb-2">ESG 가중합산 요약 (공장별 이용 비율 반영)</p>
              <div className="grid grid-cols-4 gap-3 text-xs">
                <div><span className="text-gray-500">Scope 1</span><p className="font-bold text-gray-900">{factorySummary.scope1?.toLocaleString()} tCO₂e</p></div>
                <div><span className="text-gray-500">Scope 2</span><p className="font-bold text-gray-900">{factorySummary.scope2?.toLocaleString()} tCO₂e</p></div>
                <div><span className="text-gray-500">FEOC 비중</span><p className="font-bold text-gray-900">{factorySummary.feocRatio}%</p></div>
                <div><span className="text-gray-500">TRIR</span><p className="font-bold text-gray-900">{factorySummary.trir}</p></div>
              </div>
            </Card>
          )}
          <Card className="p-6 bg-white">
            <h3 className="text-base font-bold text-gray-800 border-b pb-2 mb-4" style={{ fontSize: "16px" }}>
              공장 목록 ({factories.length}개)
            </h3>
            {factories.length > 0 ? (
              <div className="space-y-3">
                {factories.map((f) => (
                  <div key={f.id} className="border rounded-lg p-4 bg-gray-50">
                    <div className="flex justify-between items-center mb-2">
                      <div>
                        <p className="font-bold text-gray-900">{f.factory_name}</p>
                        <p className="text-xs text-gray-500">{f.factory_location}</p>
                      </div>
                      <span className={"text-xs px-2 py-1 rounded font-bold " +
                        (f.operation_status === "가동중" ? "bg-emerald-100 text-emerald-700" :
                          f.operation_status === "중단" ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700")}>
                        {f.operation_status}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 text-xs">
                      <div className="bg-white rounded p-2"><p className="text-gray-400">이용 비율</p><p className="font-bold">{f.utilization_rate}%</p></div>
                      <div className="bg-white rounded p-2"><p className="text-gray-400">Scope 1</p><p className="font-bold">{(f.scope1_emissions || 0).toLocaleString()} tCO₂e</p></div>
                      <div className="bg-white rounded p-2"><p className="text-gray-400">Scope 2</p><p className="font-bold">{(f.scope2_emissions || 0).toLocaleString()} tCO₂e</p></div>
                      <div className="bg-white rounded p-2"><p className="text-gray-400">FEOC</p><p className="font-bold">{f.feoc_raw_material_ratio}%</p></div>
                      <div className="bg-white rounded p-2"><p className="text-gray-400">TRIR</p><p className="font-bold">{f.trir_safety_rate}</p></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-6">등록된 공장 정보가 없습니다.</p>
            )}
          </Card>
        </div>
      )}
    </div>
  );
};

export default PartnerDetail;