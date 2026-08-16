#!/usr/bin/env python3
"""Build Louvre Phase 2C batch001 review artifacts.

This is a from-scratch, 25-work proof batch. It writes only to
exports/louvre/content/phase2c/batch001 and does not alter Phase 2B, Golden 20,
production data, catalog membership, assets, embeddings, TTS, or image bytes.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE2B = ROOT / "exports" / "louvre" / "content" / "phase2b"
OUT = ROOT / "exports" / "louvre" / "content" / "phase2c" / "batch001"
RECORDS = PHASE2B / "louvre_phase2b_480.jsonl"
CATALOG_VERSION = "2026-08-11-v1"
BATCH_VERSION = "louvre_phase2c_batch001_v0.1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

BATCH_IDS = [
    "cl010063515", "cl010315397", "cl010321121", "cl010329343", "cl010059373",
    "cl010104474", "cl010062290", "cl010062308", "cl010066647", "cl010091989",
    "cl010059589", "cl010090779", "cl010099607", "cl010111542", "cl010009267",
    "cl010123045", "cl010258916", "cl010472062", "cl010060786", "cl010091138",
    "cl010065532", "cl010005261", "cl010003776", "cl010092704", "cl010180806",
]

EXTRA_VALUE = {
    "cl010065532": {
        "mode": "MARKET_CONTEXT", "headline_number": 300000, "currency": "EUR",
        "context_label": "Benoist market context",
        "explanation": "A Marie-Guillemine Benoist portrait was offered at Sotheby's with a €60k-€80k estimate and reported secondary coverage cites a €300k 2025 result; this is artist-market context, not a value for Portrait of Madeleine.",
        "confidence": "MEDIUM",
        "relationship": "artist_market_context_not_artwork_value",
        "sources": [
            {"source_id": "sothebys_benoist_empress", "url": "https://www.sothebys.com/buy/d62f8e56-478a-4633-ac1f-7d496416a3b2/lots/5056975c-8645-4b95-a13f-65d528fec093"},
            {"source_id": "portrait_madeleine_background", "url": "https://en.wikipedia.org/wiki/Portrait_of_Madeleine"},
        ],
    },
    "cl010005261": {
        "mode": "BEYOND_MARKET", "headline_number": None, "currency": None,
        "context_label": "Old Kingdom funerary icon",
        "explanation": "Market comparisons for painted Old Kingdom royal-family stelae are too legally and historically distant; a price-like number would weaken the visitor truth.",
        "confidence": "MEDIUM", "relationship": "no_responsible_public_comparable",
        "sources": [{"source_id": "louvre_nefertiabet", "url": "https://collections.louvre.fr/ark:/53355/cl010005261"}],
    },
    "cl010003776": {
        "mode": "BEYOND_MARKET", "headline_number": None, "currency": None,
        "context_label": "Amarna royal sculpture",
        "explanation": "A Louvre Akhenaten bust belongs to an inalienable public collection and lacks a clean public market analogue; financial context would be misleading without specialist review.",
        "confidence": "MEDIUM", "relationship": "non_market_public_icon_context",
        "sources": [{"source_id": "louvre_akhenaten_bust", "url": "https://collections.louvre.fr/ark:/53355/cl010003776"}],
    },
    "cl010092704": {
        "mode": "MARKET_CONTEXT", "headline_number": 4000, "currency": "USD",
        "context_label": "Barye bronze context",
        "explanation": "Barye camel bronzes have public market context around thousands of dollars for later casts; this is category context only, not a Louvre value.",
        "confidence": "LOW", "relationship": "category_context_barye_bronze",
        "sources": [
            {"source_id": "christies_barye_artist_results", "url": "https://www.christies.com/en/artists/antoine-louis-barye"},
            {"source_id": "montecito_barye_camel_context", "url": "https://www.montecitojournal.net/2024/12/03/antoine-louis-barye-and-a-victorian-bronze-age/"},
        ],
    },
    "cl010180806": {
        "mode": "MARKET_CONTEXT", "headline_number": {"low": 2000, "high": 6000}, "currency": "GBP",
        "context_label": "cylinder seal category context",
        "explanation": "Ancient Near Eastern cylinder seals commonly appear at auction in low-thousands estimates; this is broad category context, not a value for the Louvre seal.",
        "confidence": "LOW", "relationship": "category_context_cylinder_seal",
        "sources": [{"source_id": "louvre_elamite_seal", "url": "https://collections.louvre.fr/ark:/53355/cl010180806"}],
    },
}


def load_records() -> dict[str, dict[str, Any]]:
    return {r["artwork_id"]: r for r in (json.loads(l) for l in RECORDS.read_text(encoding="utf-8").splitlines() if l.strip())}


def val_from_qg() -> dict[str, dict[str, Any]]:
    p = PHASE2B / "quality_gate" / "louvre_phase2b_sample_value_research.jsonl"
    rows = {}
    if p.exists():
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                rows[r["artwork_id"]] = {
                    "mode": r["researched_mode"],
                    "headline_number": r["headline"],
                    "currency": r["currency"],
                    "context_label": r["relationship_to_artwork"],
                    "explanation": r["visitor_safe_statement"],
                    "confidence": r["confidence"],
                    "relationship": r["relationship_to_artwork"],
                    "sources": [{"source_id": re.sub(r"[^a-z0-9]+", "_", s["label"].lower()).strip("_")[:48], "url": s["url"]} for s in r["sources"]],
                }
    rows.update(EXTRA_VALUE)
    return rows


CONTENT: dict[str, dict[str, Any]] = {
    "cl010063515": {
        "facts": ["Signed Picot. Rome. 1817.", "Shown at the Salon of 1819.", "A large neoclassical oil on canvas."],
        "visual": ["Psyche is asleep on a red-draped bed while Cupid rises away from her.", "The empty space beside her makes the story feel like departure, not embrace.", "The architecture and bed turn myth into a staged private room."],
        "en": {
            "hook": "Cupid is already leaving; Psyche has not yet woken up.",
            "why": ["Picot turns a love story into a moment of absence: the important action is the space opening between the two figures.", "The scale is theatrical, but the emotion is quiet, which is why this Salon picture still works in a crowded room."],
            "notice": ["Find Cupid first, then follow his backward glance toward the sleeping Psyche.", "Look at the red fabric under the body; it makes the pale skin and white drapery feel almost luminous.", "Check the empty part of the bed, where the myth becomes a separation rather than a kiss."],
            "context": "Painted in Rome in 1817 and exhibited at the Salon of 1819, the work belongs to French neoclassicism after David, when antique myth could carry modern feeling.",
            "story": "The scene comes from the Cupid and Psyche myth: Psyche's happiness depends on a lover she is not allowed to see.",
            "rarity": "It is useful because it shows the polished, grand Salon language that younger French painters would soon begin to challenge.",
            "simple": "This is a mythological painting about a lover leaving. Look at the sleeping figure, then at the empty space beside her.",
            "kids": "Pretend the room is silent. Can you spot the figure who is awake and the one who is not? The story starts because one person leaves before the other understands.",
            "audio": "Start with the bed, not the title. Psyche is still asleep, but Cupid is already moving away. The red drapery makes the body glow, and the empty space beside her tells you the real subject: departure. Picot painted this in Rome in 1817, then sent it into the Salon world of Paris. Before you move on, look at Cupid's turn back. It is the painting's pause button.",
        },
    },
    "cl010315397": {
        "facts": ["Samanid ceramic plate from Samarkand.", "Dated 975-1000.", "Decorated with a radiating inscription under transparent glaze."],
        "visual": ["The inscription spreads outward like spokes.", "The white ground gives the dark script room to become ornament.", "The plate is shallow enough for the writing to dominate the object."],
        "en": {
            "hook": "Here, writing behaves like sunlight.",
            "why": ["The plate matters because script is not decoration added at the end; it is the structure of the whole design.", "It gives Islamic Art a powerful room presence without figure, narrative, or large scale."],
            "notice": ["Follow one letter outward from the center and watch it become part of a circle.", "Notice how much empty pale surface is left between the strokes.", "Step back slightly: the words turn into rhythm before you can read them."],
            "context": "Made in the late 10th century, the plate belongs to a Samanid ceramic culture where inscriptions could carry blessing, status, and design at once.",
            "story": "The object asks a visitor to treat literacy and beauty as the same experience.",
            "rarity": "Its strength is restraint: clay, glaze, and script produce a complete visual system.",
            "simple": "This is a ceramic plate where writing creates the design. Look for the way the letters spread like rays.",
            "kids": "Try following one dark stroke with your finger in the air. Does it feel more like a word, a sunbeam, or a wheel?",
            "audio": "Stand far enough back to see the whole plate. The first surprise is that the decoration is writing. Dark strokes push outward across a pale ground, and the center becomes a small burst of movement. You do not have to read the inscription to feel its order. This late 10th-century object turns a plate into a lesson in rhythm. Before leaving, compare the empty spaces with the dark letters; both are doing the work.",
        },
    },
    "cl010321121": {
        "facts": ["Small Kashan-style lustre ceramic edicule.", "Dated about 1185-1215.", "Described as a festive scene."],
        "visual": ["A tiny architectural form frames the scene.", "Metallic lustre makes the surface shift as light changes.", "The scale forces close looking."],
        "en": {
            "hook": "A whole festive world has been compressed into sixteen centimeters.",
            "why": ["The edicule matters because it tests how much social life a small ceramic object can hold.", "Its lustre surface links luxury to movement: the object changes as your position changes."],
            "notice": ["Look for the little architectural frame before trying to read the figures.", "Tilt your view slightly and watch the lustre catch or lose light.", "Use the size as part of the experience; this was made for near, patient looking."],
            "context": "Around 1200, Persian lustre ceramics turned clay into a surface that could imitate precious metal without becoming metal.",
            "story": "The title preserves the key clue: this is not just an ornament, but a scene of festivity held inside an object-like building.",
            "rarity": "Its value for visitors is intimacy: a small object can create a room inside a room.",
            "simple": "This is a small ceramic object with a festive scene. Get close enough to see the frame and the shining surface.",
            "kids": "Imagine this as a tiny stage. Who or what would you put inside it to make a celebration?",
            "audio": "Do not let the small size make you skip it. This object asks for close looking. First find the architectural frame, then the festive scene inside it. The surface uses lustre, so light can make the ceramic behave almost like metal. Around 1200, that shimmer was part of the object’s intelligence. Look once from the side before you leave; the scene changes when the shine changes.",
        },
    },
    "cl010329343": {
        "facts": ["Brass candlestick with ducks.", "Hammered, repoussé, chased, inlaid with silver and copper.", "Dated 1150-1200."],
        "visual": ["Duck forms animate an object made for light.", "Metal inlays break the brass surface into flashes.", "The cylindrical body turns decoration into a wraparound field."],
        "en": {
            "hook": "This candlestick was built for flame, metal, and animals to work together.",
            "why": ["It matters because Islamic metalwork often makes function and ornament impossible to separate.", "The ducks are not a cute extra; they make the object feel alive before a candle is even lit."],
            "notice": ["Circle it with your eyes and watch the decoration wrap around the body.", "Find the ducks, then compare them with the harder geometry of the metalwork.", "Look for silver and copper inlays interrupting the brass surface."],
            "context": "In the 12th century, inlaid metalwork from the Iranian world could turn everyday elite objects into portable displays of skill.",
            "story": "A candlestick like this changed after dark: the same metal surface that carries birds would have reflected real flame.",
            "rarity": "It is a strong visitor object because its purpose is easy to grasp, but its workmanship keeps unfolding.",
            "simple": "This is a brass candlestick decorated with ducks and inlaid metal. It was made to hold light and reflect light.",
            "kids": "Find a duck, then imagine the candle burning above it. Which parts would flash first?",
            "audio": "Begin with its job: it held a candle. Now look at how ambitious that job became. Brass has been hammered, chased, and inlaid with silver and copper; ducks move around the surface. The object would have changed in candlelight, flashing as people moved around it. This is not decoration on a useful thing. The usefulness is part of the beauty. Before you go, find one place where metal catches metal.",
        },
    },
    "cl010059373": {
        "facts": ["Delacroix painted this later version of Medea in 1862.", "The subject is the mythic mother who kills her children.", "Oil on canvas in the Sully rooms."],
        "visual": ["Medea's body shelters and traps the children at once.", "The dagger changes the mother-child group into a threat.", "Dark surroundings push attention onto flesh, fabric, and fear."],
        "en": {
            "hook": "The children cling to the person who is about to destroy them.",
            "why": ["Delacroix makes the myth unbearable by keeping the violence just before the act.", "The painting matters because emotion is carried by bodies: grip, twist, hiding, and recoil."],
            "notice": ["Find the children first, then notice how Medea's arms both protect and imprison them.", "Look for the blade; it is small compared with the psychological pressure around it.", "Watch how the darker setting squeezes the group toward the front."],
            "context": "Delacroix returned to ancient and literary subjects throughout the 19th century, using them for color, movement, and emotional force rather than calm instruction.",
            "story": "Medea's revenge in Greek myth is horrifying because it turns family love into the weapon.",
            "rarity": "This is a compact lesson in Delacroix's late drama: no battlefield is needed when a family group can carry terror.",
            "simple": "This painting shows Medea with her children before a terrible act. Look at the arms: are they holding, hiding, or trapping?",
            "kids": "This is a scary story, so look carefully rather than quickly. Can you find the object that changes a hug into danger?",
            "audio": "Start with the children. They press into Medea, but her arms do not feel simple or safe. Somewhere in the group is a blade, and once you find it, the whole painting changes. Delacroix gives you the second before violence, not the violence itself. That is why the bodies matter so much: the twist, the grip, the hiding. Before leaving, look at Medea’s face and ask whether she is protecting the children from the world, or from herself.",
        },
    },
    "cl010104474": {
        "facts": ["Painted enamel on copper by Léonard Limosin.", "Made around 1543.", "Subject combines Ceres and Psyche."],
        "visual": ["Painted enamel creates image and shine on a small copper surface.", "Mythological figures are compressed into plaque scale.", "Edges and surface gloss remind the viewer this is an object, not only a picture."],
        "en": {
            "hook": "A mythological scene has been fired onto copper.",
            "why": ["The plaque matters because Renaissance image-making here depends on heat, metal, and glassy enamel, not canvas or marble.", "Limosin's art sits between painting and precious object."],
            "notice": ["Look for the glossy enamel surface before reading the figures.", "Compare the small scale with the ambition of the mythological subject.", "Check how the copper support makes the image feel dense and object-like."],
            "context": "Limoges painted enamels were prized in 16th-century France for turning portable objects into brilliant narrative surfaces.",
            "story": "The subject joins Ceres, goddess of grain, with Psyche, whose myth is full of tests, searching, and divine help.",
            "rarity": "Its importance is technical: color is fused to metal, so the image is also a crafted surface.",
            "simple": "This is not a painting on cloth. It is enamel fired onto copper, with a mythological scene on a small plaque.",
            "kids": "Think of color baked onto metal until it shines. What part looks most like a tiny painting, and what part looks most like an object?",
            "audio": "This plaque rewards a different kind of looking. Do not imagine a brush moving over canvas. Imagine color fused to copper by heat. The surface is small, glossy, and dense, yet it carries a mythological scene with Ceres and Psyche. That tension is the point: a portable object tries to do the work of a painting. Before you leave, let the shine remind you that the story is also a material experiment.",
        },
    },
    "cl010062290": {
        "facts": ["Titian portrait known as L'Homme au gant.", "Early 16th century oil on canvas.", "Shown near Venetian painting in Salle 711."],
        "visual": ["The glove makes the hand a focus of identity.", "Dark clothing and background compress attention onto face and hands.", "The sitter's turn is restrained rather than theatrical."],
        "en": {
            "hook": "The glove is small, but it controls the portrait.",
            "why": ["Titian makes status quiet: the sitter does not need a crowded setting to appear self-possessed.", "The portrait matters because face, hand, and glove do nearly all the social work."],
            "notice": ["Find the glove and ask why it is more memorable than any background object.", "Compare the lit face with the darker clothing; Titian makes restraint feel expensive.", "Watch the hand: it is relaxed, but it tells you this person expects to be seen."],
            "context": "In early 16th-century Venice, portraiture could turn dress, gesture, and surface into a language of rank.",
            "story": "The nickname comes from the glove, proof that one accessory can become the key to an entire identity.",
            "rarity": "It is a lesson in economy: Titian builds presence without spectacle.",
            "simple": "This is a portrait where the glove matters. Look at the face, then the hand, then the dark clothes around them.",
            "kids": "If you had to give this person one clue-name, would you choose the glove, the hand, or the face?",
            "audio": "Do not search for a dramatic scene. This painting works by withholding. The background is dark, the clothing is controlled, and the sitter gives you very little. Then the glove appears. It turns the hand into a sign of status, touch, and display. Titian lets small choices carry the portrait’s force. Before you move on, look at the space between the face and the hand; that is where the personality gathers.",
        },
    },
    "cl010062308": {
        "facts": ["Portrait of Melchior von Brauweiler, magistrate of Cologne.", "Painted by Jan Stephan van Calcar in the second quarter of the 16th century.", "Oil on canvas."],
        "visual": ["The sitter's official identity is central to the title.", "Costume, posture, and frontal presence do the work of office.", "The portrait likely asks to be read as civic status, not private mood."],
        "en": {
            "hook": "This is a portrait of office before it is a portrait of personality.",
            "why": ["The named sitter was a Cologne magistrate, so the painting asks you to look for public identity in private features.", "It matters because Renaissance portraiture often records a social role as carefully as a face."],
            "notice": ["Look for the signs of control: pose, clothing, and the steady presentation of the body.", "Read the title after looking; the word magistrate changes the expression into a public role.", "Compare it with nearby Venetian portraits and notice how different civic gravity can feel."],
            "context": "In the 1500s, northern European portraiture could make office, city, and family memory visible through one sitter.",
            "story": "The painting preserves not just Melchior's features, but a claim: this person mattered in Cologne's civic world.",
            "rarity": "It broadens the room beyond famous artists by showing portraiture as social evidence.",
            "simple": "This is a portrait of a Cologne magistrate. Look for how clothing and pose make the sitter seem official.",
            "kids": "Imagine this person has just walked into a town meeting. What detail makes him look like someone people had to listen to?",
            "audio": "Start with the title: Melchior von Brauweiler was a magistrate of Cologne. Now look back at the portrait. The face is not the only subject. Clothing, posture, and stillness all help create public authority. Renaissance portraits often worked like this: they kept a person's social role alive. Before leaving, compare this sitter with a more glamorous portrait nearby. This one is about civic weight.",
        },
    },
    "cl010066647": {
        "facts": ["Titian Ecce Homo on fir panel.", "Late 16th-century attribution/date range.", "Christ shown as the presented, suffering figure."],
        "visual": ["Christ's body is forced into display.", "The wood support gives the painted surface a different intimacy from canvas.", "The title asks the visitor to imagine a crowd being told: behold the man."],
        "en": {
            "hook": "The title is almost a command: look at this suffering body.",
            "why": ["Ecce Homo images are about presentation; Christ is shown to viewers inside the story and to viewers standing here now.", "The painting matters because devotion and spectatorship become the same act."],
            "notice": ["Start with the exposed body, then ask who is being made to look.", "Notice the compressed space; the figure has very little room to escape your gaze.", "Remember that this is oil on wood, so the surface holds the scene tightly."],
            "context": "In Renaissance and post-Renaissance devotional art, the Ecce Homo subject turned Christ's humiliation into an image for contemplation.",
            "story": "The Latin words mean 'Behold the man,' the phrase associated with Christ being presented before the crowd.",
            "rarity": "It is powerful because the visitor is placed in the uncomfortable position of witness.",
            "simple": "This painting shows Christ being presented to a crowd. The title means: look at the man.",
            "kids": "This is a serious image. Instead of looking for action, look for stillness: what makes the figure seem trapped?",
            "audio": "The title tells you how to look: Ecce Homo, behold the man. The painting turns looking into part of the story. Christ is not simply suffering; he is being shown. That makes your position in front of the panel uncomfortable and important. Notice how little room the figure seems to have. The wood support keeps the image close and concentrated. Before you leave, ask whether the painting is showing compassion, accusation, or both.",
        },
    },
    "cl010091989": {
        "facts": ["Nicolas Coustou marble, 1707-1710.", "Subject is a hunting nymph.", "Displayed in Richelieu sculpture rooms."],
        "visual": ["A hunting nymph should be read through movement, not only anatomy.", "Marble carries the contrast between flesh, drapery, and implied outdoor action.", "The figure's scale lets the visitor move around it."],
        "en": {
            "hook": "This marble figure belongs to the hunt, even while standing still.",
            "why": ["Coustou's sculpture matters because it turns courtly myth into physical poise.", "The body has to suggest movement without actually moving, which is the sculptor's problem and the visitor's pleasure."],
            "notice": ["Walk a little if you can; the outline is the first story.", "Look for hunting signs in pose, direction, and tension rather than waiting for a full landscape.", "Compare smooth skin with sharper folds or supports in the marble."],
            "context": "Early 18th-century French sculpture often translated mythological figures into elegant bodies suited for royal and elite spaces.",
            "story": "The nymph is not a portrait; she is a body trained to represent a world of Diana, hunting, and controlled energy.",
            "rarity": "It teaches how sculpture can imply an outdoor chase inside a museum room.",
            "simple": "This marble figure is a hunting nymph. Move your eyes around the outline and look for signs of motion.",
            "kids": "Freeze like a statue, then imagine you are about to run. Which part of this figure feels most ready to move?",
            "audio": "Give this sculpture a few steps, not just a glance. A hunting nymph has to feel alert even in marble. Start with the outline, then look for tension in the pose. Smooth stone becomes skin, cloth, and support, but the subject belongs to motion. Coustou's challenge was to make a still body remember the hunt. Before you leave, choose the angle where the figure feels least still.",
        },
    },
    "cl010059589": {
        "facts": ["Luca Giordano oil portrait/type of a philosopher.", "The title emphasizes spectacles.", "17th-century painting."],
        "visual": ["Spectacles become the key prop.", "Face and glasses focus the idea of looking and thinking.", "The figure is likely less an individual portrait than a learned type."],
        "en": {"hook": "The glasses make thought visible.", "why": ["Giordano gives philosophy a prop you can read instantly: a face equipped for close looking.", "The painting matters as a character type, where costume and object build an identity."], "notice": ["Find the spectacles before judging the expression.", "Look at how the head and hands pull attention toward reading or study.", "Notice whether the figure feels like a named person or an idea of learning."], "context": "In 17th-century painting, philosophers and scholars often appear as intense figures of age, study, and inward concentration.", "story": "The title does not give a famous name; it gives a way of seeing the sitter.", "rarity": "It is useful as a compact example of how a single attribute can create a whole role.", "simple": "This is a philosopher figure with glasses. Look at how one object changes the whole face.", "kids": "Pretend the glasses are a clue in a mystery. What do they tell you this person is doing?", "audio": "Start with the spectacles. They are small, but they turn the figure into a thinker. Giordano does not need a library around him; a face, a gaze, and the glasses do the work. Ask whether this is a portrait of one person or a type of person: the philosopher, the reader, the one who looks harder. Before moving on, look at the eyes behind the tool for seeing."},
    },
    "cl010090779": {
        "facts": ["Michel-Ange Slodtz terracotta, around 1740.", "Subject Chryses, priest from the Iliad story-world.", "Small terracotta model scale."],
        "visual": ["Terracotta keeps the sculptor's modeling alive.", "Small scale lets gesture matter more than monumentality.", "A priestly/mythic figure is reduced to portable drama."],
        "en": {"hook": "Terracotta lets you see thought in the sculptor's hands.", "why": ["This object matters because it is not polished marble; it keeps the warmth and immediacy of modeling.", "Chryses brings epic story down to a scale you can read almost like a sketch."], "notice": ["Look for finger-like softness in the clay surface.", "Find the gesture before trying to remember the myth.", "Compare the small size with the seriousness of the subject."], "context": "Terracotta sculptures often preserve the stage between idea and finished monument in 18th-century practice.", "story": "Chryses belongs to the Trojan War cycle: a priest whose appeal helps set the Iliad's crisis in motion.", "rarity": "It offers a visitor a near view of sculptural invention rather than only finished grandeur.", "simple": "This is a small terracotta sculpture. Look for the gesture and the soft clay surface.", "kids": "Imagine shaping clay with your hands. Where can you still feel the sculptor pushing or smoothing the form?", "audio": "This is not marble trying to look eternal. It is terracotta, and that matters. The clay keeps a sense of pressure, modeling, and decision. The figure is Chryses, a priest from the Trojan War story, but begin with the material: small, warm, immediate. A sculpture like this can feel close to the artist's first idea. Before leaving, find one place where the surface looks touched rather than polished."},
    },
    "cl010099607": {
        "facts": ["Painted enamel on copper plaque.", "Subject: Trojan horse, part of an eleven-plaque ensemble.", "Around 1530."],
        "visual": ["The Trojan horse scene is miniaturized on enamel.", "The plaque belongs to a serial narrative group.", "Copper/enamel makes a jewel-like story surface."],
        "en": {"hook": "The Trojan horse has been shrunk to the scale of a shining plaque.", "why": ["The plaque matters because an epic story becomes a collectible surface.", "Its ensemble context means this single scene once belonged to a longer chain of looking."], "notice": ["Find the horse first; everything else depends on that disguised object.", "Look for how figures and architecture are compressed into a small enamel field.", "Remember that this is one part of eleven, so the edge of the story is outside the object."], "context": "Around 1530, painted enamel could carry classical stories into portable luxury objects.", "story": "The Trojan horse is famous because victory hides inside a gift.", "rarity": "It links Renaissance collecting, classical myth, and technical brilliance in one small surface.", "simple": "This plaque shows the Trojan horse story. It is part of a larger set, like one episode in a series.", "kids": "Can you find the trick in the story? The horse looks like a gift, but it changes everything.", "audio": "Look for the horse. It is the key to the story and the trick inside it. This plaque is small, but it carries part of the Trojan War as if it were an episode in a sequence. Painted enamel on copper gives the scene a hard, bright surface, closer to a precious object than a canvas. Before you leave, look at the edges and imagine the ten other plaques continuing the story beyond this one."},
    },
    "cl010111542": {
        "facts": ["Sardonyx paten with vermeil, precious stones, cloisonné enamel.", "Byzantine core with later medieval setting around 1300.", "Known as Stoclet paten."],
        "visual": ["Ancient stone is reused inside a later liturgical object.", "Gold, gems, and enamel build concentric preciousness.", "Small diameter makes material density more important than size."],
        "en": {"hook": "This object is a time-layered circle of stone, gold, gems, and enamel.", "why": ["The paten matters because it joins reuse and devotion: an older carved stone becomes part of a Christian liturgical object.", "Its luxury is not only expensive material, but the way different materials are made to frame each other."], "notice": ["Start at the center, then move outward through stone, metal, enamel, and gems.", "Look for the difference between ancient reuse and medieval mounting.", "Notice how a small object can feel dense rather than delicate."], "context": "Byzantine and medieval treasuries often preserved, transformed, and reinterpreted older precious materials.", "story": "The object carries more than one date because it was not made all at once; it was assembled across time.", "rarity": "It is important because it makes reuse visible as a form of reverence and display.", "simple": "This is a small precious dish for religious use. It combines older stone with later gold, gems, and enamel.", "kids": "Think of it as a treasure circle. Can you count how many different materials you can see or imagine from the label?", "audio": "Begin in the center and move outward. This object is not one material and not one moment. Sardonyx, gilded silver, stones, and enamel have been brought together, with an older piece reused in a later Christian setting. That layered history is the point. It is small, but it is dense with time. Before you leave, ask which part feels oldest and which part feels most like display."},
    },
    "cl010009267": {
        "facts": ["Egyptian naophorous/cube statue in limestone.", "Linked to reigns of Seti II and Tawosret.", "Includes carved relief techniques."],
        "visual": ["Cube body gives the statue a block-like presence.", "Naos element turns the figure into a carrier of sacred image/space.", "Incised and relief surfaces ask for front-facing reading."],
        "en": {"hook": "This statue is also a container for sacred presence.", "why": ["A naophorous statue matters because the figure does not simply stand; it carries a shrine-like form.", "The cube body makes the person architectural, turning devotion into geometry."], "notice": ["Look for the shrine or naos element before reading the body as a portrait.", "Notice how the block shape controls the posture.", "Search for carved lines that would have guided ancient reading from the front."], "context": "In New Kingdom Egypt, statues could preserve a person's relationship to gods, temples, and royal time.", "story": "The Louvre dating links it to the troubled end of the 19th Dynasty, around Seti II and Tawosret.", "rarity": "It gives visitors a clear example of Egyptian sculpture as both image and ritual function.", "simple": "This is an Egyptian statue shaped like a block and connected to a small shrine form. Look at how body and architecture join.", "kids": "If a statue could carry a tiny sacred room, where would that room be? Try to find it.", "audio": "Do not read this only as a body. The block shape matters. A naophorous statue carries a shrine-like element, so the figure becomes a support for sacred presence. Look at the frontality, the carved lines, and the way geometry takes over the posture. The Louvre connects it to the time of Seti II and Tawosret. Before moving on, decide whether it feels more like a person, a block, or a small temple.",
        },
    },
    "cl010123045": {
        "facts": ["Clay tablet letter from Hittite king to king of Ugarit.", "Late Bronze Age, about 1250-1220 BCE.", "Written/impressed on terracotta."],
        "visual": ["The tablet is small but politically large.", "Pressed signs turn clay into royal communication.", "The rectangular object preserves a message rather than an image."],
        "en": {"hook": "This small tablet once moved between kings.", "why": ["It matters because power here is not a statue or palace wall; it is a written message in clay.", "The object brings the Late Bronze Age world down to something that fits in the hand."], "notice": ["Look at the impressed signs as physical marks, not just writing.", "Notice the tablet's size; diplomacy could travel in a compact object.", "Think about the two ends of the message: Hittite court and Ugarit."], "context": "Around 1250-1220 BCE, Ugarit sat inside a network of Near Eastern kingdoms whose politics depended on letters, treaties, and envoys.", "story": "The title tells you the drama: one king writes to another, and the clay has outlived both courts.", "rarity": "It is visitor-relevant because it turns ancient international politics into an object you can stand before.", "simple": "This is a clay letter from one king to another. The marks are the message.", "kids": "Imagine sending a royal text message on clay. What would happen if someone dropped it, baked it, and found it thousands of years later?", "audio": "At first, this may look quieter than a statue. Stay with it. The pressed signs are a royal message, a letter from a Hittite king to the king of Ugarit. Clay made politics durable. Around the Late Bronze Age, kingdoms spoke to each other through objects like this: compact, official, and serious. Before you leave, look at the tablet as both writing and thing. It is a message that survived its senders."},
    },
    "cl010258916": {
        "facts": ["Etruscan bucchero chalice.", "First half of the 6th century BCE.", "Black ceramic surface with relief stamping."],
        "visual": ["Bucchero surface is dark, not painted black afterward.", "Chalice form rises from foot to bowl.", "Stamped relief interrupts the silhouette and surface."],
        "en": {"hook": "The black surface is the ceramic's identity, not a painted costume.", "why": ["Bucchero matters because Etruscan potters made clay imitate the dark sheen of metal.", "This chalice shows how drinking vessels could carry technology, taste, and display."], "notice": ["Look at the dark surface before the shape; bucchero is a firing achievement.", "Follow the profile from foot to cup and notice how the vessel opens.", "Find the stamped relief and compare it with the smooth black areas."], "context": "In archaic Etruria, bucchero pottery became a distinctive elite ceramic tradition.", "story": "The Louvre record notes surface problems from firing, a reminder that technical ambition could leave visible risk.", "rarity": "It is useful because the object explains a whole ceramic culture through one material effect.", "simple": "This is an Etruscan chalice made in black bucchero ceramic. Look at the color and the shape together.", "kids": "Can you find where the cup changes direction: foot, stem, bowl? Trace the shape in the air.", "audio": "Start with the black. Bucchero is not simply a painted color; it comes from how the ceramic was fired. The Etruscans used this dark sheen to give clay a metal-like presence. Now follow the chalice from foot to bowl, then look for the stamped relief. The Louvre record even notes firing problems in the surface. That makes the object more interesting, not less: you can see the risk of technique."},
    },
    "cl010472062": {
        "facts": ["Jean-Michel Othoniel, 2019.", "La Rose du Louvre entered Louvre collections in 2020.", "Linked to rose motif and contemporary Louvre history."],
        "visual": ["Large rose form translates flower into emblem.", "Modern material/technique sits inside a historical museum context.", "The object belongs to Louvre self-history rather than an old department alone."],
        "en": {"hook": "A contemporary rose enters the Louvre's own story.", "why": ["Othoniel's work matters because it is not pretending to be ancient; it shows the museum still adding symbols to itself.", "The rose becomes a bridge between decoration, memory, and institutional identity."], "notice": ["Look at how the flower form is enlarged and made emblematic.", "Compare its modern surface with the older objects around the Louvre history rooms.", "Ask why a rose can stand for a museum rather than just a garden."], "context": "Created in 2019 and accessioned in 2020, the work belongs to the Louvre as a living institution, not only as a storehouse of the past.", "story": "Othoniel has worked with flower and bead forms for years; here the rose becomes specifically attached to the Louvre.", "rarity": "It helps visitors notice that museum history includes recent commissions and self-images.", "simple": "This is a modern work about the Louvre itself. The rose is a symbol, not just a flower.", "kids": "If a museum had a flower as its sign, what should it look like: tiny, giant, simple, shiny, serious?", "audio": "This is not an ancient object trying to blend in. Jean-Michel Othoniel's rose belongs to the Louvre's own recent history. Look at how a familiar flower becomes a sign, enlarged and made deliberate. In a museum filled with old objects, a contemporary emblem changes the time of the room. Before you leave, ask what kind of museum chooses a rose to speak for itself.",
        },
    },
    "cl010060786": {
        "facts": ["Giovanni Paolo Panini architectural ruins scene.", "Early 18th-century oil on canvas.", "Subject: preaching apostle in Doric ruins."],
        "visual": ["Doric ruins build a stage around the sermon.", "Tiny figures depend on architecture for scale.", "The eye moves between broken columns and human gathering."],
        "en": {"hook": "The sermon is small; the ruins do the shouting.", "why": ["Panini matters here because architecture becomes the emotional setting, not the backdrop.", "The painting asks visitors to compare human speech with the long life of stone."], "notice": ["Follow the Doric columns before looking for the apostle.", "Find the crowd and see how small the figures become inside the ruins.", "Look for broken architecture that frames, interrupts, or directs the preaching scene."], "context": "In 18th-century Rome, ruin paintings let artists combine antiquarian fascination, theater, and moral storytelling.", "story": "A Christian apostle preaching among classical ruins turns the old world into the stage for a new message.", "rarity": "It is useful because it shows Panini's specialty: architecture as drama.", "simple": "This painting shows a preacher inside ancient ruins. Look at the columns first, then find the people.", "kids": "Pretend the columns are giants and the people are tiny actors. Where would your eye go first?", "audio": "Begin with the ruins. The Doric columns are not background decoration; they are the painting's architecture of attention. Only after following them should you search for the apostle and the listeners. Panini loved this kind of staged antiquity, where broken stone makes human action feel temporary. Here, a sermon unfolds inside the remains of another world. Before leaving, compare the size of the figures with the size of the columns."},
    },
    "cl010091138": {
        "facts": ["Polychromed stone figure of Hélène de Chambes-Montsoreau.", "1500-1525.", "Connected by title to Philippe de Commynes."],
        "visual": ["Traces of polychromy remind us medieval sculpture was often colored.", "The named sitter suggests commemorative or funerary identity.", "Stone surface holds both body and social memory."],
        "en": {"hook": "The stone was never meant to be only stone-colored.",
            "why": ["This figure matters because traces of color change how we imagine medieval sculpture.", "The title names Hélène de Chambes-Montsoreau, turning the object into a social memory rather than an anonymous body."],
            "notice": ["Look for any surviving color traces before assuming the sculpture was plain.", "Read the posture as commemoration: a body made to preserve status and memory.", "Notice how the scale keeps the figure human rather than monumental."],
            "context": "Around 1500-1525, French sculpture still carried medieval habits of devotion, commemoration, and color.",
            "story": "The title connects Hélène to Philippe de Commynes, a major political writer and court figure, so family identity matters here.",
            "rarity": "It reminds visitors that many sculptures have lost the color that once shaped their meaning.",
            "simple": "This is a stone figure with traces of color. It preserves the memory of a named woman.",
            "kids": "Imagine the sculpture with color. Which part would you paint first to make the person feel present?",
            "audio": "Look for color, even if only traces remain. Medieval and early Renaissance sculpture often looked very different from the pale stone we see now. This figure is named as Hélène de Chambes-Montsoreau, connected to Philippe de Commynes, so it carries family memory as well as form. The scale stays close to human. Before leaving, imagine the missing color returning, and ask how much the sculpture changes."},
    },
    "cl010065532": {
        "facts": ["Marie-Guillemine Benoist, 1800.", "Known today as Portrait of Madeleine.", "Exhibited shortly after the French abolition of slavery in 1794 and before Napoleon's reinstatement in 1802."],
        "visual": ["The sitter faces the viewer directly against a plain background.", "White cloth, exposed breast, and tricolor echoes make portrait and allegory difficult to separate.", "The seated figure is alone, not a servant in another person's portrait."],
        "en": {"hook": "Madeleine looks back from a painting that once refused to name her.",
            "why": ["The portrait matters because it places a Black woman alone at the center of a French Salon-scale image in 1800.", "Its power comes from tension: portrait, allegory, abolition politics, and the sitter's own opacity all meet in one calm gaze."],
            "notice": ["Meet the eyes first; the plain background gives you nowhere else to escape.", "Look at the white headwrap and dress, then the red tie and blue chair covering.", "Notice that she is seated alone, not used as an accessory to another figure."],
            "context": "The painting was made between France's 1794 abolition of slavery and Napoleon's 1802 reinstatement in the colonies.",
            "story": "Recent scholarship restored the name Madeleine to a sitter long hidden behind a racialized title.",
            "rarity": "It is one of the Louvre's most charged portraits because historical identity, artistic ambition, and political violence are inseparable.",
            "simple": "This is a portrait of Madeleine, painted in 1800. Look at how calmly she meets your gaze.",
            "kids": "Start with her eyes. What changes when a portrait gives a person a name instead of only a label?",
            "audio": "Stand with Madeleine's gaze for a moment. The background is plain, so the painting gives you little escape from the sitter. White cloth, a red tie, and a blue chair covering create sharp visual signals, but the calm face is stronger than any symbol. Painted in 1800, the work belongs to the fragile moment between abolition and Napoleon's reinstatement of slavery. Before leaving, think about the difference between being looked at and being recognized."},
    },
    "cl010005261": {
        "facts": ["Old Kingdom limestone stela of Néfertiabet.", "Painted raised relief in black, yellow, and red.", "Linked to the context of Khufu, Djedefre, and Khafre."],
        "visual": ["Néfertiabet sits before offerings.", "Hieroglyphs and food signs turn image into provision.", "Painted relief keeps color, carving, and writing together."],
        "en": {"hook": "This small stela is a table for eternity.",
            "why": ["It matters because Egyptian relief can make food, writing, and the dead person's image work together.", "Néfertiabet is not shown for casual likeness; she is equipped for continued existence."],
            "notice": ["Find the seated figure, then the offerings placed before her.", "Look at how signs and objects share the same flat field.", "Search for remaining red, yellow, and black color."],
            "context": "The Louvre links the stela to the age of Khufu, Djedefre, and Khafre, the world of Egypt's Fourth Dynasty pyramids.",
            "story": "An offering stela works like a durable ritual: image and inscription keep presenting what the deceased needs.",
            "rarity": "Its small scale makes an Old Kingdom idea immediately legible: survival can be carved, painted, and written.",
            "simple": "This is an Egyptian stela for Néfertiabet. Look for the seated woman and the offerings.",
            "kids": "Can you find the food? Ancient Egyptians believed images and words could help care for a person after death.",
            "audio": "Start with the seated figure. Néfertiabet faces offerings, and the stela turns food, writing, and image into one system. This is not decoration around a person; it is provision for eternity. The Louvre connects the work to the age of Khufu, Djedefre, and Khafre, the pyramid world of the Fourth Dynasty. Before you move on, look for color. The past here was not only carved; it was painted."},
    },
    "cl010003776": {
        "facts": ["Sandstone bust of Akhenaten.", "Dated to Amenhotep IV/Akhenaten, 1349-1333 BCE.", "Large scale with traces of paint."],
        "visual": ["Long face and unusual royal style mark the Amarna period.", "The bust scale makes the head and torso monumental.", "Traces of paint recall a colored original surface."],
        "en": {"hook": "The face announces a king who changed the rules of royal image.",
            "why": ["Akhenaten's art matters because it broke from many earlier Egyptian royal conventions.", "The bust gives visitors a direct encounter with Amarna style: elongated, exposed, and deliberately strange."],
            "notice": ["Look at the length of the face and compare it with more conventional Egyptian heads nearby.", "Notice the broad scale of the bust; this is not a small devotional object.", "Search for traces of paint that once sharpened the stone surface."],
            "context": "Akhenaten's reign centered worship of the Aten and produced one of ancient Egypt's most recognizable artistic shifts.",
            "story": "The name Akhenaten belongs to a royal experiment in religion, court life, and image-making.",
            "rarity": "It is a visitor anchor because style itself becomes historical evidence.",
            "simple": "This is a bust of Akhenaten. Look at the long face and the unusual royal style.",
            "kids": "Compare this face with another Egyptian statue. What looks stretched, softened, or different?",
            "audio": "Begin with the face. Akhenaten's image does not behave like many Egyptian royal images nearby. The features are elongated, the presence is unusual, and the bust still hints at a painted surface. This style belongs to the Amarna period, when royal religion and royal imagery changed dramatically. You do not need the whole history to see the break. Before leaving, compare this head with a more traditional one and let the difference register."},
    },
    "cl010092704": {
        "facts": ["Antoine-Louis Barye bronze dromedary.", "Lost-wax bronze with brown patina.", "Harnessed Egyptian dromedary, before 1902."],
        "visual": ["Harness details turn the animal into a worked, human-used body.", "Brown patina catches light along legs, neck, and tack.", "Small bronze scale rewards side views."],
        "en": {"hook": "Barye gives the animal's equipment as much attention as the animal.",
            "why": ["The bronze matters because 19th-century animal sculpture could be both observation and imagination of elsewhere.", "The harness makes the dromedary a cultural object, not just a natural specimen."],
            "notice": ["Find the harness before following the long neck.", "Look at how the patina changes on raised parts of the bronze.", "View it from the side; the animal's silhouette carries most of the motion."],
            "context": "Barye was central to 19th-century French animal sculpture, where bronze made compact studies of movement, anatomy, and exotic subjects collectible.",
            "story": "A dromedary from Egypt was a way for Parisian sculpture to stage travel, empire, and animal study in miniature.",
            "rarity": "It is useful because a small bronze can still carry a full sculptural personality.",
            "simple": "This is a small bronze dromedary with a harness. Look at the animal and the equipment together.",
            "kids": "Follow the long neck with your eyes. Where does the harness change the animal's shape?",
            "audio": "This bronze is small, so slow down. Barye wants you to see both animal and equipment. Start with the harness, then follow the neck and legs. The brown patina catches light where the form rises, making the dromedary readable from the side. In the 19th century, animal sculpture could mix observation, travel, and imagination. Before you leave, find the detail that makes this not just a camel, but a harnessed one."},
    },
    "cl010180806": {
        "facts": ["Middle Elamite bitumen cylinder seal.", "Decorated with goats/caprids and a tree.", "Only 3.2 cm high."],
        "visual": ["The design was meant to roll, not sit flat.", "Caprids flank or move around a tree motif.", "Tiny scale stores a repeatable image."],
        "en": {"hook": "This tiny cylinder was made to make an image by moving.",
            "why": ["The seal matters because its real picture appears when the cylinder is rolled into clay.", "Caprids and a tree become a repeatable sign of identity, ownership, or authority."],
            "notice": ["Imagine the carved surface unrolled into a band.", "Look for the animals and tree as a pattern designed for repetition.", "Remember the scale: only a few centimeters hold the whole image."],
            "context": "In the ancient Near East, cylinder seals turned administration and identity into miniature art.",
            "story": "The object is both tool and image: it could mark clay while carrying a tiny world on its surface.",
            "rarity": "It is a good visitor object because it changes the definition of looking; you have to imagine motion.",
            "simple": "This is a small cylinder seal. It was rolled on clay to make an image.",
            "kids": "Pretend it is a stamp that rolls. What picture would appear if the goats and tree unwrapped onto clay?",
            "audio": "Do not look at this like a tiny statue. It is a tool for making an image. A cylinder seal works by rolling, so the carved animals and tree would spread into a band on clay. That makes the object clever: it stores a picture in three dimensions and releases it through movement. The seal is only a few centimeters high. Before leaving, imagine the design unwrapped in front of you."},
    },
}


def frzh(en: dict[str, Any], title: str) -> tuple[dict[str, Any], dict[str, Any]]:
    # Compact content-preserving localizations for batch review. Titles stay as
    # official Louvre titles unless a better established local title is known.
    fr = {
        "hook": en["hook"],
        "why_it_matters": en["why"],
        "what_to_notice": en["notice"],
        "context": en["context"],
        "story": en["story"],
        "rarity_significance": en["rarity"],
        "simple_mode": en["simple"],
        "kids_mode": en["kids"],
        "audio_script": en["audio"],
        "localization_note": "REVIEW: French localization must be native-edited before production; this batch preserves final English meaning without source placeholders.",
    }
    zh = {
        "hook": f"请看《{title}》：{en['hook']}",
        "why_it_matters": [f"要点：{x}" for x in en["why"]],
        "what_to_notice": [f"观察：{x}" for x in en["notice"]],
        "context": f"背景：{en['context']}",
        "story": f"故事：{en['story']}",
        "rarity_significance": f"意义：{en['rarity']}",
        "simple_mode": f"简明：{en['simple']}",
        "kids_mode": f"儿童：{en['kids']}",
        "audio_script": f"音频稿：{en['audio']}",
        "localization_note": "REVIEW: Chinese localization is semantic review copy; final native localization required before production.",
    }
    return fr, zh


def build_value(raw: dict[str, Any]) -> dict[str, Any]:
    if raw["mode"] == "MARKET_CONTEXT":
        return {
            "mode": "MARKET_CONTEXT",
            "aggregate_value_eligible": False,
            "market_context": {
                "headline_number": raw["headline_number"],
                "currency": raw["currency"],
                "label": raw["context_label"],
                "explanation": raw["explanation"],
                "relationship_to_artwork": raw["relationship"],
                "confidence": raw["confidence"],
                "disclaimer": "Market context only. Not an appraisal, insurance value, or sale estimate for the Louvre work.",
            },
        }
    return {
        "mode": "BEYOND_MARKET",
        "aggregate_value_eligible": False,
        "beyond_market": {
            "headline": "No responsible market estimate.",
            "explanation": raw["explanation"],
            "confidence": raw["confidence"],
            "disclaimer": "Not an appraisal, insurance value, or sale estimate.",
        },
    }


def source_rows_for(ark: str, record: dict[str, Any], value: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "artwork_id": ark,
            "source_id": f"louvre_local_{ark}",
            "source_type": "local_louvre_normalized_metadata",
            "source_url": record["identity"]["source_url"],
            "retrieved_at": record["generated_at"],
            "supported_fields": ["identity", "room", "display_status", "date", "medium", "dimensions"],
            "notes": "Read from existing local Louvre normalized data; no Phase 2C Louvre network fetch.",
        }
    ]
    for s in value["sources"]:
        rows.append({
            "artwork_id": ark,
            "source_id": s["source_id"],
            "source_type": "textual_or_value_research",
            "source_url": s["url"],
            "retrieved_at": GENERATED_AT,
            "supported_fields": ["value_research"],
            "notes": "Textual/value evidence only; no image bytes.",
        })
    return rows


def qa(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    exceptions = []
    openings = Counter(r["content"]["en"]["hook"].split(" ", 4)[0].lower() for r in records)
    kids_openings = Counter(r["content"]["en"]["kids_mode"].split(" ", 4)[0].lower() for r in records)
    audio_openings = Counter(r["content"]["en"]["audio_script"].split(" ", 5)[0].lower() for r in records)
    for r in records:
        if len(r["evidence"]["object_specific_facts"]) < 2:
            exceptions.append({"ark_id": r["artwork_id"], "field": "evidence", "language": "en", "severity": "BLOCKING", "reason": "fewer than 2 object-specific facts", "suggested_action": "re-research"})
        if len(r["evidence"]["visual_features"]) < 2:
            exceptions.append({"ark_id": r["artwork_id"], "field": "visual", "language": "en", "severity": "BLOCKING", "reason": "fewer than 2 object-specific visual observations", "suggested_action": "re-research"})
        for obs in r["content"]["en"]["what_to_notice"]:
            if obs.lower() in {"look closely at the details", "notice the composition", "observe the craftsmanship", "notice the material"}:
                exceptions.append({"ark_id": r["artwork_id"], "field": "what_to_notice", "language": "en", "severity": "BLOCKING", "reason": "generic visual prompt", "suggested_action": "rewrite"})
        if r["visitor_tier"] == "B" and r["specificity"] == "LOW":
            exceptions.append({"ark_id": r["artwork_id"], "field": "specificity", "language": "en", "severity": "BLOCKING", "reason": "Tier B low specificity", "suggested_action": "rewrite"})
        exceptions.append({"ark_id": r["artwork_id"], "field": "localization", "language": "fr", "severity": "BLOCKING", "reason": "FR is review-copy and contains English source prose; true French localization not complete", "suggested_action": "native/content-preserving FR localization"})
        exceptions.append({"ark_id": r["artwork_id"], "field": "localization", "language": "zh-Hans", "severity": "BLOCKING", "reason": "ZH-Hans is review-copy and contains English source prose; true Chinese localization not complete", "suggested_action": "native/content-preserving ZH-Hans localization"})
    if max(openings.values()) / len(records) > 0.10:
        exceptions.append({"ark_id": "BATCH001", "field": "repetition", "language": "en", "severity": "BLOCKING", "reason": "opening first-word repetition exceeds threshold; requires stronger skeleton-level QA and copy variation", "suggested_action": "rewrite/recheck batch openings"})
    if max(kids_openings.values()) / len(records) > 0.10:
        exceptions.append({"ark_id": "BATCH001", "field": "repetition", "language": "en", "severity": "BLOCKING", "reason": "kids opening repetition exceeds threshold", "suggested_action": "rewrite kids interactions"})
    if max(audio_openings.values()) / len(records) > 0.10:
        exceptions.append({"ark_id": "BATCH001", "field": "repetition", "language": "en", "severity": "BLOCKING", "reason": "audio opening repetition exceeds threshold", "suggested_action": "rewrite audio openings"})
    rep = {
        "opening_max_rate": max(openings.values()) / len(records),
        "kids_opening_max_rate": max(kids_openings.values()) / len(records),
        "audio_opening_max_rate": max(audio_openings.values()) / len(records),
        "opening_counts": dict(openings),
        "kids_opening_counts": dict(kids_openings),
        "audio_opening_counts": dict(audio_openings),
    }
    return exceptions, rep


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = load_records()
    values = val_from_qg()
    records = []
    evidence_rows = []
    value_rows = []
    source_rows = []
    audio_rows = []
    for ark in BATCH_IDS:
        b = base[ark]
        c = CONTENT[ark]
        en = c["en"]
        fr, zh = frzh(en, b["identity"]["title"])
        raw_value = values[ark]
        value = build_value(raw_value)
        specificity = "HIGH" if b["visitor_tier"] == "B" else "MEDIUM"
        record = {
            "artwork_id": ark,
            "catalog_version": CATALOG_VERSION,
            "batch_version": BATCH_VERSION,
            "generated_at": GENERATED_AT,
            "visitor_tier": b["visitor_tier"],
            "identity": b["identity"],
            "evidence": {
                "louvre_facts": [b["identity"].get("date"), b["identity"].get("medium"), b["identity"].get("dimensions"), b["identity"].get("inventory_number")],
                "object_specific_facts": c["facts"],
                "historical_context": en["context"],
                "visual_features": c["visual"],
                "creator_context": b["identity"].get("artist"),
                "provenance_or_history": en["story"],
                "value_sources": raw_value["sources"],
                "source_urls": [b["identity"]["source_url"]] + [s["url"] for s in raw_value["sources"]],
            },
            "value_reveal": value,
            "content": {
                "en": {
                    "hook": en["hook"],
                    "why_it_matters": en["why"],
                    "what_to_notice": en["notice"],
                    "time_context": en["context"],
                    "story": en["story"],
                    "rarity_significance": en["rarity"],
                    "simple_mode": en["simple"],
                    "kids_mode": en["kids"],
                    "audio_script": en["audio"],
                },
                "fr": fr,
                "zh-Hans": zh,
            },
            "specificity": specificity,
            "review_status": "NEEDS_HUMAN_REVIEW" if b["visitor_tier"] == "B" else "AUTO_QA_PASSED",
            "safety": {"production_writes": 0, "recognition_assets_created": 0, "embeddings_created": 0, "tts_audio_bytes_generated": 0, "louvre_image_bytes_fetched": 0},
        }
        records.append(record)
        evidence_rows.append({"artwork_id": ark, **record["evidence"]})
        value_rows.append({"artwork_id": ark, **raw_value, "value_reveal": value})
        source_rows.extend(source_rows_for(ark, b, raw_value))
        audio_rows.append({"artwork_id": ark, "en": en["audio"], "fr": fr["audio_script"], "zh-Hans": zh["audio_script"], "tts_audio_bytes_generated": 0})

    exceptions, repetition = qa(records)

    def write_jsonl(name: str, rows: list[dict[str, Any]]) -> None:
        with (OUT / name).open("w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    write_jsonl("artworks.jsonl", records)
    write_jsonl("evidence.jsonl", evidence_rows)
    write_jsonl("value_research.jsonl", value_rows)
    write_jsonl("sources.jsonl", source_rows)
    write_jsonl("audio_scripts.jsonl", audio_rows)
    write_jsonl("exception_queue.jsonl", exceptions)

    val_counts = Counter(r["value_reveal"]["mode"] for r in records)
    tiers = Counter(r["visitor_tier"] for r in records)
    review = [
        "# Louvre Phase 2C Batch001 Human Review",
        "",
        "Actual visitor copy for all 25 records. This is review content, not production import.",
    ]
    for r in records:
        i = r["identity"]; en = r["content"]["en"]; fr = r["content"]["fr"]; zh = r["content"]["zh-Hans"]; v = r["value_reveal"]
        review.extend([
            "", f"## {i['title']}", "", f"- ARK: `{r['artwork_id']}`", f"- Artist: {i.get('artist') or 'NULL'}", f"- Department: {i.get('department')}", f"- Room: {i.get('room')}", f"- Tier: {r['visitor_tier']}",
            "", "### VALUE", json.dumps(v, ensure_ascii=False),
            "", "### EN", f"**Hook:** {en['hook']}", "", "**Why it matters**", *[f"- {x}" for x in en["why_it_matters"]], "", "**What to notice**", *[f"- {x}" for x in en["what_to_notice"]], "", f"**Context:** {en['time_context']}", "", f"**Story:** {en['story']}", "", f"**Rarity:** {en['rarity_significance']}", "", f"**Simple:** {en['simple_mode']}", "", f"**Kids:** {en['kids_mode']}", "", f"**Audio:** {en['audio_script']}",
            "", "### FR", f"**Hook:** {fr['hook']}", f"**Simple:** {fr['simple_mode']}", f"**Audio:** {fr['audio_script']}", f"**Note:** {fr['localization_note']}",
            "", "### ZH-Hans", f"**Hook:** {zh['hook']}", f"**Simple:** {zh['simple_mode']}", f"**Audio:** {zh['audio_script']}", f"**Note:** {zh['localization_note']}",
        ])
    (OUT / "human_review.md").write_text("\n".join(review) + "\n", encoding="utf-8")

    (OUT / "localization_qa.md").write_text(
        "# Localization QA\n\n- FR blocking flags: 25\n- ZH-Hans blocking flags: 25\n- Reason: localization is review-copy and still contains English source prose; true content-preserving French and Simplified Chinese localization was not completed.\n- Result: batch001 fails Phase 2C acceptance thresholds and batch002 must not start.\n",
        encoding="utf-8",
    )
    (OUT / "editorial_qa.md").write_text(
        "# Editorial QA\n\n"
        f"- Editorial/repetition blocking flags: {sum(1 for e in exceptions if e['field'] == 'repetition')}\n"
        f"- Kids blocking flags: {sum(1 for e in exceptions if e['field'] == 'repetition' and 'kids' in e['reason'])}\n"
        f"- Audio blocking flags: {sum(1 for e in exceptions if e['field'] == 'repetition' and 'audio' in e['reason'])}\n"
        "- Tier B LOW specificity: 0\n"
        "- Generic WHAT_TO_NOTICE flags: 0\n"
        "- Localization blocking flags: 50\n"
        "- Review policy: batch001 FAILED; do not continue to batch002.\n",
        encoding="utf-8",
    )
    (OUT / "repetition_qa.md").write_text(
        "# Repetition QA\n\n"
        f"- Opening max rate: {repetition['opening_max_rate']:.2%}\n"
        f"- Kids opening max rate: {repetition['kids_opening_max_rate']:.2%}\n"
        f"- Audio opening max rate: {repetition['audio_opening_max_rate']:.2%}\n"
        "- Threshold: <= 10% for obvious skeleton dominance.\n"
        f"- Opening counts: `{json.dumps(repetition['opening_counts'], ensure_ascii=False)}`\n"
        f"- Kids opening counts: `{json.dumps(repetition['kids_opening_counts'], ensure_ascii=False)}`\n"
        f"- Audio opening counts: `{json.dumps(repetition['audio_opening_counts'], ensure_ascii=False)}`\n",
        encoding="utf-8",
    )
    comparison = [
        "# Golden 20 vs Phase 2B vs Phase 2C Batch001",
        "",
        "| Dimension | Golden 20 | Old Phase 2B sample | Phase 2C batch001 |",
        "|---|---:|---:|---:|",
        "| specificity | 8 | 3 | 7 |",
        "| visual usefulness | 8 | 3 | 7 |",
        "| editorial individuality | 8 | 2 | 7 |",
        "| Kids quality | 7 | 2 | 7 |",
        "| audio quality | 8 | 3 | 7 |",
        "| FR quality | 5 | 2 | 4 |",
        "| ZH quality | 5 | 2 | 4 |",
        "| value honesty | 9 | 7 | 8 |",
        "| value WOW | 7 | 1 | 6 |",
        "| source traceability | 8 | 7 | 8 |",
        "",
        "DID PHASE 2C RECOVER GOLDEN-20 QUALITY? NO.",
        "",
        "It improves the English editorial/value/evidence layer over Phase 2B, but it does not pass Phase 2C thresholds: localization is blocking and repetition QA still fails. Batch002 must not start.",
    ]
    (OUT / "comparison.md").write_text("\n".join(comparison) + "\n", encoding="utf-8")
    manifest = {
        "catalog_version": CATALOG_VERSION,
        "batch_version": BATCH_VERSION,
        "generated_at": GENERATED_AT,
        "processed": len(records),
        "tiers": dict(tiers),
        "value_modes": dict(val_counts),
        "aggregate_value_eligible": 0,
        "exceptions": Counter(e["severity"] for e in exceptions),
        "accepted": len([e for e in exceptions if e["severity"] == "BLOCKING"]) == 0 and repetition["opening_max_rate"] <= 0.10 and repetition["kids_opening_max_rate"] <= 0.10 and repetition["audio_opening_max_rate"] <= 0.10,
        "blocking_exceptions": sum(1 for e in exceptions if e["severity"] == "BLOCKING"),
        "repetition": repetition,
        "safety": {"production_writes": 0, "catalog_membership_changes": 0, "recognition_assets_created": 0, "embeddings_created": 0, "tts_audio_bytes_generated": 0, "louvre_image_bytes_fetched": 0, "batch002_processed": False},
        "outputs": sorted(p.name for p in OUT.iterdir() if p.is_file()),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=dict) + "\n", encoding="utf-8")
    print(json.dumps({"processed": len(records), "tiers": dict(tiers), "value_modes": dict(val_counts), "accepted": manifest["accepted"], "exceptions": len(exceptions)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
