# ELYIO Museum Image Audit — Real Artwork Imagery Pass

**Baseline:** `bba30d2`  
**Generated:** 2026-09-07  
**Registry:** `web/lib/data/museums-v1.json` (fields `imageLocal`, `imageCommonsUrl`, `imageLicense`, `imageAttribution`, `imageWidth/Height`, `imageConfidence`) + local assets under `web/public/images/museums/{slug}/`  
**Rule enforced:** every Masterpiece Story ships a real, rights-verified artwork/object image. No beige placeholders, no NEEDS_VERIFICATION UI, no unverified rights.

## Method

1. Every pre-existing `imageCommonsUrl` was liveness-checked (Wikimedia returned HTTP 429 rate-limit under bulk probing, so each URL was additionally resolved through the Commons API `imageinfo` — all 63 files resolve with license metadata — and every file was downloaded and magic-byte verified).
2. The 23 stories with no image were researched via the Commons API (file search + `imageinfo` dimensions/license). 19 were matched to verified files of the same artwork; 4 stories with no legally usable image were removed (see Replaced/Dropped).
3. Web-resolution copies (1280px wide via MediaWiki thumbnail service, JPEG) are vendored locally. Originals remain referenced as provenance in `imageCommonsUrl`.
4. CC BY-SA images carry an `imageAttribution` caption rendered under the artwork. Public-domain and CC0 images require no attribution.
5. Runtime safety: `MuseumMasterpieceImage` removes the media block and reflows text if a local file ever fails (emergency behavior only).

## Dropped stories (no legally usable image found)

| Museum | Story | Reason |
|---|---|---|
| Musée de l'Orangerie | The Groom (Soutine) | No verifiable Commons image of this work; collection membership of a Soutine "groom" could not be confirmed — removed rather than illustrate with the wrong painting. Orangerie keeps 3 image-backed stories. |
| National Gallery of Art, Washington | Untitled (Mobile) (Calder) | Calder (d. 1976) — no freely-licensed photograph of the NGA mobile found; removed. NGA keeps 3 image-backed stories. |
| Nordiska museet | The 1940s Flat, Frozen at Home | Period-room installation with no freely-licensed image found; removed. Nordiska keeps 3 image-backed stories. |
| Yale University Art Gallery | Equestrian Shrine Figure (Priestess of Ọya) | No freely-licensed image of this specific work found; removed rather than substitute a different culture's object. Yale keeps 3 image-backed stories. |

## Per-museum report

### Musée du Louvre (`musee-du-louvre`, PRODUCTION_CATALOG)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Mona Lisa | Leonardo da Vinci | `/images/museums/musee-du-louvre/01-mona-lisa.jpg` | Mona_Lisa.jpg | Public domain | none required | PASS |
| Winged Victory of Samothrace | Unknown | `/images/museums/musee-du-louvre/02-winged-victory-of-samothrace.jpg` | Wing_victory_Samothrace_Louvre_Ma2369.jpg | Public domain | none required | PASS |
| Venus de Milo | Unknown | `/images/museums/musee-du-louvre/03-venus-de-milo.jpg` | Venus_de_Milo_Louvre_Ma399_n4.jpg | Public domain | none required | PASS |
| Liberty Leading the People | Eugène Delacroix | `/images/museums/musee-du-louvre/04-liberty-leading-the-people.jpg` | Eug%C3%A8ne_Delacroix_-_La_libert%C3%A9_guid | Public domain | none required | PASS |

### Musée d'Orsay (`musee-d-orsay`, PRODUCTION_CATALOG)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Starry Night Over the Rhône | Vincent van Gogh | `/images/museums/musee-d-orsay/01-starry-night-over-the-rhone.jpg` | Starry_Night_Over_the_Rhone.jpg | Public domain | none required | PASS |
| Olympia | Édouard Manet | `/images/museums/musee-d-orsay/02-olympia.jpg` | Edouard_Manet_-_Olympia_-_Google_Art_Project | Public domain | none required | PASS |
| Little Dancer of Fourteen Years (Petite danseuse de quatorze ans) | Edgar Degas | `/images/museums/musee-d-orsay/03-little-dancer-of-fourteen-years-petite-danseuse-.jpg` | La_petite_danseuse_de_quatorze_ans_-_Degas_- | CC BY-SA 4.0 | required, captioned | PASS |
| Bal du moulin de la Galette | Pierre-Auguste Renoir | `/images/museums/musee-d-orsay/04-bal-du-moulin-de-la-galette.jpg` | Pierre-Auguste_Renoir_-_Bal_du_moulin_de_la_ | Public domain | none required | PASS |

### Musée de l'Orangerie (`musee-de-l-orangerie`, PRODUCTION_CATALOG)

MASTERPIECE STORIES: 3 — REAL IMAGES: 3 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Water Lilies – The Clouds | Claude Monet | `/images/museums/musee-de-l-orangerie/01-water-lilies-the-clouds.jpg` | Claude_Monet_-_The_Water_Lilies_-_The_Clouds | Public domain | none required | PASS |
| Paul Guillaume, Novo Pilota | Amedeo Modigliani | `/images/museums/musee-de-l-orangerie/02-paul-guillaume-novo-pilota.jpg` | Amedeo_Modigliani_-_Paul_Guillaume%2C_Novo_P | Public domain | none required | PASS |
| Father Junier's Cart | Henri Rousseau | `/images/museums/musee-de-l-orangerie/03-father-junier-s-cart.jpg` | Henri_Rousseau%2C_dit_le_Douanier_-_La_Carri | Public domain | none required | PASS |

### The National Gallery (`national-gallery-london`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 3 — REAL IMAGES: 3 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Arnolfini Portrait | Jan van Eyck | `/images/museums/national-gallery-london/01-the-arnolfini-portrait.jpg` | Van_Eyck_-_Arnolfini_Portrait.jpg | Public domain | none required | PASS |
| The Fighting Temeraire | J.M.W. Turner | `/images/museums/national-gallery-london/02-the-fighting-temeraire.jpg` | The_Fighting_Temeraire%2C_JMW_Turner%2C_Nati | Public domain | none required | PASS |
| Sunflowers | Vincent van Gogh | `/images/museums/national-gallery-london/03-sunflowers.jpg` | Vincent_Willem_van_Gogh_127.jpg | Public domain | none required | PASS |

### Victoria and Albert Museum (`va-london`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Ardabil Carpet | Maqsud of Kashan (attributed) | `/images/museums/va-london/01-the-ardabil-carpet.jpg` | The_Ardabil_Carpet_-_Google_Art_Project.jpg | Public domain | none required | PASS |
| Tipu's Tiger | Mysore court workshop, for Tipu Sultan | `/images/museums/va-london/04-tipu-s-tiger.jpg` | Tipu%27s_Tiger_front_view_2006AH4173.jpg | CC BY-SA 3.0 | required, captioned | PASS |
| The Cast of Michelangelo's David | After Michelangelo | `/images/museums/va-london/03-the-cast-of-michelangelo-s-david.jpg` | Plaster_cast_of_David_in_the_V%26A%27s_Cast_ | CC BY-SA 4.0 | required, captioned | PASS |
| The Raphael Cartoons | Raphael | `/images/museums/va-london/04-the-raphael-cartoons.jpg` | Raphael_-_The_Miraculous_Draft_of_Fishes_-_G | Public domain | none required | PASS |

### The Metropolitan Museum of Art (`the-met`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Washington Crossing the Delaware | Emanuel Leutze | `/images/museums/the-met/01-washington-crossing-the-delaware.jpg` | Washington_Crossing_the_Delaware_by_Emanuel_ | Public domain | none required | PASS |
| Temple of Dendur | Ancient Egyptian, Roman period | `/images/museums/the-met/02-temple-of-dendur.jpg` | The_Temple_of_Dendur_MET_DP240336.jpg | CC0 | none required | PASS |
| Madame X | John Singer Sargent | `/images/museums/the-met/03-madame-x.jpg` | Sargent_MadameX.jpeg | Public domain | none required | PASS |
| Wheat Field with Cypresses | Vincent van Gogh | `/images/museums/the-met/04-wheat-field-with-cypresses.jpg` | Wheat-Field-with-Cypresses-%281889%29-Vincen | Public domain | none required | PASS |

### Rijksmuseum (`rijksmuseum`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Night Watch | Rembrandt van Rijn | `/images/museums/rijksmuseum/01-the-night-watch.jpg` | The_Night_Watch_-_HD.jpg | Public domain | none required | PASS |
| The Milkmaid | Johannes Vermeer | `/images/museums/rijksmuseum/02-the-milkmaid.jpg` | Johannes_Vermeer_-_Het_melkmeisje_-_Google_A | Public domain | none required | PASS |
| Woman Reading a Letter | Johannes Vermeer | `/images/museums/rijksmuseum/03-woman-reading-a-letter.jpg` | Vermeer%2C_Johannes_-_Woman_reading_a_letter | Public domain | none required | PASS |
| The Jewish Bride | Rembrandt van Rijn | `/images/museums/rijksmuseum/04-the-jewish-bride.jpg` | Rembrandt_Harmensz._van_Rijn_-_Portret_van_e | Public domain | none required | PASS |

### Kunsthistorisches Museum Vienna (`khm-vienna`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Hunters in the Snow | Pieter Bruegel the Elder | `/images/museums/khm-vienna/01-the-hunters-in-the-snow.jpg` | Pieter_Bruegel_the_Elder_-_Hunters_in_the_Sn | Public domain | none required | PASS |
| The Tower of Babel | Pieter Bruegel the Elder | `/images/museums/khm-vienna/02-the-tower-of-babel.jpg` | Pieter_Bruegel_the_Elder_-_The_Tower_of_Babe | Public domain | none required | PASS |
| The Saliera | Benvenuto Cellini | `/images/museums/khm-vienna/03-the-saliera.jpg` | Saliera_Cellini_Vienna_18_04_2013_01_B.jpg | CC0 | none required | PASS |
| The Art of Painting | Johannes Vermeer | `/images/museums/khm-vienna/04-the-art-of-painting.jpg` | Jan_Vermeer_-_The_Art_of_Painting_-_Google_A | Public domain | none required | PASS |

### Statens Museum for Kunst (SMK) (`smk-copenhagen`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Russian Ship of the Line 'Assow' and a Frigate at Anchor in the Roads of Elsinore | Christoffer Wilhelm Eckersberg | `/images/museums/smk-copenhagen/01-the-russian-ship-of-the-line-assow-and-a-frigate.jpg` | Det_russiske_linieskib_%22Assow%22_og_en_fre | Public domain | none required | PASS |
| View of a Street in Østerbro outside Copenhagen, Morning Light | Christen Købke | `/images/museums/smk-copenhagen/02-view-of-a-street-in-sterbro-outside-copenhagen-m.jpg` | Christen_K%C3%B8bke_-_View_of_a_Street_in_%C | Public domain | none required | PASS |
| Artemis | Vilhelm Hammershøi | `/images/museums/smk-copenhagen/03-artemis.jpg` | Artemis.jpg | Public domain | none required | PASS |
| Portrait of Madame Matisse (The Green Line) | Henri Matisse | `/images/museums/smk-copenhagen/04-portrait-of-madame-matisse-the-green-line.jpg` | Matisse_-_Green_Line.jpeg | Public domain | none required | PASS |

### Nordiska museet (`nordiska-museet`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 3 — REAL IMAGES: 3 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Gustav Vasa, Carved King of the Entrance Hall | Carl Milles (sculptor) | `/images/museums/nordiska-museet/01-gustav-vasa-carved-king-of-the-entrance-hall.jpg` | Stockholm-Nordiska_museet_DSC6416.jpg | CC BY-SA 4.0 | required, captioned | PASS |
| Bridal Crowns and Folk Dress | Swedish folk costume & textile collection | `/images/museums/nordiska-museet/02-bridal-crowns-and-folk-dress.jpg` | Bridal_crown%2C_worn_in_Ostergotland%2C_17th | CC0 | none required | PASS |
| Sámi Life and the Arctic Collection | Sámi cultural heritage collection | `/images/museums/nordiska-museet/03-sami-life-and-the-arctic-collection.jpg` | Knives%2C_Sami_-_Nordiska_museet_-_Stockholm | CC0 | none required | PASS |

### Princeton University Art Museum (`princeton`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Mosaic Pavement: Drinking Contest of Herakles and Dionysos | Roman, Antioch | `/images/museums/princeton/01-mosaic-pavement-drinking-contest-of-herakles-and.jpg` | Mosaic_pavement_drinking_contest_of_Herakles | Public domain | none required | PASS |
| The Steerage | Alfred Stieglitz | `/images/museums/princeton/02-the-steerage.jpg` | Alfred_Stieglitz_-_The_Steerage_-_Google_Art | Public domain | none required | PASS |
| At the Window | Winslow Homer | `/images/museums/princeton/03-at-the-window.jpg` | Winslow_Homer_-_At_the_Window_-_Google_Art_P | Public domain | none required | PASS |
| Elkanah Watson | John Singleton Copley | `/images/museums/princeton/04-elkanah-watson.jpg` | Elkanah_Watson_1782_John_Singleton_Copley.jp | Public domain | none required | PASS |

### Cleveland Museum of Art (`cleveland`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Thinker | Auguste Rodin | `/images/museums/cleveland/01-the-thinker.jpg` | Cleveland_Museum_of_Art_-_damaged_Thinker.jp | Public domain | none required | PASS |
| The Large Plane Trees (Road Menders at Saint-Rémy) | Vincent van Gogh | `/images/museums/cleveland/02-the-large-plane-trees-road-menders-at-saint-remy.jpg` | The_Large_Plane_Trees_%28Road_Menders_at_Sai | Public domain | none required | PASS |
| The Crucifixion of Saint Andrew | Caravaggio | `/images/museums/cleveland/03-the-crucifixion-of-saint-andrew.jpg` | Caravaggio_-_The_Crucifixion_of_Saint_Andrew | CC0 | none required | PASS |
| Twilight in the Wilderness | Frederic Edwin Church | `/images/museums/cleveland/04-twilight-in-the-wilderness.jpg` | Twilight_in_the_Wilderness_by_Frederic_Edwin | Public domain | none required | PASS |

### National Gallery of Art (`nga-washington`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 3 — REAL IMAGES: 3 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Ginevra de' Benci | Leonardo da Vinci | `/images/museums/nga-washington/01-ginevra-de-benci.jpg` | Leonardo_da_Vinci_-_Ginevra_de%27_Benci_-_Go | Public domain | none required | PASS |
| The Skater (Portrait of William Grant) | Gilbert Stuart | `/images/museums/nga-washington/02-the-skater-portrait-of-william-grant.jpg` | Gilbert_Stuart%2C_The_Skater_%28Portrait_of_ | CC0 | none required | PASS |
| Woman Holding a Balance | Johannes Vermeer | `/images/museums/nga-washington/03-woman-holding-a-balance.jpg` | Johannes_Vermeer%2C_Woman_Holding_a_Balance% | CC0 | none required | PASS |

### J. Paul Getty Museum (`getty`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Irises | Vincent van Gogh | `/images/museums/getty/01-irises.jpg` | VanGogh-Irises_1.jpg | Public domain | none required | PASS |
| Portrait of a Halberdier | Pontormo | `/images/museums/getty/02-portrait-of-a-halberdier.jpg` | Pontormo_%28Jacopo_Carucci%29_%28Italian%2C_ | Public domain | none required | PASS |
| Arii Matamoe (The Royal End) | Paul Gauguin | `/images/museums/getty/03-arii-matamoe-the-royal-end.jpg` | Paul_Gauguin_%28French_-_Arii_Matamoe_%28The | Public domain | none required | PASS |
| Rembrandt Laughing | Rembrandt | `/images/museums/getty/04-rembrandt-laughing.jpg` | Rembrandt_laughing.jpg | Public domain | none required | PASS |

### Gemäldegalerie Berlin (`gemaldegalerie-berlin`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Wine Glass | Johannes Vermeer | `/images/museums/gemaldegalerie-berlin/01-the-wine-glass.jpg` | Jan_Vermeer_van_Delft_-_The_Glass_of_Wine_-_ | Public domain | none required | PASS |
| Netherlandish Proverbs | Pieter Bruegel the Elder | `/images/museums/gemaldegalerie-berlin/02-netherlandish-proverbs.jpg` | Pieter_Brueghel_the_Elder_-_The_Dutch_Prover | Public domain | none required | PASS |
| Portrait of Hieronymus Holzschuher | Albrecht Dürer | `/images/museums/gemaldegalerie-berlin/03-portrait-of-hieronymus-holzschuher.jpg` | D%C3%BCrer_-_Hieronymus_Holzschuher_%281469- | Public domain | none required | PASS |
| Joseph's Dream | Rembrandt | `/images/museums/gemaldegalerie-berlin/04-joseph-s-dream.jpg` | Rembrandt_van_Rijn_195.jpg | Public domain | none required | PASS |

### Alte Pinakothek (`alte-pinakothek`, CONTROLLED_PREVIEW)

MASTERPIECE STORIES: 4 — REAL IMAGES: 4 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| Self-Portrait in a Fur-Collared Robe | Albrecht Dürer | `/images/museums/alte-pinakothek/01-self-portrait-in-a-fur-collared-robe.jpg` | D%C3%BCrer_Alte_Pinakothek.jpg | Public domain | none required | PASS |
| The Great Last Judgement | Peter Paul Rubens | `/images/museums/alte-pinakothek/04-the-great-last-judgement.jpg` | Peter_Paul_Rubens_-_The_Last_Judgement_-_WGA | Public domain | none required | PASS |
| Madonna of the Carnation (Virgin and Child) | Leonardo da Vinci | `/images/museums/alte-pinakothek/03-madonna-of-the-carnation-virgin-and-child.jpg` | LEONARDO-DA-VINCI_-_MADONNA-MIT-DER-NELKE-77 | Public domain | none required | PASS |
| Lamentation Beneath the Cross | Lucas Cranach the Elder | `/images/museums/alte-pinakothek/04-lamentation-beneath-the-cross.jpg` | Lucas_Cranach_d.%C3%84._-_Klage_unter_dem_Kr | Public domain | none required | PASS |

### Yale University Art Gallery (`yale-new-haven`, NO_INSTITUTION_RECORD)

MASTERPIECE STORIES: 3 — REAL IMAGES: 3 — TEXT-ONLY STORIES: 0

| Artwork | Artist | Local asset | Source | Rights | License | Attribution | Status |
|---|---|---|---|---|---|---|---|
| The Declaration of Independence, July 4, 1776 | John Trumbull | `/images/museums/yale-new-haven/01-the-declaration-of-independence-july-4-1776.jpg` | John_Trumbull_-_The_Declaration_of_Independe | Public domain | none required | PASS |
| Le café de nuit (The Night Café) | Vincent van Gogh | `/images/museums/yale-new-haven/02-le-cafe-de-nuit-the-night-cafe.jpg` | Le_caf%C3%A9_de_nuit_%28The_Night_Caf%C3%A9% | Public domain | none required | PASS |
| Bodhisattva Avalokiteshvara in the Water-Moon Manifestation (Shuiyue Guanyin) | Unknown artist, China | `/images/museums/yale-new-haven/03-bodhisattva-avalokiteshvara-in-the-water-moon-ma.jpg` | Seated_Guanyin_%2811th%E2%80%9312th_century% | CC BY-SA 3.0 | required, captioned | PASS |

## Legacy French museum pages

The 9 legacy pages (Carnavalet, Cluny, Armée, Quai Branly, Guimet, Picasso, Rodin, Petit Palais, Versailles) carry no Masterpiece Stories imagery by design — they link to individual `/artworks/[slug]` pages. No placeholders exist there. Out of scope for image replacement; covered by the artwork-page image pipeline.

## Totals

(See final report for counts.)
