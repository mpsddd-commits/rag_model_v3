import React, { useState } from "react";
import { Chip } from "@components/Common/Chip";

const NotificationPanel = ({ notifications, setNotifications, onClose }) => {
  const [selNotif, setSelNotif] = useState(null);
  const notifs = notifications || [];
  const unread = notifs.filter(n => !n.read).length;
  const typeColor = { RISK: "red", URGENT: "orange", INSPECT: "yellow", SELF: "blue", INVITE: "green" };
  const typeLabel = { RISK: "리스크", URGENT: "긴급요청", INSPECT: "현장실사", SELF: "자가진단", INVITE: "초대" };

  const handleRead = (notifId) => {
    if (setNotifications) {
      setNotifications(prev => prev.map(n => n.id === notifId ? Object.assign({}, n, { read: true }) : n));
    }
  };

  const handleAllRead = () => {
    if (setNotifications) {
      setNotifications(prev => prev.map(n => Object.assign({}, n, { read: true })));
    }
  };

  if (selNotif) {
    return (
      <div className="absolute right-0 top-12 w-96 bg-white rounded-xl shadow-xl border border-gray-200 z-50">
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <button onClick={() => setSelNotif(null)} className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-600">← 목록</button>
          <span className="text-sm font-bold text-gray-800">알림 상세</span>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">✕</button>
        </div>
        <div className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <Chip text={typeLabel[selNotif.type] || selNotif.type} color={typeColor[selNotif.type] || "slate"} />
            {!selNotif.read && <Chip text="읽지 않음" color="red" />}
          </div>
          <h3 className="font-bold text-gray-900 mb-2">{selNotif.title}</h3>
          <p className="text-sm text-gray-600 leading-relaxed mb-4">{selNotif.msg}</p>
          <p className="text-xs text-gray-400">{selNotif.time}</p>
          <div className="mt-4 flex gap-2">
            <button className="px-4 py-2 bg-[#03a94d] hover:bg-[#02823b] text-white text-xs rounded-lg font-bold transition">관련 화면으로 이동</button>
            {!selNotif.read && (
              <button
                onClick={() => {
                  handleRead(selNotif.id);
                  setSelNotif(prev => Object.assign({}, prev, { read: true }));
                }}
                className="px-4 py-2 bg-gray-100 text-gray-700 text-xs rounded-lg"
              >
                읽음 처리
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute right-0 top-12 w-96 bg-white rounded-xl shadow-xl border border-gray-200 z-50">
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <span className="text-sm font-bold text-gray-800">
          알림 {unread > 0 && <span className="ml-1 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">{unread}</span>}
        </span>
        <div className="flex gap-2">
          <button onClick={handleAllRead} className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-600">전체 읽음</button>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">✕</button>
        </div>
      </div>
      <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
        {notifs.map(n => (
          <div key={n.id} onClick={() => setSelNotif(n)}
            className={"p-4 cursor-pointer hover:bg-gray-50 transition " + (!n.read ? "bg-emerald-50/30" : "")}>
            <div className="flex items-start gap-3">
              <span className={n.level === "fail" ? "text-red-500 text-lg shrink-0" : n.level === "warn" ? "text-amber-500 text-lg shrink-0" : "text-blue-500 text-lg shrink-0"}>●</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <p className="text-sm font-bold text-gray-900 truncate">{n.title}</p>
                  {!n.read && <span className="w-2 h-2 bg-[#03a94d] rounded-full shrink-0" />}
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">{n.msg}</p>
                <p className="text-xs text-gray-300 mt-1">{n.time}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NotificationPanel;
