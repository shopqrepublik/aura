import Image from "next/image";
import Link from "@/components/seo/SeoLink";
import type { SeoLocale } from "@/lib/seo-content";

const steps = [
  ["01", "Enter museum", "Open ELYIO, pick your museum. No tickets inside the app, just context."],
  ["02", "Point camera", "No numbers, no searching. Frame the work and let ELYIO look."],
  ["03", "Recognize instantly", "Catalog when we know. AI when we don't. Always labeled clearly."],
  ["04", "Understand story", "Context, details, value, and where to look next. Scan again."],
] as const;

const features = [
  ["◐", "Instant recognition", "0.8s median on verified catalog. No typing, no hunting for numbers."],
  ["✦", "Concise human stories", "Two paragraphs, one detail to remember, one place to look next."],
  ["◎", "Value & cultural scale", "Where responsible, ELYIO translates price into lived scale — without pretending everything is for sale."],
] as const;

const museums = [
  ["Musée Carnavalet", "History of Paris"],
  ["Musée de Cluny", "Medieval art and artifacts"],
  ["Musée de l'Armée", "Military history at Les Invalides"],
  ["Musée du quai Branly — Jacques Chirac", "Non-Western arts and cultures"],
  ["Musée Guimet", "Asian art collection"],
  ["Musée Picasso Paris", "Picasso's life and work"],
  ["Musée Rodin", "Sculpture garden and studio"],
  ["Petit Palais", "Fine arts from antiquity to the 1920s"],
] as const;

const usagePrimary = [
  ["01", "PARIS", ["Musée du Louvre", "Musée d'Orsay", "Musée de l'Orangerie"]],
  ["02", "LONDON", ["National Gallery", "Victoria and Albert Museum"]],
  ["03", "NEW YORK", ["The Metropolitan Museum of Art"]],
  ["04", "AMSTERDAM", ["Rijksmuseum"]],
  ["05", "VIENNA", ["Kunsthistorisches Museum"]],
  ["06", "LOS ANGELES", ["Getty"]],
] as const;

const usageSecondary = [
  ["BERLIN", "Gemäldegalerie, Staatliche Museen zu Berlin"],
  ["MUNICH", "Alte Pinakothek"],
  ["COPENHAGEN", "SMK — Statens Museum for Kunst"],
  ["STOCKHOLM", "Nordiska Museet"],
  ["PRINCETON", "Princeton University Art Museum"],
  ["CLEVELAND", "Cleveland Museum of Art"],
  ["WASHINGTON", "National Gallery of Art"],
  ["NEW HAVEN", "Yale University Art Gallery"],
] as const;

const usageIndex: ReadonlyArray<readonly [string, string, readonly string[]]> = [
  ...usagePrimary,
  ...usageSecondary.map(([city, name], index) => [String(index + 7).padStart(2, "0"), city, [name]] as const),
];

function PhoneResult({ floating = false }: { floating?: boolean }) {
  return (
    <div className={`landing-phone ${floating ? "landing-phone-floating" : ""}`} aria-label="Example ELYIO artwork result">
      <div className="landing-phone-island" />
      <div className="landing-phone-image">
        <div className="landing-result-location">Eugène Delacroix, 1830<br /><span>Musée du Louvre — Denon, 1st floor</span></div>
      </div>
      <div className="landing-tabs"><b>STORY</b><span>DETAILS</span><span>VALUE</span></div>
      <h3>La Liberté guidant le peuple</h3>
      <p>Painted weeks after the July Revolution, Delacroix turns a street uprising into an allegory that still circulates on stamps, murals, and protest banners.</p>
      <p className="landing-why"><span>✦</span> <b>Why it matters:</b> Not Liberty as a woman, but Liberty as action — forward, barefoot, leading.</p>
      <div className="landing-value-card">
        <small>BEYOND THE MARKET <i>Not for sale</i></small>
        <b>If sold: €400–600M estimate</b>
        <span>🏠 &nbsp;~45 apartments in Paris (75m²)</span>
        <span>🏎️ &nbsp;~1,200 supercars</span>
        <span>🚀 &nbsp;~3 space flights</span>
      </div>
      <div className="landing-scan-again">Scan another artwork</div>
    </div>
  );
}

export default function LandingPage({ locale }: { locale: SeoLocale }) {
  const visitHref = `/visit?from=organic&locale=${locale}&landing=home`;
  const guidesHref = `/${locale}/museums`;
  return (
    <div className="landing-page">
      <header className="landing-header">
        <Link className="landing-logo" href={`/${locale}`}>ELYIO</Link>
        <nav aria-label="Main navigation">
          <Link className="landing-museums-link" href={guidesHref}>Museums</Link>
          <div className="landing-languages" aria-label="Language">
            <Link href="/en" aria-current={locale === "en" ? "page" : undefined}>English</Link>
            <Link href="/fr" aria-current={locale === "fr" ? "page" : undefined}>Français</Link>
            <Link href="/zh-hans" aria-current={locale === "zh-hans" ? "page" : undefined}>简体中文</Link>
          </div>
          <Link className="landing-button landing-header-button" href={visitHref} data-ga-begin-visit="landing_header">Begin your visit</Link>
        </nav>
      </header>

      <main>
        <section className="landing-hero landing-container">
          <div className="landing-hero-copy">
            <p className="landing-eyebrow">A different way to see the museum</p>
            <h1>See a painting.<br />Scan it.<br />Understand it.</h1>
            <p className="landing-lede">Your AI companion for the world&apos;s museums. Point your camera at an artwork. ELYIO recognizes it, explains it, and gives you the story worth knowing — what it is, why it matters, and where to look next.</p>
            <div className="landing-actions">
              <Link className="landing-button" href={visitHref} data-ga-begin-visit="landing_hero">Begin your visit</Link>
              <Link className="landing-text-link" href={guidesHref}>Explore museum guides →</Link>
            </div>
            <p className="landing-live">Live in Paris • Visitors exploring museums worldwide</p>
          </div>
          <div className="landing-hero-visual">
            <Image src="/landing/elyio-museum-visitor.webp" alt="A visitor using ELYIO in a museum" fill priority sizes="(max-width: 900px) 100vw, 520px" />
            <div className="landing-scan-corners" aria-hidden="true"><span /><span /><span /><span /><i /></div>
            <div className="landing-mini-result">
              <small><i /> CATALOG • VERIFIED</small>
              <h3>La Liberté guidant le peuple</h3>
              <b>Eugène Delacroix — 1830, Louvre RF 129</b>
              <p>A woman steps over barricades, flag raised. Not a portrait, but an idea of revolution made visible.</p>
              <p>✦ <b>Why it matters:</b> The image that taught the world what liberty looks like.</p>
              <div>BEYOND THE MARKET <b>≈ 1.8 private jets</b></div>
            </div>
          </div>
        </section>

        <div className="landing-context-strip">
          <div className="landing-container">
            <p>Every museum becomes understandable the moment you walk in.</p>
            <div><span>COUNTRY</span> → <span>CITY</span> → <b>MUSEUM</b> → <span>COLLECTION</span> → <span>ARTWORK</span></div>
          </div>
        </div>

        <section className="landing-proof-strip landing-container" aria-label="ELYIO visitor usage">
          <div>
            <p className="landing-eyebrow">Already explored with ELYIO</p>
            <p className="landing-proof-museums landing-proof-desktop">Louvre <span>·</span> The Met <span>·</span> Rijksmuseum <span>·</span> National Gallery <span>·</span> Musée d&apos;Orsay <span>·</span> Getty <span>·</span> KHM <span>·</span> Alte Pinakothek <span>· +9</span></p>
            <p className="landing-proof-museums landing-proof-mobile">Louvre <span>·</span> The Met <span>·</span> Rijksmuseum <span>·</span> National Gallery <span>· +13</span></p>
          </div>
          <div className="landing-proof-stats"><b>17 <small>MUSEUMS</small></b><b>14 <small>CITIES</small></b><b>8 <small>COUNTRIES</small></b></div>
        </section>

        <section className="landing-steps landing-container">
          <h2>Enter. Point. Recognize. Discover.</h2>
          <div className="landing-step-grid">{steps.map(([number,title,body]) => <article key={number}><strong>{number}</strong><h3>{title}</h3><p>{body}</p></article>)}</div>
        </section>

        <section className="landing-experience landing-container">
          <div className="landing-experience-phone"><PhoneResult /></div>
          <div className="landing-experience-copy">
            <h2>Understand,<br />don&apos;t just identify.</h2>
            <p>Most guides tell you what it&apos;s called. ELYIO tells you why it&apos;s here, what to notice in 20 seconds, and how it connects to the next room — without turning a museum into a database.</p>
            <div className="landing-feature-list">{features.map(([icon,title,body]) => <article key={title}><span>{icon}</span><div><h3>{title}</h3><p>{body}</p></div></article>)}</div>
            <small>POINT YOUR CAMERA AT ART ONCE YOU ARE INSIDE A SUPPORTED MUSEUM.</small>
          </div>
        </section>

        <section className="landing-hybrid landing-container">
          <h2>Catalog when we know.<br />AI when we don&apos;t.</h2>
          <p>A hybrid system designed to never leave you without context. Verified when possible, helpful when not — always transparent about which it is.</p>
          <div className="landing-hybrid-grid">
            <article><small><i className="green" /> VERIFIED CATALOG</small><h3>Exact match, curated story</h3><ul><li>Louvre — curated painting, sculpture and object coverage</li><li>Musée d&apos;Orsay, Orangerie — recognition + AI fallback</li><li>Visual clues, not just text — where to look in the frame</li></ul><span className="landing-pill green-pill">● Curated by ELYIO</span></article>
            <article><small><i className="gold" /> AI INSIGHT — FALLBACK</small><h3>Helpful even when not in catalog</h3><p>If the work isn&apos;t yet in the verified catalog, ELYIO still explains what you see: period, technique, likely subject, why it might matter. Clearly labeled, never pretending to be catalog.</p><div className="landing-note">Your scans of unknown works help ELYIO understand which pieces to add next. No data sold, no gallery push.</div></article>
          </div>
        </section>

        <section className="landing-coverage">
          <div className="landing-container">
            <div className="landing-coverage-ticker"><span>Already explored with ELYIO</span><p>Louvre <i>·</i> The Met <i>·</i> Rijksmuseum <i>·</i> National Gallery <i>·</i> Orsay <i>·</i> Getty <i>·</i> KHM <i>·</i> Alte Pinakothek <em>· +9</em></p></div>
            <div className="landing-coverage-heading"><div><p className="landing-eyebrow">Museum coverage</p><h2>Curated where we know.<br />Useful wherever you go.</h2></div><p>ELYIO combines a growing catalog of museum knowledge with AI that stays useful beyond it.</p></div>
            <div className="landing-curated-label"><b>CURATED COVERAGE</b><span>3 LIVE IN PARIS · LONDON IN TESTING</span></div>
            <div className="landing-curated-primary">
              <article><small>01 · PARIS</small><h3>Musée du Louvre</h3><span>LIVE</span><p>Curated catalog</p></article>
              <article><small>02 · PARIS</small><h3>Musée d&apos;Orsay</h3><span>LIVE</span><p>Curated catalog</p></article>
              <article><small>03 · PARIS</small><h3>Musée de l&apos;Orangerie</h3><span>LIVE</span><p>Curated catalog</p></article>
              <article className="testing"><small>04 · LONDON</small><h3>National Gallery</h3><span>IN TESTING</span><p>Guide + AI fallback</p></article>
            </div>
            <div className="landing-paris-index"><p className="landing-index-label">More Paris guides</p><div>{museums.map(([name,body]) => <article key={name}><h3>{name}</h3><span>{body}</span></article>)}</div></div>
            <div className="landing-global-index"><div className="landing-global-heading"><p className="landing-index-label">Also explored · beyond curated</p><div className="landing-usage-stats"><b>17 <small>MUSEUMS</small></b><b>14 <small>CITIES</small></b><b>8 <small>COUNTRIES</small></b></div><p>Usage footprint reflects museums where visitors have already used ELYIO. Curated catalog status is shown separately.</p></div><div className="landing-city-index">{usageIndex.map(([number,city,names]) => <article key={city}><b>{number} · {city}</b><span>{names.join(" · ")}</span></article>)}</div></div>
            <div className="landing-usage-note"><p>These aren&apos;t integrations. They&apos;re museums where visitors have already explored with ELYIO.</p><small>ELYIO is an independent visitor product and is not affiliated with or endorsed by the museums listed.</small></div>
          </div>
        </section>

        <section className="landing-final">
          <div className="landing-container landing-final-inner">
            <div><h2>ELYIO</h2><p>Take ELYIO to your next museum. Point your camera at an artwork and start exploring — with a catalog match when we have one, and AI context when we don&apos;t.</p></div>
            <div><Link className="landing-final-button" href={visitHref} data-ga-begin-visit="landing_footer">Begin your visit</Link><Link href={guidesHref}>See all museums →</Link></div>
          </div>
          <div className="landing-container landing-final-meta"><span>© 2026 ELYIO • Premium cultural companion</span><span>Catalog when we know. AI when we don&apos;t.</span></div>
        </section>
      </main>

      <footer className="landing-footer landing-container"><span>© 2026 ELYIO</span><nav><a href="#">Privacy</a><a href="#">Instagram</a></nav><p>Every museum becomes understandable the moment you walk in.</p></footer>
    </div>
  );
}
