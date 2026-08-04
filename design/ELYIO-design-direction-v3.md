# ELYIO Design Direction v3
## The Curated Reveal

Museum calm. Auction-room tension. Editorial reward.

Не казино.
Не банковская выписка.
Не холодный интерфейс Linear.

Это опыт, который большую часть времени ведёт себя как современный музейный каталог, но в момент раскрытия стоимости приобретает напряжение аукционного зала.

**Главная идея:** Стоимость не должна кричать цветом. Она должна ощущаться масштабом, паузой, композицией и доказательствами.

---

## 1. Три эмоциональных состояния интерфейса

Вместо двух режимов — официально три.

### A. Observe — «Смотреть»

Используется для: Home, Camera, процесса распознавания, автора/названия/года, Why it matters, аудио, истории произведения.

Характер: спокойно, много воздуха, нейтральный фон, искусство визуально доминирует, никакого ощущения финансового приложения.

### B. Reveal — «Осознать масштаб»

Используется только для: появления оценки, аналогии, достижения крупного milestone, самой дорогой работы визита.

Характер: крупная типографика, короткая пауза, собственный материал блока, цвет произведения как атмосфера, сразу видимое объяснение оценки, один тактильный отклик.

### C. Collect — «Получить трофей»

Используется для: Visit Recap, share card, достижений, итогового результата визита.

Характер: editorial poster, музейный билет × аукционный каталог × fashion campaign, крупная сумма, композиция, которую хочется сохранить и опубликовать.

Путь: **Observe → Reveal → Collect** — эмоциональная дуга продукта.

---

## 2. Ключевой экран: Artwork Card

### Верхняя часть — искусство остаётся героем

Порядок: изображение → художник → название → год и базовые сведения → один короткий хук.

Пример:
```
VINCENT VAN GOGH
Starry Night Over the Rhône
Arles · 1888

Van Gogh turned artificial gaslight into one of the
most emotional night scenes in art.
```

Только после этого появляется стоимость. Не нужно сразу бросать человеку в лицо €95–130M. Сначала он должен понять, на что смотрит.

---

## 3. Новый ценовой компонент: Provenance Reveal

Развитие Archive Slip, но не просто серая карточка. Выглядит как вкладыш из аукционного каталога, который частично перекрывает спокойную музейную страницу.

### Структура

```
MARKET CONTEXT
Updated Aug 2026 · 3 comparable sales

€95–130M
Estimated market range

Comparable to approximately
two long-range private jets

Based on public auction results for comparable works.
Museum-held. Not for sale. This is not a formal appraisal.

View methodology →
```

### Почему это лучше предыдущих решений

Соединяет: крупную сумму, серьёзность Archive Slip, всегда видимый disclaimer, доказательную базу, человеческую аналогию, ощущение отдельного документа.

### Размеры и иерархия

**Label** "MARKET CONTEXT" — 10–11pt, uppercase, tracking 0.12em, medium, нейтрально-серый.

**Дата и comps** "Updated Aug 2026 · 3 comparable sales" — 11–12pt, regular, tabular numbers, серый.

**Цена** "€95–130M" — 44–52pt на iPhone, weight 600, tracking -0.045em, tabular numbers, одна строка где возможно; если не помещается — перенос диапазона в две строки, без уменьшения ниже 40pt.

**Подпись** "Estimated market range" — 13pt, regular, не uppercase, серый.

**Аналогия** — не pill. "Comparable to approximately two long-range private jets" — 15–16pt, medium, отдельная строка, можно маленькую монохромную пиктограмму, не использовать эмодзи в Normal-режиме.

**Disclaimer** — 11–12pt, line-height 15–16pt, виден постоянно, контраст не ниже доступного минимума. "View methodology" — отдельная подчёркнутая ссылка.

---

## 4. Материал блока: не просто серый Stone

`#F5F5F7` слишком системно — выглядит как Apple Settings. Нужен **Auction Paper** — динамический материал, основанный на самой работе.

### Базовый фон
`#F4F1EB` — тёплый бумажный, без «музейного золота».

### Dynamic artwork tint

Из картины извлекается один спокойный цвет (Monet — дымчато-голубой; Van Gogh — глубокий сине-зелёный; Renoir — пыльный розовый; Degas — серо-зелёный; Cézanne — охра), добавляется в фон блока с интенсивностью только 5–9%.

```css
background: linear-gradient(
  135deg,
  rgba(artworkAccent, 0.08),
  rgba(244, 241, 235, 0.96) 48%
);
```

Пользователь чувствует связь с картиной, но интерфейс не превращается в Spotify Wrapped.

### Детали материала
```
border: rgba(17,17,17,0.08);
radius: 18px;
бумажная текстура: 1–1.5%;
внутренняя hairline-линия;
тень: 0 12px 30px rgba(0,0,0,0.055);
без стекла, blur и ярких градиентов.
```

---

## 5. Главная WOW-механика — драматургия появления, не анимация цифр

Не крутить сумму как счётчик в казино. Нужен последовательный reveal.

### Motion storyboard

**Frame 1 — Recognition** (0–180ms): изображение, художник, название, год.

**Frame 2 — Meaning** (180–380ms): короткий хук.

**Frame 3 — Pause** (~120–160ms): короткая визуальная пауза. Даёт мозгу подготовиться к смене контекста.

**Frame 4 — Provenance Reveal enters**: opacity 0→1, translateY 10px→0, scale 0.985→1, duration 520ms, easing `cubic-bezier(0.16, 1, 0.3, 1)`.

**Frame 5 — Price resolves**: сначала "€95M", через 160ms мягко раскрывается в "€95–130M". Не счётчик — переход от нижней границы к честному диапазону.

**Frame 6 — Evidence appears** (задержка 120ms): comps, disclaimer, analogy, methodology link.

**Haptic**: один medium impact в момент появления полного диапазона. Без pulse, bounce, confetti, звука монет, сияющей рамки, повторяющейся анимации.

Полный момент ~900–1100ms, но ощущается быстро.

---

## 6. Три уровня интенсивности

Если каждый скан выглядит одинаково — эффект перестаёт быть событием.

**Standard Estimate** (до €10M): обычное появление блока, без haptic или только light, цена 40–44pt.

**Major Work** (€10–100M): полная reveal-анимация, medium haptic, цена 46–50pt, заметнее dynamic tint.

**Exceptional Work** (€100M+): добавляется строка "Exceptional market tier" (не яркий бейдж) — тонкая двойная hairline, инвентарный номер, увеличенная пауза перед раскрытием, цифра 52pt. Редкость без игровых фейерверков.

---

## 7. Отделяем деньги, понимание и наблюдение

После Provenance Reveal экран снова становится тихим.

### Why it matters
Белый/off-white фон. Заголовок 11pt uppercase, основной текст 17–18pt, weight 450/500, line-height 24–26pt, максимум 3–4 строки.

### Look closer
Не жёлтая предупреждающая карточка — **Viewing Note**. Фон — accent цвет картины с opacity 8–12%, слева тонкая вертикальная линия 2px, маленький знак глаза/crosshair, без жёлтого universal warning-color.

Итог: Value Reveal — документ и масштаб; Why it matters — спокойное объяснение; Look closer — непосредственное действие.

---

## 8. Normal / Simple / Kids

Каркас полностью одинаковый, меняется только язык.

- Normal: "Comparable to approximately two long-range private jets."
- Simple: "That is about the price of two large private planes."
- Kids: "That could buy around 30 million ice creams."

Kids-версия не превращается в мультфильм: чуть крупнее иллюстративная иконка, чуть насыщеннее artwork tint, проще аналогия. Цена, disclaimer и методология остаются честными и на том же месте.

---

## 9. Multilingual-устойчивость

Дизайн нельзя строить под английскую длину.

```
EN: Estimated market range
FR: Fourchette de valeur estimative
ZH: 估算市场价值区间
```

Правила: label-блок допускает две строки; сумма никогда не привязана к label в одной строке; аналогия располагается вертикально; не использовать fixed-height; для zh-Hans убрать letter-spacing uppercase-логику там, где неприменима; шрифт для китайского — PingFang SC; tabular numbers сохраняются во всех языках.

---

## 10. Recap v3: The Acquisition Poster

Ни Bank Statement, ни яркий Spotify Wrapped. Recap должен выглядеть как персональная страница из ежегодного отчёта крупного аукционного дома.

### Верх
```
MUSÉE D'ORSAY
PARIS · 4 AUG 2026
```
Мелкая редакционная типографика.

### Главная кульминация
```
YOU SAW
€3.8B
IN ESTIMATED ART MARKET VALUE
```
€3.8B — 64–84pt; остальной текст — 14–18pt. Цифра может частично накладываться на изображение, но не ухудшать читаемость.

### Визуальный фон — Visit Palette
1. Берём 3 самые значимые просмотренные работы.
2. Из каждой извлекаем dominant muted color.
3. Создаём спокойный трёхцветный editorial gradient.
4. Накладываем лёгкое grain.
5. Добавляем 2–3 cropped fragments картин как музейный коллаж.

Каждый recap получает уникальный вид.

### Метрики
Не четыре одинаковые клетки. Одна строка: `37 works · 14 artists · 2h 14m`. Ниже: Most valuable work / Claude Monet · €80–120M. Любимая работа — небольшой визуальный блок (thumbnail, художник, название, год).

---

## 11. Billion Euro Visitor: Collector's Seal

Круглая печать вместо плоского бейджа.

**Визуально**: диаметр 78–92px, двойная тонкая окружность, blind emboss/deboss эффект, без красной заливки. Основной вариант — тёмный графит; специальный — глубокий бордовый `#6F1D1B`. Текст по окружности: "ELYIO · CULTURAL MILESTONE · PARIS". В центре: "€1B+ VISITOR". Внизу маленькая дата: "04·08·26".

**Анимация**: однократный stamp — opacity, scale 1.08→1, rotate -2°→0, duration 420ms, один medium haptic. Без пульса после появления.

---

## 12. Что делать с красным

Красный не запрещён полностью — редкий сигнальный цвет, не основа.

**Разрешён только для**: Collector's Seal, milestone €1B+, одной тонкой линии в Recap, редких exceptional-state labels.

**Не использовать для**: обычных кнопок, цены каждой картины, ошибок распознавания и достижения одновременно, пульсирующих элементов. Для ошибок — системный красный, визуально отделённый от milestone-burgundy.

---

## 13. Обновлённые design tokens

```
Base
canvas:           #FAFAF8
surface:          #FFFFFF
paper:            #F4F1EB
text-primary:     #111111
text-secondary:   #626267
text-tertiary:    #8A8A90
hairline:         rgba(17,17,17,0.09)

Reveal
reveal-paper:     #F4F1EB
reveal-shadow:    0 12px 30px rgba(0,0,0,0.055)
accent-opacity:   0.05–0.09
price-size:       44–52pt
price-weight:     600
price-tracking:   -0.045em

Milestone
seal-graphite:    #1B1B1D
seal-burgundy:    #6F1D1B
seal-paper:       #EDE8DF

Motion
reveal-duration:  520ms
sequence-total:   900–1100ms
ease-out:         cubic-bezier(0.16,1,0.3,1)
stamp-duration:   420ms
```

---

## 14. Как должен выглядеть первый экран после распознавания

```
[ FULL ARTWORK IMAGE ]

VINCENT VAN GOGH
Starry Night Over the Rhône
Arles · 1888

Van Gogh transformed modern city light
into a deeply emotional night scene.

┌─────────────────────────────────┐
│ MARKET CONTEXT                  │
│ Updated Aug 2026 · 3 comps      │
│                                  │
│ €95–130M                        │
│ Estimated market range          │
│                                  │
│ ─────────────────────────────── │
│ Comparable to approximately     │
│ two long-range private jets     │
│                                  │
│ Based on public auction sales.  │
│ Museum-held and not for sale.   │
│ Not a formal appraisal.         │
│ View methodology →               │
└─────────────────────────────────┘

WHY IT MATTERS
Van Gogh showed that artificial light
could carry the emotion of a sunset.

LOOK CLOSER
Follow the reflections across the river.
They lead your eye back toward the city.

[ Add to my visit ]   [ Listen 45s ]
```

Главный WOW создаётся не одной яркой карточкой, а правильной последовательностью:
1. Я увидел произведение.
2. Я понял одну важную мысль.
3. Подождите… оно могло бы стоить сколько?
4. Я вижу, откуда взялась эта цифра.
5. Теперь я снова смотрю на картину — уже другими глазами.

Это и есть продукт.

---

## 15. Что конкретно передать Claude / дизайнеру

### Задача
Заменить текущий PriceBadge и два pills новым компонентом ProvenanceReveal.

### Нужно реализовать

**Компоненты**: ArtworkIdentity, ProvenanceReveal, MarketMethodologySheet, ViewingNote, VisitAcquisitionPoster, CollectorsSeal.

**Состояния**: loading, recognized, reveal-pending, reveal-visible, methodology-open, standard, major, exceptional, kids, reduced-motion.

**Обязательные примеры**: Van Gogh (тёмно-синий accent), Monet (туманно-голубой), Renoir (пыльно-розовый); английский, французский, китайский; €5–8M, €95–130M, €250–400M, диапазон неизвестен/недостаточно данных.

**Recap**: без milestone; €100M+; €1B+ Collector's Seal; светлая и тёмная картина; формат 9:16; экспорт 1080×1920.

### Финальная формула

Не "Quiet museum. Powerful reveal." — слишком общее.

**Финальная дизайн-философия**: Observe quietly. Reveal with evidence. Leave with a trophy.

По-русски: Спокойно смотреть. Эффектно раскрывать. Уходить с трофеем.

Вариант 1 дал эмоцию. Вариант 2 дал доказательность. Третий вариант соединяет их: цена крупная, но не кричащая; цвет есть, но он приходит из картины; анимация есть, но не игровая; disclaimer виден; comps доступны; recap вызывает гордость; искусство не превращается в повод для казино.

Именно так можно получить WOW, не разрушая доверие к ELYIO.
