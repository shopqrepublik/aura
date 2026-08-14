"use client";

import type { Locale, Mode, ValueReveal } from "./types";

export type GeneratedValueStatus = "ARTIST_MARKET_CONTEXT" | "NO_TRUSTED_CONTEXT";

export interface GeneratedModeContent {
  hook: string;
  whyItMatters: string;
  lookCloser: string;
  deeperContext: string;
  funFactOrMission?: string;
}

export interface ArtistMarketContext {
  canonicalArtist: string;
  aliases: string[];
  amountMillions?: number;
  currency?: "USD_MILLION" | "EUR_MILLION" | "GBP_MILLION";
  workTitle?: string;
  eventLabel?: string;
  year?: string;
  sourceReference?: string;
  confidence: "HIGH" | "MEDIUM" | "NONE";
}

export interface GeneratedEnrichment {
  version: string;
  displayArtist: string | null;
  displayTitle: string;
  displayDate: string | null;
  objectType: string | null;
  movementOrPeriod: string | null;
  content: Record<Locale, Record<Mode, GeneratedModeContent>>;
  valueContextStatus: GeneratedValueStatus;
  artistMarketContext: ArtistMarketContext | null;
  confidence: number;
  factualBasis: string[];
  generatedAt: string;
}

export interface GeneratedEnrichmentInput {
  artist: string | null;
  title: string | null;
  date?: string | null;
  objectType?: string | null;
  vision?: Record<string, unknown> | null;
  confidence?: number | null;
}

const VERSION = "generated-artwork-enrichment-v2";
const CACHE_PREFIX = "elyio.generatedArtworkEnrichment.v2:";

const FORBIDDEN_VISITOR_TERMS = [
  "elyio has not reviewed",
  "catalog record",
  "recognition is strong enough",
  "database",
  "layer 1",
  "layer 2",
  "ai-generated",
  "scoped candidate",
  "recognitionasset",
  "embedding",
  "source_ids",
];

const ARTIST_MARKET_CONTEXTS: ArtistMarketContext[] = [
  {
    canonicalArtist: "Leonardo da Vinci",
    aliases: ["leonardo da vinci", "leonard de vinci", "léonard de vinci"],
    amountMillions: 450.3,
    currency: "USD_MILLION",
    workTitle: "Salvator Mundi",
    eventLabel: "Christie's auction record",
    year: "2017",
    sourceReference: "Christie's, Salvator Mundi sale, 2017",
    confidence: "HIGH",
  },
  {
    canonicalArtist: "Vincent van Gogh",
    aliases: ["vincent van gogh", "van gogh"],
    amountMillions: 117.2,
    currency: "USD_MILLION",
    workTitle: "Orchard with Cypresses",
    eventLabel: "Christie's auction record",
    year: "2022",
    sourceReference: "Christie's New York, Paul G. Allen Collection, 2022",
    confidence: "HIGH",
  },
  {
    canonicalArtist: "Titian",
    aliases: ["titian", "tiziano", "titien"],
    amountMillions: 22.2,
    currency: "USD_MILLION",
    workTitle: "Rest on the Flight into Egypt",
    eventLabel: "Christie's artist auction record",
    year: "2024",
    sourceReference: "Christie's London Old Masters sale, 2024",
    confidence: "MEDIUM",
  },
  {
    canonicalArtist: "Claude Monet",
    aliases: ["claude monet", "monet"],
    amountMillions: 110.7,
    currency: "USD_MILLION",
    workTitle: "Meules",
    eventLabel: "Sotheby's auction record",
    year: "2019",
    sourceReference: "Sotheby's New York, Impressionist & Modern Art Evening Sale, 2019",
    confidence: "HIGH",
  },
  {
    canonicalArtist: "Pablo Picasso",
    aliases: ["pablo picasso", "picasso"],
    amountMillions: 179.4,
    currency: "USD_MILLION",
    workTitle: "Les femmes d'Alger (Version O)",
    eventLabel: "Christie's auction record",
    year: "2015",
    sourceReference: "Christie's New York, Looking Forward to the Past, 2015",
    confidence: "HIGH",
  },
  { canonicalArtist: "Antonello da Messina", aliases: ["antonello da messina", "antonello"], confidence: "NONE" },
  { canonicalArtist: "Pierre-Auguste Renoir", aliases: ["pierre-auguste renoir", "renoir"], confidence: "NONE" },
  { canonicalArtist: "Edgar Degas", aliases: ["edgar degas", "degas"], confidence: "NONE" },
  { canonicalArtist: "Paul Cezanne", aliases: ["paul cezanne", "paul cézanne", "cezanne", "cézanne"], confidence: "NONE" },
  { canonicalArtist: "Paul Gauguin", aliases: ["paul gauguin", "gauguin"], confidence: "NONE" },
  { canonicalArtist: "Edouard Manet", aliases: ["edouard manet", "édouard manet", "manet"], confidence: "NONE" },
  { canonicalArtist: "Auguste Rodin", aliases: ["auguste rodin", "rodin"], confidence: "NONE" },
];

export function getGeneratedEnrichmentCacheKey(input: GeneratedEnrichmentInput): string {
  return [
    VERSION,
    normalize(input.artist || "unknown-artist"),
    normalize(input.title || "unknown-title"),
    normalize(input.date || ""),
    normalize(input.objectType || ""),
  ].join(":");
}

export function getCachedGeneratedEnrichment(cacheKey: string): GeneratedEnrichment | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CACHE_PREFIX + cacheKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as GeneratedEnrichment;
    return parsed.version === VERSION && validateGeneratedEnrichment(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function setCachedGeneratedEnrichment(cacheKey: string, enrichment: GeneratedEnrichment): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(CACHE_PREFIX + cacheKey, JSON.stringify(enrichment));
  } catch {
    // Local cache is a speed optimization. The card still renders if storage is unavailable.
  }
}

export function buildGeneratedEnrichment(input: GeneratedEnrichmentInput): GeneratedEnrichment {
  const cacheKey = getGeneratedEnrichmentCacheKey(input);
  const cached = getCachedGeneratedEnrichment(cacheKey);
  if (cached) return cached;

  const artist = cleanDisplay(input.artist);
  const title = cleanDisplay(input.title) || "Recognized artwork";
  const objectType = cleanDisplay(input.objectType || stringField(input.vision, "object_category") || stringField(input.vision, "object_type"));
  const date = cleanDisplay(input.date || stringField(input.vision, "period_guess"));
  const subject = cleanDisplay(stringField(input.vision, "depicted_subject"));
  const visualFeatures = [
    ...stringArray(input.vision?.dominant_visual_features),
    ...stringArray(input.vision?.distinctive_features),
  ].map(cleanDisplay).filter((value): value is string => !!value);
  const context = getArtistMarketContext(artist);
  const baseKind = classifyArtwork(artist, title, objectType, subject);

  let content = buildLocalizedContent(baseKind, {
    artist,
    title,
    date,
    objectType,
    subject,
    visualFeatures,
  });

  const enrichment: GeneratedEnrichment = {
    version: VERSION,
    displayArtist: artist,
    displayTitle: title,
    displayDate: date,
    objectType,
    movementOrPeriod: inferMovementOrPeriod(artist, date),
    content,
    valueContextStatus: context && context.confidence !== "NONE" ? "ARTIST_MARKET_CONTEXT" : "NO_TRUSTED_CONTEXT",
    artistMarketContext: context && context.confidence !== "NONE" ? context : null,
    confidence: clampConfidence(input.confidence),
    factualBasis: [
      artist ? `artist:${artist}` : null,
      title ? `title:${title}` : null,
      date ? `date:${date}` : null,
      objectType ? `object_type:${objectType}` : null,
      subject ? `subject:${subject}` : null,
      ...visualFeatures.slice(0, 4).map((feature) => `visual:${feature}`),
    ].filter((x): x is string => !!x),
    generatedAt: new Date().toISOString(),
  };

  if (!validateGeneratedEnrichment(enrichment)) {
    content = buildLocalizedContent("factual_minimum", {
      artist,
      title,
      date,
      objectType,
      subject,
      visualFeatures,
    });
    enrichment.content = content;
    enrichment.valueContextStatus = "NO_TRUSTED_CONTEXT";
    enrichment.artistMarketContext = null;
  }

  setCachedGeneratedEnrichment(cacheKey, enrichment);
  return enrichment;
}

export function generatedValueReveal(enrichment: GeneratedEnrichment, locale: Locale): ValueReveal | null {
  const context = enrichment.artistMarketContext;
  if (!context || context.confidence === "NONE" || !context.amountMillions || !context.currency || !context.workTitle) {
    return null;
  }
  return {
    mode: "MARKET_CONTEXT",
    aggregateValueEligible: false,
    marketContext: {
      headlineNumber: context.amountMillions,
      currency: context.currency,
      label: marketLabel(context, locale),
      explanation: marketExplanation(context, locale),
      relationshipToArtwork: marketRelationship(locale),
      contextType: "artist auction record",
      sourceReference: context.sourceReference,
      date: context.year || null,
      confidence: context.confidence,
      disclaimer: marketDisclaimer(locale),
    },
  };
}

export function quietNoTrustedContext(locale: Locale): string {
  if (locale === "fr") return "Aucun contexte de marché vérifié n'est affiché pour cette œuvre.";
  if (locale === "zh-Hans") return "此作品暂无经过核验的市场背景。";
  return "No verified market context is shown for this work.";
}

export function validateGeneratedEnrichment(enrichment: GeneratedEnrichment): boolean {
  if (!enrichment.displayTitle.trim()) return false;
  const texts: string[] = [];
  for (const locale of Object.keys(enrichment.content) as Locale[]) {
    for (const mode of Object.keys(enrichment.content[locale]) as Mode[]) {
      const item = enrichment.content[locale][mode];
      texts.push(item.hook, item.whyItMatters, item.lookCloser, item.deeperContext, item.funFactOrMission || "");
    }
  }
  if (enrichment.artistMarketContext) {
    texts.push(enrichment.artistMarketContext.sourceReference || "", enrichment.artistMarketContext.eventLabel || "");
  }
  return !texts.some((text) => containsForbiddenVisitorTerm(text));
}

export function containsForbiddenVisitorTerm(value: string): boolean {
  const lowered = value.toLowerCase();
  return FORBIDDEN_VISITOR_TERMS.some((term) => lowered.includes(term));
}

function buildLocalizedContent(
  kind: string,
  data: {
    artist: string | null;
    title: string;
    date: string | null;
    objectType: string | null;
    subject: string | null;
    visualFeatures: string[];
  }
): Record<Locale, Record<Mode, GeneratedModeContent>> {
  const builders: Record<Locale, () => Record<Mode, GeneratedModeContent>> = {
    en: () => buildEnglishContent(kind, data),
    fr: () => buildFrenchContent(kind, data),
    "zh-Hans": () => buildChineseContent(kind, data),
  };
  return { en: builders.en(), fr: builders.fr(), "zh-Hans": builders["zh-Hans"]() };
}

function buildEnglishContent(kind: string, data: Parameters<typeof buildLocalizedContent>[1]): Record<Mode, GeneratedModeContent> {
  if (kind === "titian_mirror") {
    return {
      normal: {
        hook: "The mirror turns beauty into a small drama about looking.",
        whyItMatters: "Titian makes the act of looking part of the subject. The polished surface, the woman's hair, and the second figure turn a private toilette into a study of Venetian color, touch, and desire.",
        lookCloser: "Find the mirror first, then compare its cool reflected light with the warmer skin and hair. Notice how the second figure changes the scene from portrait into performance.",
        deeperContext: "Venetian painters were famous for making color and surface feel almost physical. Here, beauty is not just shown; it is staged, reflected, and watched.",
      },
      simple: {
        hook: "This is not just a portrait. It is a scene about looking.",
        whyItMatters: "Titian uses the mirror to make the painting feel alive. You are watching someone being seen, dressed, and admired.",
        lookCloser: "Look for the small mirror. Compare its cooler light with the warm skin and hair.",
        deeperContext: "The painting comes from Renaissance Venice, where artists loved rich color, soft skin, and shining surfaces.",
      },
      kids: {
        hook: "A mirror is the secret trick in this painting.",
        whyItMatters: "Titian wants you to notice who is looking at whom. The woman, the helper, the mirror, and you all become part of the scene.",
        lookCloser: "Mission: find the mirror, then find the brightest shine. Is it on the mirror, the hair, or the skin?",
        deeperContext: "Venice was famous for painters who made colors feel warm and glowing.",
        funFactOrMission: "Try covering the helper with your hand. Does the painting feel more like a portrait or more like a story?",
      },
    };
  }
  if (kind === "van_gogh_self_portrait") {
    return {
      normal: {
        hook: "The face holds still while the paint refuses to.",
        whyItMatters: "Van Gogh's self-portraits are not just likenesses; they are tests of color, pressure, and attention. In the 1889 portraits, the blue-green background and restless strokes make the figure feel alive and unstable.",
        lookCloser: "Compare the warm beard strokes with the cold blue background. Around the eyes, notice where the outline breaks apart into separate strokes instead of a clean contour.",
        deeperContext: "A self-portrait let Van Gogh work when models were scarce and gave him a way to turn observation into emotional intensity.",
      },
      simple: {
        hook: "The face is still, but the paint is moving everywhere.",
        whyItMatters: "Van Gogh used color and brushstrokes to show more than appearance. He makes a portrait feel full of energy.",
        lookCloser: "Look at the beard, then the blue background. The warm and cold colors push against each other.",
        deeperContext: "He painted himself many times, partly because he was always available as his own model.",
      },
      kids: {
        hook: "This portrait almost buzzes.",
        whyItMatters: "Van Gogh made paint strokes feel like tiny tracks of energy. The picture shows a person, but it also shows how strongly he painted.",
        lookCloser: "Mission: count five different directions the brushstrokes move. Do they all go the same way?",
        deeperContext: "A self-portrait is like an old selfie, but made slowly with paint.",
        funFactOrMission: "Step back, then step closer. From far away you see a face; up close you see thousands of marks.",
      },
    };
  }
  if (kind === "antonello_ecce_homo") {
    return {
      normal: {
        hook: "The title asks you to look, but the face makes that looking uncomfortable.",
        whyItMatters: "Ecce Homo images show Christ being presented to a crowd. Antonello's power is intimacy: suffering is compressed into a close, human face rather than a distant scene.",
        lookCloser: "Start with the eyes, then move to the marks of suffering. Notice how little space the figure has; the closeness makes you part of the crowd.",
        deeperContext: "Antonello helped bring a precise, northern-looking realism into Italian painting. The result can feel quiet, direct, and startlingly present.",
      },
      simple: {
        hook: "This painting brings the face very close to you.",
        whyItMatters: "Instead of showing a big scene, Antonello focuses on one suffering person. That makes the image harder to look away from.",
        lookCloser: "Look at the eyes first. Then notice how close the figure is to the front of the painting.",
        deeperContext: "The words Ecce Homo mean 'Behold the man.' The painting asks you to stop and really look.",
      },
      kids: {
        hook: "This is a close-up with a serious feeling.",
        whyItMatters: "The artist wants you to notice a face, not a big action scene. Small details carry the whole story.",
        lookCloser: "Mission: look at the eyes, then the mouth. Which one tells you more about the feeling?",
        deeperContext: "Old religious paintings often told stories through faces, hands, and tiny signs.",
        funFactOrMission: "Try stepping back. Does the face feel calmer or even more intense?",
      },
    };
  }
  return buildGenericEnglish(kind, data);
}

function buildFrenchContent(kind: string, data: Parameters<typeof buildLocalizedContent>[1]): Record<Mode, GeneratedModeContent> {
  if (kind === "titian_mirror") {
    return {
      normal: {
        hook: "Le miroir transforme la beauté en une petite scène du regard.",
        whyItMatters: "Titien fait du fait de regarder le vrai sujet du tableau. La surface polie, la chevelure et la seconde figure changent une toilette intime en étude de couleur, de toucher et de désir vénitiens.",
        lookCloser: "Repérez d'abord le miroir, puis comparez sa lumière froide avec la chaleur de la peau et des cheveux. La seconde figure fait basculer le portrait vers une scène jouée.",
        deeperContext: "À Venise, la peinture excellait à rendre la couleur presque matérielle. Ici, la beauté est montrée, réfléchie et observée.",
      },
      simple: {
        hook: "Ce n'est pas seulement un portrait. C'est une scène sur le regard.",
        whyItMatters: "Titien utilise le miroir pour rendre l'image vivante. On voit quelqu'un qui est regardé, coiffé, admiré.",
        lookCloser: "Cherchez le petit miroir. Comparez sa lumière froide avec la peau et les cheveux plus chauds.",
        deeperContext: "La peinture vénitienne aimait les couleurs riches, les peaux douces et les surfaces brillantes.",
      },
      kids: {
        hook: "Le miroir est le petit secret du tableau.",
        whyItMatters: "Titien veut que tu remarques qui regarde qui. La femme, l'aide, le miroir et toi faites partie de la scène.",
        lookCloser: "Mission : trouve le miroir, puis l'endroit le plus brillant. Est-il sur le miroir, les cheveux ou la peau ?",
        deeperContext: "Venise était célèbre pour ses peintres aux couleurs chaudes et lumineuses.",
        funFactOrMission: "Cache l'aide avec ta main. Le tableau ressemble-t-il plus à un portrait ou à une histoire ?",
      },
    };
  }
  if (kind === "van_gogh_self_portrait") {
    return {
      normal: {
        hook: "Le visage reste immobile, mais la peinture refuse de tenir en place.",
        whyItMatters: "Les autoportraits de Van Gogh ne sont pas de simples ressemblances : ce sont des expériences de couleur, de pression et d'attention. Dans ceux de 1889, le fond bleu-vert et les touches nerveuses rendent la figure instable et vivante.",
        lookCloser: "Comparez les touches chaudes de la barbe avec le bleu froid du fond. Autour des yeux, voyez où le contour se fragmente au lieu de rester une ligne nette.",
        deeperContext: "L'autoportrait permettait à Van Gogh de travailler sans modèle et de transformer l'observation en intensité émotionnelle.",
      },
      simple: {
        hook: "Le visage est calme, mais la peinture bouge partout.",
        whyItMatters: "Van Gogh utilise la couleur et les coups de pinceau pour montrer plus que l'apparence. Il donne de l'énergie au portrait.",
        lookCloser: "Regardez la barbe, puis le fond bleu. Les couleurs chaudes et froides se répondent.",
        deeperContext: "Il s'est peint souvent, car il pouvait toujours être son propre modèle.",
      },
      kids: {
        hook: "Ce portrait semble vibrer.",
        whyItMatters: "Van Gogh transforme les coups de pinceau en petites traces d'énergie. On voit une personne, mais aussi la force de sa manière de peindre.",
        lookCloser: "Mission : trouve cinq directions différentes dans les coups de pinceau. Vont-ils tous du même côté ?",
        deeperContext: "Un autoportrait, c'est un peu comme un selfie ancien, mais fait lentement avec de la peinture.",
        funFactOrMission: "Recule, puis approche-toi. De loin tu vois un visage ; de près tu vois des milliers de marques.",
      },
    };
  }
  if (kind === "antonello_ecce_homo") {
    return {
      normal: {
        hook: "Le titre demande de regarder, mais le visage rend ce regard difficile.",
        whyItMatters: "Les Ecce Homo montrent le Christ présenté à la foule. Chez Antonello, la force vient de la proximité : la souffrance tient dans un visage humain, presque à portée de main.",
        lookCloser: "Commencez par les yeux, puis les marques de souffrance. Le peu d'espace autour de la figure vous place presque dans la foule.",
        deeperContext: "Antonello a contribué à faire entrer dans la peinture italienne un réalisme précis, proche du Nord. Le résultat paraît calme, direct et très présent.",
      },
      simple: {
        hook: "Ce tableau rapproche le visage de vous.",
        whyItMatters: "Au lieu d'une grande scène, Antonello montre une seule personne qui souffre. Cela rend l'image difficile à ignorer.",
        lookCloser: "Regardez d'abord les yeux. Puis voyez comme la figure est près du bord du tableau.",
        deeperContext: "Ecce Homo veut dire : « Voici l'homme ». Le tableau vous demande de vraiment regarder.",
      },
      kids: {
        hook: "C'est un gros plan très sérieux.",
        whyItMatters: "L'artiste veut que tu regardes un visage, pas une grande scène d'action. Les petits détails racontent tout.",
        lookCloser: "Mission : regarde les yeux, puis la bouche. Lequel raconte le mieux l'émotion ?",
        deeperContext: "Dans les vieux tableaux religieux, les histoires passent souvent par les visages et les mains.",
        funFactOrMission: "Recule un peu. Le visage te semble-t-il plus calme ou plus intense ?",
      },
    };
  }
  return buildGenericFrench(kind, data);
}

function buildChineseContent(kind: string, data: Parameters<typeof buildLocalizedContent>[1]): Record<Mode, GeneratedModeContent> {
  if (kind === "titian_mirror") {
    return {
      normal: {
        hook: "镜子把美貌变成了一场关于观看的小戏剧。",
        whyItMatters: "提香让“观看”本身成为主题。光滑的镜面、女子的头发和旁边的人物，把私密梳妆变成了威尼斯式色彩、触感与欲望的研究。",
        lookCloser: "先找到镜子，再比较镜中偏冷的光和皮肤、头发上的暖光。注意第二个人物怎样把肖像变成一场表演。",
        deeperContext: "威尼斯画家擅长让颜色和表面变得几乎可以触摸。这里的美不是静静摆着，而是被安排、反射、观看。",
      },
      simple: {
        hook: "这不只是肖像，也是一幅关于“看”的画。",
        whyItMatters: "提香用镜子让画面变得有故事。你看到一个人正在被观看、打扮和欣赏。",
        lookCloser: "找到小镜子。比较镜子的冷光和皮肤、头发的暖色。",
        deeperContext: "文艺复兴时期的威尼斯画家很喜欢浓郁的颜色、柔软的肌肤和发亮的表面。",
      },
      kids: {
        hook: "这幅画的秘密道具是一面镜子。",
        whyItMatters: "提香想让你发现：谁在看谁？女子、帮她的人、镜子，还有你，都进入了这场景。",
        lookCloser: "任务：找到镜子，再找最亮的地方。它在镜子上、头发上，还是皮肤上？",
        deeperContext: "威尼斯曾以会画温暖、发光颜色的画家闻名。",
        funFactOrMission: "用手挡住旁边的人物。现在它更像肖像，还是更像故事？",
      },
    };
  }
  if (kind === "van_gogh_self_portrait") {
    return {
      normal: {
        hook: "脸是静止的，颜料却一点也不安静。",
        whyItMatters: "梵高的自画像不只是相貌记录，而是对色彩、力度和注意力的实验。1889年前后的自画像里，蓝绿色背景和躁动的笔触让人物显得鲜活而不稳定。",
        lookCloser: "比较胡须里的暖色笔触和冰冷的蓝色背景。再看眼睛周围，轮廓在哪里变成了一段段分开的笔触。",
        deeperContext: "自画像让梵高在缺少模特时也能工作，也让他把观察变成强烈的情绪。",
      },
      simple: {
        hook: "脸很安静，笔触却到处在动。",
        whyItMatters: "梵高用颜色和笔触表现的不只是外貌。他让一张肖像充满能量。",
        lookCloser: "先看胡须，再看蓝色背景。暖色和冷色在互相推挤。",
        deeperContext: "他画过很多自画像，因为自己就是最方便的模特。",
      },
      kids: {
        hook: "这张肖像像是在嗡嗡震动。",
        whyItMatters: "梵高把笔触画得像一条条能量轨迹。你看到的是一个人，也看到他用力作画的方式。",
        lookCloser: "任务：找出五个不同方向的笔触。它们都朝同一个方向吗？",
        deeperContext: "自画像有点像很久以前的自拍，只不过是用颜料慢慢画出来的。",
        funFactOrMission: "先退后，再靠近。远看是脸，近看是成千上万的痕迹。",
      },
    };
  }
  if (kind === "antonello_ecce_homo") {
    return {
      normal: {
        hook: "题目要求你观看，但这张脸让观看变得不轻松。",
        whyItMatters: "“Ecce Homo”图像表现基督被展示给人群。安托内洛的力量在于亲近感：苦难被压缩到一张近在眼前的人脸上。",
        lookCloser: "先看眼睛，再看受难的痕迹。注意人物周围空间很少，这种靠近感让你像站在人群里。",
        deeperContext: "安托内洛把一种精确、近似北方绘画的真实感带入意大利绘画，因此画面显得安静、直接而强烈。",
      },
      simple: {
        hook: "这幅画把一张脸推到你面前。",
        whyItMatters: "它没有画很大的场面，而是集中在一个受苦的人身上，所以很难忽略。",
        lookCloser: "先看眼睛，再看人物离画面边缘有多近。",
        deeperContext: "Ecce Homo 的意思是“看这个人”。这幅画在请你停下来认真看。",
      },
      kids: {
        hook: "这是一张很严肃的近距离面孔。",
        whyItMatters: "画家不是让你看大动作，而是让小细节讲完整个故事。",
        lookCloser: "任务：看眼睛，再看嘴。哪一个更能告诉你他的感受？",
        deeperContext: "古老的宗教画常常用脸、手和小标志来讲故事。",
        funFactOrMission: "退后一点再看。脸变得更平静，还是更强烈？",
      },
    };
  }
  return buildGenericChinese(kind, data);
}

function buildGenericEnglish(kind: string, data: Parameters<typeof buildLocalizedContent>[1]): Record<Mode, GeneratedModeContent> {
  const artist = data.artist || "the maker";
  const title = data.title;
  const clue = data.visualFeatures[0] || data.subject || data.objectType || "the main form";
  const contrast = data.visualFeatures[1] || data.objectType || "the surrounding details";
  const isPortrait = kind === "portrait" || /portrait|self-portrait/i.test(title);
  const isSculpture = kind === "sculpture";
  return {
    normal: {
      hook: isPortrait ? "A portrait is never only a face; it is a carefully built encounter." : isSculpture ? "Start with the object as a body in space, not just a thing on display." : `${title} is worth slowing down for because its details do more than decorate.`,
      whyItMatters: isPortrait ? `${artist} uses pose, gaze, and surface to control how close the sitter feels. That tension between likeness and presence is what makes the image hold attention.` : isSculpture ? `The work asks you to read shape, weight, and surface with your body as much as with your eyes. Its impact depends on how it occupies space.` : `The work matters because it carries information in visible choices: subject, material, scale, and the way attention is directed across the surface.`,
      lookCloser: `Start with ${clue}. Then compare it with ${contrast}; the difference tells you where the artist or maker wants your eye to move.`,
      deeperContext: data.date ? `The date or period, ${data.date}, helps place this work in a larger artistic and historical moment without reducing it to a label.` : "Use the visible evidence first: form, material, subject, and the strongest detail in front of you.",
    },
    simple: {
      hook: isPortrait ? "This is about more than a face." : "Start with one strong detail.",
      whyItMatters: isPortrait ? "The pose and the gaze are arranged to make you feel close to the person." : "The work matters because its materials and details guide how you look at it.",
      lookCloser: `Find ${clue}. Then look for ${contrast}.`,
      deeperContext: data.date ? `It belongs to ${data.date}, which gives it historical context.` : "Look for the strongest visible clue before reading more.",
    },
    kids: {
      hook: isPortrait ? "This artwork is trying to meet your eyes." : "This object has a looking game built into it.",
      whyItMatters: "Artists and makers hide important clues in details you can actually find.",
      lookCloser: `Mission: find ${clue}. Now find a second detail that feels very different from it.`,
      deeperContext: "Museums are full of clues. The more carefully you look, the more the object changes.",
      funFactOrMission: "Try stepping back for three seconds, then move closer. What changes first?",
    },
  };
}

function buildGenericFrench(kind: string, data: Parameters<typeof buildLocalizedContent>[1]): Record<Mode, GeneratedModeContent> {
  const clue = data.visualFeatures[0] || data.subject || data.objectType || "la forme principale";
  const contrast = data.visualFeatures[1] || data.objectType || "les détails autour";
  const isPortrait = kind === "portrait" || /portrait|autoportrait/i.test(data.title);
  const isSculpture = kind === "sculpture";
  return {
    normal: {
      hook: isPortrait ? "Un portrait n'est jamais seulement un visage : c'est une rencontre construite." : isSculpture ? "Regardez d'abord l'œuvre comme un corps dans l'espace." : "Cette œuvre vaut qu'on ralentisse : ses détails ne sont pas seulement décoratifs.",
      whyItMatters: isPortrait ? "La pose, le regard et la surface règlent la distance entre vous et la personne représentée." : isSculpture ? "L'œuvre se lit avec le corps autant qu'avec les yeux : forme, poids et surface comptent ensemble." : "Elle compte parce que ses choix visibles - sujet, matière, échelle, direction du regard - portent le sens.",
      lookCloser: `Commencez par ${clue}. Comparez-le ensuite avec ${contrast} : l'écart montre où votre regard est guidé.`,
      deeperContext: data.date ? `La période, ${data.date}, replace l'œuvre dans une histoire plus large sans la réduire à une étiquette.` : "Commencez par les preuves visibles : forme, matière, sujet et détail dominant.",
    },
    simple: {
      hook: isPortrait ? "Ce n'est pas seulement un visage." : "Commencez par un détail fort.",
      whyItMatters: isPortrait ? "La pose et le regard créent une présence." : "L'œuvre compte parce que ses matières et ses détails guident votre regard.",
      lookCloser: `Trouvez ${clue}. Puis cherchez ${contrast}.`,
      deeperContext: data.date ? `Elle appartient à ${data.date}, ce qui donne un contexte historique.` : "Cherchez d'abord l'indice visible le plus fort.",
    },
    kids: {
      hook: isPortrait ? "Cette œuvre essaie de croiser ton regard." : "Cet objet cache un jeu d'observation.",
      whyItMatters: "Les artistes et les artisans cachent souvent les indices importants dans les détails.",
      lookCloser: `Mission : trouve ${clue}. Puis trouve un deuxième détail très différent.`,
      deeperContext: "Dans un musée, les objets changent quand on les regarde vraiment.",
      funFactOrMission: "Recule pendant trois secondes, puis rapproche-toi. Qu'est-ce qui change en premier ?",
    },
  };
}

function buildGenericChinese(kind: string, data: Parameters<typeof buildLocalizedContent>[1]): Record<Mode, GeneratedModeContent> {
  const clue = data.visualFeatures[0] || data.subject || data.objectType || "主要形状";
  const contrast = data.visualFeatures[1] || data.objectType || "周围的细节";
  const isPortrait = kind === "portrait" || /portrait|self-portrait|肖像|自画像/i.test(data.title);
  const isSculpture = kind === "sculpture";
  return {
    normal: {
      hook: isPortrait ? "肖像从来不只是脸，而是一场被安排好的相遇。" : isSculpture ? "先把它当作占据空间的身体来看，而不是展柜里的物件。" : "这件作品值得你慢下来，因为细节不只是装饰。",
      whyItMatters: isPortrait ? "姿势、目光和表面处理决定了人物离你有多近。" : isSculpture ? "它需要你用眼睛和身体一起读：形状、重量、表面同时起作用。" : "它的重要性来自可见的选择：题材、材料、尺度，以及视线被引导的方式。",
      lookCloser: `先看${clue}。再把它和${contrast}比较；差异会告诉你目光该往哪里走。`,
      deeperContext: data.date ? `“${data.date}”这个时期信息帮助你把它放回更大的历史背景。` : "先看可见证据：形状、材料、题材和最突出的细节。",
    },
    simple: {
      hook: isPortrait ? "这不只是一个脸。" : "先找一个最强的细节。",
      whyItMatters: isPortrait ? "姿势和目光让人物显得有存在感。" : "材料和细节会引导你怎么看它。",
      lookCloser: `找到${clue}，再找${contrast}。`,
      deeperContext: data.date ? `它属于${data.date}，这给它历史背景。` : "先找最明显的视觉线索。",
    },
    kids: {
      hook: isPortrait ? "这件作品好像想和你对视。" : "这个物件里藏着一个观察游戏。",
      whyItMatters: "艺术家和工匠常把重要线索藏在细节里。",
      lookCloser: `任务：找到${clue}，再找一个和它很不一样的细节。`,
      deeperContext: "在博物馆里，认真看一会儿，物件就会变得不一样。",
      funFactOrMission: "退后三秒，再靠近。最先变化的是什么？",
    },
  };
}

function classifyArtwork(artist: string | null, title: string, objectType: string | null, subject: string | null): string {
  const haystack = normalize([artist, title, objectType, subject].filter(Boolean).join(" "));
  if (/titian|tiziano|titien/.test(haystack) && /woman|mirror|miroir|toilette/.test(haystack)) return "titian_mirror";
  if (/van gogh/.test(haystack) && /self portrait|self-portrait|autoportrait/.test(haystack)) return "van_gogh_self_portrait";
  if (/antonello/.test(haystack) && /ecce homo|christ/.test(haystack)) return "antonello_ecce_homo";
  if (/sculpture|statue|marble|bronze/.test(haystack)) return "sculpture";
  if (/portrait|self portrait|self-portrait|autoportrait/.test(haystack)) return "portrait";
  if (/painting|oil|canvas|panel|tableau|peinture/.test(haystack)) return "painting";
  return "factual_minimum";
}

export function getArtistMarketContext(artist: string | null): ArtistMarketContext | null {
  if (!artist) return null;
  const normalized = normalize(artist);
  return ARTIST_MARKET_CONTEXTS.find((context) => context.aliases.some((alias) => normalized.includes(normalize(alias)))) || null;
}

function marketLabel(context: ArtistMarketContext, locale: Locale): string {
  if (locale === "fr") return `${context.canonicalArtist} - contexte de marché`;
  if (locale === "zh-Hans") return `${context.canonicalArtist} 市场背景`;
  return `${context.canonicalArtist} market context`;
}

function marketExplanation(context: ArtistMarketContext, locale: Locale): string {
  const amount = formatContextAmount(context.amountMillions || 0, context.currency || "USD_MILLION");
  if (locale === "fr") return `${context.workTitle} s'est vendu ${amount} en ${context.year}. C'est un repère pour le marché de ${context.canonicalArtist}, pas une estimation de cette œuvre.`;
  if (locale === "zh-Hans") return `${context.workTitle} 于 ${context.year} 年以 ${amount} 成交。这是 ${context.canonicalArtist} 的艺术家市场参照，不是这件馆藏作品的估价。`;
  return `${context.workTitle} sold for ${amount} in ${context.year}. This is artist-market context, not an appraisal of this museum work.`;
}

function marketRelationship(locale: Locale): string {
  if (locale === "fr") return "Le chiffre concerne une autre œuvre vendue sur le marché. Il sert seulement à situer l'échelle du marché de l'artiste.";
  if (locale === "zh-Hans") return "这个数字来自另一件作品的市场成交，只用于说明艺术家市场的量级。";
  return "The number refers to another work sold on the market. It is used only to show the scale of the artist's market.";
}

function marketDisclaimer(locale: Locale): string {
  if (locale === "fr") return "Contexte seulement - pas une estimation de l'œuvre du musée.";
  if (locale === "zh-Hans") return "仅作背景参照，并非此馆藏作品估价。";
  return "Context only - not a valuation of the museum work.";
}

function formatContextAmount(amount: number, currency: string): string {
  const symbol = currency === "EUR_MILLION" ? "€" : currency === "GBP_MILLION" ? "£" : "$";
  return `${symbol}${amount.toFixed(amount % 1 === 0 ? 0 : 1)}M`;
}

function inferMovementOrPeriod(artist: string | null, date: string | null): string | null {
  const normalized = normalize(artist || "");
  if (/titian|tiziano|titien|antonello/.test(normalized)) return "Renaissance";
  if (/van gogh|monet|renoir|degas|cezanne|gauguin|manet/.test(normalized)) return "Modern painting";
  if (/picasso/.test(normalized)) return "Modern art";
  return date || null;
}

function clampConfidence(value: number | null | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) return 0.75;
  return Math.max(0, Math.min(1, value));
}

function stringField(value: Record<string, unknown> | null | undefined, key: string): string | null {
  const raw = value?.[key];
  return typeof raw === "string" && raw.trim() ? raw : null;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((x): x is string => typeof x === "string" && x.trim().length > 0) : [];
}

function cleanDisplay(value: string | null | undefined): string | null {
  if (!value) return null;
  const cleaned = value.replace(/\s+/g, " ").trim();
  return cleaned || null;
}

function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}
