# ELYIO.CO - FINAL BUILD PROMPT FOR CLAUDE CODE

Brand: ELYIO.CO
Domain: elyio.co
Previous name: AURA
Tagline: ELYIO — POINT. DISCOVER. UNDERSTAND.
Story: From Elysium (Champs-Élysées) - the place for cultural heroes. Operating system for culture.

# ELYIO.CO - iPhone WoW Design System - Build in Next.js + Tailwind

## ROLE
Build premium museum app like Apple ships hardware. Content is hero, UI is invisible. iPhone 15 Pro frame 390x852, radius 54px outer, 44px inner. Showcase in desktop landing + 5 iPhone frames.

## DESIGN TOKENS - EXACT FROM CODE

Palette:
- Canvas #FAFAF9 bg
- Ink #111111 text
- Obsidian #000000 primary / buttons
- Stone #F5F5F7 card/surface
- Billion #FF3B30 accent for BILLION badge
- Glow #FFF8E1 eye highlight bg + border #F5E6B8 + text #5C4D1E
- Muted #8E8E93 captions, #6E6E73 secondary
- Success dot #30D158 with glow shadow 0 0 8px #30D158

Typography: font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", Inter, Helvetica Neue, sans-serif
- Title 28px: 28px bold tracking -0.04em leading none
- Title 24px: 24px bold tracking -0.04em leading 26px
- Headline 22px: 22px semibold -0.02em
- Body 16px: 16px leading 24px tracking -0.011em weight 450 color #1D1D1F
- Caption Upper: 11px semibold tracking 0.12em uppercase #8E8E93
- Tiny Upper: 10px bold tracking 0.18em uppercase
- Mono: 11px font-mono

Radius:
- iPhone outer 54px, inner screen 44px, notch 96x28 rounded-b 16px
- Cards 20px / 24px, Badges 14px / 16px, Buttons 9999px full
- Mission card 16px

Shadows - ONLY these, no borders except black/[0.06]:
- Card soft: 0 8px 24px rgba(0,0,0,0.06)
- Card medium: 0 12px 24px rgba(0,0,0,0.06) / 0.22
- Button: 0 8px 20px rgba(0,0,0,0.18)
- Bottom sheet: 0 16px 32px rgba(0,0,0,0.22)
- iPhone frame: 0 50px 100px -20px rgba(0,0,0,0.25), 0 20px 40px -20px rgba(0,0,0,0.3)
- Hover lift: transform -translate-y-2 + shadow 0 60px 120px -20px rgba(0,0,0,0.35)

Motion:
- Easing: cubic-bezier(0.32,0.72,0,1) 300ms default, (0.16,1,0.3,1) 600ms for iPhone hover lift
- Spring: card open spring(0.8) translateY from bottom
- Flash: @keyframes flash 0% opacity 0, 15% opacity 1, 100% opacity 0 - 0.35s
- Stagger: missions 120ms each
- Haptics: navigator.vibrate(10) soft impact on detect, 20 on shutter, light on segment switch, success on Add

## PRINCIPLES - MUST FOLLOW
1. Content is Hero: Artwork takes 60% screen. UI retreats to 8% opacity until needed. No museum gold.
2. Invisible UI: Interface appears on intent, not on load. Camera is navigation. Point is click.
3. One Action Per Screen: Start / Frame / Add / Continue / Share

## 5 SCREENS - EXACT SPECS

### 01 MUSEUM HOME - "Start Visit"
Bg: radial-gradient(120% 80% at 50% 0%, #E8E0D6 0%, #D6DDE8 40%, #C9CED6 100%) + blur 18px white overlay 30%
Top pill: h28 px3 rounded-full bg-black/80 backdrop-blur-xl flex gap2 shadow 0 4 12 rgba(0,0,0,0.15) - dot 2x2 rounded-full bg #30D158 + text "Musée d'Orsay • Detected" 12px 600 white -0.01em
Center: button w164 h164 rounded-full bg-black text-white flex-col center shadow 0 20 40 rgba(0,0,0,0.25) inset 0 1 0 rgba(255,255,255,0.15) active scale 0.98 - Title 17px semibold -0.02em "Start visit" / "Visit active", subtitle 11px opacity 60 "Tap to begin"
Bottom missions: p3 pb34 space-y-2.5 - 3 cards h64 rounded 16 bg-white/90 backdrop-blur-2xl border black/0.06 shadow - flex px4 gap3 - Left: svg ring 32x32 r13 stroke #E5E5EA 3 + progress stroke #111 dasharray ring*0.82 82 linecap round + center number 10px bold - Right: title 14px semibold -0.01em, prog 12px #8E8E93

### 02 CAMERA - "Frame artwork fully"
Bg: #0A0A0A + radial 100% 100% at 50% 40% #8FA8C8 0% #6B7EA8 25% #4A5A85 55% #1A2333 100% opacity 90% + second radial 70% 60% at 50% 40% #d6e8ff
Top center pt54: "Frame artwork fully" 15px 600 white, "Hold steady • Auto-capture on" 12px white/60
Guide: absolute center w264 h352 - border white/15 rounded 8 - 4 corners w8 h8 border 2.5px white rounded 10px each - center pulse w52 h52 border white/30 animate-pulse + inner dot w2 h2 white rounded-full - on capture scale 4 transition 300ms
Flash: absolute inset 0 bg-white animate flash 0.4s pointer-events-none z30
Bottom: gradient from-black/60 to transparent pb34 pt8 flex-col gap6 items-center - Shutter w72 h72 rounded-full bg-white shadow 0 0 0 4px rgba(255,255,255,0.25) 0 8 24 rgba(0,0,0,0.4) flex center active scale 95 - inner w62 h62 border black/10 - side circles w10 h10 bg white/15 backdrop-blur-xl - label "Monet • 1901 • Likely" 11px tracking 0.14em uppercase white/50

### 03 ARTWORK CARD HERO - Main wow
Container: w-full h-full bg #F5F5F7 flex-col overflow-y-auto scrollbar-none
Image: aspect 4/3 overflow-hidden bg #EDE8E1 - inner gradient 105deg #FFD8A8 0% #FFA98E 18% #7BA7D9 42% #2B4A7A 68% #E8B86D 100% - badge bottom3 right3 px2 py1 rounded-full bg-black/70 text 10px semibold white tracking widest "4:3 • SCAN" - handle -bottom3 center w10 h1 rounded-full bg-black/15
Sheet: bg-white rounded-t 24px -mt-4 z10 flex-1 px5 pt7 pb32
Segment: flex p1 rounded-full bg #F5F5F7 mb5 - buttons ["Normal","Simple","Kids"] flex-1 h7 rounded-full 12px semibold transition-all active bg-black text-white shadow else text #8E8E93
Meta: "CLAUDE MONET" 11px semibold 0.12em uppercase #8E8E93 - Title "Vétheuil, soleil couchant" 22px bold 24px -0.03em #111 - Sub "1901 • Oil on canvas • 73 × 100 cm" 14px #6E6E73 450
Badges mt4 flex gap2: Black badge h7 px3 rounded-full bg-black text-white 12px semibold "€80–120M EST." + info icon opacity 60 - Second h7 px3 rounded-full bg #F5F5F7 13px medium "≈ 1 Boeing 787"
Body mt5: 16px 24px -0.011em #1D1D1F 450 - Normal: "Monet stopped painting the city and started painting the light that changes it every minute." Simple: "Sunset light turns water into gold..." Kids: "Look! The water is sparkly!..."
Eye Block mt5: rounded 16px bg #FFF8E1 border #F5E6B8 p3.5 flex gap3 - Icon w7 h7 rounded-full bg-black text-white center - Text 13.5px 19px -0.01em #5C4D1E 500 "Step back 3 steps. Up close — brushstrokes. From afar — glowing city on water."
Actions mt6 space-y3: Primary w-full h50 rounded-full bg-black white 15px semibold -0.01em shadow 0 8 20 rgba(0,0,0,0.18) active scale 0.98 "Add to my visit" -> "Added ✓" - Second row gap3: "Listen 45s" flex-1 h44 rounded-full bg #F5F5F7 14px semibold + icon button 44x44 bg #F5F5F7

### 04 VISIT PROGRESS - Live Progress
Bg #FAFAF9 pt60 px6 - Label 11px uppercase #8E8E93 "Live Progress" - Grid 2 cols gap6 mt6: €1.34B Value seen / 14 Works / 52m Time / 28% Museum each 28px bold -0.04em + 11px uppercase #8E8E93 - Ring absolute -top2 -right2 w16 h16 svg 32 32 r26 stroke #E5E5EA 4 + progress #111 dasharray 45 163
Divider h1 bg-black/10 mt8
Thumbnails mt6 flex gap3 overflow-x-auto -mx1 px1 pb2: w72 h72 rounded 16 bg #E8E8E8 shrink-0 - active ring2 ring-black offset2 + bottom bar h1 rounded-full bg-black/70
Deep focus card mt6 rounded 20 bg-white border black/0.06 shadow p4 flex justify-between - "Deep focus" 12px uppercase #8E8E93 + "You've spent 4.2 min with Monet" 14px semibold + circle 40px bg #F5F5F7
Bottom sticky p3 pb36: h72 rounded 20 bg-black white flex px5 justify-between shadow 0 16 32 rgba(0,0,0,0.22) - "Next" 11px uppercase opacity60 + "Find one more Monet (2/3) →" 15px semibold

### 05 VISIT RECAP VIRAL
Bg linear 180deg #FFFFFF 0% #F5F5F7 55% #EDEEF2 100% - pt64 pb36 px6 flex-col h-full
Header flex between: "ELYIO • 09.12.2025" 10px bold 0.18em uppercase #8E8E93 + A circle w6 h6 bg-black white 10px bold
Title mt8: "My Musée d'Orsay Visit" 24px bold -0.04em 26px + sub "4.7 km • 3 floors • 87% focused" 13px #6E6E73 medium
Stats mt8 space-y4: border-b black/10 pb4 flex between baseline - label 13px semibold uppercase tracking widest #8E8E93 + value 22px bold -0.03em - Works 37 / Artists 14 / Value €3.8B / Time 2h 14m
Most valuable mt6 flex gap3 p3 rounded 14 bg-white border black/5 shadow-sm - thumb w12 h12 rounded 10 bg #FFD8A8 - label 11px uppercase #8E8E93 + "Monet • €120M EST." 13px semibold
Bottom mt-auto space-y3: Billion badge w-fit px3.5 py2 rounded-full bg #FF3B30 white 12px bold tracking-wide shadow 0 8 20 rgba(255,59,48,0.35) flex gap1.5 - dot w1.5 h1.5 bg-white rounded-full animate-pulse + "BILLION EURO VISITOR" - Button w-full h52 rounded-full bg-black white 15px semibold shadow - "Share your visit ↗" - Footer "elyio.co / v" 11px #8E8E93 center

## COMPONENT SPECS FOR FIGMA
- Price Badge: black pill €80–120M EST. as StockX tag, tap (i) opens bottom-sheet disclaimer
- Eye Block: #FFF8E1 #F5E6B8 - returns eye to painting
- Mission Rings: Apple Fitness style, 3 rings Monet / €100M+ / new artist
- Billion Badge: #FF3B30 only color on B/W recap, confetti on first billion
- iPhone Frame: Om component - 390px max, aspect 390/852, min-h 640px, outer rounded 54px bg-black p10px shadow 50px 100px, inner rounded 44px overflow-hidden, notch 96x28 bg-black rounded-b 16px + speaker 56x6 #1a1a1a opacity60, home indicator 128x5 bg-white rounded-full mix-blend-difference opacity80

Build responsive landing with sticky nav - backdrop-blur 20px bg #FAFAF9/80 border-b black/0.06 - 5 sections each with label + note - hover lift -translate-y-2 shadow increase - scroll-spy IntersectionObserver rootMargin -40% 0 -55% 0

## BRAND UPDATE - MUST USE ELYIO.CO
- Everywhere where was AURA, use ELYIO
- Logo: letter E in circle w-6 h-6 bg-black white 10px bold
- Header: ELYIO • 09.12.2025
- Footer: elyio.co / v
- Hero badge: E + ELYIO — POINT. DISCOVER. UNDERSTAND.
- Domain mentions: elyio.co not aura.museum
- Keep all design tokens identical: #FAFAF9, #111111, #000000, #F5F5F7, #FF3B30, #FFF8E1
- Keep all 5 screens behavior

Build exactly as spec. Do not invent new colors.
