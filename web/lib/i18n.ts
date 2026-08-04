import { STRINGS, t as portedT } from "./artworks";
import type { Locale, LocalizedText } from "./types";

/**
 * New copy introduced by the ELYIO redesign that didn't exist in the old
 * frontend's AURA_STRINGS (see ELYIO-FINAL-PROMPT.md for the exact EN
 * strings — those are used verbatim). FR/zh-Hans here are AI-drafted
 * translations, same convention as the rest of this project's editorial
 * content: not yet reviewed by a native speaker, safe to ship because they
 * are UI chrome, not factual/curatorial claims.
 */
const NEW_STRINGS: Record<string, LocalizedText> = {
  museum_detected: {
    en: "Musée d'Orsay • Detected",
    fr: "Musée d'Orsay • Détecté",
    "zh-Hans": "奥赛博物馆 • 已识别",
  },
  museum_locating: {
    en: "Locating…",
    fr: "Localisation…",
    "zh-Hans": "正在定位…",
  },
  museum_select_prompt: {
    en: "Select your museum",
    fr: "Sélectionnez votre musée",
    "zh-Hans": "选择您所在的博物馆",
  },
  museum_confirmed_manual: {
    en: "Musée d'Orsay • Confirmed",
    fr: "Musée d'Orsay • Confirmé",
    "zh-Hans": "奥赛博物馆 • 已确认",
  },
  museum_confirm_question: {
    en: "Are you at Musée d'Orsay?",
    fr: "Êtes-vous au Musée d'Orsay ?",
    "zh-Hans": "您现在在奥赛博物馆吗？",
  },
  museum_confirm_yes: {
    en: "Yes, I'm here",
    fr: "Oui, j'y suis",
    "zh-Hans": "是的，我在这里",
  },
  museum_confirm_not_now: {
    en: "Not now",
    fr: "Pas maintenant",
    "zh-Hans": "暂不确认",
  },
  start_visit_label: { en: "Start visit", fr: "Commencer la visite", "zh-Hans": "开始参观" },
  visit_active_label: { en: "Visit active", fr: "Visite en cours", "zh-Hans": "参观进行中" },
  tap_to_begin: { en: "Tap to begin", fr: "Touchez pour commencer", "zh-Hans": "点击开始" },
  frame_artwork_fully: { en: "Frame artwork fully", fr: "Cadrez l'œuvre en entier", "zh-Hans": "请将整件作品置于画面中" },
  hold_steady: { en: "Hold steady • Auto-capture on", fr: "Restez immobile • Capture automatique activée", "zh-Hans": "保持稳定 • 自动拍摄已开启" },
  add_to_my_visit: { en: "Add to my visit", fr: "Ajouter à ma visite", "zh-Hans": "加入我的参观" },
  added_check: { en: "Added ✓", fr: "Ajouté ✓", "zh-Hans": "已加入 ✓" },
  scan_next_artwork: { en: "Scan next artwork", fr: "Scanner l'œuvre suivante", "zh-Hans": "扫描下一件作品" },
  progress_label: { en: "Progress", fr: "Progression", "zh-Hans": "进度" },
  view_visit_progress: { en: "View visit progress", fr: "Voir la progression de la visite", "zh-Hans": "查看参观进度" },
  listen_label: { en: "Listen", fr: "Écouter", "zh-Hans": "收听" },
  listen_playing_label: { en: "Playing", fr: "Lecture en cours", "zh-Hans": "播放中" },
  live_progress: { en: "Live Progress", fr: "Progression en direct", "zh-Hans": "实时进度" },
  missions_label: { en: "Missions", fr: "Missions", "zh-Hans": "任务" },
  stat_value_seen: { en: "Value seen", fr: "Valeur découverte", "zh-Hans": "已发现价值" },
  stat_works: { en: "Works", fr: "Œuvres", "zh-Hans": "作品数" },
  stat_time: { en: "Time", fr: "Durée", "zh-Hans": "用时" },
  stat_museum: { en: "Museum", fr: "Musée", "zh-Hans": "馆内进度" },
  deep_focus: { en: "Deep focus", fr: "Attention profonde", "zh-Hans": "深度专注" },
  next_label: { en: "Next", fr: "Suivant", "zh-Hans": "下一步" },
  share_your_visit: { en: "Share your visit ↗", fr: "Partagez votre visite ↗", "zh-Hans": "分享我的参观 ↗" },
  save_image: { en: "Save image", fr: "Enregistrer l'image", "zh-Hans": "保存图片" },
  billion_euro_visitor: { en: "BILLION EURO VISITOR", fr: "VISITEUR MILLIARDAIRE", "zh-Hans": "十亿欧元访客" },
  most_valuable: { en: "Most valuable", fr: "La plus estimée", "zh-Hans": "最高估值" },
  mode_normal: { en: "Normal", fr: "Normal", "zh-Hans": "普通" },
  mode_simple: { en: "Simple", fr: "Simple", "zh-Hans": "简易" },
  mode_kids: { en: "Kids", fr: "Enfants", "zh-Hans": "儿童" },
  estimate_disclaimer: {
    en: "This museum work is not for sale. The range is an editorial estimate based on comparable public sales, artist, period, subject, size, provenance and museum significance. It is not an appraisal or insurance value.",
    fr: "Cette œuvre du musée n'est pas à vendre. La fourchette est une estimation éditoriale fondée sur des ventes publiques comparables, l'artiste, la période, le sujet, la taille, la provenance et l'importance muséale. Ce n'est pas une expertise ni une valeur d'assurance.",
    "zh-Hans": "这件博物馆藏品并非用于出售。该价格区间是根据可比公开拍卖记录、艺术家、年代、主题、尺寸、来源及博物馆重要性得出的编辑性估值，并非专业鉴定或保险价值。",
  },
  we_could_not_identify: {
    en: "We could not identify this artwork",
    fr: "Nous n'avons pas pu identifier cette œuvre",
    "zh-Hans": "未能识别这件作品",
  },
  scanning: { en: "Analyzing…", fr: "Analyse en cours…", "zh-Hans": "识别中…" },
  pending_review: { en: "Pending review", fr: "En cours de révision", "zh-Hans": "待审核" },
  keep_exploring: { en: "Keep exploring the museum →", fr: "Continuez à explorer le musée →", "zh-Hans": "继续探索博物馆 →" },
  complete_visit: { en: "Finish", fr: "Terminer", "zh-Hans": "结束" },
  complete_visit_button: { en: "Complete visit", fr: "Terminer la visite", "zh-Hans": "结束参观" },
  most_valuable_today: { en: "Most valuable seen today", fr: "La plus estimée aujourd'hui", "zh-Hans": "今日最高估值" },
  featured_today: { en: "Featured today", fr: "À l'honneur aujourd'hui", "zh-Hans": "今日特写" },
  estimate_pending: { en: "Estimate pending review", fr: "Estimation en cours de révision", "zh-Hans": "估值待审核" },
  stat_artists: { en: "Artists", fr: "Artistes", "zh-Hans": "艺术家" },
  works_seen_count: { en: "Works", fr: "Œuvres", "zh-Hans": "作品" },
  new_visit: { en: "Start a new visit", fr: "Commencer une nouvelle visite", "zh-Hans": "开始新的参观" },
  my_visit_title: { en: "My Musée d'Orsay Visit", fr: "Ma visite du Musée d'Orsay", "zh-Hans": "我的奥赛博物馆之旅" },
  // {n}/{total} placeholders, replaced by string substitution at the call
  // site — shown only when SOME but not all scanned works have a reviewed
  // estimate, so the value total doesn't silently read as "everything you
  // scanned" when it's actually a partial sum (see RecapScreen.tsx).
  value_seen_partial_note: {
    en: "{n} of {total} works reviewed",
    fr: "{n} sur {total} œuvres évaluées",
    "zh-Hans": "已评估 {n}/{total} 件作品",
  },
  generating_image: { en: "Preparing image…", fr: "Préparation de l'image…", "zh-Hans": "正在生成图片…" },

  // Design-direction-v3 "The Curated Reveal", ProvenanceReveal component.
  market_context_label: { en: "Market context", fr: "Contexte de marché", "zh-Hans": "市场背景" },
  // Exact fr/zh wording from design-direction-v3.md §9's own multilingual
  // example -- used verbatim rather than re-translated.
  estimated_market_range: {
    en: "Estimated market range",
    fr: "Fourchette de valeur estimative",
    "zh-Hans": "估算市场价值区间",
  },
  view_methodology: { en: "View methodology", fr: "Voir la méthodologie", "zh-Hans": "查看估值方法" },
  // {n} placeholder. Only ever rendered when comparableSales.length > 0 --
  // never shown as "0 comparable sales" (see ProvenanceReveal.tsx). Two
  // separate keys (not one templated string) because en/fr both inflect
  // for a count of exactly 1 ("1 comparable sale", not "1 comparable
  // sales") -- zh-Hans doesn't inflect, so its two values are identical on
  // purpose, not an oversight.
  comparable_sales_count_one: {
    en: "{n} comparable sale",
    fr: "{n} vente comparable",
    "zh-Hans": "{n} 项可比拍卖记录",
  },
  comparable_sales_count_other: {
    en: "{n} comparable sales",
    fr: "{n} ventes comparables",
    "zh-Hans": "{n} 项可比拍卖记录",
  },
  exceptional_market_tier: { en: "Exceptional market tier", fr: "Niveau de marché exceptionnel", "zh-Hans": "顶级市场水平" },
  methodology_sheet_title: { en: "How estimates work", fr: "Comment les estimations sont calculées", "zh-Hans": "估值是如何计算的" },
  // General, artwork-agnostic explanation of the process -- deliberately
  // does NOT repeat any specific work's comparable-sales text or AI-drafted
  // `estimate.logic` field verbatim (both are internal editorial-review
  // metadata per lib/types.ts, not user-facing copy). This sheet describes
  // the METHOD, the always-visible disclaimer (estimate_disclaimer) already
  // carries the per-artwork legal/factual disclosure.
  methodology_sheet_body: {
    en: "Each range is an editorial estimate, drafted by comparing this work to real public auction results for comparable artists, periods, subjects, sizes and provenance, then reviewed for museum significance. It reflects public market data, not a private valuation of this specific museum-held work — which is not for sale and has no formal appraisal.",
    fr: "Chaque fourchette est une estimation éditoriale, établie en comparant cette œuvre à des résultats de ventes aux enchères publiques pour des artistes, périodes, sujets, tailles et provenances comparables, puis réexaminée au regard de son importance muséale. Elle reflète des données de marché public, non une expertise privée de cette œuvre précise conservée au musée — laquelle n'est pas à vendre et n'a fait l'objet d'aucune expertise formelle.",
    "zh-Hans": "每个估值区间都是编辑性估算，通过将该作品与可比艺术家、年代、主题、尺寸及来源的真实公开拍卖结果进行比较后得出，并结合其博物馆重要性进行复核。该区间反映的是公开市场数据，而非对这件博物馆藏品本身的私人估价——该作品并非用于出售，也未经过正式鉴定。",
  },
  reveal_pending_review_note: {
    en: "This work hasn't been reviewed for a market estimate yet.",
    fr: "Cette œuvre n'a pas encore fait l'objet d'une estimation de marché.",
    "zh-Hans": "这件作品尚未进行市场估值评审。",
  },
};

export function tt(key: string, locale: Locale): string {
  const fresh = NEW_STRINGS[key];
  if (fresh) return fresh[locale] || fresh.en;
  return portedT(key as keyof typeof STRINGS, locale);
}

export const LOCALES: { code: Locale; label: string }[] = [
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
  { code: "zh-Hans", label: "简体中文" },
];
