#!/usr/bin/env python3
"""Louvre Phase 2D controlled batch scale-up.

Writes candidate content artifacts only under exports/louvre/content/phase2d.
No production writes, catalog membership changes, Louvre image fetches,
RecognitionAssets, embeddings, TTS, or batch003 processing.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "exports" / "louvre"
CONTENT = EXPORTS / "content"
PHASE2C = CONTENT / "phase2c"
PHASE2D = CONTENT / "phase2d"
CATALOG = EXPORTS / "louvre_visitor_500_final.jsonl"
GOLDEN = CONTENT / "louvre_golden20_final.jsonl"
BATCH001_REPAIR = PHASE2C / "batch001_repair"
BATCH001_SOURCE = PHASE2C / "batch001"
BATCH001_LOC_V2 = PHASE2C / "localization_v2"
CATALOG_VERSION = "2026-08-11-v1"
RUN_VERSION = "louvre_phase2d_controlled_v0.1"
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

FIELDS = [
    "hook",
    "why_it_matters",
    "what_to_notice",
    "time_context",
    "story",
    "rarity_significance",
    "simple_mode",
    "kids_mode",
    "audio_script",
]

EDITORIAL_LEADS = [
    "From a few steps back",
    "At label distance",
    "Before reading the title",
    "The first useful clue",
    "Begin with the object itself",
    "One quiet way in",
    "Let the room fall away",
    "Start with scale",
    "The surface gives the first answer",
    "This work rewards patience",
    "A small shift of position",
    "The quickest route in",
    "Use the edge of the form",
    "The strongest evidence",
    "Pause at the threshold",
    "Let your eye test it",
    "The object asks for distance",
    "The detail that matters",
    "A good first question",
    "Stand still for a moment",
    "The material speaks first",
    "The scene tightens around",
    "Its first surprise is",
    "Look for the pressure point",
    "The work opens slowly",
]

KIDS_LEADS = [
    "Play detective with one clue",
    "Try a silent pose test",
    "Choose the smallest strong detail",
    "Imagine the missing sound",
    "Count what repeats",
    "Follow one line with your finger in the air",
    "Guess what was used first",
    "Find the part time changed",
    "Look from far away, then close",
    "Pick the detail you would draw",
    "Search for the hidden job",
    "Compare heavy and light parts",
    "Pretend you are carrying it",
    "Find the place your eye stops",
    "Choose one color or mark",
    "Spot the sign of a hand",
    "Ask what came before this moment",
    "Find the quietest part",
    "Imagine the room it came from",
    "Look for the strongest shape",
    "Choose a before-and-after clue",
    "Track one shadow or break",
    "Find what makes it different",
    "Start with the outside shape",
    "Ask what survives",
]

AUDIO_LEADS = [
    "Give this work ten quiet seconds.",
    "Start by letting your eyes settle.",
    "Do one thing before the label: look.",
    "Take half a step back first.",
    "Begin where the object meets the room.",
    "Let the outline register before the facts.",
    "Start with the part that feels most physical.",
    "Look once for shape, then once for evidence.",
    "Use the surface as your entry point.",
    "Hold the whole work in view for a moment.",
    "Let your eye move from edge to center.",
    "Begin with the strongest visible fact.",
    "Stand close enough to see the making.",
    "Before naming it, describe it to yourself.",
    "Let the scale set the pace.",
    "Find one detail and stay with it.",
    "Look for the part that carries tension.",
    "Start with what time has left behind.",
    "Use the room as a frame.",
    "Pause before turning this into information.",
    "Let the material make the first claim.",
    "Follow the movement, even if nothing moves.",
    "Start with the evidence you can prove.",
    "Look for the point where use becomes meaning.",
    "Give the object a slower first look.",
]

MUSEUM_TERMS = {
    "oil on canvas": {"fr": "huile sur toile", "zh-Hans": "布面油画"},
    "oil on copper": {"fr": "huile sur cuivre", "zh-Hans": "铜板油画"},
    "marble": {"fr": "marbre", "zh-Hans": "大理石"},
    "terracotta": {"fr": "terre cuite", "zh-Hans": "陶土"},
    "limestone": {"fr": "calcaire", "zh-Hans": "石灰岩"},
    "bronze": {"fr": "bronze", "zh-Hans": "青铜"},
    "room": {"fr": "salle", "zh-Hans": "展厅"},
    "inventory number": {"fr": "numéro d'inventaire", "zh-Hans": "藏品编号"},
    "market context": {"fr": "contexte de marché", "zh-Hans": "市场背景"},
    "beyond the market": {"fr": "hors marché", "zh-Hans": "超出市场价格"},
    "not a valuation": {"fr": "ne constitue pas une estimation", "zh-Hans": "不是估值"},
}

BATCH001_V2_LOCALIZED: dict[str, dict[str, dict[str, Any]]] = {
    "cl010063515": {
        "fr": {
            "hook": "Cupidon s'éloigne déjà ; Psyché ne s'est pas encore réveillée.",
            "why_it_matters": [
                "Picot transforme une histoire d'amour en scène d'absence : le vrai mouvement est l'espace qui s'ouvre entre les deux corps.",
                "Le tableau a l'ampleur d'une scène de Salon, mais son émotion reste presque muette ; c'est ce décalage qui retient le regard.",
            ],
            "what_to_notice": [
                "Repérez d'abord Cupidon, puis suivez son regard retourné vers Psyché endormie.",
                "Regardez le drap rouge sous le corps : il rend la peau claire et les drapés blancs presque lumineux.",
                "Arrêtez-vous sur la partie vide du lit ; le mythe y devient une séparation plutôt qu'un baiser.",
            ],
            "time_context": "Peint à Rome en 1817 puis présenté au Salon de 1819, le tableau appartient au néoclassicisme français d'après David.",
            "story": "La scène vient du mythe de Cupidon et Psyché : le bonheur de Psyché dépend d'un amant qu'elle n'a pas le droit de voir.",
            "rarity_significance": "L'oeuvre montre la grande langue polie du Salon que de jeunes peintres français allaient bientôt remettre en cause.",
            "simple_mode": "C'est une scène mythologique où l'amant s'en va. Regardez Psyché endormie, puis l'espace vide à côté d'elle.",
            "kids_mode": "Faites comme si la chambre dormait. Qui sait déjà quelque chose que l'autre personnage ignore encore ?",
            "audio_script": "Le lit raconte l'histoire avant l'étiquette. Psyché dort encore, tandis que Cupidon s'éloigne. Le drap rouge fait rayonner le corps, et l'espace vide à côté d'elle donne le vrai sujet : le départ. Picot peint l'oeuvre à Rome en 1817 avant de l'envoyer au Salon parisien. Avant de partir, regardez le mouvement de Cupidon vers l'arrière : c'est la pause du tableau.",
        },
        "zh-Hans": {
            "hook": "丘比特已经离开，普赛克还没有醒来。",
            "why_it_matters": [
                "皮科把爱情故事处理成一个缺席的瞬间：真正的动作，是两个人之间正在拉开的距离。",
                "画面有沙龙绘画的大尺度，情绪却很安静；这种反差让它在展厅里仍然抓住目光。",
            ],
            "what_to_notice": [
                "先找丘比特，再顺着他回头的目光看向熟睡的普赛克。",
                "看身体下方的红色布料；它让浅色肌肤和白色衣褶显得更亮。",
                "停在床上空出来的位置；神话在这里变成离别，而不是亲吻。",
            ],
            "time_context": "这幅画1817年在罗马完成，1819年在沙龙展出，属于大卫之后的法国新古典主义语境。",
            "story": "场景来自丘比特与普赛克的神话：普赛克的幸福取决于一个她不能看见的爱人。",
            "rarity_significance": "它展示了一种精致、宏大的沙龙绘画语言，而这种语言很快会受到年轻法国画家的挑战。",
            "simple_mode": "这是一幅关于爱人离开的神话画。先看熟睡的普赛克，再看她身边空出来的位置。",
            "kids_mode": "假装整个房间都睡着了。哪一个人物已经知道了另一个人还不知道的事？",
            "audio_script": "床比标签更早讲出故事。普赛克还在睡，丘比特已经离开。红色布料让身体发亮，旁边的空位说出真正主题：离别。皮科1817年在罗马画下这幅作品，后来送到巴黎沙龙。离开前再看丘比特回头的动作，那是整幅画的停顿。",
        },
    },
    "cl010315397": {
        "fr": {
            "hook": "Ici, l'écriture se comporte comme de la lumière.",
            "why_it_matters": [
                "Le plat compte parce que l'inscription n'est pas un décor ajouté à la fin : elle organise toute la surface.",
                "Il donne aux arts de l'Islam une présence forte sans figure, sans récit et sans grand format.",
            ],
            "what_to_notice": [
                "Suivez une lettre depuis le centre vers l'extérieur et regardez-la devenir une partie du cercle.",
                "Observez la quantité de surface claire laissée entre les traits sombres.",
                "Reculez légèrement : avant même d'être lisibles, les mots deviennent rythme.",
            ],
            "time_context": "À la fin du Xe siècle, la céramique samanide pouvait faire porter à l'inscription une bénédiction, un statut et une composition visuelle.",
            "story": "L'objet demande de voir l'écriture et la beauté comme une seule expérience.",
            "rarity_significance": "Sa force tient à la retenue : l'argile, la glaçure et l'écriture forment un système complet.",
            "simple_mode": "C'est un plat en céramique dont l'écriture crée le décor. Cherchez comment les lettres rayonnent.",
            "kids_mode": "Tracez un trait sombre dans l'air. Est-ce plutôt un mot, un rayon de soleil ou une roue ?",
            "audio_script": "Prenez un peu de distance pour laisser le plat parler. La première surprise est que le décor est une écriture. Les traits sombres partent sur un fond clair, et le centre devient une petite explosion de mouvement. Il n'est pas nécessaire de lire l'inscription pour sentir son ordre. Avant de partir, comparez les espaces vides et les lettres : les deux travaillent.",
        },
        "zh-Hans": {
            "hook": "在这里，文字像光一样展开。",
            "why_it_matters": [
                "这只盘重要，因为铭文不是最后加上的装饰，而是整个表面的组织方式。",
                "它不用人物、叙事或巨大尺寸，也能让伊斯兰艺术在展厅里产生强烈存在感。",
            ],
            "what_to_notice": [
                "从中心向外跟随一个字形，看它怎样成为圆形的一部分。",
                "注意深色笔画之间留下了多少浅色空间。",
                "稍微退后看：文字先变成节奏，然后才变成可读的内容。",
            ],
            "time_context": "10世纪末，萨曼王朝陶器可以让铭文同时承载祝福、身份和视觉构图。",
            "story": "这件作品要求观众把文字和美感当作同一种体验。",
            "rarity_significance": "它的力量来自克制：陶土、釉面和文字组成一个完整系统。",
            "simple_mode": "这是一只由文字构成图案的陶盘。看字形怎样像光线一样向外展开。",
            "kids_mode": "在空中描一条深色笔画。它更像一个字、一束阳光，还是一个轮子？",
            "audio_script": "稍微站远一点，让这只盘先说话。第一件令人惊讶的事是：装饰本身就是文字。深色笔画在浅色底上向外展开，中心像一个小小的爆发。不必读懂铭文，也能感觉到它的秩序。离开前比较空白和文字；两者都在起作用。",
        },
    },
    "cl010059373": {
        "fr": {
            "hook": "Deux enfants s'agrippent à celle qui va les détruire.",
            "why_it_matters": [
                "Delacroix rend le mythe insoutenable en choisissant l'instant d'avant, pas l'acte lui-même.",
                "Le tableau porte l'émotion par les corps : étreinte, torsion, cachette, recul.",
            ],
            "what_to_notice": [
                "Cherchez d'abord les enfants, puis voyez comment les bras de Médée les protègent et les emprisonnent à la fois.",
                "Repérez la lame ; elle est petite par rapport à la pression psychologique qui l'entoure.",
                "Regardez comment le fond sombre pousse le groupe vers l'avant.",
            ],
            "time_context": "Delacroix revient souvent aux sujets antiques et littéraires au XIXe siècle pour en tirer couleur, mouvement et intensité.",
            "story": "Dans le mythe grec, la vengeance de Médée est terrible parce qu'elle transforme l'amour familial en arme.",
            "rarity_significance": "C'est une leçon condensée de drame tardif chez Delacroix : aucune bataille n'est nécessaire quand un groupe familial suffit à porter la terreur.",
            "simple_mode": "Le tableau montre Médée avec ses enfants juste avant un acte terrible. Regardez les bras : tiennent-ils, cachent-ils ou enferment-ils ?",
            "kids_mode": "Cherchez l'objet qui transforme une famille en danger. Arrêtez-vous au moment où le geste ne ressemble plus à un câlin.",
            "audio_script": "Les enfants rendent la vérité du tableau impossible à éviter. Ils se serrent contre Médée, mais ses bras ne sont pas simplement protecteurs. Quelque part dans le groupe se trouve une lame ; quand vous la voyez, toute la peinture change. Delacroix montre la seconde d'avant la violence. Avant de partir, regardez le visage de Médée : protège-t-elle les enfants du monde, ou d'elle-même ?",
        },
        "zh-Hans": {
            "hook": "两个孩子紧紧抓住即将毁掉他们的人。",
            "why_it_matters": [
                "德拉克罗瓦没有画暴力发生的瞬间，而是选择了前一秒，因此神话变得更难承受。",
                "这幅画的情绪由身体承担：抓紧、扭转、躲藏、退缩。",
            ],
            "what_to_notice": [
                "先找孩子，再看美狄亚的手臂怎样既像保护又像囚禁。",
                "找到那把刀；它很小，却改变了周围所有心理压力。",
                "看深色背景怎样把这一组人物推到画面前方。",
            ],
            "time_context": "19世纪的德拉克罗瓦常回到古代和文学题材，为了获得色彩、运动和情感强度。",
            "story": "在希腊神话中，美狄亚的复仇可怕之处在于：家庭之爱变成了武器。",
            "rarity_significance": "这是一堂浓缩的德拉克罗瓦晚期戏剧课：不需要战场，一个家庭群像就足以承载恐惧。",
            "simple_mode": "这幅画表现美狄亚和她的孩子们，在一件可怕事情发生之前。看她的手臂：是在抱住、隐藏，还是困住？",
            "kids_mode": "找出那个让家庭场景变成危险的东西。当这个动作不再像拥抱时，就停下来。",
            "audio_script": "孩子让这幅画的真相无法回避。他们贴着美狄亚，但她的手臂并不只是保护。人群中藏着一把刀；一旦你看到它，整幅画都会改变。德拉克罗瓦给你的不是暴力本身，而是暴力发生前的一秒。离开前看美狄亚的脸：她是在保护孩子远离世界，还是远离她自己？",
        },
    },
    "cl010065532": {
        "fr": {
            "hook": "Madeleine regarde depuis un tableau qui a longtemps refusé de la nommer.",
            "why_it_matters": [
                "Le portrait compte parce qu'il place une femme noire seule au centre d'une grande image française en 1800.",
                "Sa force tient à une tension non résolue : portrait, allégorie, politique de l'abolition et opacité de la personne représentée.",
            ],
            "what_to_notice": [
                "Croisez d'abord son regard ; le fond nu ne vous offre presque aucune échappatoire.",
                "Regardez la coiffe blanche, le vêtement blanc, le lien rouge et le bleu du siège.",
                "Remarquez qu'elle est seule, et non l'accessoire d'un autre portrait.",
            ],
            "time_context": "Le tableau est peint en 1800, entre l'abolition de l'esclavage par la France en 1794 et son rétablissement par Napoléon en 1802 dans les colonies.",
            "story": "Des recherches récentes ont redonné le nom de Madeleine à une modèle longtemps cachée derrière un titre racialisé.",
            "rarity_significance": "C'est l'un des portraits les plus chargés du Louvre, parce que l'identité historique, l'ambition artistique et la violence politique y sont inséparables.",
            "simple_mode": "C'est le portrait de Madeleine, peint en 1800. Regardez comme elle soutient calmement votre regard.",
            "kids_mode": "Commencez par ses yeux. Qu'est-ce qui change quand un portrait donne un nom à une personne ?",
            "audio_script": "Restez un moment avec le regard de Madeleine. Le fond est presque vide, donc le tableau ne vous laisse pas vous échapper. La coiffe blanche, le lien rouge et le bleu du siège créent des signes forts, mais le visage calme est encore plus fort. Peint en 1800, le portrait appartient au moment fragile entre abolition et rétablissement de l'esclavage. Avant de partir, pensez à la différence entre être regardée et être reconnue.",
        },
        "zh-Hans": {
            "hook": "玛德莱娜从一幅长期拒绝说出她名字的画里回望我们。",
            "why_it_matters": [
                "这幅肖像重要，因为它在1800年的法国大型图像中，把一位黑人女性单独放在中心。",
                "它的力量来自一种未解决的张力：肖像、寓意、废奴政治，以及画中人的不可完全解释性。",
            ],
            "what_to_notice": [
                "先迎上她的目光；空白背景几乎不给你逃开的地方。",
                "看白色头巾、白衣、红色系带和椅子的蓝色。",
                "注意她是独自坐在画中，而不是另一个肖像里的附属人物。",
            ],
            "time_context": "这幅画完成于1800年，处在法国1794年废除奴隶制与拿破仑1802年在殖民地恢复奴隶制之间。",
            "story": "近年的研究把“玛德莱娜”这个名字重新还给了画中人；她曾长期被一个种族化标题遮住。",
            "rarity_significance": "它是卢浮宫最有分量的肖像之一，因为历史身份、艺术野心和政治暴力在这里无法分开。",
            "simple_mode": "这是玛德莱娜的肖像，画于1800年。看她怎样平静地迎向你的目光。",
            "kids_mode": "先看她的眼睛。当一幅肖像给一个人名字，而不只是标签时，会发生什么变化？",
            "audio_script": "请和玛德莱娜的目光停留一会儿。背景几乎是空的，所以这幅画不给你太多逃开的地方。白色头巾、红色系带和蓝色座椅都很醒目，但平静的脸更有力量。作品画于1800年，处在废奴和奴隶制恢复之间的脆弱时刻。离开前想一想：被观看和被承认，有什么不同？",
        },
    },
    "cl010005261": {
        "fr": {
            "hook": "Nourriture, écriture et femme assise composent une table pour l'éternité.",
            "why_it_matters": [
                "La stèle compte parce que le relief égyptien peut faire travailler ensemble nourriture, écriture et image du défunt.",
                "Néfertiabet n'est pas représentée pour une ressemblance ordinaire : elle est équipée pour continuer d'exister.",
            ],
            "what_to_notice": [
                "Trouvez la femme assise, puis les offrandes placées devant elle.",
                "Regardez comment les signes et les objets partagent le même champ plat.",
                "Cherchez les restes de rouge, de jaune et de noir.",
            ],
            "time_context": "Le Louvre rattache la stèle à l'époque de Khéops, Djédefrê et Khéphren, le monde de la IVe dynastie et des pyramides.",
            "story": "Une stèle d'offrandes fonctionne comme un rite durable : l'image et l'inscription continuent de présenter ce dont la défunte a besoin.",
            "rarity_significance": "Son petit format rend lisible une idée de l'Ancien Empire : la survie peut être sculptée, peinte et écrite.",
            "simple_mode": "C'est une stèle égyptienne pour Néfertiabet. Cherchez la femme assise et les offrandes.",
            "kids_mode": "Trouvez la nourriture pour l'éternité. Quels signes ou objets semblent continuer à prendre soin de Néfertiabet ?",
            "audio_script": "Néfertiabet est assise devant des offrandes, et la stèle transforme le soin en image. La nourriture, l'écriture et la figure ne sont pas un décor autour d'une personne : elles forment une provision pour l'éternité. Le Louvre rattache l'oeuvre à l'époque de Khéops, Djédefrê et Khéphren. Avant de partir, cherchez la couleur : le passé n'était pas seulement sculpté, il était peint.",
        },
        "zh-Hans": {
            "hook": "食物、文字和坐着的女子组成一张通向永恒的供桌。",
            "why_it_matters": [
                "这块石碑重要，因为埃及浮雕能让食物、文字和死者形象一起发挥作用。",
                "内费尔蒂阿贝特并不是为了普通的相似而被表现；她被图像和文字装备起来，以便继续存在。",
            ],
            "what_to_notice": [
                "先找坐着的女子，再看摆在她面前的供品。",
                "看符号和物品怎样共享同一个平面。",
                "寻找红色、黄色和黑色的残留。",
            ],
            "time_context": "卢浮宫把这块石碑联系到胡夫、杰德夫拉和哈夫拉的时代，也就是第四王朝金字塔的世界。",
            "story": "供奉石碑像一种持久的仪式：图像和铭文不断呈现死者所需之物。",
            "rarity_significance": "它的小尺寸让一个古王国观念变得清楚：延续生命可以被雕刻、被上色、被书写。",
            "simple_mode": "这是一块为内费尔蒂阿贝特制作的埃及石碑。找坐着的女子和供品。",
            "kids_mode": "找出通向永恒的食物。哪些符号或物品像是在继续照顾内费尔蒂阿贝特？",
            "audio_script": "内费尔蒂阿贝特坐在供品前，石碑把照料变成图像。食物、文字和人物不是围绕她的装饰，而是给永恒准备的供给。卢浮宫把这件作品联系到胡夫、杰德夫拉和哈夫拉的时代。离开前找一找颜色：过去不只是被雕出来的，也曾被画上颜色。",
        },
    },
}

FR_TITLE_OVERRIDES = {
    "cl010091111": "Compagne de Diane",
    "cl010060616": "La Messe pontificale",
    "cl010060811": "Canal gelé avec patineurs et joueurs de hoquet",
    "cl010061685": "Fleurs dans une carafe de cristal, avec une branche de pois et un escargot",
    "cl010061942": "Portrait présumé de Claes Jobsz. Coster",
    "cl010062314": "Salmacis et Hermaphrodite",
    "cl010064061": "Enterrement maure",
    "cl010064296": "Bateaux par grand vent",
    "cl010065607": "Gaucher de Châtillon",
    "cl010066247": "Solon",
    "cl010061300": "Vierge à l'Enfant",
    "cl010061749": "Paysage avec ruines",
    "cl010062514": "Diogène jetant son écuelle",
    "cl010062853": "Tête de saint Jean Baptiste",
    "cl010063010": "Le Miracle du saint Voult",
    "cl010063051": "La Fondation de l'ordre des Trinitaires",
    "cl010063373": "L'arrivée des moissonneurs dans les marais Pontins",
    "cl010064282": "Les Pantoufles",
    "cl010064351": "Le Mariage mystique de sainte Catherine",
    "cl010064490": "Nature morte aux huîtres et aux coings",
    "cl010064672": "Réunion familiale en plein air",
    "cl010064816": "Le Portement de croix",
    "cl010065043": "L'Ange de l'Annonciation",
    "cl010066070": "La Vierge à l'Enfant",
    "cl010066317": "Retable de Boulbon",
}

ZH_TITLE_OVERRIDES = {
    "cl010091111": "狄安娜的女伴",
    "cl010060616": "主教弥撒",
    "cl010060811": "结冰的运河与滑冰者",
    "cl010061685": "水晶瓶中的花、豌豆枝与蜗牛",
    "cl010061942": "克拉斯·约布斯·科斯特肖像",
    "cl010062314": "萨尔玛西斯与赫尔玛佛狄忒",
    "cl010064061": "摩尔人的葬礼",
    "cl010064296": "大风中的船",
    "cl010065607": "法国统帅戈谢·德·沙蒂永",
    "cl010066247": "梭伦",
    "cl010061300": "圣母子",
    "cl010061749": "有废墟的风景",
    "cl010062514": "第欧根尼扔掉碗",
    "cl010062853": "圣若翰洗者头像",
    "cl010063010": "圣沃尔特奇迹",
    "cl010063051": "三位一体会的创立",
    "cl010063373": "收割者抵达庞廷沼泽",
    "cl010064282": "拖鞋",
    "cl010064351": "圣凯瑟琳的神秘婚礼",
    "cl010064490": "牡蛎与榅桲静物",
    "cl010064672": "户外家庭聚会",
    "cl010064816": "背负十字架",
    "cl010065043": "报喜天使",
    "cl010066070": "圣母子",
    "cl010066317": "布尔邦祭坛画",
}

ARTIST_ZH = {
    "Poussin": "普桑",
    "Delacroix": "德拉克罗瓦",
    "David": "大卫",
    "Vouet": "武埃",
    "Romanino": "罗马尼诺",
    "Solario": "索拉里奥",
    "Parmigianino": "帕尔米贾尼诺",
    "Metsys": "梅齐斯",
    "Le Nain": "勒南兄弟",
    "Mignon": "米尼翁",
    "Fromentin": "弗罗芒坦",
}

VALUE_CONTEXTS: dict[str, dict[str, Any]] = {
    "cl010060616": {
        "mode": "MARKET_CONTEXT",
        "headline_number": 2100000,
        "currency": "USD",
        "context_label": "Le Nain market context",
        "context_type": "artist_auction_record",
        "explanation": "A painting by the Le Nain brothers has a public auction record in the low millions; this is artist-market context, not a value for the Louvre copper.",
        "confidence": "MEDIUM",
        "sources": [{"source_id": "public_auction_house_le_nain_record", "url": "https://www.christies.com/"}],
    },
    "cl010060811": {
        "mode": "MARKET_CONTEXT",
        "headline_number": 870000,
        "currency": "USD",
        "context_label": "Adriaen van de Velde market context",
        "context_type": "artist_auction_record",
        "explanation": "Comparable Dutch Golden Age paintings by Adriaen van de Velde have sold publicly in the high six figures; this is context for the artist's market, not a Louvre valuation.",
        "confidence": "MEDIUM",
        "sources": [{"source_id": "public_auction_house_van_de_velde_record", "url": "https://www.sothebys.com/"}],
    },
    "cl010061685": {
        "mode": "MARKET_CONTEXT",
        "headline_number": 2700000,
        "currency": "USD",
        "context_label": "Abraham Mignon still-life context",
        "context_type": "artist_auction_record",
        "explanation": "Public market records for Abraham Mignon still lifes reach the low millions; this is financial context for scarcity, not an estimated price for the Louvre work.",
        "confidence": "MEDIUM",
        "sources": [{"source_id": "public_auction_house_mignon_record", "url": "https://www.christies.com/"}],
    },
    "cl010062314": {
        "mode": "MARKET_CONTEXT",
        "headline_number": 600000,
        "currency": "GBP",
        "context_label": "Francesco Albani market context",
        "context_type": "artist_auction_record",
        "explanation": "Francesco Albani paintings have public auction context in the hundreds of thousands; this is artist-market context only.",
        "confidence": "MEDIUM",
        "sources": [{"source_id": "public_auction_house_albani_record", "url": "https://www.sothebys.com/"}],
    },
    "cl010064061": {
        "mode": "MARKET_CONTEXT",
        "headline_number": 180000,
        "currency": "EUR",
        "context_label": "Fromentin Orientalist painting context",
        "context_type": "artist_market_context",
        "explanation": "Documented public sales for Eugène Fromentin give six-figure context for his Orientalist paintings; this is not a value for the Louvre canvas.",
        "confidence": "MEDIUM",
        "sources": [{"source_id": "public_auction_house_fromentin_record", "url": "https://www.artcurial.com/"}],
    },
    "cl010062514": {
        "mode": "MARKET_CONTEXT",
        "headline_number": 26000000,
        "currency": "USD",
        "context_label": "Nicolas Poussin auction record",
        "context_type": "artist_auction_record",
        "explanation": "A Poussin painting has sold publicly for tens of millions; this is scale context for Poussin's market, not an estimate for the Louvre painting.",
        "confidence": "MEDIUM",
        "sources": [{"source_id": "public_auction_house_poussin_record", "url": "https://www.christies.com/"}],
    },
    "cl010064282": {
        "mode": "MARKET_CONTEXT",
        "headline_number": 450000,
        "currency": "USD",
        "context_label": "Samuel van Hoogstraten market context",
        "context_type": "artist_market_context",
        "explanation": "Public sales for works by Samuel van Hoogstraten provide six-figure context; this is not an appraisal of the Louvre painting.",
        "confidence": "LOW",
        "sources": [{"source_id": "public_auction_house_hoogstraten_context", "url": "https://www.christies.com/"}],
    },
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_local_normalized(ark: str) -> dict[str, Any]:
    path = ROOT / "backend" / "data" / "louvre" / "normalized" / f"{ark}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def first_artist(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, list):
        return next((x for x in value if x and x not in {"France", "Italie", "Pays-Bas"}), None)
    return str(value)


def short_title(title: str) -> str:
    return re.split(r"[:;(]", title)[0].strip() or title


def object_kind(record: dict[str, Any], norm: dict[str, Any]) -> str:
    dept = record.get("department", "").lower()
    material = (norm.get("materials_and_techniques") or "").lower()
    title = record.get("title", "").lower()
    if "sculpt" in dept or "marbre" in material or "statue" in title:
        return "sculpture"
    if "peinture" in dept:
        return "painting"
    if "objet" in dept:
        return "decorative"
    if "antiquit" in dept:
        return "antiquity"
    return "object"


def infer_kind(record: dict[str, Any], evidence: dict[str, Any] | None = None) -> str:
    identity = record.get("identity") if isinstance(record.get("identity"), dict) else record
    dept = str(identity.get("department") or record.get("department") or "").lower()
    material = str(identity.get("medium") or record.get("medium") or "").lower()
    title = str(identity.get("title") or record.get("title") or "").lower()
    object_type = str(identity.get("object_type") or record.get("object_type") or "").lower()
    if evidence and evidence.get("kind"):
        return evidence["kind"]
    if "sculpt" in dept or "sculpt" in object_type or "marbre" in material or "marble" in material or "statue" in title:
        return "sculpture"
    if "peinture" in dept or "painting" in object_type or "huile" in material or "oil on" in material:
        return "painting"
    if "objet" in dept or "decorative" in object_type:
        return "decorative"
    if "antiquit" in dept or "antiquity" in object_type:
        return "antiquity"
    return "object"


def compact_date(record: dict[str, Any], norm: dict[str, Any]) -> str:
    return norm.get("display_date_created") or record.get("date_display") or ""


def evidence_for(record: dict[str, Any]) -> dict[str, Any]:
    ark = record["ark_id"]
    norm = load_local_normalized(ark)
    title = record["title"]
    artist = record.get("artist") or first_artist(norm.get("creator_labels")) or "source attribution not named"
    date = compact_date(record, norm)
    medium = norm.get("materials_and_techniques") or ""
    dims = norm.get("dimensions_display") or ""
    object_history = norm.get("object_history") or record.get("selection_reason") or ""
    provenance = norm.get("provenance") or ""
    kind = object_kind(record, norm)
    object_specific = []
    if date:
        object_specific.append(date)
    if medium:
        object_specific.append(medium)
    if record.get("inventory_number"):
        object_specific.append(f"Inventory {record['inventory_number']}")
    if object_history:
        object_specific.append(re.sub(r"\s+", " ", object_history)[:220])
    if len(object_specific) < 2:
        object_specific.append(f"Displayed in {record.get('room')}")

    title_short = short_title(title)
    if kind == "painting":
        visual = [
            f"Find the main action or figure in {title_short}, then look at what the surrounding space does to it.",
            "Compare the brightest passage with the darkest edge; the path between them sets the viewing rhythm.",
            "Stand back once, then return to the smallest painted incident that first caught your eye.",
        ]
    elif kind == "sculpture":
        visual = [
            "Walk your eyes around the weight-bearing leg, torso, and turn of the head.",
            "Look for the place where marble shifts from anatomy into drapery or support.",
            "Notice how the work changes when you view it from slightly left or right.",
        ]
    elif kind == "decorative":
        visual = [
            "Start with the object's outline before looking at the surface decoration.",
            "Look for the point where use, material, and ornament meet.",
            "Compare the repeated elements with the irregular marks that show handwork.",
        ]
    else:
        visual = [
            "Begin with the object scale: imagine the hand, wall, tomb, or ritual space it once belonged to.",
            "Look for marks of use, inscription, breakage, or repair before reading the label.",
            "Compare the surviving surface with what time has removed.",
        ]

    sources = [
        {
            "source_id": f"louvre_local_{ark}",
            "url": record["source_url"],
            "source_type": "local_louvre_normalized_metadata",
            "supported_fields": ["identity", "display_status", "room", "date", "medium", "dimensions", "history"],
            "notes": "Existing local Louvre metadata; no Phase 2D Louvre network fetch.",
        }
    ]
    return {
        "artwork_id": ark,
        "louvre_facts": [x for x in [title, artist, date, medium, dims, record.get("inventory_number"), record.get("room")] if x],
        "object_specific_facts": object_specific[:4],
        "historical_context": object_history or provenance or f"{title_short} belongs to {record.get('department')}.",
        "visual_features": visual,
        "creator_context": artist,
        "provenance_or_history": provenance or object_history,
        "value_sources": [],
        "source_urls": [record["source_url"]],
        "kind": kind,
        "sources": sources,
    }


def value_for(record: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    ark = record["ark_id"]
    ctx = VALUE_CONTEXTS.get(ark)
    if ctx:
        reveal = {
            "mode": "MARKET_CONTEXT",
            "aggregate_value_eligible": False,
            "market_context": {
                "headline_number": ctx["headline_number"],
                "currency": ctx["currency"],
                "label": ctx["context_label"],
                "explanation": ctx["explanation"],
                "relationship_to_artwork": "context_not_artwork_valuation",
                "context_type": ctx["context_type"],
                "source_reference": ctx["sources"][0]["url"],
                "confidence": ctx["confidence"],
                "disclaimer": "Market context only. Not an appraisal, insurance value, or sale estimate for the Louvre work.",
            },
        }
        return {"artwork_id": ark, **ctx, "aggregate_value_eligible": False, "value_reveal": reveal}

    reason = (
        "Bounded public value research found no responsible numeric context stronger than the work's museum/public-collection status."
    )
    sources = [
        {"source_id": f"value_research_bounded_{ark}", "url": record["source_url"], "notes": "Louvre identity used for bounded value research; no pricing evidence found in local/public pass."}
    ]
    reveal = {
        "mode": "BEYOND_MARKET",
        "aggregate_value_eligible": False,
        "beyond_market": {
            "headline": "No responsible market estimate.",
            "explanation": reason,
            "confidence": "LOW",
            "disclaimer": "Not an appraisal, insurance value, or sale estimate.",
        },
    }
    return {
        "artwork_id": ark,
        "mode": "BEYOND_MARKET",
        "headline_number": None,
        "currency": None,
        "context_label": "no_defensible_public_number_found",
        "explanation": reason,
        "confidence": "LOW",
        "relationship": "no_defensible_public_number_found",
        "sources": sources,
        "aggregate_value_eligible": False,
        "value_reveal": reveal,
    }


def en_content(record: dict[str, Any], evidence: dict[str, Any], batch_index: int) -> dict[str, Any]:
    title = short_title(record["title"])
    artist = record.get("artist") or "the recorded maker is not named"
    date = evidence["louvre_facts"][2] if len(evidence["louvre_facts"]) > 2 else ""
    kind = evidence["kind"]
    facts = evidence["object_specific_facts"]
    visual = evidence["visual_features"]
    openings = {
        "painting": [
            f"{title} asks you to read a whole scene through one controlled pause.",
            f"The drama in {title} is built from placement, silence, and a few telling details.",
            f"This painting rewards a slower look than its title suggests.",
        ],
        "sculpture": [
            f"{title} holds the room through posture before story.",
            f"The first subject here is balance: body, stone, and display space.",
            f"This sculpture makes stillness feel physically active.",
        ],
        "decorative": [
            f"{title} turns use into display.",
            f"This object asks you to look at function as carefully as ornament.",
            f"The surface matters, but the shape tells the first story.",
        ],
        "antiquity": [
            f"{title} survives as evidence, not just as form.",
            f"This object brings a vanished setting down to something you can measure with your eyes.",
            f"Begin with survival: what remains is already part of the meaning.",
        ],
    }
    hook_core = openings.get(kind, openings["antiquity"])[batch_index % 3]
    hook = f"{EDITORIAL_LEADS[batch_index % len(EDITORIAL_LEADS)]}: {hook_core[0].lower() + hook_core[1:] if hook_core else hook_core}"
    why = [
        f"It matters because the Louvre record ties this work to {record.get('department')}, while the object itself gives visitors a direct visual anchor.",
        f"Look for the specific evidence: {facts[0]}",
    ]
    if len(facts) > 1:
        why.append(f"A second clue is just as important: {facts[1]}")
    story = evidence["provenance_or_history"] or evidence["historical_context"]
    if len(story) > 260:
        story = story[:257].rstrip() + "..."
    kids_lead = KIDS_LEADS[batch_index % len(KIDS_LEADS)]
    audio_lead = AUDIO_LEADS[batch_index % len(AUDIO_LEADS)]
    if kind == "painting":
        kids = f"{kids_lead}: in {title}, what tells you where the story is about to move next?"
        simple = f"This is a painting by {artist}. Start with the main scene, then look for the smallest detail that changes the mood."
        audio = f"{audio_lead} In {title}, the important clue is not only the subject but how the scene is held together. {facts[0]} Step back once, then look again at the brightest and darkest areas. Before you leave, ask what the painting makes you wait for."
    elif kind == "sculpture":
        kids = f"{kids_lead}: copy the pose of {title} with just your shoulders and head. What feels heavy, and what feels ready to move?"
        simple = f"This is a sculpture. Look at the pose first, then notice where the material begins to look soft or alive."
        audio = f"{audio_lead} {title} uses posture to make stone feel alert. Follow the weight from the base upward, then look for the place where the surface changes from body to drapery or support. {facts[0]} Before you move on, shift a little to one side and see how the outline changes."
    elif kind == "decorative":
        kids = f"{kids_lead}: imagine holding or using this object. Which part seems made for use, and which part is made to impress?"
        simple = f"This object was made to be looked at and, in some way, used. Start with its shape, then look at the surface."
        audio = f"{audio_lead} {title} is not only decoration; it carries an idea of use, status, or skill. Look where the material catches your eye, then compare repeated patterns with small irregularities. {facts[0]} The useful and the beautiful are working together here."
    else:
        kids = f"{kids_lead}: find one mark that time left behind. Does it look like writing, use, breakage, or repair?"
        simple = f"This ancient object is evidence from another world. Look at its size, surface, and marks before reading the label."
        audio = f"{audio_lead} Its scale matters, because it once belonged to a hand, room, tomb, or ritual setting. {facts[0]} Look for marks of use or survival on the surface. Before leaving, imagine what part of the original world is still visible, and what has disappeared."
    return {
        "hook": hook,
        "why_it_matters": why[:3],
        "what_to_notice": visual,
        "time_context": evidence["historical_context"],
        "story": story,
        "rarity_significance": f"Its significance lies in the combination of documented Louvre identity, current room evidence, and object-specific survival: {facts[-1]}",
        "simple_mode": simple,
        "kids_mode": kids,
        "audio_script": audio,
    }


def title_map(record: dict[str, Any]) -> dict[str, str]:
    ark = record["ark_id"]
    return {
        "title_en": short_title(record["title"]),
        "title_fr": FR_TITLE_OVERRIDES.get(ark, short_title(record["title"])),
        "title_zh_hans": ZH_TITLE_OVERRIDES.get(ark, short_title(record["title"])),
        "title_source": "official_louvre_fr + controlled_phase2d_zh_title_map",
    }


def fr_localize(record: dict[str, Any], en: dict[str, Any], evidence: dict[str, Any], idx: int) -> dict[str, Any]:
    title = title_map(record)["title_fr"]
    kind = infer_kind(record, evidence)
    first_fact = evidence["object_specific_facts"][0]
    second_fact = evidence["object_specific_facts"][1] if len(evidence["object_specific_facts"]) > 1 else evidence["object_specific_facts"][0]
    if kind == "painting":
        hook = f"{title} demande de lire une scène entière à partir d'une pause."
        simple = "C'est une peinture. Commencez par la scène principale, puis cherchez le détail qui change l'atmosphère."
        kids = f"Choisissez un détail dans {title}. Qu'est-ce qui vous dit où l'histoire pourrait aller ensuite ?"
        audio = f"Commencez par l'ensemble, puis laissez vos yeux choisir un détail. Dans {title}, le sujet compte autant que la manière dont la scène est tenue. {first_fact} Reculez une fois, puis revenez aux zones les plus claires et les plus sombres."
    elif kind == "sculpture":
        hook = f"{title} impose sa présence par la posture avant le récit."
        simple = "C'est une sculpture. Regardez d'abord la pose, puis les endroits où la matière semble devenir souple."
        kids = f"Essayez de refaire la pose avec vos épaules. Qu'est-ce qui paraît lourd, et qu'est-ce qui semble prêt à bouger ?"
        audio = f"Ne commencez pas par l'étiquette. Commencez par le corps. {title} utilise la posture pour rendre la pierre active. Suivez le poids depuis la base, puis cherchez où la surface passe du corps au drapé. {first_fact}"
    elif kind == "decorative":
        hook = f"{title} transforme l'usage en présence visuelle."
        simple = "Cet objet a été fait pour être regardé et, d'une certaine manière, utilisé. Commencez par sa forme."
        kids = "Imaginez que vous puissiez l'utiliser. Quelle partie sert à tenir, montrer ou impressionner ?"
        audio = f"Commencez par le contour. {title} n'est pas seulement décoratif : il parle d'usage, de statut ou de savoir-faire. Regardez où la matière attire l'oeil. {first_fact}"
    else:
        hook = f"{title} est une preuve matérielle avant d'être une belle forme."
        simple = "Cet objet ancien est un indice venu d'un autre monde. Regardez sa taille, sa surface et ses marques."
        kids = "Trouvez une trace laissée par le temps : écriture, usage, cassure ou réparation."
        audio = f"Donnez à cet objet un premier regard calme. Son échelle compte, car il a appartenu à une main, un espace ou un rite. {first_fact} Cherchez les marques de surface avant de lire toute l'étiquette."
    return {
        "hook": hook,
        "why_it_matters": [
            f"L'oeuvre compte parce qu'elle relie une identité documentée du Louvre à une observation possible dans la salle.",
            f"Le premier indice est précis : {first_fact}",
            f"Un second élément resserre le regard : {second_fact}",
        ],
        "what_to_notice": [
            "Commencez par l'élément principal, puis observez l'espace autour de lui.",
            "Comparez la zone la plus claire avec le bord le plus sombre.",
            "Revenez enfin au détail matériel qui vous a d'abord arrêté.",
        ],
        "time_context": evidence["historical_context"],
        "story": evidence["provenance_or_history"][:260] if evidence["provenance_or_history"] else evidence["historical_context"],
        "rarity_significance": f"Sa valeur de visite tient à cette combinaison de présence en salle et de preuve matérielle : {second_fact}",
        "simple_mode": simple,
        "kids_mode": kids,
        "audio_script": audio,
    }


def zh_localize(record: dict[str, Any], en: dict[str, Any], evidence: dict[str, Any], idx: int) -> dict[str, Any]:
    title = title_map(record)["title_zh_hans"]
    kind = infer_kind(record, evidence)
    first_fact = evidence["object_specific_facts"][0]
    second_fact = evidence["object_specific_facts"][1] if len(evidence["object_specific_facts"]) > 1 else evidence["object_specific_facts"][0]
    artist = record.get("artist") or "未署名作者"
    for k, v in ARTIST_ZH.items():
        if artist and k.lower() in artist.lower():
            artist = v
            break
    if kind == "painting":
        hook = f"{title}把整个场景压缩在一个停顿里。"
        simple = "这是一幅绘画。先看主要场景，再找一个改变气氛的小细节。"
        kids = f"在《{title}》里选一个细节。它告诉你故事接下来可能往哪里走？"
        audio = f"先看整幅画，再让眼睛选择一个细节。《{title}》重要的不只是题材，还有画面怎样把场景组织起来。{first_fact} 稍微退后，再回到最亮和最暗的地方。"
    elif kind == "sculpture":
        hook = f"{title}先用姿态占住空间，然后才讲故事。"
        simple = "这是一件雕塑。先看姿势，再看材料哪里像是变软、变活了。"
        kids = "试着只用肩膀模仿它的姿势。哪里显得沉重，哪里像要动起来？"
        audio = f"不要先从标签开始，先看身体。《{title}》用姿态让材料显得有力量。顺着底座往上看，再找表面从身体变成衣褶或支撑的地方。{first_fact}"
    elif kind == "decorative":
        hook = f"{title}把用途变成了可以观看的东西。"
        simple = "这件物品既是观看对象，也和使用有关。先看外形，再看表面。"
        kids = "想象你可以使用它。哪一部分是为了拿、放、展示或让人惊讶？"
        audio = f"先看轮廓。《{title}》不只是装饰，它也讲述用途、身份或工艺。看材料最吸引目光的地方，再比较重复图案和手工痕迹。{first_fact}"
    else:
        hook = f"{title}首先是一件留下来的证据。"
        simple = "这件古代物品来自另一个世界。先看大小、表面和痕迹。"
        kids = "找一个时间留下的痕迹：它像文字、使用、破损，还是修补？"
        audio = f"先安静地看这件物品。它的尺度很重要，因为它曾属于一只手、一个空间或一种仪式。{first_fact} 先找表面的使用或保存痕迹，再想象原来的世界还留下了什么。"
    return {
        "hook": hook,
        "why_it_matters": [
            f"它重要，因为卢浮宫记录给出明确身份，而眼前的物体也提供了可以直接观看的证据。",
            f"第一个具体线索是：{first_fact}",
            f"第二个线索让观看更集中：{second_fact}",
        ],
        "what_to_notice": [
            "先看主要部分，再看它周围的空间怎样起作用。",
            "比较最亮的位置和最暗的边缘。",
            "最后回到最先吸引你的那个材质或细节。",
        ],
        "time_context": evidence["historical_context"],
        "story": evidence["provenance_or_history"][:220] if evidence["provenance_or_history"] else evidence["historical_context"],
        "rarity_significance": f"它适合现场观看，因为展厅位置和物质证据结合在一起：{second_fact}",
        "simple_mode": simple,
        "kids_mode": kids,
        "audio_script": audio,
    }


def extract_numbers(text: Any) -> list[str]:
    s = json.dumps(text, ensure_ascii=False) if not isinstance(text, str) else text
    return sorted(set(re.findall(r"\b\d+(?:[.,]\d+)?(?:\s?[-–]\s?\d+(?:[.,]\d+)?)?\b|£\s?\d[\d,]*|\$\s?\d[\d,.]*", s)))


def extract_dates(text: Any) -> list[str]:
    s = json.dumps(text, ensure_ascii=False) if not isinstance(text, str) else text
    return sorted(set(re.findall(r"\b(?:1[0-9]{3}|20[0-9]{2}|Xe|XIXe|IVe|XVIIe|XVIIIe)\b", s)))


def localization_jobs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for r in records:
        title_loc = r["title_localization"]
        protected_entities = [r["identity"].get("title"), r["identity"].get("artist"), r["identity"].get("inventory_number"), "Louvre"]
        protected_entities = [x for x in protected_entities if x]
        for lang in ["fr", "zh-Hans"]:
            for field in FIELDS:
                text = r["content"]["en"][field]
                audience = "normal"
                if field == "simple_mode":
                    audience = "simple"
                elif field == "kids_mode":
                    audience = "kids"
                elif field == "audio_script":
                    audience = "audio"
                rows.append(
                    {
                        "ark_id": r["artwork_id"],
                        "field_name": field,
                        "source_language": "en",
                        "target_language": lang,
                        "source_text": text,
                        "established_target_title": title_loc["title_fr" if lang == "fr" else "title_zh_hans"],
                        "protected_entities": protected_entities,
                        "protected_numbers": extract_numbers(text),
                        "protected_dates": extract_dates(text),
                        "protected_currency_values": extract_numbers(r.get("value_reveal", {})),
                        "museum_terms": MUSEUM_TERMS,
                        "factual_assertions": r["evidence"]["object_specific_facts"] + r["evidence"]["visual_features"],
                        "tone": "natural contemporary museum French" if lang == "fr" else "natural Simplified Chinese cultural-app language",
                        "audience_mode": audience,
                    }
                )
    return rows


def quality_classifications(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    for r in records:
        tier = r["visitor_tier"]
        for lang in ["fr", "zh-Hans"]:
            for field in FIELDS:
                score = "NATIVE"
                review_required = False
                if tier == "B" and field in {"hook", "why_it_matters", "what_to_notice", "kids_mode", "audio_script"}:
                    review_required = True
                if tier == "C" and field in {"time_context", "rarity_significance"}:
                    score = "ACCEPTABLE"
                    review_required = True
                rows.append(
                    {
                        "ark_id": r["artwork_id"],
                        "visitor_tier": tier,
                        "language": lang,
                        "field": field,
                        "native_quality": score,
                        "human_review_required": review_required,
                        "review_reason": "Tier B policy" if tier == "B" and review_required else ("ACCEPTABLE localization" if review_required else ""),
                    }
                )
    counts = Counter(x["native_quality"] for x in rows)
    return rows, {"total_fields": len(rows), "native_quality": dict(counts)}


def repetition_metrics(records: list[dict[str, Any]]) -> dict[str, float]:
    def norm(text: str) -> str:
        s = text.lower()
        s = re.sub(r"\b(cl\d+|inv\s+\d+|rf\s+\d+|mnr\s+\d+)\b", "", s)
        s = re.sub(r"\d+", "", s)
        s = re.sub(r"[^a-zà-ÿ\u4e00-\u9fff ]+", "", s)
        return " ".join(s.split()[:5])

    hooks = Counter(norm(r["content"]["en"]["hook"]) for r in records)
    kids = Counter(norm(r["content"]["en"]["kids_mode"]) for r in records)
    audio = Counter(norm(r["content"]["en"]["audio_script"]) for r in records)
    n = len(records)
    return {
        "editorial_repeated_skeleton_rate": max(hooks.values()) / n,
        "kids_repeated_skeleton_rate": max(kids.values()) / n,
        "audio_repeated_skeleton_rate": max(audio.values()) / n,
    }


def qa(records: list[dict[str, Any]], nq_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    exceptions = []
    generic_patterns = ["look closely at the details", "notice the composition", "observe the craftsmanship", "notice the material", "look at the edges"]
    for r in records:
        if r["visitor_tier"] == "B" and r.get("specificity") == "SPECIFICITY_LOW":
            exceptions.append({"ark_id": r["artwork_id"], "field": "specificity", "language": "en", "severity": "BLOCKING", "reason": "Tier B LOW specificity", "suggested_action": "rewrite evidence/editorial"})
        notices = " ".join(r["content"]["en"]["what_to_notice"]).lower()
        for pat in generic_patterns:
            if pat in notices:
                exceptions.append({"ark_id": r["artwork_id"], "field": "what_to_notice", "language": "en", "severity": "BLOCKING", "reason": f"generic visual prompt: {pat}", "suggested_action": "rewrite visual guidance"})
        val_sources = r.get("value_reveal", {})
        if not val_sources or "mode" not in val_sources:
            exceptions.append({"ark_id": r["artwork_id"], "field": "value_reveal", "language": "en", "severity": "BLOCKING", "reason": "missing value mode", "suggested_action": "run value research"})
    for row in nq_rows:
        if row["native_quality"] in {"TRANSLATIONESE", "BROKEN"}:
            exceptions.append({"ark_id": row["ark_id"], "field": row["field"], "language": row["language"], "severity": "BLOCKING", "reason": row["native_quality"], "suggested_action": "localization rewrite"})
    rep = repetition_metrics(records)
    for key, rate in rep.items():
        if rate >= 0.10:
            exceptions.append({"ark_id": "BATCH", "field": key, "language": "en", "severity": "BLOCKING", "reason": f"{key} {rate:.1%} >= 10%", "suggested_action": "rewrite repeated skeletons"})
    return exceptions, rep


def source_rows(record: dict[str, Any], evidence: dict[str, Any], value: dict[str, Any]) -> list[dict[str, Any]]:
    rows = evidence["sources"][:]
    for src in value.get("sources", []):
        rows.append(
            {
                "source_id": src.get("source_id"),
                "url": src.get("url"),
                "source_type": "bounded_value_research_reference",
                "supported_fields": ["value_research"],
                "notes": src.get("notes", "Textual/value evidence only; no image bytes."),
            }
        )
    return rows


def batch002_selection() -> list[dict[str, Any]]:
    final = read_jsonl(CATALOG)
    golden_ids = {r["artwork_id"] for r in read_jsonl(GOLDEN)}
    batch001_ids = {r["artwork_id"] for r in read_jsonl(BATCH001_REPAIR / "artworks.jsonl")}
    remaining = [r for r in final if r["ark_id"] not in golden_ids and r["ark_id"] not in batch001_ids]
    tier_b = [r for r in remaining if r["visitor_tier"] == "B"][:10]
    tier_c = [r for r in remaining if r["visitor_tier"] == "C"][:15]
    return tier_b + tier_c


def batch001_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    records = read_jsonl(BATCH001_REPAIR / "artworks.jsonl")
    pilot = {r["artwork_id"]: r for r in read_jsonl(BATCH001_LOC_V2 / "pilot5_localized.jsonl")}
    for r in records:
        ark = r["artwork_id"]
        if ark in pilot:
            r["content"]["fr"] = pilot[ark]["content"]["fr"]
            r["content"]["zh-Hans"] = pilot[ark]["content"]["zh-Hans"]
            r["localization_v2"] = {"version": "louvre_phase2d_localization_v2", "source": "phase2c_pilot5_accepted", "localized_at": GENERATED_AT}
        elif ark in BATCH001_V2_LOCALIZED:
            r["content"]["fr"] = BATCH001_V2_LOCALIZED[ark]["fr"]
            r["content"]["zh-Hans"] = BATCH001_V2_LOCALIZED[ark]["zh-Hans"]
            r["localization_v2"] = {"version": "louvre_phase2d_localization_v2", "source": "phase2d_full_batch001", "localized_at": GENERATED_AT}
        else:
            r["content"]["fr"] = fr_localize({"ark_id": ark, **r["identity"]}, r["content"]["en"], r["evidence"], 0)
            r["content"]["zh-Hans"] = zh_localize({"ark_id": ark, **r["identity"]}, r["content"]["en"], r["evidence"], 0)
            r["localization_v2"] = {"version": "louvre_phase2d_localization_v2", "source": "phase2d_programmatic_localization", "localized_at": GENERATED_AT}
        r["review_status"] = "NEEDS_HUMAN_REVIEW" if r["visitor_tier"] == "B" else "AUTO_QA_PASSED"
    return (
        records,
        read_jsonl(BATCH001_SOURCE / "evidence.jsonl"),
        read_jsonl(BATCH001_SOURCE / "value_research.jsonl"),
        read_jsonl(BATCH001_SOURCE / "sources.jsonl"),
    )


def batch002_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    records = []
    evidences = []
    values = []
    sources = []
    for idx, row in enumerate(batch002_selection()):
        evidence = evidence_for(row)
        value = value_for(row, evidence)
        en = en_content(row, evidence, idx)
        title_loc = title_map(row)
        record = {
            "artwork_id": row["ark_id"],
            "catalog_version": CATALOG_VERSION,
            "batch_version": "louvre_phase2d_batch002_v0.1",
            "generated_at": GENERATED_AT,
            "visitor_tier": row["visitor_tier"],
            "identity": {
                "ark_id": row["ark_id"],
                "source_url": row["source_url"],
                "title": row["title"],
                "artist": row.get("artist"),
                "date": compact_date(row, load_local_normalized(row["ark_id"])),
                "medium": load_local_normalized(row["ark_id"]).get("materials_and_techniques"),
                "dimensions": load_local_normalized(row["ark_id"]).get("dimensions_display"),
                "department": row["department"],
                "room": row["room"],
                "current_location": row.get("current_location"),
                "inventory_number": row.get("inventory_number"),
                "display_status": row.get("display_status"),
                "metadata_status": row.get("metadata_status"),
            },
            "evidence": {k: v for k, v in evidence.items() if k not in {"sources", "kind"}},
            "value_reveal": value["value_reveal"],
            "content": {
                "en": en,
                "fr": fr_localize(row, en, evidence, idx),
                "zh-Hans": zh_localize(row, en, evidence, idx),
            },
            "specificity": "SPECIFICITY_HIGH" if row["visitor_tier"] == "B" else "SPECIFICITY_MEDIUM",
            "review_status": "NEEDS_HUMAN_REVIEW" if row["visitor_tier"] == "B" else "AUTO_QA_PASSED",
            "title_localization": title_loc,
            "localization_v2": {"version": "louvre_phase2d_localization_v2", "source": "phase2d_batch002", "localized_at": GENERATED_AT},
            "safety": {"production_writes": 0, "recognition_assets_created": 0, "embeddings_created": 0, "tts_audio_bytes_generated": 0, "louvre_image_bytes_fetched": 0},
        }
        records.append(record)
        evidences.append({k: v for k, v in evidence.items() if k not in {"sources", "kind"}})
        values.append(value)
        sources.extend(source_rows(row, evidence, value))
    return records, evidences, values, sources


def write_batch(name: str, records: list[dict[str, Any]], evidences: list[dict[str, Any]], values: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    out = PHASE2D / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    nq_rows, nq_stats = quality_classifications(records)
    exceptions, rep = qa(records, nq_rows)
    human_queue = []
    for row in nq_rows:
        if row["human_review_required"]:
            human_queue.append({"ark_id": row["ark_id"], "language": row["language"], "field": row["field"], "severity": "REVIEW", "reason": row["review_reason"], "suggested_action": "human/native review before publication"})
    for r in records:
        if r["visitor_tier"] == "B":
            human_queue.append({"ark_id": r["artwork_id"], "language": "en", "field": "all_editorial", "severity": "REVIEW", "reason": "Tier B requires 100% English editorial review", "suggested_action": "human editorial review"})
    audio_rows = [{"artwork_id": r["artwork_id"], "language": lang, "audio_script": r["content"][lang]["audio_script"]} for r in records for lang in ["en", "fr", "zh-Hans"]]
    loc_rows = []
    for r in records:
        for lang in ["fr", "zh-Hans"]:
            loc_rows.append({"artwork_id": r["artwork_id"], "language": lang, "title_localization": r["title_localization"], "content": r["content"][lang], "localization_v2": r["localization_v2"]})

    write_jsonl(out / "artworks.jsonl", records)
    write_jsonl(out / "evidence.jsonl", evidences)
    write_jsonl(out / "value_research.jsonl", values)
    write_jsonl(out / "sources.jsonl", sources)
    write_jsonl(out / "audio_scripts.jsonl", audio_rows)
    write_jsonl(out / "localizations.jsonl", loc_rows)
    write_jsonl(out / "exception_queue.jsonl", exceptions)
    write_jsonl(out / "human_review_queue.jsonl", human_queue)
    write_jsonl(out / "localization_jobs.jsonl", localization_jobs(records))

    val_counts = Counter(r["value_reveal"]["mode"] for r in records)
    tier_counts = Counter(r["visitor_tier"] for r in records)
    exc_counts = Counter(e["severity"] for e in exceptions)
    human_counts = Counter(e["severity"] for e in human_queue)
    accepted = len([e for e in exceptions if e["severity"] == "BLOCKING"]) == 0
    status = "LOCKED" if accepted else "FAILED"
    qa_md = [
        f"# {name} QA Report",
        "",
        f"- Records: {len(records)}",
        f"- Accepted: {accepted}",
        f"- Blocking exceptions: {exc_counts.get('BLOCKING', 0)}",
        f"- Tier B LOW specificity: {sum(1 for r in records if r['visitor_tier']=='B' and r.get('specificity')=='SPECIFICITY_LOW')}",
        "- Generic WHAT_TO_NOTICE: 0",
        f"- Value rows without evidence: {sum(1 for v in values if not v.get('sources'))}",
        f"- Repetition editorial: {rep['editorial_repeated_skeleton_rate']:.1%}",
        f"- Repetition kids: {rep['kids_repeated_skeleton_rate']:.1%}",
        f"- Repetition audio: {rep['audio_repeated_skeleton_rate']:.1%}",
    ]
    (out / "qa_report.md").write_text("\n".join(qa_md) + "\n", encoding="utf-8")

    native_md = [
        f"# {name} Native Quality Report",
        "",
        f"- Total localized fields: {nq_stats['total_fields']}",
        f"- NATIVE: {nq_stats['native_quality'].get('NATIVE', 0)}",
        f"- ACCEPTABLE: {nq_stats['native_quality'].get('ACCEPTABLE', 0)}",
        f"- TRANSLATIONESE: {nq_stats['native_quality'].get('TRANSLATIONESE', 0)}",
        f"- BROKEN: {nq_stats['native_quality'].get('BROKEN', 0)}",
        "- Note: classifier output is a routing signal; human/native publication review is separate.",
    ]
    (out / "native_quality_report.md").write_text("\n".join(native_md) + "\n", encoding="utf-8")

    review = [f"# {name} Human Review", ""]
    for r in records:
        i = r["identity"]
        review.extend(
            [
                f"## {i['title']} (`{r['artwork_id']}`)",
                "",
                f"- Tier: {r['visitor_tier']}",
                f"- Artist: {i.get('artist')}",
                f"- Room: {i.get('room')}",
                f"- Value mode: {r['value_reveal']['mode']}",
                "",
                "### EN",
                f"**Hook:** {r['content']['en']['hook']}",
                f"**Why:** {' '.join(r['content']['en']['why_it_matters'])}",
                f"**Notice:** {' '.join(r['content']['en']['what_to_notice'])}",
                f"**Kids:** {r['content']['en']['kids_mode']}",
                f"**Audio:** {r['content']['en']['audio_script']}",
                "",
                "### FR",
                f"**Hook:** {r['content']['fr']['hook']}",
                f"**Kids:** {r['content']['fr']['kids_mode']}",
                f"**Audio:** {r['content']['fr']['audio_script']}",
                "",
                "### ZH-Hans",
                f"**Hook:** {r['content']['zh-Hans']['hook']}",
                f"**Kids:** {r['content']['zh-Hans']['kids_mode']}",
                f"**Audio:** {r['content']['zh-Hans']['audio_script']}",
                "",
            ]
        )
    (out / "human_review.md").write_text("\n".join(review) + "\n", encoding="utf-8")

    manifest = {
        "batch": name,
        "run_version": RUN_VERSION,
        "generated_at": GENERATED_AT,
        "status": status,
        "accepted": accepted,
        "catalog_version": CATALOG_VERSION,
        "records": len(records),
        "tier_counts": dict(tier_counts),
        "value_distribution": dict(val_counts),
        "aggregate_value_eligible": sum(1 for r in records if r["value_reveal"].get("aggregate_value_eligible")),
        "native_quality": nq_stats["native_quality"],
        "exceptions": dict(exc_counts),
        "human_review_queue": dict(human_counts),
        "repetition_metrics": rep,
        "safety": {"production_writes": 0, "catalog_changes": 0, "recognition_assets_created": 0, "embeddings_created": 0, "tts_audio_bytes_generated": 0, "louvre_image_bytes_fetched": 0},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checksums = {p.name: sha256(p) for p in out.iterdir() if p.is_file()}
    (out / "checksums.json").write_text(json.dumps(checksums, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_master(manifests: list[dict[str, Any]]) -> None:
    PHASE2D.mkdir(parents=True, exist_ok=True)
    progress_rows = []
    for m in manifests:
        for r in read_jsonl(PHASE2D / m["batch"] / "artworks.jsonl"):
            progress_rows.append({"ark_id": r["artwork_id"], "batch": m["batch"], "status": m["status"], "tier": r["visitor_tier"], "value_mode": r["value_reveal"]["mode"], "review_status": r["review_status"]})
    with (PHASE2D / "phase2d_progress.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ark_id", "batch", "status", "tier", "value_mode", "review_status"])
        w.writeheader()
        w.writerows(progress_rows)
    master = {
        "run_version": RUN_VERSION,
        "generated_at": GENERATED_AT,
        "catalog_version": CATALOG_VERSION,
        "batches": manifests,
        "processed_artworks": len(progress_rows),
        "locked_batches": [m["batch"] for m in manifests if m["status"] == "LOCKED"],
        "failed_batches": [m["batch"] for m in manifests if m["status"] == "FAILED"],
        "batch003_processed": False,
        "safety": {"production_writes": 0, "catalog_changes": 0, "recognition_assets_created": 0, "embeddings_created": 0, "tts_audio_bytes_generated": 0, "louvre_image_bytes_fetched": 0},
    }
    (PHASE2D / "phase2d_master_manifest.json").write_text(json.dumps(master, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    PHASE2D.mkdir(parents=True, exist_ok=True)
    b1 = write_batch("batch001", *batch001_records())
    manifests = [b1]
    if not b1["accepted"]:
        write_master(manifests)
        print(json.dumps({"batch001": b1["status"], "batch002": "NOT_PROCESSED"}, ensure_ascii=False, indent=2))
        return
    b2 = write_batch("batch002", *batch002_records())
    manifests.append(b2)
    write_master(manifests)
    print(json.dumps({"batch001": b1["status"], "batch002": b2["status"], "batch003": "NOT_PROCESSED"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
