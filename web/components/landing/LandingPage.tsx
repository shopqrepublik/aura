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
  ["Musée du Louvre", "12,000+ works • Paintings, sculptures, antiquities", "Live • 12k works"],
  ["Musée d'Orsay", "Impressionism to Post-Impressionism", "Live"],
  ["Musée de l'Orangerie", "Monet Water Lilies & early modern masters", "Live"],
  ["Musée Carnavalet", "History of Paris", "Guide"],
  ["Musée de Cluny", "Medieval art & artifacts", ""],
  ["Musée de l'Armée", "Military history at Les Invalides", ""],
  ["Musée du quai Branly", "Non-Western arts & cultures", ""],
  ["Musée Guimet", "Asian art collection", ""],
  ["Musée Picasso", "Picasso life and work", ""],
  ["Musée Rodin", "Sculpture garden & studio", ""],
  ["Petit Palais", "Fine arts from antiquity to 1920s", ""],
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
          <Link className="landing-button landing-header-button" href={visitHref}>Begin your visit</Link>
        </nav>
      </header>

      <main>
        <section className="landing-hero landing-container">
          <div className="landing-hero-copy">
            <p className="landing-eyebrow">A different way to see the museum</p>
            <h1>See a painting.<br />Scan it.<br />Understand it.</h1>
            <p className="landing-lede">Your AI companion for the world&apos;s museums. Point your camera at an artwork. ELYIO recognizes it, explains it, and gives you the story worth knowing — what it is, why it matters, and where to look next.</p>
            <div className="landing-actions">
              <Link className="landing-button" href={visitHref}>Begin your visit</Link>
              <Link className="landing-text-link" href={guidesHref}>Explore museum guides →</Link>
            </div>
            <p className="landing-live">Live at Louvre, Musée d&apos;Orsay, Orangerie • London coming next</p>
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
            <article><small><i className="green" /> VERIFIED CATALOG</small><h3>Exact match, curated story</h3><ul><li>Louvre (12k+ works) — paintings, sculptures, objects</li><li>Musée d&apos;Orsay, Orangerie — recognition + AI fallback</li><li>Visual clues, not just text — where to look in the frame</li></ul><span className="landing-pill green-pill">● Curated by ELYIO</span></article>
            <article><small><i className="gold" /> AI INSIGHT — FALLBACK</small><h3>Helpful even when not in catalog</h3><p>If the work isn&apos;t yet in the verified catalog, ELYIO still explains what you see: period, technique, likely subject, why it might matter. Clearly labeled, never pretending to be catalog.</p><div className="landing-note">Your scans of unknown works help ELYIO understand which pieces to add next. No data sold, no gallery push.</div></article>
          </div>
        </section>

        <section className="landing-usage landing-container" aria-labelledby="landing-usage-title">
          <div className="landing-usage-intro">
            <div>
              <p className="landing-eyebrow">A growing geography of visits</p>
              <h2 id="landing-usage-title">From the Louvre to The Met.<br />ELYIO is already being used around the world.</h2>
            </div>
            <p>Visitors are already pointing ELYIO at art in some of the world&#8217;s great museums — from Paris and London to New York, Amsterdam and Vienna.</p>
          </div>
          <div className="landing-usage-stats" aria-label="17 museums, 14 cities, 8 countries">
            <div><strong>17</strong><span>MUSEUMS</span></div><div><strong>14</strong><span>CITIES</span></div><div><strong>8</strong><span>COUNTRIES</span></div>
          </div>
          <div className="landing-usage-primary">{usagePrimary.map(([number, city, names]) => <article key={city}><div className="landing-usage-city"><span>{number}</span><b>{city}</b></div><ul>{names.map(name => <li key={name}>{name}</li>)}</ul></article>)}</div>
          <div className="landing-usage-secondary">{usageSecondary.map(([city, name]) => <div key={city}><small>{city}</small><span>{name}</span></div>)}</div>
          <div className="landing-usage-note"><p>These aren&#8217;t integrations. They&#8217;re museums where visitors have already explored with ELYIO.</p><small>ELYIO is an independent visitor product and is not affiliated with or endorsed by the museums listed.</small></div>
        </section>

        <section className="landing-coverage">
          <div className="landing-container">
            <div className="landing-coverage-heading"><h2>Curated when we know.<br />Useful wherever you go.</h2><p>Curated museum knowledge is one layer of ELYIO. Where a guide is available, start with the collection; everywhere else, AI keeps the visit useful and clearly labeled.</p></div>
            <div className="landing-city-heading"><b>PARIS</b><span>Live now • 3 verified catalogs, 8 guides</span></div>
            <div className="landing-museum-grid">{museums.map(([name,body,badge]) => <article key={name}><small>PARIS • MUSÉE</small><h3>{name}</h3><p>{body}</p>{badge && <span className={badge.startsWith("Live") ? "live" : "guide"}>{badge}</span>}</article>)}</div>
            <div className="landing-city-heading london"><b>LONDON</b><span>Guide coverage where available</span></div>
            <article className="landing-london-card"><small>LONDON • NATIONAL GALLERY</small><h3>National Gallery, London</h3><p>Curated guide layer alongside ELYIO&apos;s AI fallback.</p></article>
          </div>
        </section>

        <section className="landing-final">
          <div className="landing-container landing-final-inner">
            <div><h2>ELYIO</h2><p>Take ELYIO to your next museum. Point your camera at an artwork and start exploring — with a catalog match when we have one, and AI context when we don&apos;t.</p></div>
            <div><Link className="landing-final-button" href={visitHref}>Begin your visit</Link><Link href={guidesHref}>See all museums →</Link></div>
          </div>
          <div className="landing-container landing-final-meta"><span>© 2026 ELYIO • Premium cultural companion</span><span>Catalog when we know. AI when we don&apos;t.</span></div>
        </section>
      </main>

      <footer className="landing-footer landing-container"><span>© 2026 ELYIO</span><nav><a href="#">Privacy</a><a href="#">Instagram</a></nav><p>Every museum becomes understandable the moment you walk in.</p></footer>
    </div>
  );
}
