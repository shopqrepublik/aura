# ELYIO — Visual Match Rebuild: Design Contract

## Задача

Переработать текущую визуальную реализацию ELYIO так, чтобы она максимально точно
соответствовала эталонному референсу №1 (прикладывается отдельно как изображение).

Текущая структура продукта в целом правильная. Не нужно заново придумывать UX,
менять информационную архитектуру или удалять существующие функции.

Проблема именно в визуальной реализации:

- материал слишком цифровой и стерильный;
- типографика выглядит как обычный iOS/SaaS-интерфейс;
- recap похож на банковский dashboard;
- ценовой блок выглядит как системная карточка;
- отсутствует редакционная, аукционная и музейная материальность;
- визуально не ощущается переход `Observe → Reveal → Collect`.

## Главная инструкция

> Референс №1 является целевым визуальным результатом, а не общим источником вдохновения.

Нужно приблизиться к нему по: типографике, пропорциям, цвету, материалам, теням,
текстуре, композиции, визуальной плотности, обработке фотографий, оформлению price
reveal, оформлению recap, оформлению Collector's Seal.

Не используй текущие экраны как визуальный референс. Используй их только для
сохранения функциональности и структуры.

---

## 1. Дизайн-философия

**ELYIO: Observe quietly. Reveal with evidence. Leave with a trophy.**

### Observe
Спокойный современный музейный каталог. Произведение доминирует; интерфейс отступает;
много воздуха; сдержанная редакционная типографика; никакого fintech/SaaS-впечатления.

### Reveal
Напряжение аукционного зала. Цена становится самостоятельным событием; крупная
display-типографика; тёплый бумажный материал; понятное доказательство оценки;
один художественный accent, извлечённый из картины.

### Collect
Персональный музейный трофей. Итог выглядит как страница каталога Christie's или
fashion-editorial poster; сумма становится главной; recap хочется сохранить и
опубликовать; milestone выглядит как коллекционная печать, а не UI badge.

---

## 2. Критически важное различие

### Текущая неверная реализация
Сейчас визуальный язык напоминает: Apple Health, Linear, generic React/Tailwind
mobile app, банковский dashboard, системные iOS-карточки.

Признаки, которые нужно убрать:
- слишком чистый белый фон
- одинаковый sans-serif во всех элементах
- огромный жирный grotesk без editorial contrast
- белые карточки с generic shadow
- большие чёрные rounded-кнопки как главный визуальный мотив
- светло-зелёные SaaS backgrounds
- одинаковая громкость всех элементов
- layout, похожий на таблицу KPI

### Целевая реализация
Гибрид: Sotheby's auction catalogue, Christie's editorial, Monocle, Financial Times
Weekend, Hermès print campaign, Apple editorial storytelling, музейный билет,
архивный документ, коллекционный сертификат. Не копировать бренд ни одного из них
буквально.

---

## 3. Шрифтовая система

**Главное правило: не использовать один SF Pro / Inter для всего продукта.**

### Editorial serif
Используется для: названия произведения, цены в Reveal Mode, суммы в Visit Recap,
названия художника в постере, важных editorial statements, Collector's Seal.

```css
font-family:
  "Iowan Old Style",
  "New York",
  "Baskerville",
  "Times New Roman",
  serif;

/* web */
--font-editorial:
  "Cormorant Garamond",
  "EB Garamond",
  "Libre Baskerville",
  Georgia,
  serif;
```

Предпочтительный бесплатный вариант: **Cormorant Garamond**.
Начертания: Regular 400, Medium 500, Semibold 600. Не использовать overly decorative
italic для основных данных.

### Neutral sans-serif
Используется для: UI controls, body, disclaimers, metadata, tabs, buttons, navigation.

```css
font-family:
  -apple-system,
  BlinkMacSystemFont,
  "SF Pro Text",
  "Helvetica Neue",
  Arial,
  sans-serif;
```

Китайский (body): `"PingFang SC", "Noto Sans SC", sans-serif;`
Китайский (editorial headers): `"Songti SC", "Noto Serif SC", serif;`

---

## 4. Типографическая шкала — Artwork Card

**Artist eyebrow**
```css
font-family: var(--font-sans);
font-size: 11px; line-height: 14px; font-weight: 600;
letter-spacing: 0.16em; text-transform: uppercase;
color: #696763;
```
Пример: `VINCENT VAN GOGH`

**Artwork title**
```css
font-family: var(--font-editorial);
font-size: 31px; line-height: 0.98; font-weight: 500;
letter-spacing: -0.025em; color: #181714;
/* small screen */
font-size: clamp(28px, 7.3vw, 34px);
```
Название должно ощущаться как заголовок каталога, а не название статьи в приложении.

**Artwork metadata**
```css
font-family: var(--font-sans);
font-size: 13px; line-height: 18px; font-weight: 400;
letter-spacing: 0; color: #686662;
```

**Hook**
```css
font-family: var(--font-sans);
font-size: 17px; line-height: 25px; font-weight: 400;
letter-spacing: -0.01em; color: #272622;
```
Не делать hook bold.

---

## 5. Типографика price reveal

**Market label**
```css
font-family: var(--font-sans);
font-size: 10px; line-height: 13px; font-weight: 600;
letter-spacing: 0.15em; text-transform: uppercase;
color: #65625d;
```
Текст: `MARKET CONTEXT`

**Updated/comparable metadata**
```css
font-family: var(--font-sans);
font-size: 11px; line-height: 15px; font-weight: 400;
font-variant-numeric: tabular-nums; color: #77736d;
```

**Main price** (главный объект Reveal Mode)
```css
font-family: var(--font-editorial);
font-size: clamp(48px, 13vw, 62px);
line-height: 0.88; font-weight: 500;
letter-spacing: -0.055em;
font-variant-numeric: lining-nums tabular-nums;
color: #161512;
/* на 390px viewport желательно 54px */
```
Не использовать generic bold sans-serif. Не делать сумму похожей на банковский
баланс. Цена должна выглядеть как оценка лота в каталоге.

**Price caption**
```css
font-family: var(--font-sans);
font-size: 12px; line-height: 16px; font-weight: 400; color: #68655f;
```

**Analogy**
```css
font-family: var(--font-sans);
font-size: 14px; line-height: 20px; font-weight: 500; color: #24231f;
```
Не использовать pill.

**Disclaimer**
```css
font-family: var(--font-sans);
font-size: 11px; line-height: 16px; font-weight: 400; color: #66635e;
```
Disclaimer всегда виден.

---

## 6. Типографика Visit Recap

**Museum label**
```css
font-family: var(--font-sans);
font-size: 11px; line-height: 15px; font-weight: 600;
letter-spacing: 0.13em; text-transform: uppercase;
color: rgba(248, 242, 229, 0.88);
```

**Intro phrase**
```css
font-family: var(--font-editorial);
font-size: 18px; line-height: 21px; font-weight: 500; color: #F4EBDD;
```
Текст: `YOU SAW`

**Recap value**
```css
font-family: var(--font-editorial);
font-size: clamp(70px, 19vw, 92px);
line-height: 0.82; font-weight: 500;
letter-spacing: -0.06em;
font-variant-numeric: lining-nums tabular-nums;
color: #F3E8D7;
```
Не использовать чёрный sans-serif размером 80px на белом фоне. Сумма должна быть
встроена в постер.

**Supporting phrase**
```css
font-family: var(--font-editorial);
font-size: 26px; line-height: 0.98; font-weight: 500;
letter-spacing: -0.02em; color: #F3E8D7;
```
Текст: `OF ART`

**Stats**
```css
font-family: var(--font-editorial);
font-size: 24px; line-height: 26px; font-weight: 500;
font-variant-numeric: tabular-nums; color: #F3E8D7;
```
Labels:
```css
font-family: var(--font-sans);
font-size: 9px; line-height: 12px; font-weight: 600;
letter-spacing: 0.10em; text-transform: uppercase;
color: rgba(243, 232, 215, 0.75);
```

---

## 7. Цветовая система

**Base palette**
```css
--canvas: #F7F3EC;
--canvas-light: #FBF8F2;
--surface: #FDFBF7;
--paper: #EDE6DA;
--paper-deep: #E4DACB;

--ink: #181714;
--ink-soft: #302E29;
--text-secondary: #67635C;
--text-tertiary: #8B867E;

--hairline: rgba(30, 27, 22, 0.10);
--hairline-strong: rgba(30, 27, 22, 0.17);
```

Не использовать: `#FFFFFF` как основной фон всего приложения; `#F2F2F7` как основной
материал; generic iOS blue; яркий зелёный; яркий красный вне ошибок.

**Artwork tints** (accent извлекается из картины, должен быть приглушённым, низкая chroma)

Van Gogh:
```css
--art-accent: #667A78;
--art-accent-light: #DDE4DF;
--art-accent-deep: #243A3B;
```
Monet:
```css
--art-accent: #8198A0;
--art-accent-light: #DEE6E6;
--art-accent-deep: #344E55;
```
Renoir:
```css
--art-accent: #A9857E;
--art-accent-light: #E9DDD7;
--art-accent-deep: #614942;
```

---

## 8. Auction Paper — материал ценового блока

`ProvenanceReveal` должен ощущаться как физический лист, вложенный в музейный или
аукционный каталог — не как стандартная карточка приложения.

**Background**
```css
background:
  linear-gradient(
    145deg,
    color-mix(in srgb, var(--art-accent) 8%, #EDE6DA),
    #F1EBE1 47%,
    color-mix(in srgb, var(--art-accent) 5%, #E6DED1)
  );

/* fallback */
background:
  linear-gradient(
    145deg,
    rgba(102, 122, 120, 0.09),
    #F1EBE1 47%,
    #E8E0D4
  );
```

**Texture**
```css
background-image:
  url("/textures/paper-grain.png"),
  linear-gradient(...);
background-blend-mode: soft-light, normal;
background-size: 240px 240px, cover;
/* opacity: 1.5–2.5% */
```
Не использовать видимую бумажную фотографию. Материал должен ощущаться, а не
бросаться в глаза.

**Border**
```css
border: 1px solid rgba(45, 39, 31, 0.12);
box-shadow:
  inset 0 1px 0 rgba(255, 255, 255, 0.55),
  0 14px 35px rgba(37, 31, 24, 0.075);
```

**Radius**
```css
border-radius: 22px;
/* нижний sheet: */
border-radius: 28px 28px 0 0;
```

**Padding**
```css
padding: 24px 22px 22px;
```

**Расстояния**
```
label → metadata: 4px
metadata → price: 24–28px
price → caption: 10px
caption → divider: 22px
divider → analogy: 20px
analogy → disclaimer: 18px
```

**Divider**
```css
height: 1px;
background: rgba(35, 31, 26, 0.12);
```

---

## 9. Main artwork sheet

```css
background: #FBF8F2;
border-radius: 30px 30px 0 0;
box-shadow:
  0 -16px 45px rgba(22, 19, 15, 0.09),
  inset 0 1px 0 rgba(255,255,255,0.80);
```
Вместо абсолютно белого UI должно быть ощущение тёплой бумаги.

---

## 10. Viewing Note

Превратить текущий зелёный success-message блок в редакционную заметку.

```css
background: color-mix(in srgb, var(--art-accent) 10%, #F6F1E8);
border-left: 2px solid color-mix(in srgb, var(--art-accent) 70%, #333);
border-radius: 4px 16px 16px 4px;
padding: 17px 18px;
```

Заголовок:
```css
font-size: 10px; font-weight: 600;
letter-spacing: 0.13em; text-transform: uppercase;
```
Текст:
```css
font-size: 15px; line-height: 21px; font-weight: 400;
```
Иконка глаза: 18px, тонкий stroke, без круглой SaaS-подложки либо на почти
незаметном фоне.

---

## 11. Кнопки

Кнопки присутствуют, но не должны визуально доминировать над контентом.

**Primary**
```css
height: 54px; border-radius: 14px;
background: #181714; color: #FAF7F0;
font-size: 16px; font-weight: 500; letter-spacing: -0.01em;
box-shadow: 0 7px 18px rgba(20, 18, 15, 0.12);
```
Не использовать radius 9999px для всех кнопок — pill-кнопки делают продукт похожим
на fintech/food delivery.

**Secondary**
```css
height: 50px; border-radius: 14px;
background: rgba(24, 23, 20, 0.055);
border: 1px solid rgba(24, 23, 20, 0.06);
color: #25231F;
```

**Tertiary** — текстовая кнопка без большой подложки.

---

## 12. Tabs Normal / Simple / Kids

```css
background: rgba(37, 33, 28, 0.055);
border: 1px solid rgba(37, 33, 28, 0.055);
border-radius: 15px; padding: 3px;
/* height: 44px */
```
Active:
```css
background: #1A1916; color: #F8F4EC;
border-radius: 12px;
box-shadow: 0 4px 10px rgba(0,0,0,0.09);
```

---

## 13. Visit Progress

Не превращать экран в dashboard KPI. Убрать четыре одинаковых квадранта.

Новая композиция:
```
LIVE VISIT

€95–130M seen
1 work · 2 minutes

01 / 50 essential works
```

Один главный показатель + одна вторичная строка. `1% MUSEUM` не должно конкурировать
с `€95–130M`. Missions → editorial checklist, не тяжёлая двойная линия на thumbnail.

---

## 14. Visit Recap — полностью переработать

Не косметика — полная пересборка.

**Формат:** 9:16, 1080×1920

**Background** — тёмный editorial collage (архитектура музея, детали часов Орсе,
crop картины, muted palette из просмотренных работ). Не светлый градиент с floating
rounded rectangles.

Пример (Van Gogh):
```css
background:
  linear-gradient(180deg, rgba(13, 26, 40, 0.50), rgba(26, 29, 29, 0.78)),
  url("/recap/orsay-clock-crop.jpg");
```

**Overlay**
```css
background:
  linear-gradient(
    180deg,
    rgba(10, 19, 28, 0.10) 0%,
    rgba(18, 20, 20, 0.55) 50%,
    rgba(21, 20, 18, 0.94) 100%
  );
```
Grain: 2–3%

**Layout**
```
top padding: 64px
horizontal padding: 44px
bottom padding: 48px
```

**Artwork thumbnails**: 120–150px высотой, ratio ~4:5, radius 8–10px, тонкая
светлая border, без огромных белых карточек.

**Most valuable work** — прямо на постере, не в белой SaaS-карточке:
```
MOST VALUABLE WORK

Claude Monet
Le bassin aux nymphéas
€80–120M
```

---

## 15. Collector's Seal

Не badge с красной заливкой — физическая печать: слегка несовершенная, тёмный
бордовый сургуч, двойная граница, deboss/emboss, serif typography, микротекст по
кругу, несимметричный поворот −3°…2°.

```css
--seal-dark: #681E1A;
--seal-mid: #8A2D25;
--seal-highlight: #B35B4C;
--seal-shadow: rgba(39, 10, 8, 0.33);
--seal-text: #F2D5BD;

box-shadow:
  0 10px 22px rgba(54, 12, 9, 0.28),
  inset 0 2px 4px rgba(255, 211, 184, 0.19),
  inset 0 -5px 9px rgba(53, 8, 6, 0.25);
```

Текст по окружности: `ELYIO · CULTURAL MILESTONE · PARIS`
Центр: `€1B+ / VISITOR`
Внизу: `2026`

Не использовать современные UI sans-serif внутри seal.

---

## 16. Shadows (не одна generic shadow на всё)

```
Artwork sheet:      0 -16px 45px rgba(22, 19, 15, 0.09)
Auction Paper:       0 14px 35px rgba(37, 31, 24, 0.075)
Floating controls:   0 6px 16px rgba(16, 15, 13, 0.13)
Recap thumbnails:    0 6px 16px rgba(0, 0, 0, 0.22)
Seal:                0 10px 22px rgba(54, 12, 9, 0.28)
```
Тени должны иметь тёплый оттенок, не серо-синий.

---

## 17. Border radii (иерархия, не одинаковые везде)

```
Full artwork bottom sheet:  28–30px
Provenance Reveal:          20–22px
Viewing Note:                14–16px
Primary/Secondary buttons:  14px
Small thumbnails:            8–10px
Methodology sheet:          26–28px
Seal:                        круглая форма
```
Не использовать `rounded-full` кроме: маленьких icon buttons, status dots, seal.

---

## 18. Spacing system

Базовая сетка 4px, интервалы: 4/8/12/16/20/24/32/40/48/64.

```
artwork → sheet overlap:        18–24px
title → metadata:                10–12px
metadata → hook:                 24px
hook → price reveal:             30–34px
price reveal → Why it matters:   34–40px
Why it matters → Viewing Note:   26–30px
Viewing Note → actions:          32px
```
Не сжимать price reveal ради показа всех кнопок на одном viewport — пусть
пользователь скроллит.

---

## 19. Motion

**Artwork recognized**
```
image settle: 180ms
sheet rise: 420ms
title reveal: 180–320ms
hook reveal: 320–480ms
```

**Price reveal**
```
pause: 140ms
card enter: 520ms
price lower bound: 180ms
full range resolve: +160ms
evidence fade: +120ms
```
Easing: `cubic-bezier(0.16, 1, 0.3, 1)`

Price motion: `€95M → €95–130M`. Не использовать count-up animation.

**Collector Seal**
```
opacity: 0 → 1
scale: 1.07 → 1
rotate: -3deg → -1deg
duration: 420ms (однократно)
```

**Reduced motion**: `prefers-reduced-motion` → никаких scale, только opacity,
duration до 180ms, haptics отключить или оставить light.

---

## 20. Accessibility

- contrast body text: минимум 4.5:1
- disclaimer не светлее `#67635C` на paper-background
- touch targets минимум 44×44px
- body минимум 16px для длинных текстов
- zoom не блокировать
- price range доступен screen reader как единая строка
- не кодировать значение только цветом
- accent extraction должен проходить contrast check
- zh-Hans проверять отдельно на реальном iPhone

---

## 21. Responsive behavior

Целевые viewport: 375×812, 390×844, 393×852, 430×932

Не использовать fixed height для: title, disclaimer, analogy, methodology,
translations.

```css
/* Price */
font-size: clamp(46px, 13vw, 60px);
/* Recap */
font-size: clamp(68px, 20vw, 94px);
```

Французский: перенос supporting text допустим, сумма остаётся главной.
Китайский: убрать uppercase letter-spacing, вертикально устойчивые text blocks,
не имитировать латинскую editorial композицию механически.

---

## 22. Что конкретно изменить в существующей реализации

**Artwork page** — сохранить: hero image, modes, artist, title, hook, market
context, viewing note, actions.
Изменить: фон на warm canvas; title/price на editorial serif; Market Context →
Auction Paper; увеличить цену; убрать fintech appearance и generic green block;
уменьшить доминирование кнопок; добавить paper texture и artwork-derived tint;
исправить spacing.

**Progress page** — сохранить данные и missions.
Изменить: убрать KPI-dashboard composition; одна большая сумма вместо сетки;
уменьшить circle progress; missions как editorial checklist; убрать тяжёлую
двойную линию на thumbnail; next mission — меньше похоже на CTA-рекламу.

**Recap page** — не косметика, полная пересборка: full-screen poster, тёмный
image-based background, serif typography, large value, no white stat table, no
floating SaaS card, three artwork thumbnails, valuable work directly on poster,
seal, ELYIO wordmark.

**Share export** — файл должен совпадать с recap-постером, а не экспортировать
текущую web page с кнопками.

---

## 23. Компоненты (создать/обновить)

```
EditorialArtworkTitle
ArtworkMetadata
ProvenanceReveal
MarketValueTypography
MarketEvidence
ViewingNote
MethodologySheet
EditorialVisitProgress
AcquisitionPoster
ArtworkStrip
MostValuableWork
CollectorsSeal
SharePosterRenderer
```
Не делать все компоненты generic cards.

---

## 24. CSS tokens

```css
:root {
  /* Typography */
  --font-editorial:
    "Cormorant Garamond", "Iowan Old Style", "New York",
    Baskerville, Georgia, serif;
  --font-sans:
    -apple-system, BlinkMacSystemFont, "SF Pro Text",
    "Helvetica Neue", Arial, sans-serif;

  /* Canvas */
  --color-canvas: #F7F3EC;
  --color-canvas-light: #FBF8F2;
  --color-surface: #FDFBF7;
  --color-paper: #EDE6DA;
  --color-paper-deep: #E4DACB;

  /* Ink */
  --color-ink: #181714;
  --color-ink-soft: #302E29;
  --color-secondary: #67635C;
  --color-tertiary: #8B867E;

  /* Lines */
  --hairline: rgba(30, 27, 22, 0.10);
  --hairline-strong: rgba(30, 27, 22, 0.17);

  /* Artwork accent — overridden per artwork */
  --art-accent: #667A78;
  --art-accent-light: #DDE4DF;
  --art-accent-deep: #243A3B;

  /* Milestone */
  --seal-dark: #681E1A;
  --seal-mid: #8A2D25;
  --seal-highlight: #B35B4C;
  --seal-text: #F2D5BD;

  /* Radius */
  --radius-sheet: 30px;
  --radius-reveal: 22px;
  --radius-note: 16px;
  --radius-button: 14px;
  --radius-thumbnail: 9px;

  /* Shadows */
  --shadow-sheet: 0 -16px 45px rgba(22, 19, 15, 0.09);
  --shadow-reveal: 0 14px 35px rgba(37, 31, 24, 0.075);
  --shadow-control: 0 6px 16px rgba(16, 15, 13, 0.13);
  --shadow-seal: 0 10px 22px rgba(54, 12, 9, 0.28);

  /* Motion */
  --ease-reveal: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-sheet: 420ms;
  --duration-reveal: 520ms;
  --duration-stamp: 420ms;
}
```

---

## 25. Запрещённые решения

Не использовать: Inter как основной display font; SF Pro Display для цены и
recap-суммы; pure white во всех surfaces; generic pastel gradient; floating
translucent glass cards; uniform pill buttons; rounded rectangles как фоновые
decorations; KPI grid на recap; чёрную сумму на почти белом пустом background как
весь share poster; ярко-зелёную карточку Look closer; saturated artwork accent;
confetti; pulse; bounce; count-up money animation; casino semantics; crypto/fintech
visual language; чрезмерно крупный sans-serif bold; скрытый disclaimer.

---

## 26. Definition of Done

1. Artwork page визуально ближе к reference 1, чем к текущей реализации.
2. Price выглядит как аукционная оценка, а не банковский баланс.
3. Title и recap используют настоящий editorial serif.
4. Auction Paper обладает заметной, но сдержанной материальностью.
5. Viewing Note больше не выглядит как success alert.
6. Recap полностью пересобран как image-based editorial poster.
7. Share export совпадает с poster-design.
8. Collector's Seal выглядит физическим и редким.
9. English, French и zh-Hans не ломают layout.
10. Normal, Simple и Kids используют один визуальный каркас.
11. Disclaimer виден без дополнительного действия.
12. Motion поддерживает reveal, а не отвлекает.
13. Реальный iPhone screenshot визуально соответствует приложенному reference board.
14. Не используются placeholder rectangles вместо реальных изображений в финальном export.
15. Все screens проверены на 390×844 и 430×932.

---

## 27. Порядок выполнения (не менять всё сразу без проверки)

**Шаг 1** — статический visual prototype: Artwork Page, Provenance Reveal, Viewing
Note. Screenshot 390×844.

**Шаг 2** — после визуального подтверждения: motion.

**Шаг 3** — полная пересборка Recap Poster: in-app recap, чистый 1080×1920 export,
вариант €100M, вариант €1B+ с seal.

**Шаг 4** — обновление Progress screen.

**Шаг 5** — проверка en/fr/zh-Hans и modes.

Не переходить к следующему шагу, пока предыдущий визуально не совпадает с
эталонным направлением.

---

## 28. Финальная инструкция

> Do not reinterpret the reference into a modern generic SaaS aesthetic.
>
> Reproduce its editorial warmth, serif typography, paper materials, muted
> artwork-derived colors, auction-catalogue tension and poster-like recap
> composition.
>
> The existing information architecture should remain, but the visual system must
> be rebuilt.
>
> The goal is not "cleaner UI." The goal is:
> **museum calm → auction tension → collectible reward.**
>
> Before modifying production code, first create a faithful static prototype of
> the Artwork screen and Visit Recap at the exact target viewport.
>
> Do not declare completion based only on component structure. Completion requires
> visual comparison against Reference 1.
