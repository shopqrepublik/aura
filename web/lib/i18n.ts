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
  start_visit_label: { en: "Start visit", fr: "Commencer la visite", "zh-Hans": "开始参观" },
  visit_active_label: { en: "Visit active", fr: "Visite en cours", "zh-Hans": "参观进行中" },
  tap_to_begin: { en: "Tap to begin", fr: "Touchez pour commencer", "zh-Hans": "点击开始" },
  frame_artwork_fully: { en: "Frame artwork fully", fr: "Cadrez l'œuvre en entier", "zh-Hans": "请将整件作品置于画面中" },
  hold_steady: { en: "Hold steady • Auto-capture on", fr: "Restez immobile • Capture automatique activée", "zh-Hans": "保持稳定 • 自动拍摄已开启" },
  add_to_my_visit: { en: "Add to my visit", fr: "Ajouter à ma visite", "zh-Hans": "加入我的参观" },
  added_check: { en: "Added ✓", fr: "Ajouté ✓", "zh-Hans": "已加入 ✓" },
  listen_label: { en: "Listen", fr: "Écouter", "zh-Hans": "收听" },
  listen_playing_label: { en: "Playing", fr: "Lecture en cours", "zh-Hans": "播放中" },
  live_progress: { en: "Live Progress", fr: "Progression en direct", "zh-Hans": "实时进度" },
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
  most_valuable_today: { en: "Most valuable seen today", fr: "La plus estimée aujourd'hui", "zh-Hans": "今日最高估值" },
  featured_today: { en: "Featured today", fr: "À l'honneur aujourd'hui", "zh-Hans": "今日特写" },
  estimate_pending: { en: "Estimate pending review", fr: "Estimation en cours de révision", "zh-Hans": "估值待审核" },
  stat_artists: { en: "Artists", fr: "Artistes", "zh-Hans": "艺术家" },
  works_seen_count: { en: "Works", fr: "Œuvres", "zh-Hans": "作品" },
  new_visit: { en: "Start a new visit", fr: "Commencer une nouvelle visite", "zh-Hans": "开始新的参观" },
  my_visit_title: { en: "My Musée d'Orsay Visit", fr: "Ma visite du Musée d'Orsay", "zh-Hans": "我的奥赛博物馆之旅" },
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
