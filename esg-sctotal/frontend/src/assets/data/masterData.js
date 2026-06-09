// ══════════════════════════════════════════════════════════
// ■ MASTER DATA  (협력사 세트 2개)
// ══════════════════════════════════════════════════════════
export const COMPANIES = [
  // ── 원청사
  { id: "HMOS-001", tier: 0, tierLabel: "원청사", short: "현대모비스", company_name: "현대모비스(주)", ceo_name: "이규석", biz_no: "264-81-00498", founded: "1977-06-24", address: "서울특별시 강남구 테헤란로 521", size: "대기업", country: "대한민국", esg: { E: 82, S: 78, G: 90 }, risk: "저위험", employees: 46947, revenue: 572000, assets: 665000, scope1: 180000, scope2: 105000, feoc_ratio: 3.2, trir: 0.38, cmrt: "Y", emat: "N", iso14001: "Y", iso45001: "Y", iatf: "Y", rba: "Y", rmap: "N", deforest_yn: "N", cert_count: 5, parent_id: null },
  // ── 세트 1 (1차)
  { id: "NOV-001", tier: 1, tierLabel: "1차 협력사", short: "노벨리스코리아", company_name: "(주)노벨리스코리아", ceo_name: "박진수", biz_no: "128-81-33210", founded: "1999-03-15", address: "경기도 시흥시 공단1대로 200", size: "대기업", country: "대한민국", esg: { E: 74, S: 71, G: 80 }, risk: "저위험", employees: 1850, revenue: 84200, assets: 216000, scope1: 82000, scope2: 60000, feoc_ratio: 8.1, trir: 0.62, cmrt: "N", emat: "N", iso14001: "Y", iso45001: "N", iatf: "N", rba: "N", rmap: "Y", deforest_yn: "N", cert_count: 2, parent_id: "HMOS-001" },
  // ── 세트 2 (1차)
  { id: "NSM-001", tier: 1, tierLabel: "1차 협력사", short: "남성알루미늄", company_name: "(주)남성알루미늄", ceo_name: "최병훈", biz_no: "310-81-12345", founded: "2001-05-10", address: "경상남도 창원시 성산구 공단로 120", size: "중견기업", country: "대한민국", esg: { E: 68, S: 65, G: 74 }, risk: "저위험", employees: 780, revenue: 38500, assets: 95000, scope1: 45000, scope2: 32000, feoc_ratio: 6.3, trir: 0.78, cmrt: "N", emat: "N", iso14001: "Y", iso45001: "Y", iatf: "Y", rba: "N", rmap: "N", deforest_yn: "N", cert_count: 3, parent_id: "HMOS-001" },
  // ── 세트 1 (2차)
  { id: "KRM-001", tier: 2, tierLabel: "2차 협력사", short: "케이알엠", company_name: "(주)케이알엠", ceo_name: "이성훈", biz_no: "402-81-45123", founded: "2003-07-20", address: "인천광역시 남동구 앵고개로 490", size: "중견기업", country: "대한민국", esg: { E: 62, S: 68, G: 72 }, risk: "중위험", employees: 420, revenue: 21800, assets: 56400, scope1: 58000, scope2: 40000, feoc_ratio: 12.5, trir: 1.12, cmrt: "N", emat: "N", iso14001: "Y", iso45001: "N", iatf: "N", rba: "N", rmap: "N", deforest_yn: "N", cert_count: 1, parent_id: "NOV-001" },
  // ── 세트 2 (2차)
  { id: "HMC-002", tier: 2, tierLabel: "2차 협력사", short: "현대머티리얼", company_name: "현대머티리얼(주)", ceo_name: "정민수", biz_no: "501-81-67890", founded: "2005-09-01", address: "충청남도 아산시 둔포면 산업단지로 55", size: "중소기업", country: "대한민국", esg: { E: 60, S: 66, G: 70 }, risk: "중위험", employees: 280, revenue: 15200, assets: 38000, scope1: 42000, scope2: 28000, feoc_ratio: 9.8, trir: 0.95, cmrt: "N", emat: "N", iso14001: "Y", iso45001: "N", iatf: "N", rba: "N", rmap: "N", deforest_yn: "N", cert_count: 1, parent_id: "NSM-001" },
  // ── 세트 1 (3차 A·B·C)
  { id: "COM-001", tier: 3, tierLabel: "3차-A", short: "Comilog", company_name: "Comilog Gabon S.A.", ceo_name: "Jean-Pierre M.", biz_no: "GAB-20031200", founded: "1962-08-10", address: "Moanda, Haut-Ogooué, Gabon", size: "대기업", country: "가봉", esg: { E: 55, S: 60, G: 65 }, risk: "중위험", employees: 5200, revenue: 123000, assets: 387000, scope1: 52000, scope2: 0, feoc_ratio: 0, trir: 2.15, cmrt: "N", emat: "N", iso14001: "Y", iso45001: "N", iatf: "N", rba: "N", rmap: "N", deforest_yn: "Y", cert_count: 1, parent_id: "KRM-001", deforest_note: "가봉 열대우림 인근 — IUCN 보호지역 인접" },
  { id: "WIN-001", tier: 3, tierLabel: "3차-B", short: "Windalco", company_name: "Windalco Jamaica Ltd.", ceo_name: "Michael Thompson", biz_no: "JAM-19801045", founded: "1980-04-22", address: "Ewarton, Saint Catherine, Jamaica", size: "대기업", country: "자메이카", esg: { E: 58, S: 65, G: 70 }, risk: "중위험", employees: 3800, revenue: 89000, assets: 224000, scope1: 68000, scope2: 0, feoc_ratio: 0, trir: 1.85, cmrt: "N", emat: "N", iso14001: "N", iso45001: "N", iatf: "N", rba: "N", rmap: "N", deforest_yn: "N", cert_count: 0, parent_id: "KRM-001" },
  { id: "COD-001", tier: 3, tierLabel: "3차-C", short: "Codelco", company_name: "Codelco Norte S.A.", ceo_name: "Carlos Mendez", biz_no: "CHL-19761009", founded: "1976-04-01", address: "Calama, Antofagasta, Chile", size: "대기업", country: "칠레", esg: { E: 60, S: 63, G: 68 }, risk: "중위험", employees: 18400, revenue: 482000, assets: 1250000, scope1: 112000, scope2: 0, feoc_ratio: 0, trir: 1.42, cmrt: "N", emat: "Y", iso14001: "Y", iso45001: "Y", iatf: "N", rba: "N", rmap: "N", deforest_yn: "N", cert_count: 2, parent_id: "KRM-001" },
  // ── 세트 2 (3차 A·B)
  { id: "EMG-002", tier: 3, tierLabel: "3차-A", short: "EMG Brasil", company_name: "Electro Manganese Brasil Ltda", ceo_name: "Fernando Lima", biz_no: "BRA-20101055", founded: "2010-03-20", address: "Pará, Brazil", size: "중견기업", country: "브라질", esg: { E: 58, S: 62, G: 67 }, risk: "중위험", employees: 2100, revenue: 65000, assets: 180000, scope1: 38000, scope2: 0, feoc_ratio: 0, trir: 1.92, cmrt: "N", emat: "N", iso14001: "Y", iso45001: "N", iatf: "N", rba: "N", rmap: "N", deforest_yn: "N", cert_count: 1, parent_id: "HMC-002" },
  { id: "ALU-002", tier: 3, tierLabel: "3차-B", short: "AluNorte", company_name: "Alunorte Alumina S.A.", ceo_name: "Rodrigo Ferreira", biz_no: "BRA-19980822", founded: "1998-08-22", address: "Barcarena, Pará, Brazil", size: "대기업", country: "브라질", esg: { E: 62, S: 67, G: 71 }, risk: "중위험", employees: 4500, revenue: 98000, assets: 310000, scope1: 72000, scope2: 0, feoc_ratio: 0, trir: 1.65, cmrt: "N", emat: "N", iso14001: "Y", iso45001: "N", iatf: "N", rba: "N", rmap: "N", deforest_yn: "N", cert_count: 1, parent_id: "HMC-002" },
];

// PO 목록
export const PO_LIST = [
  { id: "PO-2025-3003-001", partner_id: "NOV-001", product: "Al 3003-H14 판재", width: 1000, length: 2000, weight: 1.2, volume: 2.4, diameter: null, material: "Al-Mn 합금", qty: 45.0, unit_price: 3150, total: 141750, delivery: "2025-03-28", status: "COMPLETED" },
  { id: "PO-2025-3003-002", partner_id: "NOV-001", product: "Al 3003-H16 코일", width: 1200, length: null, weight: 0.6, volume: null, diameter: null, material: "Al-Mn 합금", qty: 60.0, unit_price: 3080, total: 184800, delivery: "2025-07-15", status: "COMPLETED" },
  { id: "PO-2026-3003-001", partner_id: "NOV-001", product: "Al 3003-H16 박판", width: 1000, length: null, weight: 0.5, volume: null, diameter: null, material: "Al-Mn 합금", qty: 55.0, unit_price: 3020, total: 166100, delivery: "2026-04-05", status: "CONFIRMED" },
  { id: "PO-2026-3003-002", partner_id: "NSM-001", product: "Al 3003-H14 판재", width: 1500, length: 3000, weight: 1.5, volume: 6.75, diameter: null, material: "Al-Mn 합금", qty: 42.0, unit_price: 3180, total: 133560, delivery: "2026-07-30", status: "PENDING" },
  { id: "PO-2026-3003-003", partner_id: "NSM-001", product: "Al 3003 튜브", width: null, length: 3000, weight: null, volume: null, diameter: 25.4, material: "Al-Mn 합금", qty: 120.0, unit_price: 1250, total: 150000, delivery: "2026-05-15", status: "CONFIRMED" },
];

// 원자재 (PO별 트리 포함)
export const RAW_MATERIALS = [
  {
    id: "RM-001", po_id: "PO-2025-3003-001", partner_id: "NOV-001", name: "Al 3003 슬라브", width: 600, length: 3000, weight_kg: 1520, diameter_mm: null, components: "Al 97.9%, Mn 1.25%, Cu 0.12%, Si 0.28%, Fe 0.45%", origin: "KRM-001", status: "APPROVED", requested_at: "2026-01-10", approved_at: "2026-01-15",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003 슬라브", comp: "Al 97.9%+Mn 1.25%", qty_kg: 1520 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳", comp: "Al 99.7%", qty_kg: 1570 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", comp: "Al₂O₃ 99.4%", qty_kg: 2930 }, { tier: 3, short: "Comilog", item: "Mn 정광(MnO₂)", comp: "MnO₂ 82%", qty_kg: 62 }, { tier: 3, short: "Codelco", item: "황동광(Cu)", comp: "Cu 28%", qty_kg: 6 }]
  },
  {
    id: "RM-002", po_id: "PO-2025-3003-001", partner_id: "KRM-001", name: "전기동(Cu) 캐소드", width: null, length: 900, weight_kg: 125, diameter_mm: null, components: "Cu 99.99%, Pb≤5ppm, S≤15ppm", origin: "COD-001", status: "APPROVED", requested_at: "2026-01-05", approved_at: "2026-01-12",
    tier_tree: [{ tier: 2, short: "케이알엠", item: "전기동 캐소드", comp: "Cu 99.99%", qty_kg: 125 }, { tier: 3, short: "Codelco", item: "황동광(CuFeS₂)", comp: "Cu 28%+Fe 30%", qty_kg: 380 }]
  },
  {
    id: "RM-003", po_id: "PO-2025-3003-001", partner_id: "KRM-001", name: "전해망간(EMD) — 긴급", width: null, length: null, weight_kg: 5, diameter_mm: null, components: "Mn 99.7%, Fe 0.05%, S 0.03%", origin: "COM-001", status: "REQUESTED", requested_at: "2026-01-05", approved_at: null,
    tier_tree: [{ tier: 2, short: "케이알엠", item: "전해망간 EMD", comp: "Mn 99.7%", qty_kg: 5 }, { tier: 3, short: "Comilog", item: "파이롤루사이트(MnO₂)", comp: "MnO₂ 82%", qty_kg: 8.5 }]
  },
  {
    id: "RM-004", po_id: "PO-2026-3003-001", partner_id: "NOV-001", name: "Al 3003-H16 코일 슬라브", width: 1200, length: 4000, weight_kg: 2100, diameter_mm: null, components: "Al 97.8%, Mn 1.32%, Cu 0.15%", origin: "KRM-001", status: "PENDING", requested_at: "2026-04-01", approved_at: null,
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-H16 슬라브", comp: "Al 97.8%", qty_kg: 2100 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳", comp: "Al 99.7%", qty_kg: 2170 }]
  },
  {
    id: "RM-005", po_id: "PO-2026-3003-002", partner_id: "NSM-001", name: "Al 3003-H14 빌렛", width: 200, length: 6000, weight_kg: 980, diameter_mm: null, components: "Al 97.9%, Mn 1.20%, Cu 0.11%", origin: "HMC-002", status: "APPROVED", requested_at: "2026-05-01", approved_at: "2026-05-08",
    tier_tree: [{ tier: 1, short: "남성알루미늄", item: "Al 3003-H14 빌렛", comp: "Al 97.9%", qty_kg: 980 }, { tier: 2, short: "현대머티리얼", item: "P1020 잉곳", comp: "Al 99.7%", qty_kg: 1010 }, { tier: 3, short: "AluNorte", item: "알루미나", comp: "Al₂O₃ 99.3%", qty_kg: 1890 }, { tier: 3, short: "EMG Brasil", item: "Mn 정광", comp: "MnO₂ 80%", qty_kg: 59 }]
  },
  {
    id: "RM-006", po_id: "PO-2026-3003-003", partner_id: "NSM-001", name: "Al 3003-H18 빌렛", width: 220, length: 5000, weight_kg: 850, diameter_mm: null, components: "Al 98.0%, Mn 1.15%, Cu 0.10%", origin: "HMC-002", status: "IN_PROGRESS", requested_at: "2026-05-10", approved_at: null,
    tier_tree: [{ tier: 1, short: "남성알루미늄", item: "Al 3003-H18 빌렛", comp: "Al 98.0%", qty_kg: 850 }]
  },
  {
    id: "RM-007", po_id: "PO-2026-3003-003", partner_id: "NOV-001", name: "Al 3003 코일 슬라브", width: 1100, length: 3500, weight_kg: 1900, diameter_mm: null, components: "Al 97.5%, Mn 1.40%, Cu 0.20%", origin: "KRM-001", status: "REJECTED", requested_at: "2026-05-12", approved_at: null,
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003 슬라브", comp: "Al 97.5%", qty_kg: 1900 }]
  },
];

// BOM (티어 트리 포함)
export const BOM_LIST = [
  {
    id: "BOM-001", category: "열 차폐판", product: "Al 3003-H14 판재 1.5T 400×300mm", item_no: "HSP-400-300-001", item_name: "Al 3003-H14 판재 1.5T", qty: 1.02, unit: "pcs/pcs", supplier_id: "NOV-001", lead_time: 14, price: 280, status: "ACTIVE", components: "Al 97.9%, Mn 1.25%, Cu 0.12%", weight_g: 491, approved_at: "2026-05-08",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-H14 판재 1.5T", qty_kg: 0.495 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳+EMD", qty_kg: 0.512 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 0.956 }, { tier: 3, short: "Comilog", item: "Mn 정광(MnO₂)", qty_kg: 0.061 }, { tier: 3, short: "Codelco", item: "황동광(Cu)", qty_kg: 0.006 }]
  },
  {
    id: "BOM-002", category: "열 차폐판", product: "Al 3003-H14 판재 2.0T 600×400mm", item_no: "HSP-600-400-001", item_name: "Al 3003-H14 판재 2.0T", qty: 1.03, unit: "pcs/pcs", supplier_id: "NOV-001", lead_time: 14, price: 420, status: "ACTIVE", components: "Al 97.9%, Mn 1.25%, Cu 0.12%", weight_g: 1310, approved_at: "2026-05-12",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-H14 판재 2.0T", qty_kg: 1.310 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳+EMD", qty_kg: 1.354 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 2.529 }, { tier: 3, short: "Comilog", item: "Mn 정광(MnO₂)", qty_kg: 0.163 }]
  },
  {
    id: "BOM-003", category: "휠", product: "Al 3003-H16 판재 3.0T 17인치(D432mm)", item_no: "WHL-17-001", item_name: "Al 3003-H16 판재 3.0T", qty: 2.15, unit: "pcs/pcs", supplier_id: "NOV-001", lead_time: 21, price: 850, status: "INACTIVE", components: "Al 97.8%, Mn 1.32%, Cu 0.15%", weight_g: 1347, approved_at: "2026-04-10",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-H16 판재 3.0T", qty_kg: 3.016 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳+EMD", qty_kg: 3.117 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 5.820 }, { tier: 3, short: "Comilog", item: "Mn 정광(MnO₂)", qty_kg: 0.399 }, { tier: 3, short: "Codelco", item: "황동광(Cu)", qty_kg: 0.045 }]
  },
  {
    id: "BOM-004", category: "휠", product: "Al 3003-H16 판재 3.5T 18인치(D457mm)", item_no: "WHL-18-001", item_name: "Al 3003-H16 판재 3.5T", qty: 2.40, unit: "pcs/pcs", supplier_id: "NOV-001", lead_time: 21, price: 980, status: "REGISTERING", components: "Al 97.8%, Mn 1.32%, Cu 0.15%", weight_g: 1596, approved_at: "2026-04-15",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-H16 판재 3.5T", qty_kg: 3.798 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳+EMD", qty_kg: 3.926 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 7.330 }, { tier: 3, short: "Comilog", item: "Mn 정광(MnO₂)", qty_kg: 0.503 }]
  },
  {
    id: "BOM-005", category: "파이프", product: "Al 3003-O 튜브 Ø12×1.5T L3000mm", item_no: "PIP-012-001", item_name: "Al 3003-O 튜브 Ø12mm×1.5T", qty: 1.05, unit: "m/m", supplier_id: "NOV-001", lead_time: 28, price: 45, status: "DISCONTINUED", components: "Al 97.9%, Mn 1.25%, Cu 0.12%", weight_g: 180, approved_at: "2025-12-01",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-O 튜브 Ø12", qty_kg: 0.189 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳", qty_kg: 0.195 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 0.365 }, { tier: 3, short: "Comilog", item: "Mn 정광", qty_kg: 0.024 }]
  },
  {
    id: "BOM-006", category: "파이프", product: "Al 3003-O 튜브 Ø25×2.0T L3000mm", item_no: "PIP-025-001", item_name: "Al 3003-O 튜브 Ø25mm×2.0T", qty: 1.05, unit: "m/m", supplier_id: "NOV-001", lead_time: 28, price: 78, status: "ACTIVE", components: "Al 97.9%, Mn 1.25%, Cu 0.12%", weight_g: 411, approved_at: "2026-03-20",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-O 튜브 Ø25", qty_kg: 0.412 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳", qty_kg: 0.426 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 0.795 }, { tier: 3, short: "Comilog", item: "Mn 정광", qty_kg: 0.052 }]
  },
  {
    id: "BOM-007", category: "튜브", product: "Al 3003-H14 튜브 Ø8×1.0T L2000mm", item_no: "TUB-008-001", item_name: "Al 3003-H14 튜브 Ø8mm×1.0T", qty: 1.03, unit: "m/m", supplier_id: "NOV-001", lead_time: 21, price: 32, status: "REGISTERING", components: "Al 97.9%, Mn 1.25%, Cu 0.12%", weight_g: 107, approved_at: "2026-05-15",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-H14 튜브 Ø8", qty_kg: 0.107 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳", qty_kg: 0.111 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 0.207 }, { tier: 3, short: "Comilog", item: "Mn 정광", qty_kg: 0.014 }]
  },
  {
    id: "BOM-008", category: "튜브", product: "Al 3003-H14 튜브 Ø16×1.5T L2000mm", item_no: "TUB-016-001", item_name: "Al 3003-H14 튜브 Ø16mm×1.5T", qty: 1.04, unit: "m/m", supplier_id: "NOV-001", lead_time: 21, price: 55, status: "INACTIVE", components: "Al 97.9%, Mn 1.25%, Cu 0.12%", weight_g: 218, approved_at: "2026-02-18",
    tier_tree: [{ tier: 1, short: "노벨리스코리아", item: "Al 3003-H14 튜브 Ø16", qty_kg: 0.218 }, { tier: 2, short: "케이알엠", item: "P1020 잉곳", qty_kg: 0.225 }, { tier: 3, short: "Windalco", item: "알루미나(Al₂O₃)", qty_kg: 0.421 }, { tier: 3, short: "Comilog", item: "Mn 정광", qty_kg: 0.027 }]
  },
];

// 시점별 모의 이력 데이터셋 (NODE_HISTORY)
export const NODE_HISTORY = [
  // === NOV-001 (노벨리스코리아) 이력 ===
  { partner_id: "NOV-001", date: "2026-05-15", scope1: 82000, scope2: 60000, feoc_ratio: 8.1, trir: 0.62, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-H14 튜브", weight_kg: 0.22, components: "Al 97.9%, Mn 1.25%, Cu 0.12%", width: 16, length: 2000, diameter_mm: 16 },
  { partner_id: "NOV-001", date: "2026-05-12", scope1: 81800, scope2: 59800, feoc_ratio: 8.1, trir: 0.62, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-H14 판재", weight_kg: 1.31, components: "Al 97.9%, Mn 1.25%, Cu 0.12%", width: 600, length: 400, diameter_mm: null },
  { partner_id: "NOV-001", date: "2026-05-08", scope1: 81500, scope2: 59500, feoc_ratio: 8.0, trir: 0.61, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-H14 판재", weight_kg: 0.495, components: "Al 97.9%, Mn 1.25%, Cu 0.12%", width: 400, length: 300, diameter_mm: null },
  { partner_id: "NOV-001", date: "2026-04-15", scope1: 81000, scope2: 59000, feoc_ratio: 8.0, trir: 0.60, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-H16 판재 3.5T", weight_kg: 3.798, components: "Al 97.8%, Mn 1.32%, Cu 0.15%", width: null, length: null, diameter_mm: 457 },
  { partner_id: "NOV-001", date: "2026-04-10", scope1: 80800, scope2: 58800, feoc_ratio: 7.9, trir: 0.60, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-H16 판재 3.0T", weight_kg: 3.016, components: "Al 97.8%, Mn 1.32%, Cu 0.15%", width: null, length: null, diameter_mm: 432 },
  { partner_id: "NOV-001", date: "2026-03-20", scope1: 80000, scope2: 58000, feoc_ratio: 7.8, trir: 0.58, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-O 튜브 Ø25", weight_kg: 0.412, components: "Al 97.9%, Mn 1.25%, Cu 0.12%", width: null, length: 3000, diameter_mm: 25 },
  { partner_id: "NOV-001", date: "2026-02-18", scope1: 79500, scope2: 57500, feoc_ratio: 7.7, trir: 0.58, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-H14 튜브 Ø16", weight_kg: 0.218, components: "Al 97.9%, Mn 1.25%, Cu 0.12%", width: null, length: 2000, diameter_mm: 16 },
  { partner_id: "NOV-001", date: "2026-01-15", scope1: 79000, scope2: 57000, feoc_ratio: 7.5, trir: 0.57, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003 슬라브", weight_kg: 1520, components: "Al 97.9%, Mn 1.25%, Cu 0.12%, Si 0.28%, Fe 0.45%", width: 600, length: 3000, diameter_mm: null },
  { partner_id: "NOV-001", date: "2026-01-12", scope1: 79000, scope2: 57000, feoc_ratio: 7.5, trir: 0.57, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003 슬라브", weight_kg: 1500, components: "Al 97.9%, Mn 1.25%, Cu 0.12%", width: 600, length: 3000, diameter_mm: null },
  { partner_id: "NOV-001", date: "2025-12-01", scope1: 78000, scope2: 56000, feoc_ratio: 7.2, trir: 0.55, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003-O 튜브 Ø12", weight_kg: 0.189, components: "Al 97.9%, Mn 1.25%, Cu 0.12%", width: null, length: 3000, diameter_mm: 12 },
  { partner_id: "NOV-001", date: "2025-11-20", scope1: 77500, scope2: 55500, feoc_ratio: 7.0, trir: 0.55, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "울산", name: "Al 3003 슬라브 (시제품)", weight_kg: 1450, components: "Al 97.5%, Mn 1.30%, Cu 0.10%", width: 600, length: 3000, diameter_mm: null },

  // === NSM-001 (남성알루미늄) 이력 ===
  { partner_id: "NSM-001", date: "2026-05-15", scope1: 45000, scope2: 32000, feoc_ratio: 6.3, trir: 0.78, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "창원", name: "Al 3003-H14 빌렛", weight_kg: 980, components: "Al 97.9%, Mn 1.20%, Cu 0.11%", width: 200, length: 6000, diameter_mm: null },
  { partner_id: "NSM-001", date: "2026-05-08", scope1: 44800, scope2: 31800, feoc_ratio: 6.3, trir: 0.77, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "창원", name: "Al 3003-H14 빌렛", weight_kg: 980, components: "Al 97.9%, Mn 1.20%, Cu 0.11%", width: 200, length: 6000, diameter_mm: null },
  { partner_id: "NSM-001", date: "2026-04-15", scope1: 44500, scope2: 31500, feoc_ratio: 6.2, trir: 0.75, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "창원", name: "Al 3003 빌렛", weight_kg: 950, components: "Al 97.9%, Mn 1.20%, Cu 0.11%", width: 200, length: 6000, diameter_mm: null },
  { partner_id: "NSM-001", date: "2026-01-15", scope1: 43000, scope2: 30000, feoc_ratio: 6.0, trir: 0.72, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "창원", name: "Al 3003 압출 빌렛", weight_kg: 900, components: "Al 97.8%, Mn 1.22%, Cu 0.10%", width: 200, length: 5000, diameter_mm: null },
  { partner_id: "NSM-001", date: "2025-12-01", scope1: 42000, scope2: 29000, feoc_ratio: 5.8, trir: 0.70, risk: "저위험", deforest_yn: "N", deforest_note: "", origin: "창원", name: "Al 3003 빌렛 (초기)", weight_kg: 850, components: "Al 97.8%, Mn 1.25%, Cu 0.10%", width: 200, length: 5000, diameter_mm: null },

  // === KRM-001 (케이알엠) 이력 ===
  { partner_id: "KRM-001", date: "2026-05-15", scope1: 58000, scope2: 40000, feoc_ratio: 12.5, trir: 1.12, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 알루미늄 잉곳", weight_kg: 1020, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2026-05-08", scope1: 57900, scope2: 39900, feoc_ratio: 12.5, trir: 1.12, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 알루미늄 잉곳", weight_kg: 0.512, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2026-04-15", scope1: 57500, scope2: 39500, feoc_ratio: 12.3, trir: 1.10, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 알루미늄 잉곳", weight_kg: 3.926, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2026-04-10", scope1: 57200, scope2: 39200, feoc_ratio: 12.2, trir: 1.09, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 알루미늄 잉곳", weight_kg: 3.117, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2026-03-20", scope1: 57000, scope2: 39000, feoc_ratio: 12.0, trir: 1.08, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 알루미늄 잉곳", weight_kg: 0.426, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2026-02-18", scope1: 56500, scope2: 38500, feoc_ratio: 11.8, trir: 1.05, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 알루미늄 잉곳", weight_kg: 0.225, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2026-01-15", scope1: 56000, scope2: 38000, feoc_ratio: 11.5, trir: 1.02, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 잉곳", weight_kg: 1570, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2026-01-12", scope1: 56000, scope2: 38000, feoc_ratio: 11.5, trir: 1.02, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "전기동(Cu) 캐소드", weight_kg: 125, components: "Cu 99.99%, Pb≤5ppm, S≤15ppm", width: null, length: 900, diameter_mm: null },
  { partner_id: "KRM-001", date: "2025-12-01", scope1: 55000, scope2: 37000, feoc_ratio: 11.0, trir: 1.00, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 알루미늄 잉곳", weight_kg: 0.195, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "KRM-001", date: "2025-11-20", scope1: 54500, scope2: 36500, feoc_ratio: 10.8, trir: 1.00, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "인천", name: "P1020 잉곳 (시범납품)", weight_kg: 1400, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },

  // === HMC-002 (현대머티리얼) 이력 ===
  { partner_id: "HMC-002", date: "2026-05-15", scope1: 42000, scope2: 28000, feoc_ratio: 9.8, trir: 0.95, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 (AluNorte)", name: "알루미늄 잉곳 P1020", weight_kg: 25, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "HMC-002", date: "2026-05-08", scope1: 41800, scope2: 27800, feoc_ratio: 9.8, trir: 0.94, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 (AluNorte)", name: "알루미늄 잉곳 P1020", weight_kg: 25, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "HMC-002", date: "2026-04-15", scope1: 41500, scope2: 27500, feoc_ratio: 9.7, trir: 0.92, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 (AluNorte)", name: "알루미늄 잉곳 P1020", weight_kg: 24, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "HMC-002", date: "2026-01-15", scope1: 40000, scope2: 26000, feoc_ratio: 9.5, trir: 0.90, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 (AluNorte)", name: "알루미늄 잉곳 P1020", weight_kg: 22, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },
  { partner_id: "HMC-002", date: "2025-12-01", scope1: 39000, scope2: 25000, feoc_ratio: 9.2, trir: 0.88, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 (AluNorte)", name: "알루미늄 잉곳 P1020 (초기)", weight_kg: 20, components: "Al 99.7%", width: 200, length: 800, diameter_mm: null },

  // === COM-001 (Comilog) 이력 ===
  { partner_id: "COM-001", date: "2026-05-15", scope1: 52000, scope2: 0, feoc_ratio: 0, trir: 2.15, risk: "중위험", deforest_yn: "Y", deforest_note: "가봉 열대우림 인근 — IUCN 보호지역 인접", origin: "가봉 Moanda", name: "망간 정광(MnO₂)", weight_kg: 62, components: "MnO₂ 82%, Fe 5%", width: null, length: null, diameter_mm: null },
  { partner_id: "COM-001", date: "2026-05-08", scope1: 51800, scope2: 0, feoc_ratio: 0, trir: 2.15, risk: "중위험", deforest_yn: "Y", deforest_note: "가봉 열대우림 인근 — IUCN 보호지역 인접", origin: "가봉 Moanda", name: "망간 정광(MnO₂)", weight_kg: 0.061, components: "MnO₂ 82%, Fe 5%", width: null, length: null, diameter_mm: null },
  { partner_id: "COM-001", date: "2026-04-15", scope1: 51500, scope2: 0, feoc_ratio: 0, trir: 2.12, risk: "중위험", deforest_yn: "Y", deforest_note: "가봉 열대우림 인근 — IUCN 보호지역 인접", origin: "가봉 Moanda", name: "망간 정광(MnO₂)", weight_kg: 0.503, components: "MnO₂ 82%, Fe 5%", width: null, length: null, diameter_mm: null },
  { partner_id: "COM-001", date: "2026-04-10", scope1: 51200, scope2: 0, feoc_ratio: 0, trir: 2.10, risk: "중위험", deforest_yn: "Y", deforest_note: "가봉 열대우림 인근 — IUCN 보호지역 인접", origin: "가봉 Moanda", name: "망간 정광(MnO₂)", weight_kg: 0.399, components: "MnO₂ 82%, Fe 5%", width: null, length: null, diameter_mm: null },
  { partner_id: "COM-001", date: "2026-03-20", scope1: 51000, scope2: 0, feoc_ratio: 0, trir: 2.08, risk: "중위험", deforest_yn: "Y", deforest_note: "가봉 열대우림 인근", origin: "가봉 Moanda", name: "망간 정광", weight_kg: 0.052, components: "MnO₂ 82%, Fe 5%", width: null, length: null, diameter_mm: null },
  { partner_id: "COM-001", date: "2026-02-18", scope1: 50500, scope2: 0, feoc_ratio: 0, trir: 2.05, risk: "중위험", deforest_yn: "Y", deforest_note: "가봉 열대우림 인근", origin: "가봉 Moanda", name: "망간 정광", weight_kg: 0.027, components: "MnO₂ 82%, Fe 5%", width: null, length: null, diameter_mm: null },
  { partner_id: "COM-001", date: "2026-01-15", scope1: 50000, scope2: 0, feoc_ratio: 0, trir: 2.02, risk: "중위험", deforest_yn: "Y", deforest_note: "가봉 열대우림 인근", origin: "가봉 Moanda", name: "Mn 정광(MnO₂)", weight_kg: 62, components: "MnO₂ 82%", width: null, length: null, diameter_mm: null },
  { partner_id: "COM-001", date: "2025-12-01", scope1: 49000, scope2: 0, feoc_ratio: 0, trir: 2.00, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "가봉 Moanda", name: "망간 정광", weight_kg: 0.024, components: "MnO₂ 80%", width: null, length: null, diameter_mm: null },

  // === WIN-001 (Windalco) 이력 ===
  { partner_id: "WIN-001", date: "2026-05-15", scope1: 68000, scope2: 0, feoc_ratio: 0, trir: 1.85, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 2930, components: "Al₂O₃ 99.4%", width: null, length: null, diameter_mm: null },
  { partner_id: "WIN-001", date: "2026-05-08", scope1: 67800, scope2: 0, feoc_ratio: 0, trir: 1.85, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 0.956, components: "Al₂O₃ 99.4%", width: null, length: null, diameter_mm: null },
  { partner_id: "WIN-001", date: "2026-04-15", scope1: 67500, scope2: 0, feoc_ratio: 0, trir: 1.82, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 7.330, components: "Al₂O₃ 99.4%", width: null, length: null, diameter_mm: null },
  { partner_id: "WIN-001", date: "2026-04-10", scope1: 67200, scope2: 0, feoc_ratio: 0, trir: 1.82, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 5.820, components: "Al₂O₃ 99.4%", width: null, length: null, diameter_mm: null },
  { partner_id: "WIN-001", date: "2026-03-20", scope1: 67000, scope2: 0, feoc_ratio: 0, trir: 1.80, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 0.795, components: "Al₂O₃ 99.4%", width: null, length: 3000, diameter_mm: 25 },
  { partner_id: "WIN-001", date: "2026-02-18", scope1: 66500, scope2: 0, feoc_ratio: 0, trir: 1.78, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 0.421, components: "Al₂O₃ 99.4%", width: null, length: 2000, diameter_mm: 16 },
  { partner_id: "WIN-001", date: "2026-01-15", scope1: 66000, scope2: 0, feoc_ratio: 0, trir: 1.75, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 2930, components: "Al₂O₃ 99.4%", width: null, length: null, diameter_mm: null },
  { partner_id: "WIN-001", date: "2025-12-01", scope1: 65000, scope2: 0, feoc_ratio: 0, trir: 1.72, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "자메이카 Ewarton", name: "알루미나(Al₂O₃)", weight_kg: 0.365, components: "Al₂O₃ 99.4%", width: null, length: 3000, diameter_mm: 12 },

  // === COD-001 (Codelco) 이력 ===
  { partner_id: "COD-001", date: "2026-05-15", scope1: 112000, scope2: 0, feoc_ratio: 0, trir: 1.42, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "칠레 Calama", name: "황동광(Cu)", weight_kg: 6, components: "Cu 28%, Fe 30%", width: null, length: null, diameter_mm: null },
  { partner_id: "COD-001", date: "2026-05-08", scope1: 111800, scope2: 0, feoc_ratio: 0, trir: 1.42, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "칠레 Calama", name: "황동광(Cu)", weight_kg: 0.006, components: "Cu 28%, Fe 30%", width: null, length: null, diameter_mm: null },
  { partner_id: "COD-001", date: "2026-04-10", scope1: 111000, scope2: 0, feoc_ratio: 0, trir: 1.40, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "칠레 Calama", name: "황동광(Cu)", weight_kg: 0.045, components: "Cu 28%, Fe 30%", width: null, length: null, diameter_mm: null },
  { partner_id: "COD-001", date: "2026-01-15", scope1: 109000, scope2: 0, feoc_ratio: 0, trir: 1.38, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "칠레 Calama", name: "황동광(Cu)", weight_kg: 6, components: "Cu 28%, Fe 30%", width: null, length: null, diameter_mm: null },
  { partner_id: "COD-001", date: "2025-12-01", scope1: 108000, scope2: 0, feoc_ratio: 0, trir: 1.35, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "칠레 Calama", name: "황동광(Cu) (시험용)", weight_kg: 5, components: "Cu 28%", width: null, length: null, diameter_mm: null },

  // === EMG-002 (EMG Brasil) 이력 ===
  { partner_id: "EMG-002", date: "2026-05-15", scope1: 38000, scope2: 0, feoc_ratio: 0, trir: 1.92, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Pará", name: "Mn 정광", weight_kg: 59, components: "MnO₂ 80%", width: null, length: null, diameter_mm: null },
  { partner_id: "EMG-002", date: "2026-05-08", scope1: 37800, scope2: 0, feoc_ratio: 0, trir: 1.91, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Pará", name: "Mn 정광", weight_kg: 59, components: "MnO₂ 80%", width: null, length: null, diameter_mm: null },
  { partner_id: "EMG-002", date: "2026-04-15", scope1: 37500, scope2: 0, feoc_ratio: 0, trir: 1.90, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Pará", name: "Mn 정광", weight_kg: 55, components: "MnO₂ 80%", width: null, length: null, diameter_mm: null },
  { partner_id: "EMG-002", date: "2026-01-15", scope1: 36000, scope2: 0, feoc_ratio: 0, trir: 1.85, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Pará", name: "Mn 정광", weight_kg: 50, components: "MnO₂ 80%", width: null, length: null, diameter_mm: null },

  // === ALU-002 (AluNorte) 이력 ===
  { partner_id: "ALU-002", date: "2026-05-15", scope1: 72000, scope2: 0, feoc_ratio: 0, trir: 1.65, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Barcarena", name: "알루미나", weight_kg: 1890, components: "Al₂O₃ 99.3%", width: null, length: null, diameter_mm: null },
  { partner_id: "ALU-002", date: "2026-05-08", scope1: 71800, scope2: 0, feoc_ratio: 0, trir: 1.65, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Barcarena", name: "알루미나", weight_kg: 1890, components: "Al₂O₃ 99.3%", width: null, length: null, diameter_mm: null },
  { partner_id: "ALU-002", date: "2026-04-15", scope1: 71500, scope2: 0, feoc_ratio: 0, trir: 1.62, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Barcarena", name: "알루미나", weight_kg: 1800, components: "Al₂O₃ 99.3%", width: null, length: null, diameter_mm: null },
  { partner_id: "ALU-002", date: "2026-01-15", scope1: 70000, scope2: 0, feoc_ratio: 0, trir: 1.60, risk: "중위험", deforest_yn: "N", deforest_note: "", origin: "브라질 Barcarena", name: "알루미나", weight_kg: 1750, components: "Al₂O₃ 99.3%", width: null, length: null, diameter_mm: null }
];

// 실사 데이터
export const INSPECTIONS_DATA = [
  {
    id: 1, target: "(주)케이알엠 (2차)", type: "특별현장실사", phase: "IMPROVEMENT", risk: "중위험", scheduled: "2026-03-15", actual: "2026-03-18",
    findings: "FEOC 원료 12.5% 초과",
    improvements: "1. FEOC 비해당 알루미나 대체 소싱 계획 제출\n2. PFC 모니터링 시스템 구축",
    deadline: "2026-09-30"
  },
  {
    id: 2, target: "Comilog Gabon (3차-A)", type: "정기현장실사", phase: "MONITORING", risk: "중위험", scheduled: "2026-01-20", actual: "2026-01-23",
    findings: "TRIR 2.15 CSDDD Art.8 기준 초과 / 산림파괴 리스크 지역",
    improvements: "1. 산업안전 개선계획서 제출\n2. 산림복원 계획 수립 및 이행 착수",
    deadline: "2026-06-30"
  },
  {
    id: 3, target: "(주)노벨리스코리아 (1차)", type: "정기현장실사", phase: "COMPLETED", risk: "저위험", scheduled: "2025-10-10", actual: "2025-10-12",
    findings: "FEOC 8.1% 주의",
    improvements: "1. FEOC 대안 소싱 계획 제출",
    deadline: "2026-03-31"
  },
];

// ESG 리스크 알림 (알림 센터용)
export const NOTIFICATIONS = [
  { id: 1, type: "RISK", level: "fail", title: "FEOC 초과 — (주)케이알엠", msg: "FEOC 원료 12.5% IRA 세액공제 위험 임계점 초과. 대안 소싱 계획 제출 요청.", time: "2026-05-19 09:15", read: false },
  { id: 2, type: "RISK", level: "fail", title: "산림파괴 리스크 — Comilog Gabon", msg: "IUCN 보호지역 인접. 현대모비스 산림파괴방지 정책 복원계획 제출 필요.", time: "2026-05-19 08:50", read: false },
  { id: 3, type: "URGENT", level: "warn", title: "긴급 요청 제출 완료 — RM-003", msg: "케이알엠이 전해망간(EMD) 원산지 증명서를 제출했습니다. 검토 필요.", time: "2026-05-18 16:30", read: false },
  { id: 4, type: "INSPECT", level: "warn", title: "현장 실사 예정 — Comilog", msg: "2026-06-15 현장 실사 일정이 확정되었습니다. 담당자 배정이 필요합니다.", time: "2026-05-18 11:20", read: true },
  { id: 5, type: "SELF", level: "info", title: "자가진단 보고서 제출 — Comilog", msg: "SAR-2025-0001 자가진단 보고서가 제출되었습니다. 원청사 최종 승인이 필요합니다.", time: "2026-05-17 14:05", read: true },
  { id: 6, type: "INVITE", level: "info", title: "초대 링크 수락 — (주)노벨리스코리아", msg: "초대 이메일이 수락되었습니다. COM_PARTNER 테이블 등록이 완료되었습니다.", time: "2026-05-16 09:00", read: true },
];

export const NET_ZERO = [
  { year: "2020", s12: 340, s3: 1180, tgt: null }, { year: "2022", s12: 318, s3: 1050, tgt: null },
  { year: "2024", s12: 285, s3: 936, tgt: null }, { year: "2026E", s12: 260, s3: 820, tgt: 1100 },
  { year: "2030E", s12: 200, s3: 650, tgt: 800 }, { year: "2040E", s12: 50, s3: 300, tgt: 400 },
  { year: "2045E", s12: 0, s3: 0, tgt: 0 },
];

export const ESG_INDICATORS = {
  "3차 협력사 (채굴)": [
    { no: 1, cat: "인권·노동", name: "아동·강제노동 Zero", priority: "Low", regs: ["CSDDD", "UFLPA"], value: "확인서 완비", status: "pass", partner: "Comilog" },
    { no: 5, cat: "인권·노동", name: "산업안전 TRIR", priority: "High", regs: ["CSDDD", "CSRD"], value: "2.15건/백만h", status: "warn", partner: "Comilog" },
    { no: 18, cat: "거버넌스", name: "FEOC 원료 비중", priority: "Low", regs: ["IRA", "FEOC"], value: "0%", status: "pass", partner: "Comilog" },
  ],
  "2차 협력사 (제련)": [
    { no: 34, cat: "거버넌스", name: "FEOC 지분 구조", priority: "Critical", regs: ["IRA", "FEOC"], value: "12.5%", status: "fail", partner: "(주)케이알엠" },
  ],
  "1차 협력사 (합금)": [
    { no: 40, cat: "공정·품질", name: "Mn 함량 1.0~1.5%", priority: "Low", regs: ["ASTM"], value: "1.25%", status: "pass", partner: "(주)노벨리스코리아" },
    { no: 50, cat: "거버넌스", name: "FEOC Mn·Cu 공급사", priority: "Critical", regs: ["IRA", "FEOC"], value: "8.1%", status: "warn", partner: "(주)노벨리스코리아" },
  ],
  "원청사 (가공)": [
    { no: 55, cat: "에너지·기후", name: "기후전환계획 이사회 승인", priority: "Critical", regs: ["CSDDD", "CSRD"], value: "2030 Net-Zero", status: "pass", partner: "현대모비스" },
    { no: 64, cat: "인권·노동", name: "강제노동 실사 완료율", priority: "Critical", regs: ["CSDDD", "UFLPA"], value: "94%", status: "warn", partner: "현대모비스" },
  ],
};
