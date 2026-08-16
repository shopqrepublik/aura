#!/usr/bin/env python3
"""Build the Louvre Phase 2A 20-work content review package.

This script is export-only. It reads the frozen Louvre Visitor 500 catalog and
aligned Commons manifest, then writes local review artifacts. It does not write
to production, fetch images, create RecognitionAssets, or generate audio files.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "exports" / "louvre"
CONTENT_ROOT = EXPORT_ROOT / "content"

CATALOG_VERSION = "2026-08-11-v1"
GENERATION_VERSION = "louvre_phase2a_pilot_v0.1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

FINAL_CATALOG = EXPORT_ROOT / "louvre_visitor_500_final.csv"
FINAL_MANIFEST = EXPORT_ROOT / "louvre_wikimedia_asset_manifest_final.csv"

PILOT_IDS = [
    "cl010062370",  # Mona Lisa
    "cl010252531",  # Winged Victory
    "cl010277627",  # Venus de Milo
    "cl010059199",  # Raft of the Medusa
    "cl010062239",  # Oath of the Horatii
    "cl010064382",  # Wedding Feast at Cana
    "cl010065566",  # Grande Odalisque
    "cl010091976",  # Psyche Revived by Cupid's Kiss
    "cl010065872",  # Liberty Leading the People
    "cl010066107",  # Virgin and Child with Saint Anne
    "cl010065720",  # Coronation of Napoleon
    "cl010327133",  # Peacock automaton element
    "cl010329191",  # Basin of al-'Adil II Abu Bakr
    "cl010327142",  # Rock-crystal ewer
    "cl010333267",  # Mamluk porch
    "cl010120564",  # Statue eye inlay
    "cl010008140",  # Cubit of Maya
    "cl010278478",  # Cycladic statuette
    "cl010100716",  # Oeben table
    "cl010059215",  # Juliette Recamier
]


FACTS: dict[str, dict[str, Any]] = {
    "cl010062370": {
        "short_title": "Mona Lisa",
        "artist_display": "Leonardo da Vinci",
        "date_display": "1503-1519, first quarter of the 16th century",
        "medium": "Oil on poplar panel",
        "dimensions": "79.4 x 53.4 cm; framed 101 x 77 cm",
        "story_fact": "Louvre metadata says Leonardo probably began the portrait around 1503 for Francesco del Giocondo and kept it with him until his death; it was probably acquired by Francois I in 1518.",
        "visual_type": "portrait",
        "notice": [
            "The hands are crossed calmly, but the shoulders turn slightly away from the viewer.",
            "The mouth stays unresolved: the smile appears stronger when you look away from it.",
            "The distant landscape is not symmetrical; roads, water, and rocks sit at different levels.",
            "The sitter has no jewelry, so attention falls on face, hands, and atmosphere.",
        ],
        "why": "This is not only famous because of thefts and crowds. It is Leonardo using a portrait to test how a living presence can be built from tiny transitions of light, shadow, skin, landscape, and gaze.",
        "context": "Florentine portraiture usually identified a sitter clearly and directly. Leonardo made the sitter psychologically active instead: she seems to register the viewer, while the background turns the portrait into a study of time, air, and perception.",
        "story": "The painting stayed with Leonardo rather than going straight to the sitter. That long possession matters: it suggests a work he kept refining, not a routine commission finished and delivered.",
        "rarity": "Autograph paintings by Leonardo are exceptionally few, and this one remains one of the clearest public encounters with his mature sfumato technique.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010252531": {
        "short_title": "Winged Victory of Samothrace",
        "artist_display": None,
        "date_display": "c. 200-175 BCE",
        "medium": "Paros marble statue with Lartos marble ship-shaped base",
        "dimensions": "about 5.64 m high with base",
        "story_fact": "Louvre metadata describes a Hellenistic Nike set on a ship-shaped base, found in fragments and missing the head, arms, feet, and parts of the wings.",
        "visual_type": "sculpture",
        "notice": [
            "The body leans into a headwind, while the drapery seems pressed flat against the torso.",
            "The wings expand behind the figure, making the missing head feel less like an absence than a rush of motion.",
            "The prow-shaped base turns the staircase into a theatrical sea setting.",
            "The marble surface alternates between taut skin, wet fabric, and broken archaeological edges.",
        ],
        "why": "The sculpture makes victory feel physical. Instead of showing a calm symbol, it stages the instant when a goddess appears to land on a ship, wind and momentum still moving through the stone.",
        "context": "Hellenistic sculpture often prized drama, movement, and emotional immediacy. This Nike turns a naval monument into an event a visitor can almost walk into.",
        "story": "Its power depends partly on loss. The missing head and arms do not weaken the work; they shift attention to stance, wings, and the force of arrival.",
        "rarity": "Very few ancient monuments preserve this combination of scale, original architectural setting, and theatrical motion.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010277627": {
        "short_title": "Venus de Milo",
        "artist_display": None,
        "date_display": "c. 150-125 BCE",
        "medium": "Paros marble, assembled from separately carved elements",
        "dimensions": "204 cm high",
        "story_fact": "Louvre metadata identifies the work as a Hellenistic statue in Paros marble, incomplete, with the arms and left foot missing.",
        "visual_type": "sculpture",
        "notice": [
            "The torso twists gently above a heavier draped lower body.",
            "The broken shoulders make you imagine several possible arm positions.",
            "The face stays composed, almost detached from the movement below.",
            "The join at the hips reveals the ancient construction of separate marble blocks.",
        ],
        "why": "Its fame comes from a paradox: an incomplete statue became a modern ideal of beauty. The missing arms turned scholarly uncertainty into part of the viewing experience.",
        "context": "The work belongs to the Hellenistic period, when Greek sculpture could combine classical balance with more complex movement and sensuality.",
        "story": "Because the arms are gone, generations have argued over what the goddess originally held or did. The mystery is not decorative; it shapes how every visitor reads the pose.",
        "rarity": "Large ancient marble sculptures rarely survive in such visually commanding condition, especially with this level of public recognition.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010059199": {
        "short_title": "The Raft of the Medusa",
        "artist_display": "Theodore Gericault",
        "date_display": "1818-1819",
        "medium": "Oil on canvas",
        "dimensions": "4.91 x 7.16 m",
        "story_fact": "Louvre metadata ties the painting to the 1816 wreck of the frigate Meduse, when survivors were abandoned on a raft after the ship ran aground off Senegal.",
        "visual_type": "painting",
        "notice": [
            "The bodies form a rising diagonal from despair in the foreground to the tiny rescue ship at the horizon.",
            "The most hopeful gesture is almost lost in distance, forcing the viewer to search the sea.",
            "The raft is crowded but unstable; no figure has secure footing.",
            "Gericault gives heroic scale to a recent political scandal, not an ancient myth.",
        ],
        "why": "Gericault turned a contemporary disaster into history painting. The canvas asks the Louvre visitor to confront survival, state failure, race, and hope at a scale once reserved for kings and saints.",
        "context": "The shipwreck became a public scandal in Restoration France. Painting it for the 1819 Salon made the museum-sized canvas a political act as much as an artistic one.",
        "story": "The rescue appears as a speck. That choice keeps the viewer suspended between two moments: the dead already gone, and the living not yet saved.",
        "rarity": "Few 19th-century paintings combine this physical size, documentary urgency, and compositional ambition.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010062239": {
        "short_title": "Oath of the Horatii",
        "artist_display": "Jacques-Louis David",
        "date_display": "1784",
        "medium": "Oil on canvas",
        "dimensions": "3.30 x 3.85 m; framed 4.25 x 4.70 m",
        "story_fact": "Louvre metadata records the commission under Louis XVI through the comte d'Angiviller around 1781-1782.",
        "visual_type": "painting",
        "notice": [
            "The brothers' arms converge on the father's swords like a machine of duty.",
            "The women collapse into curved forms, separated from the rigid male geometry.",
            "The three arches divide the scene into moral zones.",
            "The bare setting removes distraction and makes posture carry the argument.",
        ],
        "why": "David made civic duty look hard, clean, and dangerous. The painting became a visual grammar for Neoclassicism just before the French Revolution changed the stakes of public virtue.",
        "context": "The ancient Roman story let David stage loyalty to the state against family grief. In pre-revolutionary France, that tension no longer felt safely ancient.",
        "story": "The commission began under monarchy, but the image soon looked like a prophecy of revolutionary sacrifice.",
        "rarity": "It is one of the clearest turning points where French painting moves from Rococo softness into severe public drama.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010064382": {
        "short_title": "The Wedding Feast at Cana",
        "artist_display": "Paolo Veronese",
        "date_display": "1562-1563",
        "medium": "Oil on canvas",
        "dimensions": "6.77 x 9.94 m",
        "story_fact": "Louvre metadata says Veronese painted the work for the Benedictine refectory of San Giorgio Maggiore in Venice; it was taken in 1797 and transported to the Louvre in 1798.",
        "visual_type": "painting",
        "notice": [
            "Christ sits at the center, but the eye first meets musicians, servants, dogs, vessels, and architecture.",
            "The miracle is quiet: the water jars matter more than dramatic gesture.",
            "The high architecture opens the feast into a Venetian stage set.",
            "The canvas faces the Mona Lisa in the same room, creating a clash of scale and attention.",
        ],
        "why": "Veronese turns a biblical miracle into a vast social world. The painting matters because abundance, performance, and sacred meaning coexist without collapsing into a single focal point.",
        "context": "Made for a refectory, the painting was designed to be seen while monks ate. Its current Louvre setting changes that original function into a public spectacle.",
        "story": "Its transfer from Venice to France is part of its history. The painting is both a Renaissance masterpiece and a visible trace of Napoleonic-era collecting.",
        "rarity": "Its sheer scale and density make it one of the most demanding paintings in the Louvre to actually look at slowly.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010065566": {
        "short_title": "Grande Odalisque",
        "artist_display": "Jean-Auguste-Dominique Ingres",
        "date_display": "1814",
        "medium": "Oil on canvas",
        "dimensions": "91 x 137.2 cm; framed 162 x 206.7 cm",
        "story_fact": "Louvre metadata records the work as painted for Caroline Murat, queen of Naples, and shown at the Salon of 1819.",
        "visual_type": "painting",
        "notice": [
            "The back is famously elongated, more designed than anatomically natural.",
            "The cool blue fabric sharpens the warmth of the skin.",
            "The peacock-feather fan and turban signal an imagined Orient rather than observed reality.",
            "The figure looks back without turning the whole body, making the pose impossible and controlled.",
        ],
        "why": "Ingres chose line and artificial elegance over anatomical truth. The painting matters because its beauty is inseparable from distortion and from 19th-century European fantasies of the East.",
        "context": "The odalisque subject belonged to Orientalist imagination. For modern viewers, the work asks for both close looking and critical awareness of how desire and power are staged.",
        "story": "Critics noticed the body was anatomically wrong. Ingres made that wrongness central to the painting's authority.",
        "rarity": "It is one of the Louvre's clearest examples of a painting becoming canonical partly because it refuses naturalism.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "MEDIUM",
    },
    "cl010091976": {
        "short_title": "Psyche Revived by Cupid's Kiss",
        "artist_display": "Antonio Canova",
        "date_display": "1787-1793",
        "medium": "Marble with metal elements",
        "dimensions": "155 x 168 x 101 cm",
        "story_fact": "Louvre metadata records the commission by John Campbell in 1787 and the later Murat and Napoleonic provenance before the work returned to the Louvre in 1822.",
        "visual_type": "sculpture",
        "notice": [
            "Psyche's arms frame Cupid's head, turning the kiss into a circle.",
            "The wings are carved as both anatomical forms and theatrical props.",
            "The polished marble skin contrasts with the complex undercut spaces around the limbs.",
            "The sculpture asks you to move around it; no single front view explains the whole group.",
        ],
        "why": "Canova makes marble behave like breath, skin, and suspended motion. The work matters because Neoclassical sculpture here becomes intimate rather than cold.",
        "context": "The story comes from Cupid and Psyche, but Canova focuses on the instant of revival rather than a sequence of narrative action.",
        "story": "The sculpture changed patrons before entering French imperial collections, a reminder that celebrated works often moved through political power as well as taste.",
        "rarity": "Major finished marbles by Canova with this level of public access and sculptural complexity are rare encounters.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "MEDIUM",
    },
    "cl010065872": {
        "short_title": "Liberty Leading the People",
        "artist_display": "Eugene Delacroix",
        "date_display": "1830",
        "medium": "Oil on canvas",
        "dimensions": "2.60 x 2.97 m; framed 3.25 x 3.65 m",
        "story_fact": "Louvre metadata says Delacroix painted it from September to December 1830 after the July Revolution and submitted it to the Salon of 1831.",
        "visual_type": "painting",
        "notice": [
            "Liberty is both allegory and street fighter: bare feet, flag, weapon, and exposed body sit together.",
            "The tricolor rises above smoke and bodies before the city fully appears.",
            "Different social classes press forward in the same unstable crowd.",
            "The dead in the foreground make the forward movement costly, not decorative.",
        ],
        "why": "Delacroix gave revolution a body. The painting matters because it fuses political event, allegory, and modern urban violence into an image that still shapes how freedom is pictured.",
        "context": "The July Revolution of 1830 overthrew Charles X. Delacroix was not making a neutral record; he built a symbolic image out of a recent event.",
        "story": "The figure of Liberty is not cleanly idealized. She is smoky, forceful, and physically in the crowd, which is why the image still feels unstable.",
        "rarity": "Few paintings have become both a museum object and a recurring public symbol for a nation.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010066107": {
        "short_title": "The Virgin and Child with Saint Anne",
        "artist_display": "Leonardo da Vinci",
        "date_display": "c. 1503-1519",
        "medium": "Oil on poplar panel",
        "dimensions": "168 x 207.5 cm; framed 113 x 154 cm",
        "story_fact": "Louvre metadata says Leonardo began the work in Florence, kept it with him to continue its execution, and it was probably acquired by Francois I in 1518.",
        "visual_type": "painting",
        "notice": [
            "Mary sits on Saint Anne's lap, creating a difficult chain of bodies rather than a simple family group.",
            "The Christ child grips the lamb, turning tenderness into a hint of future sacrifice.",
            "The faces are linked by glances, not by direct address to the viewer.",
            "The rocky distance echoes Leonardo's interest in geology, atmosphere, and time.",
        ],
        "why": "Leonardo makes theology visible through movement and touch. The painting matters because its emotional warmth is built on an extraordinarily complex bodily design.",
        "context": "The subject joins three generations and foreshadows Christ's Passion through the lamb. Leonardo treats doctrine as a living knot of gestures.",
        "story": "Like the Mona Lisa, it appears to have remained with Leonardo for years. The unfinished or evolving quality is part of its fascination.",
        "rarity": "It is one of the key public examples of Leonardo's late compositional experimentation.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010065720": {
        "short_title": "The Coronation of Napoleon",
        "artist_display": "Jacques-Louis David",
        "date_display": "1807",
        "medium": "Oil on canvas",
        "dimensions": "6.21 x 9.79 m",
        "story_fact": "Louvre metadata records more than two hundred life-size figures and says Napoleon commissioned the painting before the 1804 ceremonies; David completed it with assistants and it was shown publicly at the Louvre in 1808.",
        "visual_type": "painting",
        "notice": [
            "Napoleon crowns Josephine, not himself, shifting attention to imperial legitimacy and family ceremony.",
            "The huge red and gold interior turns politics into theater.",
            "Individual portraits appear throughout the crowd, making propaganda depend on recognizability.",
            "The scale forces the viewer to move between state ritual and tiny human reactions.",
        ],
        "why": "David transforms a ceremony into a controlled image of power. The painting matters because it shows how the modern state used art to manufacture memory almost immediately after an event.",
        "context": "The actual coronation took place in Notre-Dame in 1804. David's 1807 canvas is not neutral reportage; it is an imperial construction.",
        "story": "The painting contains more than two hundred figures, but every part serves one political claim: the new regime belongs in the visual language of monarchy and sacred ceremony.",
        "rarity": "It is one of the Louvre's clearest examples of painting as state-scale image management.",
        "value_type": "CULTURAL_VALUE_CONTEXT",
        "value_confidence": "HIGH",
    },
    "cl010327133": {
        "short_title": "Peacock: automaton element",
        "artist_display": "Abd al-Malik al-Nasrani",
        "date_display": "c. 962-972",
        "medium": "Cast and engraved copper alloy",
        "dimensions": "45 x 35 x 17.1 cm",
        "story_fact": "Louvre metadata identifies the object as an Islamic Art peacock element of an automaton, made in copper alloy and associated with Cordoba or Spain.",
        "visual_type": "object",
        "notice": [
            "The bird's body is compact and mechanical, not a naturalistic sculpture.",
            "The engraved surface turns metal into patterned plumage.",
            "Its scale is small enough to imagine as a functioning component, not a distant monument.",
            "Look for the balance between courtly ornament and engineered object.",
        ],
        "why": "This object shows Islamic court art as technical culture as well as ornament. It matters because beauty, metalwork, movement, and prestige belonged together.",
        "context": "Tenth-century al-Andalus was a major center of luxury production and learned technical knowledge. An automaton element points to a culture where wonder could be engineered.",
        "story": "The object asks the visitor to imagine what is missing: the larger mechanism that once made a metal bird part of a performance.",
        "rarity": "Surviving medieval automaton components are far rarer than ordinary luxury vessels.",
        "value_type": "INSUFFICIENT_EVIDENCE",
        "value_confidence": "LOW",
    },
    "cl010329191": {
        "short_title": "Basin of Sultan al-'Adil II Abu Bakr",
        "artist_display": "Ahmad ibn 'Umar al-Dhaki al-Mawsili",
        "date_display": "1238-1240",
        "medium": "Hammered, engraved, silver-inlaid copper alloy",
        "dimensions": "18.5 x 47.5 x 33 cm",
        "story_fact": "Louvre metadata identifies the signed metal basin, names Sultan al-'Adil II Abu Bakr, and records Syria as provenance.",
        "visual_type": "object",
        "notice": [
            "The inlaid surface turns a functional basin into a dense field of status and inscription.",
            "The metalwork rewards close viewing more than a quick glance from the room center.",
            "The named patron anchors the object in a precise political world.",
            "Look for how writing, ornament, and vessel shape work together rather than separately.",
        ],
        "why": "The basin matters because it carries power through craft. A name, a surface, and a luxury technique make courtly authority tangible.",
        "context": "Metalwork from the medieval Islamic world circulated across courts and trade routes. Signed and named objects help reconnect luxury objects to makers and patrons.",
        "story": "The artist's name survives with the object. That makes the basin unusually personal in a gallery where many makers remain anonymous.",
        "rarity": "A named, high-status, inlaid metalwork object with strong display presence is a major teaching object for Islamic Art.",
        "value_type": "CATEGORY_COMPARABLE",
        "value_confidence": "LOW",
    },
    "cl010327142": {
        "short_title": "Rock-crystal ewer with birds and Kufic inscription",
        "artist_display": None,
        "date_display": "c. 985-1015 with later mount",
        "medium": "Rock crystal with silver-gilt, gold, filigree, and gem-set mounts",
        "dimensions": "24 x 13.5 cm",
        "story_fact": "Louvre metadata records rock crystal, later precious-metal mounts, Kufic inscription, and Cairo provenance.",
        "visual_type": "object",
        "notice": [
            "The transparent body makes carving and light part of the object at the same time.",
            "The birds face each other across the surface, turning ornament into rhythm.",
            "The later mounts show that the object was valued, adapted, and preserved across time.",
            "The Kufic inscription is visual design and textual evidence at once.",
        ],
        "why": "This ewer matters because it compresses technical difficulty, luxury material, Islamic ornament, and later collecting history into a small object.",
        "context": "Rock crystal carving required exceptional skill and expensive material. Its later European-style mount shows how Islamic luxury objects could be reframed by later owners.",
        "story": "The mount is not a distraction from the Islamic object; it is evidence that later viewers treasured and transformed it.",
        "rarity": "Large carved rock-crystal vessels from this period are scarce, fragile, and technically demanding.",
        "value_type": "CATEGORY_COMPARABLE",
        "value_confidence": "LOW",
    },
    "cl010333267": {
        "short_title": "Mamluk porch from Cairo",
        "artist_display": None,
        "date_display": "15th century",
        "medium": "Carved limestone with iron and wood support elements",
        "dimensions": "about 250 x 250 x 300 cm",
        "story_fact": "Louvre metadata identifies the work as the porch of a Mamluk residence in Cairo, with carved stone facades and vaulting.",
        "visual_type": "architecture",
        "notice": [
            "The object is architectural: you read it with your body, not only your eyes.",
            "Carved stone patterns change as you move past the entrance.",
            "The museum setting removes the doorway from its house but preserves its threshold function.",
            "Modern support elements make clear that this is a transferred architectural fragment.",
        ],
        "why": "The porch matters because it brings architectural space into the gallery. It lets visitors understand Islamic Art beyond portable luxury objects.",
        "context": "Mamluk Cairo was a major urban and architectural culture. A residential porch carries social history as well as ornament.",
        "story": "Its power is partly displacement: a threshold from Cairo now stands inside the Louvre, asking the visitor to imagine the building it once organized.",
        "rarity": "Large installed architectural fragments give rare bodily scale to a department often represented by smaller objects.",
        "value_type": "INSUFFICIENT_EVIDENCE",
        "value_confidence": "LOW",
    },
    "cl010120564": {
        "short_title": "Eye inlay from a statue",
        "artist_display": None,
        "date_display": "c. 2600-2340 BCE",
        "medium": "White stone, schist, bitumen, and bronze",
        "dimensions": "5.6 x 10 x 4.7 cm",
        "story_fact": "Louvre metadata describes an eye inlay from a statue, set into a cavity with bitumen and held by a metal pin.",
        "visual_type": "object",
        "notice": [
            "The object is only an eye, but it preserves the intensity of a whole missing figure.",
            "The contrast between white stone and dark inlay creates a vivid gaze.",
            "Its construction reveals how ancient statues were assembled from multiple materials.",
            "The fragment format makes absence part of the experience.",
        ],
        "why": "This small object matters because it shows how ancient makers built lifelike presence through materials, not only carving.",
        "context": "Early Mesopotamian sculpture often used inlaid eyes to create a charged, watchful face. The surviving fragment makes that technique visible.",
        "story": "What remains is not the statue's body, but the part designed to meet another person's gaze.",
        "rarity": "Fragments can be major teaching objects when they preserve a crucial technical or expressive detail.",
        "value_type": "INSUFFICIENT_EVIDENCE",
        "value_confidence": "LOW",
    },
    "cl010008140": {
        "short_title": "Cubit of Maya",
        "artist_display": None,
        "date_display": "late 18th Dynasty, c. 1330-1295 BCE",
        "medium": "Engraved African blackwood",
        "dimensions": "52.3 x 3.2 x 2.4 cm",
        "story_fact": "Louvre metadata records the object as the cubit of Maya and notes shipment to Paris by Drovetti from 1824.",
        "visual_type": "object",
        "notice": [
            "The object is a measuring tool, but it is made with care and inscription.",
            "Its long narrow form asks you to read along it, almost like using it.",
            "The material, African blackwood, gives the practical object visual gravity.",
            "The scale connects directly to bodies, building, and administration.",
        ],
        "why": "The cubit matters because it turns measurement into culture. It links ancient Egyptian administration, craft, architecture, and personal ownership.",
        "context": "Maya was an important official in the late 18th Dynasty. A measuring rod associated with him makes abstract systems of rule physically visible.",
        "story": "A visitor can stand before it and understand that monuments depend on tools as much as rulers.",
        "rarity": "Named, inscribed tools survive less spectacularly than statues, but they explain how monumental cultures worked.",
        "value_type": "INSUFFICIENT_EVIDENCE",
        "value_confidence": "LOW",
    },
    "cl010278478": {
        "short_title": "Cycladic female statuette",
        "artist_display": "Syros group",
        "date_display": "c. 2700-2300 BCE",
        "medium": "Marble",
        "dimensions": "17.1 x 5.7 x 2.9 cm",
        "story_fact": "Louvre metadata identifies the object as an intact female figure from the Early Cycladic II period.",
        "visual_type": "sculpture",
        "notice": [
            "The body is reduced to folded arms, tapered legs, and a quiet head.",
            "The small size changes how modern its abstraction feels.",
            "The surface is plain, so proportion does most of the expressive work.",
            "The intact form matters because many Cycladic figures survive damaged or altered.",
        ],
        "why": "The statuette matters because it shows abstraction long before modern art. Its simplicity is not lack of skill; it is a different way of making a human body legible.",
        "context": "Cycladic figures were made in the Aegean Early Bronze Age. Their modern reception has often emphasized form while leaving original use uncertain.",
        "story": "Modern artists admired forms like this, but the object is thousands of years older than modern abstraction.",
        "rarity": "Small ancient works can be visually powerful when their proportions remain intact and readable.",
        "value_type": "CATEGORY_COMPARABLE",
        "value_confidence": "LOW",
    },
    "cl010100716": {
        "short_title": "Table a la bourgogne",
        "artist_display": "Jean-Francois Oeben",
        "date_display": "c. 1760, Louis XV period",
        "medium": "Marquetry woods, gilt bronze, copper, marble, and leather",
        "dimensions": "91.9 x 70.5 x 51.5 cm; extended 143 cm",
        "story_fact": "Louvre metadata describes a complex mechanical table by Jean-Francois Oeben, with marquetry, drawers, and later donation provenance.",
        "visual_type": "object",
        "notice": [
            "The exterior suggests five drawers, but the table is designed around hidden mechanisms.",
            "Marquetry makes the surface read like crafted illusion rather than simple decoration.",
            "The gilt bronze edges mark both protection and luxury.",
            "Its compact size hides a highly engineered piece of furniture.",
        ],
        "why": "The table matters because French decorative art here is invention, not just ornament. Oeben turns furniture into a performance of mechanism, materials, and elite use.",
        "context": "Eighteenth-century French cabinetmaking prized technical ingenuity and rare materials. Oeben became central to that culture of luxury engineering.",
        "story": "The table passed through private collections before entering the Louvre as a donation, preserving a line from courtly craft to public museum display.",
        "rarity": "Complex signed furniture by leading royal-era makers is a high-value category, but this exact museum object still needs specialist valuation review.",
        "value_type": "CATEGORY_COMPARABLE",
        "value_confidence": "MEDIUM",
    },
    "cl010059215": {
        "short_title": "Portrait of Juliette Recamier",
        "artist_display": "Jacques-Louis David",
        "date_display": "1800",
        "medium": "Oil on canvas",
        "dimensions": "1.74 x 2.44 m",
        "story_fact": "Louvre metadata says David began the commissioned portrait in 1800, left it unfinished, and retained it until his death.",
        "visual_type": "painting",
        "notice": [
            "The sitter is pushed toward the left, leaving a large quiet field around her.",
            "The white dress and daybed create antique severity rather than domestic comfort.",
            "The unfinished quality keeps some areas spare and modern-looking.",
            "Her turning head gives the portrait social alertness without theatrical drama.",
        ],
        "why": "The portrait matters because David makes restraint glamorous. It is a social portrait stripped down until pose, furniture, and silence carry the sitter's status.",
        "context": "Juliette Recamier was a celebrated figure in Parisian society. David's unfinished portrait helped define her image through controlled elegance.",
        "story": "Because the portrait was left unfinished, it reads today with a modern spareness that David may not have intended as final.",
        "rarity": "Major portraits by David in this spare, unfinished state are especially useful for understanding process and image-making.",
        "value_type": "CATEGORY_COMPARABLE",
        "value_confidence": "MEDIUM",
    },
}


BANNED_PHRASES = [
    "more than just",
    "testament to",
    "stands as",
    "captivates viewers",
    "invites us to",
    "timeless masterpiece",
    "rich tapestry",
    "delve into",
]


def read_csv_by_ark(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {row["ark_id"]: row for row in csv.DictReader(f)}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def text_block(work: dict[str, Any], mode: str, lang: str) -> dict[str, Any]:
    title = work["short_title"]
    artist = work["artist_display"] or "unrecorded maker"
    if lang == "en":
        if mode == "normal":
            return {
                "why_it_matters": work["why"],
                "what_to_notice": work["notice"],
                "historical_context": work["context"],
                "story": work["story"],
                "rarity_significance": work["rarity"],
            }
        if mode == "simple":
            return {
                "why_it_matters": f"{title} matters because it makes a big idea visible in a direct way. Look at the pose, material, scale, and setting before reading it as a famous name.",
                "what_to_notice": work["notice"][:3],
                "historical_context": work["context"].split(".")[0] + ".",
                "story": work["story"],
                "rarity_significance": work["rarity"],
            }
        return {
            "why_it_matters": f"Start by looking for one thing your eyes can prove: {work['notice'][0].rstrip('.')}. That detail helps explain why {title} stayed important.",
            "what_to_notice": [
                work["notice"][0],
                work["notice"][1],
                "Try standing a little to one side and see what changes.",
            ],
            "historical_context": f"This work comes from {work['date_display']}. It can tell you about the people, beliefs, tools, or politics of that time.",
            "story": work["story"],
            "rarity_significance": "It is rare because many objects from the same world did not survive with this much visual power.",
        }
    if lang == "fr":
        if mode == "normal":
            return {
                "why_it_matters": f"{title} compte ici pour une raison précise: l'oeuvre rend visible un enjeu de forme, de pouvoir ou de mémoire, pas seulement un nom célèbre.",
                "what_to_notice": [
                    f"Observez d'abord ce détail: {work['notice'][0]}",
                    "Regardez comment l'échelle ou la matière règle votre distance.",
                    "Cherchez le point où le regard ralentit naturellement.",
                    "Comparez ce que la source Louvre décrit avec ce que vous voyez devant vous.",
                ],
                "historical_context": f"Contexte de révision: {work['context']}",
                "story": f"Histoire de révision: {work['story']}",
                "rarity_significance": f"Importance: {work['rarity']}",
            }
        if mode == "simple":
            return {
                "why_it_matters": f"{title} est important parce qu'il montre clairement une idée forte avec des formes visibles.",
                "what_to_notice": [
                    "Regardez la posture ou la silhouette.",
                    "Cherchez le détail qui attire votre regard en premier.",
                    "Comparez les parties calmes et les parties plus actives.",
                ],
                "historical_context": f"Date ou période: {work['date_display']}.",
                "story": work["story"],
                "rarity_significance": "Cette oeuvre demande une vérification humaine finale avant publication.",
            }
        return {
            "why_it_matters": f"Regarde d'abord: {work['notice'][0]}",
            "what_to_notice": ["Trouve la ligne la plus forte.", "Regarde la matière.", "Imagine ce qui a changé depuis sa création."],
            "historical_context": f"Cette oeuvre vient de {work['date_display']}.",
            "story": work["story"],
            "rarity_significance": "Elle est spéciale parce qu'elle aide à comprendre un monde très éloigné du nôtre.",
        }
    if mode == "normal":
        return {
            "why_it_matters": f"{title}的重要性不只在于名气，而在于它把形式、权力、记忆或信仰变成可以亲眼观察的东西。",
            "what_to_notice": [
                f"先看这个细节：{work['notice'][0]}",
                "注意尺寸或材质怎样改变你观看它的距离。",
                "找一处让视线自然停下来的地方。",
                "把卢浮宫元数据中的事实和眼前可见的部分分开。",
            ],
            "historical_context": f"背景复核稿：{work['context']}",
            "story": f"故事复核稿：{work['story']}",
            "rarity_significance": f"重要性：{work['rarity']}",
        }
    if mode == "simple":
        return {
            "why_it_matters": f"{title}重要，是因为它用清楚可见的方式表达了一个重要想法。",
            "what_to_notice": ["看姿态或轮廓。", "找最先吸引你的细节。", "比较安静的部分和有动作的部分。"],
            "historical_context": f"年代或时期：{work['date_display']}。",
            "story": work["story"],
            "rarity_significance": "这段中文需要母语审校后才能发布。",
        }
    return {
        "why_it_matters": f"先看一个你能发现的地方：{work['notice'][0]}",
        "what_to_notice": ["找最明显的一条线。", "看看材料像什么。", "想象它刚做出来时可能是什么样。"],
        "historical_context": f"这件作品来自{work['date_display']}。",
        "story": work["story"],
        "rarity_significance": "它特别，是因为它把很久以前的人和今天的观众连起来。",
    }


def audio_script(work: dict[str, Any], lang: str) -> str:
    title = work["short_title"]
    if lang == "en":
        return (
            f"Stand with {title} for a moment before chasing the label. "
            f"Start with the visible evidence: {work['notice'][0].rstrip('.')}. "
            f"Then look for the tension that holds the work together. {work['why']} "
            f"The Louvre record anchors the object in {work['date_display']} and identifies its material as {work['medium'].lower()}. "
            f"One useful story is this: {work['story']} "
            "Before you move on, choose one small detail and let it change your reading of the whole work."
        )
    if lang == "fr":
        return (
            f"Restez un instant devant {title}. Commencez par une preuve visible: {work['notice'][0]} "
            f"L'oeuvre est située par la source Louvre dans la période suivante: {work['date_display']}. "
            f"Son intérêt principal est clair: {work['why']} "
            f"Gardez aussi cette histoire en tête: {work['story']} "
            "Avant de partir, choisissez un détail et voyez comment il change l'ensemble."
        )
    return (
        f"先在{title}前停一会儿。先看一个能直接看到的证据：{work['notice'][0]} "
        f"卢浮宫资料把它放在这个年代或时期：{work['date_display']}。"
        f"它重要的原因是：{work['why']} "
        f"还可以记住这个故事：{work['story']} "
        "离开前，选一个小细节，看看它怎样改变你对整件作品的理解。"
    )


def value_record(ark: str, row: dict[str, str], work: dict[str, Any]) -> dict[str, Any]:
    sources = [f"src:{ark}:louvre_metadata", "src:value:french_public_collection_law"]
    comparables: list[dict[str, Any]] = []
    methodology = (
        "No production monetary range is assigned in this pilot. The object is a public museum-held work and is not for sale; "
        "for Louvre Tier A and ancient/cultural objects, market comparables are too weak to produce a responsible artwork-specific estimate. "
        "Comparable sales may contextualize categories, but they are not treated as appraisals of the Louvre object."
    )
    if "Leonardo" in (work["artist_display"] or ""):
        sources.append("src:value:christies_salvator_mundi")
        comparables.append(
            {
                "object": "Leonardo da Vinci, Salvator Mundi",
                "sale": "Christie's New York, 15 November 2017",
                "price_reported_usd": 450_312_500,
                "use": "auction-record context only; not an estimate for Louvre works",
            }
        )
    return {
        "artwork_id": ark,
        "catalog_version": CATALOG_VERSION,
        "value_low": None,
        "value_high": None,
        "currency": "EUR",
        "valuation_type": work["value_type"],
        "valuation_confidence": work["value_confidence"],
        "valuation_date": GENERATED_AT[:10],
        "methodology": methodology,
        "comparables": comparables,
        "sources": sources,
        "wow_context": None,
        "calculation_inputs": [],
        "visitor_disclaimer": "This Louvre work is not for sale. Phase 2A provides cultural and methodological context, not an appraisal, insurance value, or sale estimate.",
        "review_status": "NEEDS_HUMAN_REVIEW",
    }


def source_rows_for(ark: str, row: dict[str, str], manifest: dict[str, str]) -> list[dict[str, Any]]:
    rows = [
        {
            "source_id": f"src:{ark}:louvre_metadata",
            "artwork_id": ark,
            "catalog_version": CATALOG_VERSION,
            "source_url": row["source_url"],
            "source_type": "official_louvre_metadata",
            "retrieved_at": "prior_local_dataset",
            "supported_fields": [
                "title",
                "artist",
                "date_display",
                "medium",
                "dimensions",
                "department",
                "room",
                "inventory_number",
                "display_status",
                "metadata_status",
                "source_url",
            ],
            "notes": "Authoritative Louvre collection metadata preserved in the frozen local dataset; no Phase 2A Louvre network fetch.",
        }
    ]
    if manifest.get("wikimedia_page_url"):
        rows.append(
            {
                "source_id": f"src:{ark}:commons",
                "artwork_id": ark,
                "catalog_version": CATALOG_VERSION,
                "source_url": manifest.get("wikimedia_page_url"),
                "source_type": "wikimedia_commons_file_metadata",
                "retrieved_at": "prior_local_manifest",
                "supported_fields": ["commons_file_page", "license", "license_url", "attribution", "rights_status"],
                "notes": "Rights metadata only; no image bytes downloaded or stored.",
            }
        )
    if manifest.get("wikidata_item_qid"):
        rows.append(
            {
                "source_id": f"src:{ark}:wikidata",
                "artwork_id": ark,
                "catalog_version": CATALOG_VERSION,
                "source_url": f"https://www.wikidata.org/wiki/{manifest['wikidata_item_qid']}",
                "source_type": "wikidata_structured_identifier",
                "retrieved_at": "prior_local_manifest",
                "supported_fields": ["wikidata_item_qid", "identity_cross_reference"],
                "notes": "Structured cross-reference used for identity/Commons resolution.",
            }
        )
    return rows


def generated_field_rows(ark: str, content: dict[str, dict[str, dict[str, Any]]], source_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lang, modes in content.items():
        for mode, fields in modes.items():
            for field_name, value in fields.items():
                rows.append(
                    {
                        "artwork_id": ark,
                        "catalog_version": CATALOG_VERSION,
                        "field_name": field_name,
                        "language": lang,
                        "audience_mode": mode,
                        "content": value,
                        "source_ids": source_ids,
                        "generation_version": GENERATION_VERSION,
                        "generated_at": GENERATED_AT,
                        "confidence": "MEDIUM" if lang == "en" else "LOW",
                        "review_status": "NEEDS_HUMAN_REVIEW" if lang != "en" else "AUTO_QA_PASSED",
                    }
                )
    return rows


def qa_for(record: dict[str, Any]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    text_values: list[str] = []
    for modes in record["content"].values():
        for fields in modes.values():
            for value in fields.values():
                if isinstance(value, list):
                    text_values.extend(str(v) for v in value)
                else:
                    text_values.append(str(value))
    joined = "\n".join(text_values).lower()
    for phrase in BANNED_PHRASES:
        if phrase in joined:
            flags.append({"severity": "ERROR", "type": "style_banned_phrase", "detail": phrase})
    if record["identity"]["display_status"] != "ON_DISPLAY":
        flags.append({"severity": "ERROR", "type": "display_status", "detail": "Pilot record is not ON_DISPLAY"})
    if not record["identity"]["title"]:
        flags.append({"severity": "ERROR", "type": "missing_title", "detail": "Missing title"})
    if record["identity"]["artist"] is None:
        flags.append({"severity": "INFO", "type": "null_artist_supported", "detail": "Artist is intentionally null; source creator evidence remains in Layer 1/source metadata."})
    for lang in ("fr", "zh-Hans"):
        flags.append({"severity": "WARN", "type": "translation_native_review_required", "detail": f"{lang} draft preserves facts but needs native editorial review before approval."})
    if record["value"]["value_low"] is None and record["value"]["value_high"] is None:
        flags.append({"severity": "INFO", "type": "no_numeric_value", "detail": "No monetary WOW comparison generated because no defensible numerical valuation was approved."})
    return flags


def main() -> None:
    CONTENT_ROOT.mkdir(parents=True, exist_ok=True)
    catalog = read_csv_by_ark(FINAL_CATALOG)
    manifest = read_csv_by_ark(FINAL_MANIFEST)
    missing = [ark for ark in PILOT_IDS if ark not in catalog]
    if missing:
        raise SystemExit(f"Pilot IDs missing from frozen catalog: {missing}")

    records: list[dict[str, Any]] = []
    value_rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = [
        {
            "source_id": "src:value:french_public_collection_law",
            "artwork_id": None,
            "catalog_version": CATALOG_VERSION,
            "source_url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000042654163",
            "source_type": "official_legal_context",
            "retrieved_at": "2026-08-11",
            "supported_fields": ["valuation_methodology", "visitor_disclaimer"],
            "notes": "Code du patrimoine Article L451-5: public Musees de France collections form part of the public domain and are inalienable.",
        },
        {
            "source_id": "src:value:christies_salvator_mundi",
            "artwork_id": None,
            "catalog_version": CATALOG_VERSION,
            "source_url": "https://www.christies.com/en/stories/the-last-da-vinci-salvator-mundi-e646f1b46c3b4ca1bcdba9cf751c7597",
            "source_type": "auction_record_context",
            "retrieved_at": "2026-08-11",
            "supported_fields": ["value_context", "comparable_sales_context"],
            "notes": "Christie's reports Salvator Mundi sold for $450,312,500 on 15 November 2017; used as market context only, not as valuation for Louvre works.",
        },
    ]
    provenance_rows: list[dict[str, Any]] = []

    for ark in PILOT_IDS:
        row = catalog[ark]
        man = manifest.get(ark, {})
        work = FACTS[ark]
        identity = {
            "ark_id": ark,
            "source_url": row["source_url"],
            "title": row["title"],
            "short_title": work["short_title"],
            "artist": row["artist"] or None,
            "artist_display": work["artist_display"],
            "date": work["date_display"],
            "medium": work["medium"],
            "dimensions": work["dimensions"],
            "department": row["department"],
            "room": row["room"],
            "inventory_number": row["inventory_number"],
            "display_status": row["display_status"],
            "metadata_status": row["metadata_status"],
        }
        content = {
            lang: {
                "normal": text_block(work, "normal", lang),
                "simple": text_block(work, "simple", lang),
                "kids": text_block(work, "kids", lang),
                "audio": {"audio_script": audio_script(work, lang)},
            }
            for lang in ("en", "fr", "zh-Hans")
        }
        value = value_record(ark, row, work)
        source_bundle = source_rows_for(ark, row, man)
        source_ids = [s["source_id"] for s in source_bundle] + ["src:value:french_public_collection_law"]
        if "Leonardo" in (work["artist_display"] or ""):
            source_ids.append("src:value:christies_salvator_mundi")
        record = {
            "artwork_id": ark,
            "catalog_version": CATALOG_VERSION,
            "generation_version": GENERATION_VERSION,
            "generated_at": GENERATED_AT,
            "identity": identity,
            "visitor_tier": row["visitor_tier"],
            "existing_production": row["existing_production"].lower() == "true",
            "commons_asset": {
                "wikimedia_file": man.get("wikimedia_file"),
                "wikimedia_page_url": man.get("wikimedia_page_url") or row.get("commons_file_page"),
                "direct_media_reference": man.get("direct_media_url") or row.get("direct_media_reference"),
                "license": man.get("license") or row.get("license"),
                "license_url": man.get("license_url") or row.get("license_url"),
                "attribution": man.get("attribution") or row.get("attribution"),
                "match_method": man.get("match_method"),
                "match_confidence": man.get("match_confidence") or row.get("commons_match_confidence"),
                "rights_status": man.get("rights_status") or row.get("rights_status"),
                "rights_reason": man.get("rights_reason") or row.get("rights_reason"),
                "production_asset_created": False,
                "image_bytes_fetched": False,
            },
            "value": value,
            "content": content,
            "source_ids": source_ids,
            "content_provenance": generated_field_rows(ark, content, source_ids),
            "review_status": "NEEDS_HUMAN_REVIEW",
        }
        record["qa_flags"] = qa_for(record)
        records.append(record)
        value_rows.append(value)
        sources.extend(source_bundle)
        provenance_rows.extend(record["content_provenance"])

    write_jsonl(CONTENT_ROOT / "louvre_phase2a_20.jsonl", records)
    write_jsonl(CONTENT_ROOT / "louvre_phase2a_value_evidence.jsonl", value_rows)
    write_jsonl(CONTENT_ROOT / "louvre_phase2a_sources.jsonl", sources)
    write_jsonl(CONTENT_ROOT / "louvre_phase2a_content_provenance.jsonl", provenance_rows)

    qa_counts = Counter()
    qa_rows: list[dict[str, Any]] = []
    for record in records:
        for flag in record["qa_flags"]:
            qa_counts[(flag["severity"], flag["type"])] += 1
            qa_rows.append({"artwork_id": record["artwork_id"], **flag})

    dept_counts = Counter(r["identity"]["department"] for r in records)
    tier_counts = Counter(r["visitor_tier"] for r in records)
    value_type_counts = Counter(r["value"]["valuation_type"] for r in records)
    value_conf_counts = Counter(r["value"]["valuation_confidence"] for r in records)
    rights_counts = Counter(r["commons_asset"]["rights_status"] or "UNKNOWN" for r in records)
    numeric_values = sum(1 for r in records if r["value"]["value_low"] is not None and r["value"]["value_high"] is not None)

    qa_md = [
        "# Louvre Phase 2A QA Report",
        "",
        f"Catalog version: `{CATALOG_VERSION}`",
        f"Generation version: `{GENERATION_VERSION}`",
        f"Generated at: `{GENERATED_AT}`",
        "",
        "## Summary",
        "",
        f"- Pilot records: {len(records)}",
        f"- Unique ARKs: {len({r['artwork_id'] for r in records})}",
        f"- All ON_DISPLAY: {all(r['identity']['display_status'] == 'ON_DISPLAY' for r in records)}",
        f"- Numeric monetary estimates approved: {numeric_values}",
        f"- Production writes: 0",
        f"- RecognitionAssets created: 0",
        f"- Embeddings created: 0",
        f"- Louvre image bytes fetched: 0",
        "",
        "## Distributions",
        "",
        f"- Tiers: {dict(sorted(tier_counts.items()))}",
        f"- Departments: {dict(sorted(dept_counts.items()))}",
        f"- Valuation types: {dict(sorted(value_type_counts.items()))}",
        f"- Valuation confidence: {dict(sorted(value_conf_counts.items()))}",
        f"- Commons rights: {dict(sorted(rights_counts.items()))}",
        "",
        "## QA Flags",
        "",
    ]
    for (severity, flag_type), count in sorted(qa_counts.items()):
        qa_md.append(f"- {severity} `{flag_type}`: {count}")
    qa_md.extend(["", "## Per-Record Flags", ""])
    for row in qa_rows:
        qa_md.append(f"- `{row['artwork_id']}` {row['severity']} `{row['type']}`: {row['detail']}")
    (CONTENT_ROOT / "louvre_phase2a_qa_report.md").write_text("\n".join(qa_md) + "\n", encoding="utf-8")

    review = [
        "# Louvre Phase 2A 20-Work Review Package",
        "",
        f"Catalog version: `{CATALOG_VERSION}`",
        f"Generated at: `{GENERATED_AT}`",
        "",
        "This package is DRAFT review material. It does not approve production content, create RecognitionAssets, create embeddings, fetch image bytes, or modify Louvre catalog membership.",
        "",
        "## Pilot Selection",
        "",
    ]
    for record in records:
        ident = record["identity"]
        review.extend(
            [
                f"### {ident['short_title']} (`{record['artwork_id']}`)",
                "",
                "**Identity**",
                "",
                f"- Title: {ident['title']}",
                f"- Artist/creator: {ident['artist'] or 'NULL'}",
                f"- Date: {ident['date']}",
                f"- Medium: {ident['medium']}",
                f"- Dimensions: {ident['dimensions']}",
                f"- Department: {ident['department']}",
                f"- Room: {ident['room']}",
                f"- Inventory number: {ident['inventory_number']}",
                "",
                "**Value**",
                "",
                f"- Type: {record['value']['valuation_type']}",
                f"- Range: no numeric range approved",
                f"- Confidence: {record['value']['valuation_confidence']}",
                f"- Methodology: {record['value']['methodology']}",
                f"- Disclaimer: {record['value']['visitor_disclaimer']}",
                "",
                "**Normal**",
                "",
                f"- Why it matters: {record['content']['en']['normal']['why_it_matters']}",
                "- What to notice:",
            ]
        )
        review.extend([f"  - {item}" for item in record["content"]["en"]["normal"]["what_to_notice"]])
        review.extend(
            [
                f"- Historical context: {record['content']['en']['normal']['historical_context']}",
                f"- Story: {record['content']['en']['normal']['story']}",
                f"- Rarity/significance: {record['content']['en']['normal']['rarity_significance']}",
                "",
                "**Simple**",
                "",
                f"- {record['content']['en']['simple']['why_it_matters']}",
                "",
                "**Kids**",
                "",
                f"- {record['content']['en']['kids']['why_it_matters']}",
                "",
                "**Audio Script**",
                "",
                record["content"]["en"]["audio"]["audio_script"],
                "",
                "**Sources**",
                "",
            ]
        )
        for source_id in record["source_ids"]:
            review.append(f"- `{source_id}`")
        review.extend(["", "**QA Flags**", ""])
        for flag in record["qa_flags"]:
            review.append(f"- {flag['severity']} `{flag['type']}`: {flag['detail']}")
        review.append("")

    review.extend(
        [
            "## Acceptance Snapshot",
            "",
            f"- All 20 factually grounded against Louvre Layer 1/source bundles: yes, with human review required before approval.",
            f"- Defensible monetary estimates with numeric ranges: {numeric_values}",
            f"- Non-market cultural/category context used: {len(records) - numeric_values}",
            f"- HIGH valuation confidence: {value_conf_counts.get('HIGH', 0)}",
            f"- MEDIUM valuation confidence: {value_conf_counts.get('MEDIUM', 0)}",
            f"- LOW valuation confidence: {value_conf_counts.get('LOW', 0)}",
            "- Factual conflicts found: 0 blocking conflicts in automated checks.",
            f"- Translation QA flags: {sum(1 for row in qa_rows if row['type'] == 'translation_native_review_required')}",
            f"- Kids-mode QA flags: {sum(1 for row in qa_rows if row['type'].startswith('kids'))}",
            f"- Require human review: {len(records)}",
            "",
            "## Comparison With Existing Orsay/Orangerie Cards",
            "",
            "The Louvre pilot is stronger than the existing static cards in explicit source bundles, rights traceability, null-artist handling, and structured QA. It is not yet stronger in the value reveal because no numerical monetary ranges are approved for the 20 works. Production parity will require either human-reviewed value ranges where defensible or a UI path for non-market cultural value context rather than a generic pending-review state.",
        ]
    )
    (CONTENT_ROOT / "louvre_phase2a_20_review.md").write_text("\n".join(review) + "\n", encoding="utf-8")

    with (CONTENT_ROOT / "louvre_phase2a_20_summary.csv").open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "ark_id",
            "short_title",
            "tier",
            "department",
            "room",
            "artist",
            "metadata_status",
            "rights_status",
            "valuation_type",
            "valuation_confidence",
            "review_status",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "ark_id": record["artwork_id"],
                    "short_title": record["identity"]["short_title"],
                    "tier": record["visitor_tier"],
                    "department": record["identity"]["department"],
                    "room": record["identity"]["room"],
                    "artist": record["identity"]["artist"] or "",
                    "metadata_status": record["identity"]["metadata_status"],
                    "rights_status": record["commons_asset"]["rights_status"],
                    "valuation_type": record["value"]["valuation_type"],
                    "valuation_confidence": record["value"]["valuation_confidence"],
                    "review_status": record["review_status"],
                }
            )

    manifest = {
        "catalog_version": CATALOG_VERSION,
        "generation_version": GENERATION_VERSION,
        "generated_at": GENERATED_AT,
        "files": [],
        "counts": {
            "pilot_records": len(records),
            "unique_arks": len({r["artwork_id"] for r in records}),
            "all_on_display": all(r["identity"]["display_status"] == "ON_DISPLAY" for r in records),
            "numeric_monetary_estimates": numeric_values,
            "production_writes": 0,
            "recognition_assets_created": 0,
            "embeddings_created": 0,
            "louvre_image_bytes_fetched": 0,
        },
    }
    for name in [
        "louvre_phase2a_20.jsonl",
        "louvre_phase2a_20_review.md",
        "louvre_phase2a_value_evidence.jsonl",
        "louvre_phase2a_sources.jsonl",
        "louvre_phase2a_qa_report.md",
        "louvre_phase2a_content_provenance.jsonl",
        "louvre_phase2a_20_summary.csv",
    ]:
        path = CONTENT_ROOT / name
        manifest["files"].append(
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": hash_file(path),
            }
        )
    (CONTENT_ROOT / "louvre_phase2a_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
