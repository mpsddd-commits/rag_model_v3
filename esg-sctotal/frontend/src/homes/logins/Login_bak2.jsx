// Login.jsx
// ────────────────────────────────────────────────────────
// [v1.0] 2026-06-04 — 원청사/N차 협력사 로그인 분기, Tailwind CSS
// ────────────────────────────────────────────────────────

import { useState } from "react";
import heroLogo from "@assets/logos/TVLogo.png";

const Login = ({ onLoginSuccess }) => {
  // ── States ──
  const [loginType, setLoginType] = useState("oem"); // "oem" | "supplier"
  const [email, setEmail] = useState("");
  const [authCode, setAuthCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ── 원청사 로그인 ──
  const handleOemLogin = async (e) => {
    e.preventDefault();
    if (!email.trim()) { setError("이메일을 입력해 주세요."); return; }
    try {
      setLoading(true); setError("");
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, loginType: "oem" }),
      }).then(r => r.json());
      if (res.status) {
        if (onLoginSuccess) onLoginSuccess(res.data);
        else alert("로그인 성공");
      } else { setError(res.message || "로그인에 실패했습니다."); }
    } catch { setError("서버 연결 오류가 발생했습니다."); }
    finally { setLoading(false); }
  };

  // ── N차 협력사: 인증 코드 발송 ──
  const handleSendCode = async () => {
    if (!email.trim()) { setError("이메일을 입력해 주세요."); return; }
    try {
      setLoading(true); setError("");
      const res = await fetch("/api/auth/send-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      }).then(r => r.json());
      if (res.status) { setCodeSent(true); alert("인증 코드가 이메일로 발송되었습니다."); }
      else { setError(res.message || "인증 코드 발송에 실패했습니다."); }
    } catch { setError("서버 연결 오류가 발생했습니다."); }
    finally { setLoading(false); }
  };

  // ── N차 협력사: 인증 코드 검증 + 로그인 ──
  const handleSupplierLogin = async (e) => {
    e.preventDefault();
    if (!email.trim()) { setError("이메일을 입력해 주세요."); return; }
    if (!authCode.trim()) { setError("인증 코드를 입력해 주세요."); return; }
    try {
      setLoading(true); setError("");
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, authCode, loginType: "supplier" }),
      }).then(r => r.json());
      if (res.status) {
        if (onLoginSuccess) onLoginSuccess(res.data);
        else alert("로그인 성공");
      } else { setError(res.message || "로그인에 실패했습니다."); }
    } catch { setError("서버 연결 오류가 발생했습니다."); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-emerald-50">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8 space-y-6 border border-gray-100">

        {/* 로고 */}
        <div className="flex justify-center">
          <img src={heroLogo} alt="Triple Values" className="h-14 object-contain" />
        </div>

        <h1 className="text-center text-xl font-black text-gray-900">ESG 공급망 관리 시스템</h1>

        {/* 권한 탭 전환 */}
        <div className="flex border-b border-gray-200">
          {[
            { key: "oem", label: "원청사 로그인" },
            { key: "supplier", label: "협력사 로그인" },
          ].map((tab) => (
            <button key={tab.key}
              onClick={() => { setLoginType(tab.key); setError(""); setCodeSent(false); setAuthCode(""); }}
              className={"flex-1 py-2.5 text-sm font-bold border-b-2 transition-all " +
                (loginType === tab.key
                  ? "border-[#03a94d] text-[#03a94d]"
                  : "border-transparent text-gray-400 hover:text-gray-600")}
            >{tab.label}</button>
          ))}
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 text-xs font-medium rounded-lg p-3">
            {error}
          </div>
        )}

        {/* ── 원청사 로그인 폼 ── */}
        {loginType === "oem" && (
          <form onSubmit={handleOemLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-1.5">이메일 *</label>
              <input type="email" value={email} placeholder="원청사 담당자 이메일을 입력해주세요"
                onChange={(e) => { setEmail(e.target.value); setError(""); }}
                className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30 focus:border-[#03a94d]" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 text-sm font-bold text-white rounded-lg transition hover:opacity-90 disabled:opacity-50"
              style={{ backgroundColor: "#03a94d" }}>
              {loading ? "로그인 중..." : "로그인"}
            </button>
          </form>
        )}

        {/* ── N차 협력사 로그인 폼 (2차 인증) ── */}
        {loginType === "supplier" && (
          <form onSubmit={handleSupplierLogin} className="space-y-4">
            {/* 이메일 + 인증 코드 발송 버튼 */}
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-1.5">이메일 *</label>
              <div className="flex gap-2">
                <input type="email" value={email} placeholder="협력사 담당자 이메일"
                  onChange={(e) => { setEmail(e.target.value); setError(""); }}
                  className="flex-1 border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30 focus:border-[#03a94d]" />
                <button type="button" onClick={handleSendCode} disabled={loading}
                  className="shrink-0 px-4 py-2.5 text-xs font-bold text-white rounded-lg transition hover:opacity-90 disabled:opacity-50"
                  style={{ backgroundColor: "#03a94d" }}>
                  {codeSent ? "재발송" : "인증 코드 발송"}
                </button>
              </div>
            </div>
            {/* 2차 인증 코드 입력 */}
            <div>
              <label className="block text-xs font-bold text-gray-600 mb-1.5">2차 인증 코드 *</label>
              <input type="text" value={authCode} placeholder="이메일로 받은 6자리 인증 코드 입력" maxLength={6}
                onChange={(e) => { setAuthCode(e.target.value.replace(/\D/g, "")); setError(""); }}
                className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm tracking-[0.3em] text-center font-mono focus:outline-none focus:ring-2 focus:ring-[#03a94d]/30 focus:border-[#03a94d]" />
              {codeSent && <p className="text-xs text-emerald-600 mt-1">인증 코드가 발송되었습니다. 이메일을 확인해주세요.</p>}
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 text-sm font-bold text-white rounded-lg transition hover:opacity-90 disabled:opacity-50"
              style={{ backgroundColor: "#03a94d" }}>
              {loading ? "인증 중..." : "로그인"}
            </button>
          </form>
        )}

        <p className="text-center text-xs text-gray-400">© 2026 Triple Values. All rights reserved.</p>
      </div>
    </div>
  );
};

export default Login;
