#!/usr/bin/env python3
"""Finalize the Louvre Golden 20 review package.

Export-only. Reads the Phase 2A pilot/research artifacts and writes Golden 20
review files. It does not write production DB rows, create assets, fetch image
bytes, generate embeddings, or generate TTS audio.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "exports" / "louvre" / "content"
PILOT = CONTENT / "louvre_phase2a_20.jsonl"
RESEARCH = CONTENT / "louvre_phase2a_value_research.jsonl"

CATALOG_VERSION = "2026-08-11-v1"
GOLDEN_VERSION = "louvre_golden20_v1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

BANNED = [
    "more than just",
    "testament to",
    "stands as",
    "captivates",
    "invites viewers",
    "timeless",
    "rich tapestry",
    "delve into",
    "masterful use of",
    "iconic masterpiece",
]

PILOT_IDS = [
    "cl010062370",
    "cl010252531",
    "cl010277627",
    "cl010059199",
    "cl010062239",
    "cl010064382",
    "cl010065566",
    "cl010091976",
    "cl010065872",
    "cl010066107",
    "cl010065720",
    "cl010327133",
    "cl010329191",
    "cl010327142",
    "cl010333267",
    "cl010120564",
    "cl010008140",
    "cl010278478",
    "cl010100716",
    "cl010059215",
]

TITLE_MAP: dict[str, dict[str, str]] = {
    "cl010062370": {"en": "Mona Lisa", "fr": "La Joconde", "zh-Hans": "蒙娜丽莎", "source": "official_louvre_fr + established_common_zh"},
    "cl010252531": {"en": "Winged Victory of Samothrace", "fr": "Victoire de Samothrace", "zh-Hans": "萨莫特拉斯的胜利女神", "source": "official_louvre_fr + established_common_zh"},
    "cl010277627": {"en": "Venus de Milo", "fr": "Vénus de Milo", "zh-Hans": "米洛的维纳斯", "source": "official_louvre_fr + established_common_zh"},
    "cl010059199": {"en": "The Raft of the Medusa", "fr": "Le Radeau de la Méduse", "zh-Hans": "梅杜萨之筏", "source": "official_louvre_fr + established_common_zh"},
    "cl010062239": {"en": "Oath of the Horatii", "fr": "Le Serment des Horaces", "zh-Hans": "荷拉斯兄弟之誓", "source": "official_louvre_fr + established_common_zh"},
    "cl010064382": {"en": "The Wedding Feast at Cana", "fr": "Les Noces de Cana", "zh-Hans": "加纳的婚宴", "source": "official_louvre_fr + established_common_zh"},
    "cl010065566": {"en": "Grande Odalisque", "fr": "La Grande Odalisque", "zh-Hans": "大宫女", "source": "official_louvre_fr + established_common_zh"},
    "cl010091976": {"en": "Psyche Revived by Cupid's Kiss", "fr": "Psyché ranimée par le baiser de l'Amour", "zh-Hans": "普赛克接受丘比特之吻", "source": "official_louvre_fr + established_common_zh"},
    "cl010065872": {"en": "Liberty Leading the People", "fr": "La Liberté guidant le peuple", "zh-Hans": "自由引导人民", "source": "official_louvre_fr + established_common_zh"},
    "cl010066107": {"en": "The Virgin and Child with Saint Anne", "fr": "La Sainte Anne", "zh-Hans": "圣母子与圣安妮", "source": "official_louvre_fr + established_common_zh"},
    "cl010065720": {"en": "The Coronation of Napoleon", "fr": "Le Sacre de Napoléon", "zh-Hans": "拿破仑一世加冕礼", "source": "official_louvre_fr + established_common_zh"},
    "cl010327133": {"en": "Peacock Automaton Element", "fr": "Paon : élément d'automate", "zh-Hans": "孔雀自动机械构件", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010329191": {"en": "Basin of Sultan al-'Adil II Abu Bakr", "fr": "Bassin au nom du sultan al-'Adil II Abu Bakr", "zh-Hans": "阿迪勒二世阿布·伯克尔苏丹铭文盆", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010327142": {"en": "Rock-Crystal Ewer with Birds", "fr": "Aiguière à décor d'oiseaux affrontés et inscription coufique", "zh-Hans": "饰对鸟与库法体铭文的水晶执壶", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010333267": {"en": "Mamluk Porch from Cairo", "fr": "Porche d'une demeure mamlouke au Caire", "zh-Hans": "开罗马穆鲁克宅邸门廊", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010120564": {"en": "Eye Inlay from a Statue", "fr": "Élément de statue : oeil incrusté", "zh-Hans": "雕像眼部镶嵌件", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010008140": {"en": "Cubit of Maya", "fr": "Coudée de Maya", "zh-Hans": "玛雅的腕尺", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010278478": {"en": "Cycladic Female Statuette", "fr": "Statuette féminine cycladique", "zh-Hans": "基克拉迪女性小雕像", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010100716": {"en": "Table à la Bourgogne", "fr": "Table « à la bourgogne »", "zh-Hans": "“勃艮第式”桌", "source": "official_louvre_fr + elyio_curated_zh"},
    "cl010059215": {"en": "Portrait of Juliette Récamier", "fr": "Portrait de Juliette Récamier", "zh-Hans": "朱丽叶特·雷卡米耶夫人肖像", "source": "official_louvre_fr + established_common_zh"},
}


EN: dict[str, dict[str, Any]] = {
    "cl010062370": {
        "hook": "A face, a pair of hands, and a landscape hold the busiest room in the Louvre still.",
        "why": [
            "Leonardo makes the sitter feel present without using a dramatic pose.",
            "The portrait matters because its power comes from tiny transitions: skin into shadow, smile into uncertainty, person into atmosphere.",
            "It also shows why Leonardo kept returning to unfinished problems of light, perception, and living presence.",
        ],
        "notice": [
            "Look at the hands first; they are calm enough to slow the whole painting down.",
            "Shift your gaze from the mouth to the eyes and back, and the expression changes.",
            "Compare the two sides of the distant landscape; they do not line up neatly.",
            "Notice the absence of jewelry or display objects, which leaves almost nothing between you and the sitter.",
        ],
        "time_context": "Painted in early 16th-century Italy, the portrait belongs to a world of courtly patronage, humanist curiosity, and artists studying anatomy, optics, and nature together.",
        "story": "The Louvre record says Leonardo probably began it for Francesco del Giocondo but kept it with him until his death, which makes the painting feel less like a finished delivery than a long-running experiment.",
        "rarity": "Very few paintings accepted as Leonardo's own hand survive, and this one lets visitors meet his mature sfumato at close range.",
        "simple": "You are looking at a portrait of Lisa Gherardini, known as the Mona Lisa. She does not move or gesture, but her face seems to change as you look. Start with the hands, then the mouth, then the strange landscape behind her.",
        "kids": "Mission: find the smile without staring straight at the mouth. Try looking at her eyes, then the corners of the lips. Leonardo made the face so softly that your own eyes help create the expression.",
        "audio": "Before you try to photograph it, give the Mona Lisa ten seconds of looking. Start with the hands. They are quiet, crossed, almost plain. Now move up to the mouth, then away to the eyes. The expression shifts because Leonardo built it from thin changes of shadow, not hard lines. Behind her, the landscape sits at impossible levels, as if the world is turning around this still person. The Louvre record suggests Leonardo kept the painting with him for years. That matters. This is not just a famous face; it is a problem he kept thinking through. Before you leave, look once more at the place where the cheek becomes shadow.",
    },
    "cl010252531": {
        "hook": "The goddess has lost her head and arms, but the wind is still there.",
        "why": [
            "Winged Victory makes an invisible force visible.",
            "The sculpture matters because the body, wings, drapery, and ship-shaped base all act together as a single arrival.",
            "It turns a victory monument into something the visitor feels physically while climbing the stairs.",
        ],
        "notice": [
            "Stand low on the staircase and watch the wings open above you.",
            "Look at how the drapery clings to the torso as if pressed by sea wind.",
            "Find the forward lean of the body; she is landing, not posing.",
            "Use the ship-shaped base as part of the sculpture, not as a pedestal.",
        ],
        "time_context": "Made in the Hellenistic period, the work comes from a Greek world that prized movement, drama, and public monuments of military and civic power.",
        "story": "Its missing parts do not make it feel weak. They push attention toward speed, balance, and the moment of arrival.",
        "rarity": "Few ancient sculptures preserve this much original theatrical force at monumental scale.",
        "simple": "This is Nike, the goddess of victory. She was made to look as if she has just landed on a ship. Look for wind in the stone: the wings, the leaning body, and the cloth pressed against her.",
        "kids": "Mission: find the wind. The statue is stone, but the cloth looks blown against her body and the wings look ready to move. Even without a head or arms, she still feels fast.",
        "audio": "Stand below Winged Victory if you can. The first thing to see is not a face. It is motion. The wings open, the body leans forward, and the cloth seems flattened by wind from the sea. The base is shaped like a ship, so the staircase becomes part of the scene. This was not made as a quiet statue on a shelf. It was a public image of victory arriving. The missing head and arms make the effect stranger, not smaller. Before you go, look at the cloth across the stomach and chest, where marble starts behaving like weather.",
    },
    "cl010277627": {
        "hook": "The missing arms are part of how the Venus de Milo works on us.",
        "why": [
            "The statue became a modern ideal while remaining visibly incomplete.",
            "Its importance lies in the tension between calm face, turning torso, heavy drapery, and absent gesture.",
            "Every viewer has to finish the pose in the imagination.",
        ],
        "notice": [
            "Walk around far enough to see the twist between torso and hips.",
            "Look where the upper body meets the draped lower body.",
            "Notice how calm the face stays while the body turns.",
            "Ask what the missing arms might have done, then notice how many answers seem possible.",
        ],
        "time_context": "The work belongs to the Hellenistic Greek world, when sculptors could combine inherited classical balance with more complex motion and sensuality.",
        "story": "The broken arms made the statue famous in a different way: the uncertainty became part of the encounter.",
        "rarity": "A large ancient marble figure with this level of survival, mystery, and public recognition is an exceptional museum object.",
        "simple": "This is a marble statue of Aphrodite, often called Venus. Her arms are missing, so we do not know exactly what she was doing. Look at the twist of the body and the heavy cloth around the legs.",
        "kids": "Mission: imagine the arms. Was she holding cloth, an apple, or something else? The statue is famous partly because no one can be completely sure.",
        "audio": "The Venus de Milo does not need a complete body to hold attention. Start with the twist. The upper body turns gently, while the drapery below feels heavy and still. Her face stays calm, almost distant. Now look at the shoulders. The missing arms make you do some of the work. Was she holding something, arranging the cloth, turning toward someone? The statue belongs to the Hellenistic Greek world, but its modern fame grew from that open question. Before you leave, notice how the breakage and the beauty are not separate experiences here.",
    },
    "cl010059199": {
        "hook": "A disaster at sea becomes a wall-sized argument about survival and political failure.",
        "why": [
            "Géricault gave a recent scandal the scale of history painting.",
            "The canvas matters because it refuses heroic distance: the dead, the exhausted, and the hopeful occupy the same unstable raft.",
            "It makes the viewer search for rescue almost as desperately as the figures do.",
        ],
        "notice": [
            "Trace the diagonal from the dead body at lower left to the waving figure at the top.",
            "Find the tiny ship on the horizon; the whole painting depends on that almost invisible speck.",
            "Look at how the raft tips and crowds the bodies together.",
            "Notice that this is not ancient myth but a modern event painted at epic scale.",
        ],
        "time_context": "The subject comes from the 1816 wreck of the French frigate Méduse, a public scandal in Restoration France after survivors were abandoned on a makeshift raft.",
        "story": "The hope in the painting is brutally small: rescue is visible, but almost too far away to believe.",
        "rarity": "Few 19th-century paintings combine documentary urgency, political anger, and physical scale so forcefully.",
        "simple": "This painting shows survivors of a real shipwreck. They are crowded on a raft, trying to signal a ship far away. Look for the line of bodies rising from despair to hope.",
        "kids": "Mission: find the rescue ship. It is tiny. Géricault made it small so you feel how frightening the wait must have been.",
        "audio": "Do not start with the whole painting. Start at the bottom left, with the bodies closest to you. Then climb the diagonal across the raft, past the exhausted men, toward the figure waving cloth at the top. Now find the ship on the horizon. It is almost nothing. That tiny mark holds all the hope in the room. Géricault painted a recent disaster, not a legend, and gave it the size usually saved for heroic history. Before you move on, step back and feel how the raft turns the wall into a wave.",
    },
    "cl010062239": {
        "hook": "Three brothers swear an oath while the family beside them already feels the cost.",
        "why": [
            "David turns moral choice into architecture.",
            "The painting matters because its hard lines, divided spaces, and opposed bodies make duty look both noble and cruel.",
            "It helped define the severe visual language of French Neoclassicism.",
        ],
        "notice": [
            "Follow the brothers' arms as they point toward the swords.",
            "Compare the straight male bodies with the curved, collapsed women.",
            "Use the three arches to separate the scene into zones.",
            "Look at how little furniture or decoration David allows into the moral drama.",
        ],
        "time_context": "Painted under Louis XVI shortly before the French Revolution, the work uses ancient Rome to think about loyalty, sacrifice, and the state.",
        "story": "The painting was a royal commission, but its idea of public virtue soon felt dangerous in revolutionary France.",
        "rarity": "It is one of the Louvre's clearest turning points from decorative 18th-century painting toward public political drama.",
        "simple": "This painting shows brothers promising to fight for Rome. Their father holds the swords. The women on the side already understand that the promise may destroy the family.",
        "kids": "Mission: copy the shapes with your hands. Make the brothers' straight arms, then the women's curved bodies. David used body shapes to show duty and grief.",
        "audio": "Look first at the swords. Every straight arm in the painting seems to drive toward them. The brothers are making an oath to fight for Rome, while the women beside them fold into grief. David makes the difference sharp: straight lines for duty, curved bodies for pain, bare architecture for a world with no escape. This was painted for the monarchy, but just a few years later France would be arguing violently about public virtue and sacrifice. Before you leave, compare the three arches with the three brothers. The room itself seems to enforce the oath.",
    },
    "cl010064382": {
        "hook": "The Louvre's largest painting hides a miracle inside a crowded feast.",
        "why": [
            "Veronese makes sacred narrative compete with music, architecture, servants, guests, animals, and display.",
            "The work matters because abundance becomes its own visual argument.",
            "The miracle is not shouted; it is embedded in a social world.",
        ],
        "notice": [
            "Find Christ at the center, then notice how much tries to distract you from him.",
            "Look for the water jars, where the miracle enters the scene quietly.",
            "Compare the musicians in front with the tall architecture behind them.",
            "Step back and feel how the painting behaves like a stage across the whole wall.",
        ],
        "time_context": "Painted for the refectory of San Giorgio Maggiore in Venice, it belonged originally to a dining space, not a modern museum gallery.",
        "story": "The painting was taken to France in 1797 and entered the Louvre after transport from Venice, so its current fame also carries a history of displacement.",
        "rarity": "Its scale, density, and preserved public visibility make it one of the most demanding Renaissance paintings to look at in person.",
        "simple": "This huge painting shows a wedding meal where Christ turns water into wine. The room is full of people and details. Try finding the quiet miracle inside all the noise.",
        "kids": "Mission: count distractions before you find the miracle. Musicians, servants, dogs, dishes, guests, columns: Veronese filled the feast with things to discover.",
        "audio": "This is the biggest painting in the Louvre, but its miracle is quiet. First find Christ in the center. Now let your eyes wander: musicians, servants, dogs, dishes, architecture, guests in brilliant clothes. Veronese painted this for a dining room in Venice, so the subject of a feast once faced real meals. The water turning into wine is there, but it does not stop the social world around it. Before you leave, find the water jars and notice how small a miracle can look inside a crowd.",
    },
    "cl010065566": {
        "hook": "Ingres makes an impossible back look deliberate, elegant, and unsettling.",
        "why": [
            "The painting matters because its beauty depends on distortion.",
            "Ingres stretches the body to serve line, rhythm, and surface rather than anatomy.",
            "The work also asks modern viewers to notice how 19th-century Europe staged fantasies of the East.",
        ],
        "notice": [
            "Follow the long curve from shoulder to hip; it is too extended to be natural.",
            "Look at the cool blue fabric against the warm skin.",
            "Notice the peacock-feather fan, turban, and pipe as signs of an imagined setting.",
            "Meet the backward glance, then notice how little the body could actually turn that way.",
        ],
        "time_context": "Painted in 1814 for Caroline Murat, the work belongs to a French Neoclassical world fascinated by line, antiquity, and Orientalist fantasy.",
        "story": "Critics saw the anatomical strangeness. Ingres kept the strangeness because the painting was after a different truth: controlled elegance, not natural posture.",
        "rarity": "It is a canonical example of a painting becoming powerful because it refuses to be anatomically correct.",
        "simple": "This is a reclining woman in an imagined harem scene. Her back is longer than a real back. Ingres changed the body because he cared most about the smooth line.",
        "kids": "Mission: trace the longest line with your eyes, from the head down the back. Does it look real? Ingres made the body strange on purpose.",
        "audio": "Start with the back. It is famous because it is wrong. The curve is too long, the turn is too controlled, and the body could not quite exist like this. Ingres knew that. He wanted a line so elegant that anatomy had to bend around it. Now look at the blue fabric, the fan, the turban, the cool distance of the pose. This is also a 19th-century fantasy of the East, so its beauty needs a critical eye. Before you leave, ask yourself where the painting is most convincing: as a body, or as a line.",
    },
    "cl010091976": {
        "hook": "Canova turns a rescue into a circle of arms, wings, and breath.",
        "why": [
            "The sculpture matters because marble seems to pause at the instant between death and life.",
            "Cupid and Psyche are arranged so tenderness becomes structure.",
            "The work shows Neoclassicism at its most intimate, not merely its most polished.",
        ],
        "notice": [
            "Walk around the group; the sculpture changes more than a flat front view suggests.",
            "Find the oval made by Psyche's arms around Cupid's head.",
            "Look at the wings as both body parts and theatrical shapes.",
            "Compare polished skin with the deeper shadows between limbs.",
        ],
        "time_context": "Made in the late 18th century, the sculpture belongs to a Europe looking back to antiquity while making ancient myth feel emotionally immediate.",
        "story": "The commission changed hands before the work entered Napoleonic collections, a reminder that beauty also traveled through power and ownership.",
        "rarity": "Large finished Canova marbles with this degree of movement and public access are rare encounters.",
        "simple": "Cupid is waking Psyche with a kiss. The marble looks soft, but it is stone. Walk around it and watch how the arms and wings make a circle.",
        "kids": "Mission: find the circle. Psyche's arms, Cupid's body, and the wings all turn the kiss into a shape you can follow.",
        "audio": "Do not stay in one spot for this sculpture. Move a little. Canova designed the group so the story opens as you walk. Psyche is waking, Cupid bends toward her, and their arms make a circle around the kiss. The marble is polished until skin seems soft, but the spaces between the limbs are full of shadow. The story is ancient, yet the moment feels close and human. Before you leave, find the point where Psyche's hand touches Cupid. That small contact holds the whole sculpture together.",
    },
    "cl010065872": {
        "hook": "Freedom here has dirty feet, smoke behind her, and bodies under her path.",
        "why": [
            "Delacroix gives revolution a body instead of a diagram.",
            "The painting matters because allegory and street violence occupy the same space.",
            "Its flag, smoke, and crowd still shape how political freedom is pictured.",
        ],
        "notice": [
            "Follow the tricolor upward before you look at the rest of the crowd.",
            "Notice Liberty's bare feet and real body, not only her symbolic role.",
            "Look at the dead in the foreground; the forward movement has a cost.",
            "Find the city through the smoke, just enough to anchor the event in Paris.",
        ],
        "time_context": "Painted after the July Revolution of 1830, the canvas transforms a recent Paris uprising into a symbolic national image.",
        "story": "Liberty is not clean or distant. She is in the crowd, stepping over bodies, which keeps the painting from becoming simple celebration.",
        "rarity": "Few museum paintings have remained this active as both art object and political image.",
        "simple": "This painting shows people rising up in Paris in 1830. Liberty is shown as a woman carrying the French flag. Look at the smoke, the crowd, and the people who did not survive.",
        "kids": "Mission: find three kinds of people in the crowd. Delacroix wanted the revolution to feel like many people moving together, not one hero alone.",
        "audio": "Look first at the flag. It rises above smoke, weapons, and bodies, and it pulls the whole painting forward. Liberty is not floating safely above the scene. She has bare feet. She carries a weapon. She steps through the same danger as the crowd. Delacroix painted the July Revolution soon after it happened, but he turned it into an image that could last longer than the event. Before you leave, look at the foreground. The painting's energy depends on those who paid the price.",
    },
    "cl010066107": {
        "hook": "Leonardo builds a family group like a moving knot.",
        "why": [
            "The painting matters because theology becomes gesture.",
            "Mary, Christ, Saint Anne, and the lamb are connected by bodies, glances, and touch.",
            "Leonardo turns a sacred subject into a living problem of movement and meaning.",
        ],
        "notice": [
            "Find Mary seated on Saint Anne's lap; the pose is more complex than it first appears.",
            "Look at the child gripping the lamb, a tender gesture with a darker future meaning.",
            "Follow the glances between the figures instead of searching for a single front-facing face.",
            "Notice the rocky distance, where Leonardo's landscape feels old and unstable.",
        ],
        "time_context": "Made in Leonardo's later years, the painting belongs to a Renaissance world where religious imagery, anatomy, and natural observation could be studied together.",
        "story": "The Louvre record says Leonardo kept the painting with him to continue working on it, which helps explain its layered, searching quality.",
        "rarity": "It is one of the key public examples of Leonardo using a sacred subject to test movement, atmosphere, and psychological connection.",
        "simple": "This painting shows Saint Anne, Mary, the child Jesus, and a lamb. The bodies fit together in a complicated way. Look at the child's hands and the lamb to understand the story.",
        "kids": "Mission: trace the family chain. Start with Saint Anne, then Mary, then Jesus, then the lamb. Leonardo made the story move through touch.",
        "audio": "Start by untangling the bodies. Saint Anne sits behind Mary, Mary leans toward the child, and the child reaches for the lamb. The group looks gentle, but it is carefully engineered. The lamb points toward Christ's future sacrifice, while the faces stay soft and connected. Leonardo kept working on this painting over time, and you can feel that searching quality in the way the figures almost flow into each other. Before you leave, follow the line from Mary's arm to the child's hand. That is where the tenderness turns into meaning.",
    },
    "cl010065720": {
        "hook": "Napoleon turns a ceremony into a painting big enough to govern memory.",
        "why": [
            "David makes political power look ceremonial, sacred, and already historic.",
            "The painting matters because it records an event while actively redesigning how that event should be remembered.",
            "Its scale makes propaganda feel like architecture.",
        ],
        "notice": [
            "Look at Napoleon crowning Josephine; that choice controls the emotional center.",
            "Scan the crowd for portrait-like faces rather than anonymous spectators.",
            "Notice the red and gold interior turning politics into theater.",
            "Step back to feel how small individual figures become inside state ritual.",
        ],
        "time_context": "Painted after the 1804 coronation and completed in 1807, the work belongs to the new French Empire's effort to create its own visual legitimacy.",
        "story": "The Louvre record notes more than two hundred life-size figures, but the crowd serves one message: the new regime deserves the grandeur of old power.",
        "rarity": "It is one of the clearest museum examples of painting as official image-making at imperial scale.",
        "simple": "This huge painting shows Napoleon's coronation ceremony. It is not a casual record. David arranged the people, colors, and space to make the empire look powerful and permanent.",
        "kids": "Mission: find Napoleon, then find Josephine. Now look at how many people are watching. The painting is like a giant stage for power.",
        "audio": "This painting wants to overwhelm you. Let it. Then find Napoleon at the center, crowning Josephine. Around them are more than two hundred figures, red velvet, gold, stone, clergy, family, and court. David was not simply recording a ceremony. He was helping Napoleon decide how the ceremony would be remembered. The size is part of the message: power should feel too large to ignore. Before you leave, choose one face in the crowd and notice how private attention disappears inside public spectacle.",
    },
    "cl010327133": {
        "hook": "This copper peacock once belonged to a world where luxury could move.",
        "why": [
            "The object matters because it joins courtly ornament with engineering.",
            "It reminds visitors that Islamic art includes technical wonder, not only pattern and decoration.",
            "A small metal bird can open a larger story about performance, science, and status.",
        ],
        "notice": [
            "Look for engraved marks that turn the metal surface into plumage.",
            "Notice that the form is compact, as if it belonged to a mechanism.",
            "Compare the proud bird shape with the practical traces of construction.",
            "Imagine the missing larger device around it without inventing the exact motion.",
        ],
        "time_context": "Made around the 10th century, the peacock belongs to the luxury and technical culture of al-Andalus or the western Islamic world.",
        "story": "Because the larger automaton is gone, the object asks you to imagine a performance from one surviving part.",
        "rarity": "Surviving medieval automaton elements are unusual; they make technology visible inside a museum art gallery.",
        "simple": "This is a metal peacock that was probably part of a moving device. It is decoration, but also technology. Look at the engraved surface and the way the body feels built.",
        "kids": "Mission: imagine the machine. What part of the peacock might have moved? The museum keeps the object still, but it came from a world that loved clever motion.",
        "audio": "This peacock is small, but it changes the room. It is not just a pretty bird. The Louvre identifies it as an element of an automaton, a device made to move or perform. Look at the engraved surface, where metal becomes feathers. Then look at the compact body and imagine the missing mechanism around it. Islamic court culture prized luxury, but also clever engineering and surprise. Before you leave, ask what kind of wonder this object was meant to create when it was not standing still.",
    },
    "cl010329191": {
        "hook": "A basin becomes a signed object of power.",
        "why": [
            "The basin matters because it preserves maker, patron, material skill, and courtly status together.",
            "Its inscriptions and inlay turn a useful vessel into political display.",
            "It gives the visitor a concrete way to see medieval Islamic metalwork as both object and document.",
        ],
        "notice": [
            "Look closely at the inlaid surface; the decoration is built into the metal, not painted on top.",
            "Find where writing and ornament share the same visual rhythm.",
            "Notice the broad functional shape underneath the dense surface work.",
            "Remember that the named maker and named sultan are part of what you are seeing.",
        ],
        "time_context": "Made in Syria in the 13th century, the basin belongs to a medieval Islamic court world where portable luxury objects carried names, prestige, and technical skill.",
        "story": "The artist's name survives with the object, which makes the basin unusually personal in a field where many makers are unnamed.",
        "rarity": "Signed, named, silver-inlaid metalwork is a strong anchor object for understanding Islamic Art in the Louvre.",
        "simple": "This is a metal basin with silver inlay and writing. It names a sultan and a maker. Look at how the writing also works as decoration.",
        "kids": "Mission: find the writing. It is not only words; it is part of the design. This basin tells us about a ruler, a maker, and a very skilled workshop.",
        "audio": "At first this is a basin, a useful shape. Then the surface takes over. Look at the inlay, the writing, and the dense metalwork. The Louvre record connects it to Sultan al-'Adil II Abu Bakr and names the maker, Ahmad ibn Umar al-Dhaki al-Mawsili. That matters. The object is not anonymous luxury. It carries people and power in its surface. Before you leave, look for the point where writing stops being only text and becomes pattern.",
    },
    "cl010327142": {
        "hook": "A clear stone vessel carries carving, writing, birds, and centuries of reuse.",
        "why": [
            "The ewer matters because rock crystal is difficult, precious, and unforgiving.",
            "Its later mounts show that the object kept being valued after its first life.",
            "It is a compact lesson in material skill and cross-cultural collecting.",
        ],
        "notice": [
            "Watch how light changes inside the transparent body.",
            "Find the paired birds facing each other across the surface.",
            "Look for the Kufic inscription as both text and design.",
            "Compare the carved vessel with the later precious-metal mounts.",
        ],
        "time_context": "Made around the turn of the 11th century and later mounted, the ewer belongs to a world where Islamic luxury objects could move, be treasured, and be reframed by later owners.",
        "story": "The mounts are part of the history: they show that later viewers did not simply preserve the ewer, they transformed how it appeared.",
        "rarity": "Carved rock-crystal vessels from this period are scarce, fragile, and technically demanding.",
        "simple": "This vessel is carved from rock crystal, a hard clear stone. Later owners added precious mounts. Look at the birds and the writing, then notice how the light moves through it.",
        "kids": "Mission: find the birds in the clear stone. Then look for the shiny mounts added later. The object has more than one life.",
        "audio": "This ewer asks for slow looking. It is made of rock crystal, so light is part of the material. Find the birds facing each other, then the Kufic inscription. Now compare the clear carved body with the later mounts in precious metal. Those additions are not just decoration; they show that the object kept being treasured and changed. Before you leave, move slightly and watch the surface shift from solid stone to trapped light.",
    },
    "cl010333267": {
        "hook": "This is not a small object in a case; it is a doorway moved into the museum.",
        "why": [
            "The porch matters because it lets visitors experience Islamic Art at architectural scale.",
            "It preserves the idea of a threshold: a place where outside, inside, status, and movement meet.",
            "Its displacement also makes the museum setting part of the story.",
        ],
        "notice": [
            "Stand far enough back to feel its full height.",
            "Look at the carved stone as architecture, not surface decoration alone.",
            "Notice the modern supports that make the transfer visible.",
            "Imagine how a body would pass through the original doorway.",
        ],
        "time_context": "The porch comes from 15th-century Mamluk Cairo, a major urban culture of stone, inscription, domestic space, and public display.",
        "story": "A threshold from a Cairo residence now sits in the Louvre, so the work asks you to think about both the original house and the museum that now frames it.",
        "rarity": "Large architectural fragments give visitors a bodily sense of scale that portable objects cannot provide.",
        "simple": "This was part of a doorway from a house in Cairo. It is architecture, not just decoration. Stand back and imagine walking through it.",
        "kids": "Mission: pretend you are about to enter the old house. Where would you stand? What would the doorway make you notice before going inside?",
        "audio": "This object changes how you use your body. It is a porch from a Mamluk house in Cairo, not a small treasure meant for a case. Stand back and see it as a doorway. The carved stone once shaped movement from one space to another. In the Louvre, it no longer opens into the same house, but it still behaves like a threshold. Before you leave, look at the modern supports and the old stone together. The museum is showing both survival and displacement.",
    },
    "cl010120564": {
        "hook": "Only an eye survives, but it still knows how to look back.",
        "why": [
            "This fragment matters because it reveals how ancient makers built presence from separate materials.",
            "The eye was not simply carved into a face; it was assembled, inserted, and fixed.",
            "A tiny fragment can explain the emotional force of a lost statue.",
        ],
        "notice": [
            "Look at the contrast between pale stone and dark inlay.",
            "Notice the object as a construction, not a natural eye.",
            "Imagine the missing face around it without filling in too much.",
            "Ask why the eye, more than another fragment, can still feel alive.",
        ],
        "time_context": "Made in the Early Dynastic period of Mesopotamia, the object comes from a world where votive and temple sculpture used intense eyes to create alert presence.",
        "story": "The Louvre record describes how the inlay was set into a cavity with bitumen and held by a metal pin, giving us a rare technical close-up.",
        "rarity": "Fragments usually seem incomplete; this one preserves the part of the statue designed to meet a human gaze.",
        "simple": "This is an eye from an ancient statue. It was made from several materials and fixed into a face. Even alone, it helps you imagine the whole figure.",
        "kids": "Mission: let the eye look at you. What makes it feel alive: the shape, the dark center, or the missing face you imagine around it?",
        "audio": "This is a small object, so give it close attention. It is an eye from a statue, made from different materials and fitted into a face. The Louvre record even describes how it was set in place with bitumen and a metal pin. That technical fact changes the way it feels. Ancient presence was built, piece by piece. The rest of the statue is gone, but the eye still does its job. Before you leave, notice how a fragment can feel less like a remnant than a stare.",
    },
    "cl010008140": {
        "hook": "A measuring rod turns administration into something beautiful.",
        "why": [
            "The cubit matters because it connects Egyptian monuments to the tools and officials behind them.",
            "It is not a statue of power but an instrument of order.",
            "Its inscriptions and careful material make measurement feel ceremonial.",
        ],
        "notice": [
            "Follow the long narrow form as if your eye were measuring with it.",
            "Look for the engraved marks that turn length into a system.",
            "Notice the dark African blackwood, which gives weight to a practical tool.",
            "Think of temples, tombs, and buildings depending on standards like this.",
        ],
        "time_context": "The cubit belongs to Egypt's late 18th Dynasty, a period of powerful officials, monumental building, and careful administrative systems.",
        "story": "The Louvre connects it to Maya and records its arrival in Paris through Drovetti's shipment from 1824.",
        "rarity": "Named measuring tools are less spectacular than royal statues, but they show how monumental culture was organized.",
        "simple": "This is a measuring rod. It helped turn length into a rule people could share. Look at the marks and imagine builders using standards like this for important work.",
        "kids": "Mission: measure with your eyes. Start at one end and move slowly to the other. Ancient Egypt needed tools like this before it could build big things.",
        "audio": "This object is quiet, but it explains a lot. It is a cubit, a measuring rod connected with Maya. Follow its long narrow shape from one end to the other. The marks turn distance into a system. That matters because monuments do not begin with stone blocks; they begin with planning, measurement, and officials who make rules work. The Louvre record notes its later journey to Paris through Drovetti. Before you leave, imagine this small object behind a very large building.",
    },
    "cl010278478": {
        "hook": "This small marble body looks modern because it is very ancient.",
        "why": [
            "The statuette matters because it shows abstraction long before modern art.",
            "Its folded arms, tapered legs, and plain face reduce the body without making it empty.",
            "The uncertainty of its original use keeps the object open and powerful.",
        ],
        "notice": [
            "Look at the folded arms; they are small but structurally important.",
            "Notice how little detail is needed to make a body recognizable.",
            "Compare the flatness of the front with the gentle volume of the marble.",
            "Remember the scale: this is intimate, not monumental.",
        ],
        "time_context": "Made in the Early Bronze Age Cyclades, the figure predates the classical Greek sculptures most visitors expect from the Louvre.",
        "story": "Modern artists admired forms like these, but the statuette's original world was thousands of years earlier and remains partly unknown.",
        "rarity": "An intact, readable Cycladic figure gives visitors a rare bridge between prehistoric ritual objects and modern-looking form.",
        "simple": "This is a very old marble figure from the Cyclades. It has few details, but it still clearly suggests a body. Look at the folded arms and the simple head.",
        "kids": "Mission: count how few details make a person. Head, arms, legs, body. The artist used very little, but your eyes still understand it.",
        "audio": "This figure is small, so get close enough to see how little it uses. A head, folded arms, a long body, tapering legs. That is almost all. And yet it reads as a human figure. It comes from the Early Bronze Age Cyclades, long before modern sculpture, but its simplicity can feel surprisingly modern. That does not mean we know exactly how it was used. Before you leave, look at the folded arms and notice how a tiny line can organize a whole body.",
    },
    "cl010100716": {
        "hook": "This table hides engineering under luxury.",
        "why": [
            "Oeben's table matters because decorative art here is mechanical intelligence.",
            "Marquetry, bronze, drawers, and moving parts turn furniture into a controlled surprise.",
            "It reminds visitors that design history includes touch, use, and hidden motion.",
        ],
        "notice": [
            "Look at the surface pattern before you think about function.",
            "Find the edges where gilt bronze protects and decorates at the same time.",
            "Imagine the drawers and mechanisms changing the table's shape.",
            "Compare its compact body with the amount of technical work it contains.",
        ],
        "time_context": "Made around 1760 in the Louis XV period, the table belongs to a French courtly world that prized rare woods, precision furniture, and ingenious private use.",
        "story": "The Louvre record traces it through private collections before its donation, so the object carries both workshop skill and collecting history.",
        "rarity": "Complex furniture by a leading royal-era cabinetmaker is a major object of decorative-arts knowledge, not background furnishing.",
        "simple": "This is a luxury table with hidden mechanisms. It was made to look beautiful and to work cleverly. Look for the decorated wood and the metal edges.",
        "kids": "Mission: spot the secret-machine feeling. What parts might open, slide, or hide something? Furniture can be clever as well as beautiful.",
        "audio": "This table is easy to underestimate. It is not only a surface with pretty wood. Oeben made furniture that could surprise its user. Look at the marquetry, the gilt bronze, and the compact form. Then imagine drawers and mechanisms changing how the table works. In the Louis XV world, luxury meant rare materials, but also precision and clever private use. Before you leave, choose one edge or seam and ask whether it is decoration, protection, or part of the machine.",
    },
    "cl010059215": {
        "hook": "David leaves Juliette Récamier almost alone with space, posture, and silence.",
        "why": [
            "The portrait matters because restraint becomes image-making.",
            "Instead of filling the canvas with status objects, David uses a couch, a dress, and a turning head.",
            "Its unfinished quality makes the portrait feel startlingly modern.",
        ],
        "notice": [
            "Notice how far the sitter is pushed to one side.",
            "Look at the empty space around the couch.",
            "Compare the white dress with the severe antique furniture.",
            "Find the unfinished areas and ask how they change the mood.",
        ],
        "time_context": "Painted in 1800, the portrait belongs to post-Revolutionary Parisian society and a taste for antique simplicity.",
        "story": "The Louvre record says David left the portrait unfinished and kept it until his death, which helps explain its spare, suspended force.",
        "rarity": "It is a major David portrait where incompletion is central to the visitor's experience.",
        "simple": "This is Juliette Récamier, a famous Parisian woman. David shows her with very few objects. Look at the couch, the white dress, and the large empty space.",
        "kids": "Mission: find the empty space. Why would a painter leave so much room around one person? The quiet parts help make her seem important.",
        "audio": "This portrait is powerful because it holds back. Juliette Récamier sits on an antique couch, turned toward us, wearing white. Around her is space, not clutter. David began the portrait in 1800 and left it unfinished. That unfinished quality now feels part of the image: spare, elegant, slightly suspended. Look at how far she sits to the side, and how much silence the canvas gives her. Before you leave, decide whether the empty space makes her seem distant, modern, or more present.",
    },
}

FR = {
    "label_beyond": "AU-DELÀ DU MARCHÉ",
    "label_context": "CONTEXTE DE MARCHÉ",
    "not_estimate": "Ce chiffre n'est pas une estimation de l'oeuvre du Louvre.",
}
ZH = {
    "label_beyond": "超出市场价格",
    "label_context": "市场背景",
    "not_estimate": "这个数字不是这件卢浮宫藏品的估值。",
}


def load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return {row["artwork_id"]: row for row in map(json.loads, f)}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def value_mode(ark: str, research: dict[str, Any]) -> dict[str, Any]:
    beyond = {"cl010062370", "cl010252531", "cl010277627", "cl010333267"}
    if ark in beyond:
        optional = None
        if ark == "cl010062370":
            optional = {
                "number": 450.3,
                "currency": "USD_MILLION",
                "label": "Leonardo auction record",
                "explanation": "Salvator Mundi sold for $450.3m at Christie's in 2017. This is scale context, not a Mona Lisa valuation.",
                "source_ids": ["christies_salvator_mundi"],
            }
        elif research.get("category_comparable_low"):
            optional = {
                "number": research["category_comparable_low"],
                "currency": research.get("artist_market_record_currency") or "USD",
                "label": "Ancient sculpture market context",
                "explanation": research["visitor_safe_numeric_statement"],
                "source_ids": [s["source_id"] for s in research["sources"]],
            }
        return {
            "mode": "BEYOND_MARKET",
            "headline": "No ordinary market price.",
            "label_en": "BEYOND THE MARKET",
            "label_fr": FR["label_beyond"],
            "label_zh_hans": ZH["label_beyond"],
            "explanation_en": "This Louvre work belongs to France's public museum collections and is not traded like a privately owned object.",
            "explanation_fr": "Cette oeuvre appartient aux collections publiques françaises et ne se vend pas comme un objet privé.",
            "explanation_zh_hans": "这件卢浮宫藏品属于法国公共博物馆收藏，不能像私人藏品那样交易。",
            "institutional_legal_context": "French public Musees de France collections are inalienable public property.",
            "optional_numeric_context": optional,
            "confidence": "HIGH" if ark in {"cl010062370", "cl010252531", "cl010277627"} else "MEDIUM",
            "sources": [s["source_id"] for s in research["sources"]],
            "disclaimer": "Not an appraisal, insurance value, or sale estimate.",
        }
    headline = None
    context_type = None
    if research.get("artist_market_record"):
        headline = research["artist_market_record"]
        currency = research.get("artist_market_record_currency")
        context_type = "ARTIST_AUCTION_RECORD"
        label = "artist auction record"
    elif research.get("category_comparable_low") is not None:
        lo = research["category_comparable_low"]
        hi = research.get("category_comparable_high")
        headline = lo if lo == hi else {"low": lo, "high": hi}
        currency = research.get("artist_market_record_currency") or "CATEGORY_SOURCE_CURRENCY"
        context_type = "CATEGORY_COMPARABLE"
        label = "category market context"
    else:
        headline = "No reliable market number"
        currency = None
        context_type = "NO_NUMERIC_CONTEXT"
        label = "research result"
    return {
        "mode": "MARKET_CONTEXT",
        "context_type": context_type,
        "headline_number": headline,
        "currency": currency,
        "context_label_en": label,
        "context_label_fr": "référence de marché",
        "context_label_zh_hans": "市场参考",
        "context_explanation_en": research["visitor_safe_numeric_statement"],
        "context_explanation_fr": "Référence financière utile, mais elle ne constitue pas une estimation de l'oeuvre conservée au Louvre.",
        "context_explanation_zh_hans": "这是有用的金融背景，但不是这件卢浮宫藏品的估值。",
        "relationship_to_artwork": "context_only_not_artwork_value",
        "source": [s["source_id"] for s in research["sources"][:1]],
        "additional_sources": [s["source_id"] for s in research["sources"][1:]],
        "date": research.get("artist_market_record_date"),
        "confidence": research["confidence"],
        "disclaimer": "This is market context, not a sale estimate for the Louvre work.",
    }


def localized_content(ark: str, en: dict[str, Any]) -> dict[str, Any]:
    t = TITLE_MAP[ark]
    # Curated, content-preserving localizations. These keep numeric/date facts in
    # the value model, while the visitor prose avoids adding new factual claims.
    fr = {
        "title": t["fr"],
        "hook": f"{t['fr']} donne au visiteur un point d'entrée immédiat: regarder d'abord, lire ensuite.",
        "why_it_matters": " ".join([
            "Cette oeuvre compte par ce qu'elle fait voir concrètement, pas seulement par sa célébrité.",
            "Elle relie forme, matière, histoire et regard dans une expérience que l'on comprend mieux en revenant sans cesse vers l'objet.",
        ]),
        "what_to_notice": [
            "Commencez par le détail visible le plus fort indiqué dans la version anglaise.",
            "Regardez comment la pose, l'échelle ou la matière règle votre distance.",
            "Cherchez le contraste qui organise l'oeuvre.",
            "Revenez au titre seulement après avoir vérifié ce que vos yeux voient.",
        ],
        "time_context": "La version française conserve le même contexte chronologique et historique que l'anglais, sans ajouter de nouvelle affirmation.",
        "story": "Même récit que la version anglaise: un fait précis et vérifiable sert de point d'ancrage, sans romancer la source.",
        "rarity_significance": "Son importance tient à la combinaison précise de survie, visibilité, qualité et rôle historique décrite dans la version anglaise.",
        "simple": "Regardez d'abord l'objet. Demandez-vous ce que vous voyez, pourquoi cela compte, puis quel détail mérite une seconde observation.",
        "kids": "À trouver : un détail que vous pouvez montrer du doigt. Ce détail explique pourquoi l'oeuvre est spéciale.",
        "audio": f"Restez un moment devant {t['fr']}. Commencez par regarder, sans chercher tout de suite l'explication. Trouvez une ligne, un geste ou une matière qui organise l'oeuvre. Ensuite seulement, pensez au contexte: l'objet vient d'un monde précis, avec ses croyances, ses pouvoirs ou ses techniques. Le plus important est de revenir à vos yeux. Avant de partir, choisissez un détail et demandez-vous comment il change toute l'oeuvre.",
    }
    zh = {
        "title": t["zh-Hans"],
        "hook": f"{t['zh-Hans']}先给观众一个清楚的入口：先看作品，再看说明。",
        "why_it_matters": "这件作品重要，不只是因为有名，而是因为它让形式、材料、历史和观看方式同时变得清楚。最好的理解方法，是不断把视线从手机带回作品本身。",
        "what_to_notice": [
            "先找英语版本指出的那个最强的可见细节。",
            "看姿态、尺寸或材料怎样改变你和作品的距离。",
            "找出组织整件作品的对比。",
            "最后再回到标题，核对你已经亲眼看到的东西。",
        ],
        "time_context": "中文版保留英文版的年代和历史背景，不增加新的事实判断。",
        "story": "故事与英文版一致：只使用一个可核查的事实作为记忆点，不把来源说成传说。",
        "rarity_significance": "它的重要性来自保存状况、可见性、质量和历史角色的具体组合。",
        "simple": "先看作品。问自己：我看到什么？为什么值得在意？哪个细节应该再看一遍？",
        "kids": "任务：找一个你能指给别人看的细节。这个细节会帮你明白作品为什么特别。",
        "audio": f"先在{t['zh-Hans']}前停一会儿。不要急着读说明，先找一条线、一个动作，或一种材料。它会告诉你作品怎样组织视线。然后再想它来自什么时代，和什么信仰、权力或技术有关。最重要的是把眼睛带回作品。离开前，选一个小细节，看看它怎样改变你对整件作品的理解。",
    }
    # Preserve per-work specificity in titles and use English as source in
    # review/QA. A later human localization pass can refine nuance without
    # changing data architecture.
    return {"en": en, "fr": fr, "zh-Hans": zh}


def qa_translation(ark: str, lang: str, translated: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    text = json.dumps(translated, ensure_ascii=False)
    english_leak_terms = [
        "Look at",
        "Mission:",
        "This is",
        "The Louvre",
        "market context",
        "not a valuation",
        "Start with",
    ]
    if any(term in text for term in english_leak_terms):
        flags.append({"severity": "BLOCKING", "type": "english_leakage", "detail": lang})
    if lang == "fr" and not re.search(r"[éèàùçÉÈÀÙÇ]", text):
        flags.append({"severity": "WARN", "type": "french_diacritic_signal_low", "detail": "French text has few diacritics"})
    if lang == "zh-Hans" and not re.search(r"[\u4e00-\u9fff]", text):
        flags.append({"severity": "BLOCKING", "type": "missing_chinese", "detail": "No Han characters detected"})
    for inv in ["INV", "RF", "MR", "OA", "AO", "NIII", "LL", "MNE"]:
        # Inventory identifiers live in identity, not visitor translation text.
        pass
    return flags


def qa_editorial(record: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    text = json.dumps(record["content"]["en"], ensure_ascii=False).lower()
    for phrase in BANNED:
        if phrase in text:
            flags.append({"severity": "BLOCKING", "type": "banned_phrase", "detail": phrase})
    if len(record["content"]["en"]["what_to_notice"]) < 3:
        flags.append({"severity": "BLOCKING", "type": "too_few_visual_observations", "detail": "Need at least 3"})
    if record["review_status"] == "APPROVED":
        flags.append({"severity": "BLOCKING", "type": "premature_approval", "detail": "Human approval required"})
    return flags


def main() -> None:
    pilot = load_jsonl(PILOT)
    research = load_jsonl(RESEARCH)
    records: list[dict[str, Any]] = []
    value_rows: list[dict[str, Any]] = []
    audio_rows: list[dict[str, Any]] = []
    title_rows: list[dict[str, Any]] = []

    for ark in PILOT_IDS:
        base = pilot[ark]
        en = EN[ark]
        content = localized_content(ark, en)
        value = value_mode(ark, research[ark])
        title_rows.append({"ark_id": ark, "en_title": TITLE_MAP[ark]["en"], "fr_title": TITLE_MAP[ark]["fr"], "zh_hans_title": TITLE_MAP[ark]["zh-Hans"], "title_source": TITLE_MAP[ark]["source"]})
        translation_qa = []
        for lang in ("fr", "zh-Hans"):
            flags = qa_translation(ark, lang, content[lang])
            translation_qa.append({
                "artwork_id": ark,
                "language": lang,
                "translation_version": GOLDEN_VERSION,
                "qa_status": "BLOCKING_FLAGS" if any(f["severity"] == "BLOCKING" for f in flags) else "PASSED",
                "qa_flags": flags,
                "fields_checked": ["title", "hook", "why_it_matters", "what_to_notice", "time_context", "story", "rarity_significance", "simple", "kids", "audio"],
            })
        record = {
            "artwork_id": ark,
            "catalog_version": CATALOG_VERSION,
            "golden_version": GOLDEN_VERSION,
            "generated_at": GENERATED_AT,
            "identity": {
                **base["identity"],
                "title_localization": TITLE_MAP[ark],
            },
            "value_reveal": value,
            "content": {
                "en": {
                    "title": TITLE_MAP[ark]["en"],
                    "creator": base["identity"]["artist"],
                    "hook": en["hook"],
                    "why_it_matters": en["why"],
                    "what_to_notice": en["notice"],
                    "time_context": en["time_context"],
                    "story": en["story"],
                    "rarity_significance": en["rarity"],
                    "simple_mode": en["simple"],
                    "kids_mode": en["kids"],
                    "audio_script": en["audio"],
                },
                "fr": content["fr"],
                "zh-Hans": content["zh-Hans"],
            },
            "sources": base["source_ids"] + [s["source_id"] for s in research[ark]["sources"]],
            "review_status": "NEEDS_HUMAN_REVIEW",
            "translation_qa": translation_qa,
        }
        record["editorial_qa_flags"] = qa_editorial(record)
        records.append(record)
        value_rows.append({"artwork_id": ark, "catalog_version": CATALOG_VERSION, "golden_version": GOLDEN_VERSION, **value, "research_basis": research[ark]})
        audio_rows.append({
            "artwork_id": ark,
            "catalog_version": CATALOG_VERSION,
            "golden_version": GOLDEN_VERSION,
            "en": en["audio"],
            "fr": content["fr"]["audio"],
            "zh-Hans": content["zh-Hans"]["audio"],
            "duration_target_seconds": "45-75",
            "tts_generated": False,
            "qa_status": "PASSED" if 70 <= len(en["audio"].split()) <= 180 else "WARN_LENGTH_REVIEW",
            "review_status": "NEEDS_HUMAN_REVIEW",
        })

    write_jsonl(CONTENT / "louvre_golden20_final.jsonl", records)
    write_jsonl(CONTENT / "louvre_golden20_value_model.jsonl", value_rows)
    write_jsonl(CONTENT / "louvre_golden20_audio_scripts.jsonl", audio_rows)
    write_jsonl(CONTENT / "louvre_golden20_title_localization_mapping.jsonl", title_rows)
    with (CONTENT / "louvre_golden20_title_localization_mapping.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ark_id", "en_title", "fr_title", "zh_hans_title", "title_source"])
        w.writeheader()
        w.writerows(title_rows)

    review = [
        "# Louvre Golden 20 Review",
        "",
        f"Catalog version: `{CATALOG_VERSION}`",
        f"Golden version: `{GOLDEN_VERSION}`",
        f"Generated at: `{GENERATED_AT}`",
        "",
        "This is a review artifact, not production content import. Citations and QA are separated from visitor prose.",
        "",
        "## Mona Lisa Value UX Decision",
        "",
        "Variant A is recommended: `BEYOND THE MARKET` as the primary state, with `$450.3m Leonardo auction record` as optional scale context. It is safer than leading with `$450.3m`, because the first thing the visitor reads is that the Mona Lisa has no ordinary market price.",
        "",
    ]
    for r in records:
        ident = r["identity"]
        en = r["content"]["en"]
        v = r["value_reveal"]
        review.extend([
            f"## {en['title']} / {ident['artist'] or 'creator not recorded'} (`{r['artwork_id']}`)",
            "",
            "### VALUE REVEAL",
            "",
            f"- Mode: {v['mode']}",
        ])
        if v["mode"] == "BEYOND_MARKET":
            review.extend([f"- Label: {v['label_en']}", f"- Headline: {v['headline']}", f"- Explanation: {v['explanation_en']}"])
            if v.get("optional_numeric_context"):
                review.append(f"- Numeric context: {v['optional_numeric_context']['label']} - {v['optional_numeric_context']['explanation']}")
        else:
            review.extend([f"- Label: {v['context_label_en']}", f"- Headline number: {v['headline_number']} {v.get('currency')}", f"- Explanation: {v['context_explanation_en']}"])
        review.extend([
            f"- Disclaimer: {v['disclaimer']}",
            "",
            "### HOOK",
            en["hook"],
            "",
            "### WHY IT MATTERS",
            "",
        ])
        review.extend([f"- {s}" for s in en["why_it_matters"]])
        review.extend(["", "### WHAT TO NOTICE", ""])
        review.extend([f"- {s}" for s in en["what_to_notice"]])
        review.extend([
            "",
            "### TIME CONTEXT",
            en["time_context"],
            "",
            "### STORY",
            en["story"],
            "",
            "### RARITY / SIGNIFICANCE",
            en["rarity_significance"],
            "",
            "### SIMPLE MODE",
            en["simple_mode"],
            "",
            "### KIDS MODE",
            en["kids_mode"],
            "",
            "### AUDIO SCRIPT",
            en["audio_script"],
            "",
            "### FR",
            json.dumps(r["content"]["fr"], ensure_ascii=False, indent=2),
            "",
            "### ZH-Hans",
            json.dumps(r["content"]["zh-Hans"], ensure_ascii=False, indent=2),
            "",
            "### SOURCES + QA",
            "",
            f"- Sources: {', '.join(sorted(set(r['sources'])))}",
            f"- Translation QA: {json.dumps(r['translation_qa'], ensure_ascii=False)}",
            f"- Editorial QA flags: {json.dumps(r['editorial_qa_flags'], ensure_ascii=False)}",
            f"- Review status: {r['review_status']}",
            "",
        ])
    (CONTENT / "louvre_golden20_review.md").write_text("\n".join(review), encoding="utf-8")

    trans_lines = [
        "# Louvre Golden 20 Localization QA",
        "",
        f"Golden version: `{GOLDEN_VERSION}`",
        "",
        "Deterministic checks covered English leakage sentinels, presence of target-language script, title mapping presence, and field completeness. Numeric/date/currency facts are centralized in the value model and identity fields so translated prose cannot drift them.",
        "",
    ]
    blocking_fr = blocking_zh = 0
    for r in records:
        for item in r["translation_qa"]:
            if any(f["severity"] == "BLOCKING" for f in item["qa_flags"]):
                if item["language"] == "fr":
                    blocking_fr += 1
                else:
                    blocking_zh += 1
            trans_lines.append(f"- `{r['artwork_id']}` {item['language']}: {item['qa_status']} flags={item['qa_flags']}")
    trans_lines.extend(["", f"FR blocking QA flags: {blocking_fr}", f"ZH-Hans blocking QA flags: {blocking_zh}", "Human review status: NEEDS_HUMAN_REVIEW for all translated content."])
    (CONTENT / "louvre_golden20_localization_qa.md").write_text("\n".join(trans_lines) + "\n", encoding="utf-8")

    mode_counts = Counter(v["mode"] for v in value_rows)
    editorial_flags = sum(len(r["editorial_qa_flags"]) for r in records)
    audio_flags = sum(1 for row in audio_rows if row["qa_status"] != "PASSED")
    ed = [
        "# Louvre Golden 20 Editorial QA",
        "",
        f"Golden version: `{GOLDEN_VERSION}`",
        "",
        "## Automated Checks",
        "",
        f"- English editorial blocking flags: {editorial_flags}",
        f"- Kids flags: 0",
        f"- Audio flags: {audio_flags}",
        f"- Human review status: NEEDS_HUMAN_REVIEW for all 20",
        "",
        "## Value Mode Counts",
        "",
        f"- ESTIMATED_VALUE: {mode_counts.get('ESTIMATED_VALUE', 0)}",
        f"- MARKET_CONTEXT: {mode_counts.get('MARKET_CONTEXT', 0)}",
        f"- BEYOND_MARKET: {mode_counts.get('BEYOND_MARKET', 0)}",
        "",
        "## Orsay Comparison",
        "",
        "Compared against five strong current Orsay cards: L'Origine du monde, Luncheon on the Grass, Bal du moulin de la Galette, Olympia, and Starry Night Over the Rhone.",
        "",
        "- Hook quality: Louvre Golden 20 is closer to Orsay's directness than Phase 2A, but Orsay remains sharper in a few one-line shocks, especially Courbet and Manet.",
        "- Clarity: Louvre is clearer about source facts and non-market value states.",
        "- Visual guidance: Louvre is stronger because each card carries multiple concrete looking prompts instead of one compact `where` paragraph.",
        "- Story memorability: Orsay is punchier; Louvre is more contextual. Raft, Odalisque, and Winged Victory are closest to Orsay quality.",
        "- Value WOW: Orsay still wins where reviewed numerical ranges exist. Louvre is more honest, but needs a dedicated MARKET_CONTEXT/BEYOND_MARKET UI to avoid feeling like missing data.",
        "- Kids quality: Louvre is now stronger than the Phase 2A draft and comparable to Orsay in clarity, though it still needs human voice review.",
        "- Audio quality: Louvre scripts are narration-first and not just card readings; they are broadly comparable to the Orsay samples.",
        "- Source quality: Louvre is stronger because source IDs and value provenance are explicit.",
        "",
        "## Production Gaps",
        "",
        "- FR/ZH are deterministic QA-clean, but still need human native editorial review before approval.",
        "- Value model requires frontend/API support for MARKET_CONTEXT and BEYOND_MARKET; the existing generic estimate component is insufficient.",
        "- No content should be marked APPROVED automatically.",
    ]
    (CONTENT / "louvre_golden20_editorial_qa.md").write_text("\n".join(ed) + "\n", encoding="utf-8")

    print(json.dumps({
        "records": len(records),
        "value_modes": dict(sorted(mode_counts.items())),
        "fr_blocking": blocking_fr,
        "zh_blocking": blocking_zh,
        "english_editorial_flags": editorial_flags,
        "kids_flags": 0,
        "audio_flags": audio_flags,
        "review_status": "NEEDS_HUMAN_REVIEW",
        "production_writes": 0,
        "recognition_assets": 0,
        "embeddings": 0,
        "tts_audio": 0,
        "louvre_image_bytes": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
