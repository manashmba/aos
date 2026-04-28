/**
 * Localized scripted agent replies for the demo-mode chat.
 *
 * Strategy:
 *  1. Detect intent from the user's message — works on either English keywords
 *     or the native-script keywords surfaced in suggestion chips.
 *  2. Pick the reply for the active i18n language; fall back to English.
 *
 * Hindi has full reply text. The other Indic languages get a short localized
 * lead line + the English detail block, so finance figures stay readable in
 * the accounting convention everyone learns in.
 */

import i18n from "@/i18n";
import type { LangCode } from "@/i18n";

export type Intent =
  | "trialBalance"
  | "createPO"
  | "reorder"
  | "leave"
  | "salesAgeing"
  | "fallback";

interface IntentMeta {
  agent: string;
  tool: string;
  toolArgs?: Record<string, unknown>;
  confidence: number;
  requiresApproval?: boolean;
  approvalId?: string;
  // Keywords we look for in user input — both English and Indic surface forms.
  // Lowercased before match for Latin; Indic scripts have no case so direct match works.
  keywords: string[];
}

export const INTENTS: Record<Exclude<Intent, "fallback">, IntentMeta> = {
  trialBalance: {
    agent: "finance",
    tool: "finance.trial_balance",
    confidence: 0.97,
    keywords: [
      "trial", "balance",
      "ट्रायल", "बैलेंस",                // hi/mr
      "ட்ரையல்", "பேலன்ஸ்",                // ta
      "ট্রায়াল", "ব্যালেন্স",              // bn
      "ట్రయల్", "బ్యాలెన్స్",                // te
      "ટ્રાયલ", "બૅલેન્સ",                  // gu
      "ಟ್ರಯಲ್", "ಬ್ಯಾಲೆನ್ಸ್",                // kn
    ],
  },
  createPO: {
    agent: "procurement",
    tool: "procurement.create_po",
    toolArgs: { vendor: "Acme Bearings", qty: 100, rate: 500 },
    confidence: 0.93,
    requiresApproval: true,
    approvalId: "apr_demo_po142",
    keywords: [
      "po", "purchase", "procure",
      "खरीद", "ख़रीद",
      "கொள்முதல்", "பிஓ",
      "ক্রয়", "পিও",
      "కొనుగోలు", "పిఓ",
      "ખરીદી", "પીઓ",
      "ಖರೀದಿ", "ಪಿಒ",
    ],
  },
  reorder: {
    agent: "inventory",
    tool: "inventory.reorder_suggestions",
    confidence: 0.95,
    keywords: [
      "reorder", "stock", "inventory",
      "पुनः ऑर्डर", "स्टॉक",
      "மறு-ஆர்டர்", "சரக்கு", "கையிருப்பு",
      "পুনঃঅর্ডার", "স্টক",
      "మళ్ళీ", "స్టాక్",
      "રી-ઓર્ડર", "સ્ટૉક",
      "ಮರು-ಆರ್ಡರ್", "ಸ್ಟಾಕ್",
    ],
  },
  leave: {
    agent: "hr",
    tool: "hr.apply_leave",
    toolArgs: { days: 3 },
    confidence: 0.9,
    keywords: [
      "leave", "hr", "payroll",
      "छुट्टी", "अवकाश", "वेतन",
      "விடுமுறை", "சம்பளம்",
      "ছুটি", "বেতন",
      "సెలవు", "జీతం",
      "રજા", "પગાર",
      "ರಜೆ", "ಸಂಬಳ",
    ],
  },
  salesAgeing: {
    agent: "sales",
    tool: "sales.ageing_summary",
    confidence: 0.94,
    keywords: [
      "customer", "sales", "credit", "ageing",
      "ग्राहक", "बिक्री", "क्रेडिट",
      "வாடிக்கையாளர்", "விற்பனை",
      "গ্রাহক", "বিক্রয়",
      "కస్టమర్", "అమ్మకం",
      "ગ્રાહક", "વેચાણ",
      "ಗ್ರಾಹಕ", "ಮಾರಾಟ",
    ],
  },
};

// Per-language reply text. Each entry maps Intent → lines. Multi-line strings
// include figures in Latin digits (accounting convention) while prose is in
// the active language. English serves as a fallback for any missing locale.
type ReplyMap = Record<Intent, string>;

const replies: Record<LangCode, ReplyMap> = {
  en: {
    trialBalance:
      "Trial Balance as of today (FY2025–26):\n" +
      "• Total Debits: ₹1,24,50,000\n" +
      "• Total Credits: ₹1,24,50,000\n" +
      "• Balanced ✓\n\n" +
      "Open Trial Balance for full breakdown.",
    createPO:
      "Drafted PO-2026-0142 for Acme Bearings — 100 units × ₹500 = ₹50,000 + GST ₹9,000.\n" +
      "Exceeds ₹25,000 threshold → pending Finance Manager approval.",
    reorder:
      "3 SKUs below reorder level:\n" +
      "• SS-6205 Ball Bearing — 24 on hand (ROL 50) → suggest 200\n" +
      "• PCB-A11 Controller — 8 on hand (ROL 25) → suggest 100\n" +
      "• LUB-Syn-5L — 2 on hand (ROL 10) → suggest 40",
    leave:
      "Leave request LR-0087 recorded: 3 days (18–20 Apr) for Rohan Das.\n" +
      "Auto-approved — balance 9 → 6 days.",
    salesAgeing:
      "Top 3 customers by outstanding:\n" +
      "• Bharat Tools — ₹8,40,000 (15 days avg)\n" +
      "• NovaCorp — ₹4,10,000 (42 days avg) ⚠ over credit days\n" +
      "• RelayTech — ₹2,75,000 (current)",
    fallback:
      "(demo) I can help with finance, procurement, sales, inventory, HR or audit. " +
      'Try: "show trial balance", "reorder suggestions", "create PO Acme 100 bearings at ₹500", ' +
      'or "apply 3 days leave".',
  },

  hi: {
    trialBalance:
      "आज की ट्रायल बैलेंस (FY2025–26):\n" +
      "• कुल डेबिट: ₹1,24,50,000\n" +
      "• कुल क्रेडिट: ₹1,24,50,000\n" +
      "• संतुलित ✓\n\n" +
      "विस्तृत ब्योरे के लिए ट्रायल बैलेंस खोलें।",
    createPO:
      "Acme Bearings के लिए PO-2026-0142 तैयार — 100 यूनिट × ₹500 = ₹50,000 + GST ₹9,000.\n" +
      "₹25,000 की सीमा से अधिक → वित्त प्रबंधक की अनुमोदन प्रतीक्षित।",
    reorder:
      "पुनः ऑर्डर स्तर से नीचे 3 SKU:\n" +
      "• SS-6205 बॉल बेयरिंग — स्टॉक 24 (ROL 50) → 200 सुझाई\n" +
      "• PCB-A11 कंट्रोलर — स्टॉक 8 (ROL 25) → 100 सुझाई\n" +
      "• LUB-Syn-5L — स्टॉक 2 (ROL 10) → 40 सुझाई",
    leave:
      "छुट्टी अनुरोध LR-0087 दर्ज: 3 दिन (18–20 अप्रैल), रोहन दास के लिए।\n" +
      "स्वतः अनुमोदित — शेष 9 → 6 दिन।",
    salesAgeing:
      "बकाया के अनुसार शीर्ष 3 ग्राहक:\n" +
      "• Bharat Tools — ₹8,40,000 (औसत 15 दिन)\n" +
      "• NovaCorp — ₹4,10,000 (औसत 42 दिन) ⚠ क्रेडिट सीमा पार\n" +
      "• RelayTech — ₹2,75,000 (वर्तमान)",
    fallback:
      "(डेमो) मैं वित्त, खरीद, बिक्री, स्टॉक, कर्मचारी या ऑडिट में मदद कर सकता हूँ। " +
      'उदाहरण: "ट्रायल बैलेंस दिखाएँ", "क्या पुनः ऑर्डर चाहिए?", "₹50,000 का PO बनाएँ"।',
  },

  // For the remaining 6 languages: translated lead sentence + figures.
  // Intentionally lighter than Hindi so the file stays readable; finance
  // numerics are language-neutral anyway.
  ta: leadOnly({
    trialBalance: "இன்றைய டிரையல் பேலன்ஸ் (FY2025–26):\n• மொத்த டெபிட்: ₹1,24,50,000\n• மொத்த க்ரெடிட்: ₹1,24,50,000\n• சமநிலை ✓",
    createPO: "Acme Bearings-க்காக PO-2026-0142 உருவாக்கப்பட்டது — 100 × ₹500 = ₹50,000 + GST ₹9,000.\n₹25,000 வரம்பை மீறுகிறது → நிதி மேலாளர் அனுமதி நிலுவையில்.",
    reorder: "மறு-ஆர்டர் நிலைக்கு கீழே 3 SKU:\n• SS-6205 — 24 (ROL 50) → 200\n• PCB-A11 — 8 (ROL 25) → 100\n• LUB-5L — 2 (ROL 10) → 40",
    leave: "விடுமுறை LR-0087 பதிவு: 3 நாட்கள், ரோகன் தாஸ். தானாக அனுமதிக்கப்பட்டது.",
    salesAgeing: "நிலுவை அடிப்படையில் முதல் 3 வாடிக்கையாளர்கள்:\n• Bharat Tools — ₹8,40,000\n• NovaCorp — ₹4,10,000 ⚠\n• RelayTech — ₹2,75,000",
    fallback: "(டெமோ) நிதி, கொள்முதல், விற்பனை, சரக்கு, பணியாளர் தொடர்பாக கேளுங்கள்.",
  }),

  bn: leadOnly({
    trialBalance: "আজকের ট্রায়াল ব্যালেন্স (FY2025–26):\n• মোট ডেবিট: ₹1,24,50,000\n• মোট ক্রেডিট: ₹1,24,50,000\n• সমতুল ✓",
    createPO: "Acme Bearings-এর জন্য PO-2026-0142 তৈরি — 100 × ₹500 = ₹50,000 + GST ₹9,000.\n₹25,000 সীমা ছাড়িয়েছে → অনুমোদনের অপেক্ষায়।",
    reorder: "পুনঃঅর্ডার স্তরের নিচে 3 SKU:\n• SS-6205 — 24 (ROL 50) → 200\n• PCB-A11 — 8 (ROL 25) → 100\n• LUB-5L — 2 (ROL 10) → 40",
    leave: "ছুটির অনুরোধ LR-0087: 3 দিন, রোহন দাস। স্বয়ংক্রিয়ভাবে অনুমোদিত।",
    salesAgeing: "বকেয়া অনুসারে শীর্ষ 3 গ্রাহক:\n• Bharat Tools — ₹8,40,000\n• NovaCorp — ₹4,10,000 ⚠\n• RelayTech — ₹2,75,000",
    fallback: "(ডেমো) অর্থ, ক্রয়, বিক্রয়, স্টক বা কর্মী সম্পর্কে জিজ্ঞাসা করুন।",
  }),

  mr: leadOnly({
    trialBalance: "आजचे ट्रायल बॅलन्स (FY2025–26):\n• एकूण डेबिट: ₹1,24,50,000\n• एकूण क्रेडिट: ₹1,24,50,000\n• संतुलित ✓",
    createPO: "Acme Bearings साठी PO-2026-0142 तयार — 100 × ₹500 = ₹50,000 + GST ₹9,000.\n₹25,000 मर्यादा ओलांडली → मंजुरी प्रलंबित.",
    reorder: "पुन्हा-ऑर्डर पातळीच्या खाली 3 SKU:\n• SS-6205 — 24 (ROL 50) → 200\n• PCB-A11 — 8 (ROL 25) → 100\n• LUB-5L — 2 (ROL 10) → 40",
    leave: "रजेची विनंती LR-0087: 3 दिवस, रोहन दास. स्वयं-मंजूर.",
    salesAgeing: "थकबाकीनुसार 3 ग्राहक:\n• Bharat Tools — ₹8,40,000\n• NovaCorp — ₹4,10,000 ⚠\n• RelayTech — ₹2,75,000",
    fallback: "(डेमो) वित्त, खरेदी, विक्री, साठा किंवा कर्मचाऱ्यांविषयी विचारा.",
  }),

  gu: leadOnly({
    trialBalance: "આજનું ટ્રાયલ બૅલેન્સ (FY2025–26):\n• કુલ ડેબિટ: ₹1,24,50,000\n• કુલ ક્રેડિટ: ₹1,24,50,000\n• સંતુલિત ✓",
    createPO: "Acme Bearings માટે PO-2026-0142 તૈયાર — 100 × ₹500 = ₹50,000 + GST ₹9,000.\n₹25,000 મર્યાદા વટાવી → મંજૂરી બાકી.",
    reorder: "રી-ઓર્ડર સ્તરથી નીચે 3 SKU:\n• SS-6205 — 24 (ROL 50) → 200\n• PCB-A11 — 8 (ROL 25) → 100\n• LUB-5L — 2 (ROL 10) → 40",
    leave: "રજા વિનંતી LR-0087: 3 દિવસ, રોહન દાસ. સ્વતઃ મંજૂર.",
    salesAgeing: "બાકી મુજબ ટોચના 3 ગ્રાહકો:\n• Bharat Tools — ₹8,40,000\n• NovaCorp — ₹4,10,000 ⚠\n• RelayTech — ₹2,75,000",
    fallback: "(ડેમો) નાણાં, ખરીદી, વેચાણ, સ્ટૉક કે કર્મચારી વિશે પૂછો.",
  }),

  te: leadOnly({
    trialBalance: "ఈరోజు ట్రయల్ బ్యాలెన్స్ (FY2025–26):\n• మొత్తం డెబిట్: ₹1,24,50,000\n• మొత్తం క్రెడిట్: ₹1,24,50,000\n• సమతౌల్యం ✓",
    createPO: "Acme Bearings కోసం PO-2026-0142 — 100 × ₹500 = ₹50,000 + GST ₹9,000.\n₹25,000 దాటింది → అనుమతి పెండింగ్.",
    reorder: "మళ్ళీ-ఆర్డర్ స్థాయి కంటే తక్కువ 3 SKU:\n• SS-6205 — 24 (ROL 50) → 200\n• PCB-A11 — 8 (ROL 25) → 100\n• LUB-5L — 2 (ROL 10) → 40",
    leave: "సెలవు అభ్యర్థన LR-0087: 3 రోజులు, రోహన్ దాస్. స్వయంచాలకంగా ఆమోదించబడింది.",
    salesAgeing: "బకాయి ప్రకారం టాప్ 3 కస్టమర్లు:\n• Bharat Tools — ₹8,40,000\n• NovaCorp — ₹4,10,000 ⚠\n• RelayTech — ₹2,75,000",
    fallback: "(డెమో) ఆర్థిక, కొనుగోలు, అమ్మకం, స్టాక్ లేదా సిబ్బంది గురించి అడగండి.",
  }),

  kn: leadOnly({
    trialBalance: "ಇಂದಿನ ಟ್ರಯಲ್ ಬ್ಯಾಲೆನ್ಸ್ (FY2025–26):\n• ಒಟ್ಟು ಡೆಬಿಟ್: ₹1,24,50,000\n• ಒಟ್ಟು ಕ್ರೆಡಿಟ್: ₹1,24,50,000\n• ಸಮತೋಲನ ✓",
    createPO: "Acme Bearings ಗೆ PO-2026-0142 — 100 × ₹500 = ₹50,000 + GST ₹9,000.\n₹25,000 ಮಿತಿ ಮೀರಿದೆ → ಅನುಮೋದನೆ ಬಾಕಿ.",
    reorder: "ಮರು-ಆರ್ಡರ್ ಮಟ್ಟಕ್ಕಿಂತ ಕಡಿಮೆ 3 SKU:\n• SS-6205 — 24 (ROL 50) → 200\n• PCB-A11 — 8 (ROL 25) → 100\n• LUB-5L — 2 (ROL 10) → 40",
    leave: "ರಜೆ ವಿನಂತಿ LR-0087: 3 ದಿನಗಳು, ರೋಹನ್ ದಾಸ್. ಸ್ವಯಂ-ಅನುಮೋದಿತ.",
    salesAgeing: "ಬಾಕಿ ಪ್ರಕಾರ ಟಾಪ್ 3 ಗ್ರಾಹಕರು:\n• Bharat Tools — ₹8,40,000\n• NovaCorp — ₹4,10,000 ⚠\n• RelayTech — ₹2,75,000",
    fallback: "(ಡೆಮೊ) ಹಣಕಾಸು, ಖರೀದಿ, ಮಾರಾಟ, ಸ್ಟಾಕ್ ಅಥವಾ ಸಿಬ್ಬಂದಿ ಬಗ್ಗೆ ಕೇಳಿ.",
  }),
};

function leadOnly(m: ReplyMap): ReplyMap {
  return m;
}

export function detectIntent(message: string): Intent {
  const lower = message.toLowerCase();
  for (const [intent, meta] of Object.entries(INTENTS) as Array<[Intent, IntentMeta]>) {
    if (meta.keywords.some((k) => lower.includes(k.toLowerCase()) || message.includes(k))) {
      return intent;
    }
  }
  return "fallback";
}

export function getReply(intent: Intent): string {
  const lng = (i18n.resolvedLanguage ?? "en") as LangCode;
  return replies[lng]?.[intent] ?? replies.en[intent];
}
