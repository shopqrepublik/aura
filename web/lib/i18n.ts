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
  // {museum} interpolated with the real detected/confirmed Museum row's
  // name (Phase 2 §1) -- was hardcoded to "Musée d'Orsay" before the
  // geofence logic was generalized to any museum in the database.
  museum_detected: {
    en: "{museum} • Detected",
    fr: "{museum} • Détecté",
    "zh-Hans": "{museum} • 已识别",
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
    en: "{museum} • Confirmed",
    fr: "{museum} • Confirmé",
    "zh-Hans": "{museum} • 已确认",
  },
  museum_confirm_question: {
    en: "Are you at {museum}?",
    fr: "Êtes-vous au {museum} ?",
    "zh-Hans": "您现在在{museum}吗？",
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
  // Home redesign (§7 "Begin your visit" ticket action) -- replaces the old
  // circular "Start visit" / "Tap to begin" pairing (visit_active_label /
  // tap_to_begin are no longer read anywhere; the returning-user "Continue
  // visit" state below covers what visit_active_label used to communicate).
  start_visit_label: { en: "Begin your visit", fr: "Commencez votre visite", "zh-Hans": "开始您的参观" },
  home_hero_title: {
    en: "A different way to see the museum.",
    fr: "Une autre façon de voir le musée.",
    "zh-Hans": "用一种新的方式看懂博物馆",
  },
  home_hero_subtitle: {
    en: "Scan the works around you to discover what they are, why they matter and what they could be worth.",
    fr: "Scannez les œuvres autour de vous pour découvrir leur histoire, leur importance et leur valeur estimée.",
    "zh-Hans": "扫描眼前的艺术品，了解它是什么、为何重要，以及它可能具有的市场价值。",
  },
  home_todays_visit_label: { en: "Today's visit", fr: "Visite du jour", "zh-Hans": "今日参观" },
  home_museum_time: {
    en: "{city} · Estimated time 60–90 min",
    fr: "{city} · Durée estimée 60–90 min",
    "zh-Hans": "{city} · 预计用时 60–90 分钟",
  },
  home_todays_missions_label: { en: "Today's missions", fr: "Missions du jour", "zh-Hans": "今日任务" },
  home_missions_subtitle: {
    en: "Three discoveries selected for your visit.",
    fr: "Trois découvertes sélectionnées pour votre visite.",
    "zh-Hans": "为您的参观精选的三项发现。",
  },
  mission_eyebrow_m1: { en: "Follow the brushwork", fr: "Suivez la touche", "zh-Hans": "追寻笔触" },
  mission_eyebrow_m2: { en: "Meet the artist", fr: "Rencontrez l'artiste", "zh-Hans": "遇见艺术家" },
  mission_eyebrow_m3: { en: "Discover the masterpiece", fr: "Découvrez le chef-d'œuvre", "zh-Hans": "发现镇馆之作" },
  // Returning-user "Continue visit" state (§17) -- shown instead of the
  // first-use hero when state.visitStarted is already true (the user backed
  // out to Home mid-visit via Camera's back action). Reuses state.seen /
  // getArtwork, no separate storage.
  welcome_back_label: { en: "Welcome back", fr: "Bon retour", "zh-Hans": "欢迎回来" },
  continue_visit_heading: {
    en: "Continue your {museum} visit",
    fr: "Continuez votre visite de {museum}",
    "zh-Hans": "继续您的{museum}参观",
  },
  continue_visit_stat: {
    en: "{n} {works} · {value} seen",
    fr: "{n} {works} vues · {value}",
    "zh-Hans": "已看 {n} 件{works} · {value}",
  },
  continue_visit_button: { en: "Continue visit", fr: "Continuer la visite", "zh-Hans": "继续参观" },
  museum_available_now: { en: "Available now", fr: "Disponible maintenant", "zh-Hans": "现已开放" },
  museum_coming_soon: { en: "Coming soon", fr: "Bientôt disponible", "zh-Hans": "即将开放" },
  select_museum_sheet_title: { en: "Select museum", fr: "Choisir un musée", "zh-Hans": "选择博物馆" },
  museum_search_placeholder: { en: "Search museum or city", fr: "Rechercher un musée ou une ville", "zh-Hans": "搜索博物馆或城市" },
  museum_featured_label: { en: "Featured guides", fr: "Guides sélectionnés", "zh-Hans": "精选导览" },
  museum_results_label: { en: "Museum directory", fr: "Répertoire des musées", "zh-Hans": "博物馆目录" },
  museum_curated_label: { en: "Curated guide", fr: "Guide éditorial", "zh-Hans": "精选导览" },
  museum_ai_guide_label: { en: "AI Guide available", fr: "Guide IA disponible", "zh-Hans": "AI 导览可用" },
  museum_no_results: { en: "No museums found", fr: "Aucun musée trouvé", "zh-Hans": "未找到博物馆" },
  home_museum_context: {
    en: "{city} · {experience}",
    fr: "{city} · {experience}",
    "zh-Hans": "{city} · {experience}",
  },

  // Replaces an earlier, inaccurate "Private · No personal data stored"
  // framing: once §13 analytics (PostHog, anonymized events, no
  // autocapture/session recording -- see lib/analytics.ts) ship, "no data"
  // is no longer literally true, so this says what actually happens instead
  // of a blanket claim that would be false the moment the app sends its
  // first event.
  //
  // "(processed in the US)" added 2026-08 -- live network traffic confirmed
  // events go to us.i.posthog.com, not the eu.i.posthog.com the analytics.ts
  // default implies. Product decision (resolved, reviewed with the user):
  // consciously stay on US Cloud rather than migrate for the Paris museum
  // launch (PostHog can't move an existing project's region in place --
  // would need a new EU project and losing all historical events, or a
  // support-assisted migration) -- but the footer must say where data
  // actually goes, not where the code comments originally assumed.
  privacy_footer_note: {
    en: "Anonymized visit analytics (processed in the US) · No data sold or shared",
    fr: "Statistiques de visite anonymisées (traitées aux États-Unis) · Aucune donnée vendue ou partagée",
    "zh-Hans": "匿名参观统计（数据在美国处理）· 不出售或共享任何数据",
  },

  // Desktop shell -- header nav labels and the phone-handoff row.
  // "How it works" / "Experience" now scroll to the real Journey section
  // (DesktopHeader.tsx); "Your visits" stays inert with a "coming soon"
  // tooltip -- there's no real visit-history view on desktop yet, and an
  // honest disabled label beats a dead link.
  desktop_nav_how_it_works: { en: "How it works", fr: "Comment ça marche", "zh-Hans": "使用方法" },
  desktop_nav_experience: { en: "Experience", fr: "L'expérience", "zh-Hans": "体验" },
  desktop_nav_your_visits: { en: "Your visits", fr: "Vos visites", "zh-Hans": "我的参观" },
  desktop_coming_soon: { en: "Coming soon", fr: "Bientôt disponible", "zh-Hans": "即将推出" },
  desktop_install_elyio: { en: "Install ELYIO", fr: "Installer ELYIO", "zh-Hans": "安装 ELYIO" },
  desktop_open_on_phone: { en: "Open on your phone", fr: "Ouvrir sur votre téléphone", "zh-Hans": "在手机上打开" },
  desktop_scan_to_continue: { en: "Scan to continue", fr: "Scannez pour continuer", "zh-Hans": "扫码继续" },
  desktop_available_platforms: { en: "Available on iOS & Android", fr: "Disponible sur iOS et Android", "zh-Hans": "支持 iOS 和安卓" },
  // Shown instead of the real install prompt when the browser doesn't
  // support beforeinstallprompt (Safari, Firefox) or has already fired
  // it once this session -- an honest fallback, not a fake button.
  desktop_install_hint_title: { en: "Install ELYIO", fr: "Installer ELYIO", "zh-Hans": "安装 ELYIO" },
  desktop_install_hint_body: {
    en: "Look for the install icon in your address bar (Chrome, Edge). Safari and Firefox on desktop don't support this yet — open elyio.co on your phone instead.",
    fr: "Repérez l'icône d'installation dans votre barre d'adresse (Chrome, Edge). Safari et Firefox sur ordinateur ne le prennent pas encore en charge — ouvrez plutôt elyio.co sur votre téléphone.",
    "zh-Hans": "请在地址栏中查找安装图标（Chrome、Edge）。桌面版 Safari 和 Firefox 暂不支持此功能——请改为在手机上打开 elyio.co。",
  },

  // Desktop Journey section (hero-refinement round 3) -- reuses the exact
  // three-chapter structure/copy already established in the desktop spec
  // (§30 of the original brief): Scan / Understand / Reveal.
  desktop_journey_eyebrow: { en: "From looking to understanding", fr: "Du regard à la compréhension", "zh-Hans": "从观看到理解" },
  desktop_journey_scan_title: { en: "Scan", fr: "Scanner", "zh-Hans": "扫描" },
  desktop_journey_scan_body: {
    en: "Point your phone at a work of art. ELYIO identifies it in seconds.",
    fr: "Pointez votre téléphone vers une œuvre. ELYIO l'identifie en quelques secondes.",
    "zh-Hans": "用手机对准一件艺术品，ELYIO 几秒内即可识别。",
  },
  desktop_journey_understand_title: { en: "Understand", fr: "Comprendre", "zh-Hans": "理解" },
  desktop_journey_understand_body: {
    en: "Learn the story, the artist and the historical context behind the work.",
    fr: "Découvrez l'histoire, l'artiste et le contexte historique de l'œuvre.",
    "zh-Hans": "了解作品背后的故事、艺术家与历史背景。",
  },
  desktop_journey_reveal_title: { en: "Reveal", fr: "Révéler", "zh-Hans": "揭示" },
  desktop_journey_reveal_body: {
    en: "Discover researched market context based on comparable public sales.",
    fr: "Découvrez un contexte de marché documenté, basé sur des ventes publiques comparables.",
    "zh-Hans": "基于可比公开拍卖记录，了解经过研究的市场行情。",
  },

  // Desktop Recap strip -- deliberately reuses real demo catalog data
  // (see components/desktop/RecapStrip.tsx) instead of the reference
  // mockup's literal "€3.8B" -- this project has never shown an invented
  // number anywhere else (RecapScreen.tsx, ProvenanceReveal, etc. all
  // compute real sums or show "pending review"), so the desktop marketing
  // strip doesn't get an exception.
  desktop_recap_eyebrow: { en: "Your visit recap", fr: "Le récapitulatif de votre visite", "zh-Hans": "参观回顾" },
  desktop_recap_you_saw: { en: "You saw", fr: "Vous avez vu", "zh-Hans": "您已欣赏" },
  desktop_recap_of_art: { en: "of art.", fr: "d'œuvres d'art.", "zh-Hans": "的艺术品。" },
  desktop_recap_sub: {
    en: "Every visit becomes a record of what you discovered.",
    fr: "Chaque visite devient la trace de ce que vous avez découvert.",
    "zh-Hans": "每一次参观，都会成为您发现的记录。",
  },
  desktop_recap_view: { en: "View your recap", fr: "Voir votre récapitulatif", "zh-Hans": "查看您的回顾" },

  // Real registration (email magic link + Google; Apple deferred), shown
  // on Home before "Begin your visit" is reachable at all -- free for
  // everyone, no paywall, just a real identity behind the visit.
  auth_modal_title: { en: "Sign in to begin", fr: "Connectez-vous pour commencer", "zh-Hans": "登录后开始" },
  auth_modal_subtitle: {
    en: "Free, always. We just need to know it's you.",
    fr: "Gratuit, toujours. Nous avons juste besoin de savoir que c'est vous.",
    "zh-Hans": "永久免费。我们只需要确认是您本人。",
  },
  auth_email_label: { en: "Email", fr: "E-mail", "zh-Hans": "电子邮箱" },
  auth_send_link: { en: "Send magic link", fr: "Envoyer le lien magique", "zh-Hans": "发送登录链接" },
  auth_or_divider: { en: "or", fr: "ou", "zh-Hans": "或" },
  auth_continue_google: { en: "Continue with Google", fr: "Continuer avec Google", "zh-Hans": "使用 Google 继续" },
  auth_check_email_title: { en: "Check your email", fr: "Vérifiez vos e-mails", "zh-Hans": "请查收邮件" },
  auth_check_email_body: {
    en: "We sent a sign-in link to {email}.",
    fr: "Nous avons envoyé un lien de connexion à {email}.",
    "zh-Hans": "登录链接已发送至 {email}。",
  },
  auth_error_generic: {
    en: "Something went wrong. Please try again.",
    fr: "Une erreur est survenue. Veuillez réessayer.",
    "zh-Hans": "出了点问题，请重试。",
  },
  auth_close: { en: "Not now", fr: "Pas maintenant", "zh-Hans": "暂不登录" },
  frame_artwork_fully: { en: "Frame artwork fully", fr: "Cadrez l'œuvre en entier", "zh-Hans": "请将整件作品置于画面中" },
  hold_steady: { en: "Hold steady • Auto-capture on", fr: "Restez immobile • Capture automatique activée", "zh-Hans": "保持稳定 • 自动拍摄已开启" },
  pwa_install_title: { en: "Install ELYIO", fr: "Installer ELYIO", "zh-Hans": "安装 ELYIO" },
  pwa_install_body: {
    en: "Add ELYIO to your phone for a faster, app-like museum visit.",
    fr: "Ajoutez ELYIO à votre téléphone pour une visite du musée plus rapide, comme dans une application.",
    "zh-Hans": "将 ELYIO 添加到手机，获得更流畅的应用式参观体验。",
  },
  pwa_install_action: { en: "Install", fr: "Installer", "zh-Hans": "安装" },
  pwa_ios_install_title: {
    en: "Add ELYIO to your Home Screen",
    fr: "Ajoutez ELYIO à l'écran d'accueil",
    "zh-Hans": "将 ELYIO 添加到主屏幕",
  },
  pwa_ios_install_body: {
    en: "In Safari, tap Share, then Add to Home Screen.",
    fr: "Dans Safari, touchez Partager, puis Ajouter à l'écran d'accueil.",
    "zh-Hans": "在 Safari 中点击“共享”，然后选择“添加到主屏幕”。",
  },
  pwa_install_dismiss: { en: "Dismiss install instructions", fr: "Fermer les instructions d'installation", "zh-Hans": "关闭安装提示" },
  add_to_my_visit: { en: "Add to my visit", fr: "Ajouter à ma visite", "zh-Hans": "加入我的参观" },
  added_check: { en: "Added ✓", fr: "Ajouté ✓", "zh-Hans": "已加入 ✓" },
  scan_next_artwork: { en: "Scan next artwork", fr: "Scanner l'œuvre suivante", "zh-Hans": "扫描下一件作品" },
  progress_label: { en: "Progress", fr: "Progression", "zh-Hans": "进度" },
  view_visit_progress: { en: "View visit progress", fr: "Voir la progression de la visite", "zh-Hans": "查看参观进度" },
  why_it_matters_label: { en: "Why it matters", fr: "Pourquoi c'est important", "zh-Hans": "为什么重要" },
  look_closer_label: { en: "Look closer", fr: "Regardez de plus près", "zh-Hans": "仔细看" },
  view_deeper_context: { en: "View deeper context", fr: "Voir le contexte", "zh-Hans": "查看更多背景" },
  listen_label: { en: "Listen", fr: "Écouter", "zh-Hans": "收听" },
  listen_playing_label: { en: "Playing", fr: "Lecture en cours", "zh-Hans": "播放中" },
  live_progress: { en: "Live Progress", fr: "Progression en direct", "zh-Hans": "实时进度" },
  missions_label: { en: "Missions", fr: "Missions", "zh-Hans": "任务" },
  stat_value_seen: { en: "Value seen", fr: "Valeur découverte", "zh-Hans": "已发现价值" },
  value_context_work_one: { en: "1 context work", fr: "1 œuvre avec contexte", "zh-Hans": "1件有价值背景的作品" },
  value_context_work_other: { en: "{n} context works", fr: "{n} œuvres avec contexte", "zh-Hans": "{n}件有价值背景的作品" },
  market_context_seen: { en: "financial context, not estimated value", fr: "contexte financier, pas valeur estimée", "zh-Hans": "金融背景，不是估值" },
  beyond_market_icons_seen: { en: "beyond-market icons", fr: "icônes hors marché", "zh-Hans": "超出市场的名作" },
  context_and_beyond_market_seen: { en: "context and beyond-market works", fr: "œuvres avec contexte et hors marché", "zh-Hans": "价值背景与超出市场的作品" },
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
  recognition_network_error: {
    en: "Connection lost. Recognition needs the internet.",
    fr: "Connexion perdue. La reconnaissance nécessite Internet.",
    "zh-Hans": "网络连接已断开。识别需要联网。",
  },
  retry_recognition: { en: "Retry recognition", fr: "Réessayer la reconnaissance", "zh-Hans": "重新识别" },
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
  estimated_value_label: { en: "Estimated value", fr: "Valeur estimée", "zh-Hans": "估算价值" },
  market_context_label: { en: "Market context", fr: "Contexte de marché", "zh-Hans": "市场背景" },
  beyond_market_label: { en: "Beyond the market", fr: "Au-delà du marché", "zh-Hans": "超出市场价格" },
  not_artwork_value_label: { en: "Not this artwork's estimated value", fr: "Pas l'estimation de cette œuvre", "zh-Hans": "不是这件作品的估值" },
  view_value_context: { en: "View context", fr: "Voir le contexte", "zh-Hans": "查看背景" },
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
  market_context_disclaimer: {
    en: "This is financial context around the work, not an appraisal, insurance value, or sale estimate for this museum object.",
    fr: "Il s'agit d'un contexte financier autour de l'œuvre, non d'une expertise, d'une valeur d'assurance ou d'une estimation de vente de cet objet de musée.",
    "zh-Hans": "这是围绕作品的金融背景，不是对这件博物馆藏品的鉴定、保险价值或出售估价。",
  },
  beyond_market_disclaimer: {
    en: "This work is outside ordinary private-market valuation and is not represented by a sale estimate.",
    fr: "Cette œuvre échappe à l'évaluation ordinaire du marché privé et n'est pas représentée par une estimation de vente.",
    "zh-Hans": "这件作品不适合用普通私人市场估值来表示，也不以出售估价呈现。",
  },
  mixed_value_recap_subtitle: {
    en: "{n} of {total} works included in estimated value, plus {context} context/icon works",
    fr: "{n} sur {total} œuvres incluses dans la valeur estimée, plus {context} œuvres de contexte ou hors marché",
    "zh-Hans": "{total}件中有{n}件计入估值，另有{context}件为背景或超出市场作品",
  },
  reveal_pending_review_note: {
    en: "This work hasn't been reviewed for a market estimate yet.",
    fr: "Cette œuvre n'a pas encore fait l'objet d'une estimation de marché.",
    "zh-Hans": "这件作品尚未进行市场估值评审。",
  },

  // Recap "Acquisition Poster" headline (design-direction-v3.md §10).
  you_saw_label: { en: "You saw", fr: "Vous avez vu", "zh-Hans": "您看到了" },
  // Singular forms for the "{n} works · {n} artists · {time}" stat line --
  // works_seen_count/stat_artists above are the plural/label forms used
  // everywhere else; without these, a 1-work visit read "1 works · 1
  // artists" (zh-Hans doesn't inflect, so its value is identical on
  // purpose, same convention as scaleComparison.ts's pickLabel).
  stat_work_one: { en: "work", fr: "œuvre", "zh-Hans": "作品" },
  stat_artist_one: { en: "artist", fr: "artiste", "zh-Hans": "艺术家" },
  in_estimated_market_value: {
    en: "in estimated art market value",
    fr: "en valeur marchande estimée",
    "zh-Hans": "的估算艺术市场价值",
  },
  // Shown instead of the caption above when NONE of the seen works have a
  // reviewed estimate -- same honesty rule as everywhere else this data
  // appears: never caption a "Pending review" headline as if it were a real
  // market-value claim.
  recap_value_pending_caption: {
    en: "None of the works you saw have a reviewed market estimate yet.",
    fr: "Aucune des œuvres vues n'a encore d'estimation de marché.",
    "zh-Hans": "您看到的作品均尚未进行市场估值评审。",
  },
  // Native share-sheet text (RecapScreen.tsx handleShare) -- was a raw
  // hardcoded English template literal that never called tt() at all
  // ("1 works • 1 artists • 1m at {museum} — ELYIO"), a separate bug
  // from the Progress-screen plural fix, not fixed by it. {count}/{works}/{museum}
  // are filled in from the SAME worksLabel the on-screen stats row already
  // computes (singular/plural via stat_work_one/works_seen_count above),
  // not reimplemented here. Two variants because the value clause's
  // grammar differs when there's nothing to report yet: with a value, "{n}
  // works, €X–YM in estimated value"; pending, "{n} works, Pending review"
  // -- swapping only {value} into the with-value template would have
  // produced "Pending review in estimated value", which reads as a false
  // market claim on data that doesn't exist.
  share_visit_with_value: {
    en: "You saw {count} {works}, {value} in estimated value — {museum} — ELYIO",
    fr: "Vous avez vu {count} {works}, {value} de valeur estimée — {museum} — ELYIO",
    "zh-Hans": "您看到了{count}件{works}，估值 {value} — {museum} — ELYIO",
  },
  share_visit_pending: {
    en: "You saw {count} {works}, {value} — {museum} — ELYIO",
    fr: "Vous avez vu {count} {works}, {value} — {museum} — ELYIO",
    "zh-Hans": "您看到了{count}件{works}，{value} — {museum} — ELYIO",
  },

  // Reduced result state for a recognized artwork/object without a full
  // editorial catalog match.
  uncataloged_note: {
    en: "Start with what is visible: the subject, materials, and strongest details in front of you.",
    fr: "Commencez par ce qui est visible : le sujet, les matières et les détails les plus forts.",
    "zh-Hans": "先从眼前可见的内容开始：题材、材料和最突出的细节。",
  },
  uncataloged_value_note: {
    en: "No verified market context is shown for this work.",
    fr: "Aucun contexte de marché vérifié n'est affiché pour cette œuvre.",
    "zh-Hans": "此作品暂无经过核验的市场背景。",
  },
  uncataloged_unknown_artist: { en: "Unknown artist", fr: "Artiste inconnu", "zh-Hans": "未知艺术家" },
  uncataloged_unknown_title: { en: "Unidentified work", fr: "Œuvre non identifiée", "zh-Hans": "未识别的作品" },
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

/**
 * Runtime message-bundle boundary. Institution locale configuration is not
 * restricted to these values, but the visitor UI must fall back to a bundle
 * that is actually shipped instead of claiming an untranslated locale works.
 */
export function resolveUiLocale(locale: string | null | undefined): Locale {
  if (locale === "fr") return "fr";
  if (locale?.toLowerCase() === "zh-hans") return "zh-Hans";
  return "en";
}
