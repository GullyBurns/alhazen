# Gobtown: Founding Era — Design Spec

**Date:** 2026-07-26
**Campaign:** `goblinpak` — `myth-campaign-f0745885c38a` (TypeDB `alh_mythras`)
**System:** Mythras Classic Fantasy Imperative (CFI)
**Status:** Draft for review

---

## 1. Premise

GoblinPack is a Classic Fantasy supplement in which goblinoids are protagonists rather than
battle-fodder. This spec covers the **founding era** of Gobtown: a settlement roughly eight
years old, a few hundred souls in a cave network in a remote northern pass, which everyone
including most of its own residents expects to fail.

The design thesis, from Haidt's moral foundations work: goblinoids are not immoral, they
weight the foundations differently. They are "evil" the way a foreign culture is evil to a
xenophobe — legibly, consistently, with internal logic about who deserves what.

**Tribal hatred is contextual, not innate.** Two warbands competing for one valley have
excellent reasons to slaughter each other; the same two under a competent captain may not.
How hate-filled a group is depends on leadership, scarcity, and history — not species.

**The Evil passion is not psychopathy.** Pre-modern humans enjoyed public executions without
being unable to love their children. Cruelty is a spectator taste and a tool, directed by
cultural rules about who is fair game. This distinction is load-bearing; see §5.5.

### Scope boundary

This spec covers the founding era only. The present-day Year 12 material already in the
database (the full city, the Accords, the inner circle) is retained as GM-visibility
*future canon* — it tells the GM what is at stake, and is not playable content here.

---

## 2. Canon boundaries

Greymyr setting material is under NDA and has **not** been read. Nothing in this spec derives
from it. The proxy policy:

| Keep (published TDM pantheon / user's own work) | Proxy (Greymyr gazetteer) |
|---|---|
| Ehrendil Beldroth — elven god of music and creation | the mountain range |
| Garex Blood-Drinker, Grumash, Thaogg Axefang, Zulfang | the human realm |
| The user's cults: Vykthar, Velthara, Grottendacz, Mawhunger Gnawbone, Khorthak, Sniktch, Razak, Skarrak | the duke |
| Drakmoor, the Ironspear Clan, Thekla Morvani, Gobtown | any named site from the manuscripts |

**Coined proxy names** (cheap to change; all follow the stated rule that descriptive elements
should be titles rather than surnames):

- **The Kazhrun** — the mountain spine east of human lands; goblinoid heartland, permanently
  at war with itself, no institution outliving the chief who founded it. Humans call it the
  Eastern Wall.
- **The Duchy of Valdenmark** — the human realm to the west. Wealthy, hostile to goblinoids,
  under low-grade pressure from Kazhrun raiding.
- **Duke Aldric Kessarin** — its ruler; advised on goblinoid matters by Thekla Morvani.
- **Khorvenn**, *the humming* — the cave system Gobtown grows inside.

Location is deliberately loose: a high pass at the cold northern end of the Kazhrun, outside
the tribal lands, reachable only by routes that kill the careless. **Remoteness is the city's
first wall** and the reason a secret this large can be kept at all.

---

## 3. Thekla Morvani as narrator

Thekla Morvani, Grand Prevaricator of Vykthar, advisor on goblinoid matters to Duke Aldric
Kessarin, narrates the supplement. Each chapter is framed by her commentary.

A Grand Prevaricator is a professional myth-maker. This makes the narrator **unreliable by
doctrine**: she is not neutrally describing goblinoid society, she is selling it to a hostile
human court, and every framing is an act of advocacy by a priestess whose goddess rewards the
tale told well.

**Thekla does not know about the Wellspring.** (Decided 2026-07-26.) Her narration is honest
as far as it goes; she is arguing for goblinoid complexity from evidence, not protecting a
secret. Her eventual discovery of what actually underwrites Gobtown is therefore a real event
with real consequences for her position, her faith, and her patron.

Her established voice, from the v0 draft:

> "Your Grace — it might be wiser to stop thinking of your adversaries in the mountains as
> just chaotic and 'evil.' It is true that they want nothing more in life than to wade
> through the blood of your countrymen... But you must also remember that the only reason
> they would contemplate these actions is that it would make a fantastic drinking song.
> Please… at least try to see it from their point of view."

---

## 4. The Wellspring

### 4.1 What it is

In the deepest chamber of Khorvenn, a natural cathedral of stone holds a pool that sings.
Bound in chains of crystallised song is an angelic spirit of Ehrendil Beldroth — and the
spring and the spirit are **one entity, two aspects**. The water is the angel's presence made
physical. Ancient carvings cover the approach: spiralling patterns that shift in torchlight,
musical notation in an unreadable script. Objects left overnight are found arranged in
geometric patterns by morning.

The water carries the harmony through the settlement — drunk, bathed in, irrigating the fungus
beds. This answers the standing question of how a hidden cave feeds several hundred people:
**it feeds them because the god is in the water.** Cutting the water is cutting the god.

### 4.2 The four-layer irony

| Party | Believes |
|---|---|
| Drakmoor | He captured and bound a celestial being and forces it to serve. Daily ritual maintains the binding. |
| The angel | It was assigned by cosmic bureaucracy to a degrading rehabilitation project among creatures it finds crude and aesthetically offensive. It suffers from the company, not the chains — and is personally insulted that second-rate goblin hedge-wizards imagine their ritual could hold it. (It could leave at any time. It has not mentioned this.) |
| Ehrendil Beldroth | Goblinoids are part of creation and currently outside the Song. They cannot be commanded into harmony without destroying what makes them themselves. So they must be brought in through their own cunning and self-interest — offered civilisation as a prize they think they stole. |
| Everyone else | Will be horrified on discovery, and will not understand what they are looking at. |

The binding ritual is theatre. It is also a daily meditation that gradually attunes Drakmoor
to reciprocity, deferred gratification, and mutual benefit. The angel's grudging advice
consistently steers him toward solutions that strengthen the community rather than his grip.

### 4.3 The Concord (mechanics)

The harmony has a real mechanical footprint. Within Gobtown:

- Cooperative actions (assisting, coordinated effort, shared labour) gain an **augment**.
- Inter-species friction checks run **one difficulty grade easier**.
- Passions pulling toward communal benefit **deepen** faster than normal; passions pulling
  toward predation on fellow settlers **wane** faster. (Uses `cfi/alignment/deepening-waning`.)

**The decay clock.** If the dawn ritual is missed, the Concord degrades visibly:

| Elapsed | Effect |
|---|---|
| Day 1 | Augment lost. Bickering, old grudges resurface. |
| Day 2 | Friction checks return to normal grade. Hoarding begins; shared stores are raided. |
| Day 3 | Friction checks one grade *harder* than baseline. Knives. |
| Day 4+ | The settlement begins to disassemble along tribal lines. |

This makes "keep the chief alive and on schedule" a live playable pressure, and lets players
feel the divine presence through their own dice long before anyone explains it.

### 4.4 Discovery vectors

- A cleric of Ehrendil senses **one** presence, unmistakably, at considerable range.
- The water tastes wrong to anyone who has drunk from a real spring.
- Anyone who follows wet stone downhill far enough arrives.
- **Koolinth can enter the pool.** They are the only settlers who can physically swim in the
  god. This is a standing risk and a standing story opportunity — see §5.2.

---

## 5. Character generation

### 5.1 The structural key: Race vs Culture

CFI Step 5 separates **Race** (physiology: characteristic dice, darkvision, movement,
lifespan) from **Culture** (skill package, alignment, passions — what you were raised into).

In year eight, **Gobtown culture does not exist yet.** Every adult in the caves was raised in
the Kazhrun. Every PC therefore arrives with tribal skills, tribal passions, and tribal
instincts about who is fair game — all wrong for the place they now live. The friction between
what the character was raised to be and what the settlement needs is not colour text; it is
on the sheet, and it is the campaign.

Two culture packages are written. Only one is available.

### 5.2 Races

Characteristic dice follow the CFI Racial Characteristics Table format. Averages in
parentheses are used for Points Build.

| Stat | Goblin | Hobgoblin | Orc | Bugbear | Koolinth | Orog |
|:--|:--:|:--:|:--:|:--:|:--:|:--:|
| STR | 2d6+1 (8) | 2d6+6 (13) | 2d6+8 (15) | 2d6+12 (19) | 2d6+5 (12) | 2d6+9 (16) |
| CON | 3d6 (11) | 2d6+6 (13) | 2d6+6 (13) | 2d6+7 (14) | 2d6+7 (14) | 2d6+8 (15) |
| SIZ | 1d4+5 (8) | 2d6+6 (13) | 2d6+6 (13) | 2d6+14 (21) | 2d6+5 (12) | 2d6+7 (14) |
| DEX | 2d6+7 (14) | 3d6 (11) | 3d6 (11) | 3d6 (11) | 2d6+5 (12) | 3d6 (11) |
| INT | 2d6+5 (12) | 2d6+6 (13) | 2d6+4 (11) | 2d6+3 (10) | 2d6+5 (12) | 2d6+6 (13) |
| POW | 3d6 (11) | 3d6 (11) | 3d6 (11) | 3d6 (11) | 3d6 (11) | 3d6 (11) |
| CHA | 2d6 (7) | 2d6+3 (10) | 2d6+1 (8) | 2d6+1 (8) | 2d6+2 (9) | 2d6+2 (9) |

**Common to all goblinoids:** Darkvision 60 ft (as CFI Half-Orc). Illiterate unless raised in
a literate culture. Additional languages limited to goblin, hobgoblin, orc, and gnoll.

**Per-race special rules:**

- **Goblin** — Movement 20 ft. *Light sensitivity*: Perception and ranged attacks one grade
  harder in full daylight. Lifespan ~50. Most likely of all goblinoids to be literate; a
  Goblin may take literacy at creation without the Experience Roll cost.
- **Hobgoblin** — Movement 25 ft. *Thick hide*: natural 1 AP on all locations. **No light
  sensitivity.** Lifespan ~60. Natural officers; other goblinoids expect them to command.
- **Orc** — Movement 25 ft. Light sensitivity as Goblin. Lifespan ~40 — the shortest, and it
  shapes the psychology: an orc of thirty is old and knows it.
- **Bugbear** — Movement 25 ft. **No light sensitivity.** *Scent*: Perception by smell one
  grade easier. Their SIZ makes some cave galleries impassable — a real constraint in Khorvenn
  and a running joke.
- **Koolinth** — Movement 20 ft land / 30 ft swim. *Amphibious*: breathes water indefinitely;
  Swim base doubled. Suffers in dry heat (Endurance one grade harder). **Can enter the
  Wellspring pool.** In a settlement built on a sacred spring this is enormous: a Koolinth PC
  can go where Drakmoor cannot follow.
- **Orog** — Movement 25 ft. *Thick hide*: natural 1 AP. Darkvision 90 ft (deep-dwelling), but
  light sensitivity is **severe** — two grades harder in full daylight. Disciplined and
  markedly smarter than common orcs, which common orcs resent.

### 5.3 Half-breeds and mixed heritage

Orcs, per the source material, "will breed with anything," and half-breeds are common
throughout the Kazhrun. Crucially: **a half-breed belongs to no clan.** In tribal society this
is a permanent disqualification from status, protection, and inheritance.

Which is exactly why they came. The people with no tribe are the first to arrive at a place
that does not ask what tribe you are from. **Mixed-heritage characters are a disproportionate
share of founding-era Gobtown, and are a large part of why the settlement cohered at all.**
This is the historical root of the Mixed District that dominates the Year 12 city.

- **Half-Orc** — use the CFI Half-Orc entry as printed. Add the Gobtown note: a half-orc raised
  among orcs takes the Kazhrun Tribal culture below rather than a human culture.
- **Goblinoid mixed heritage** (orc×goblin, hobgoblin×orc, bugbear×hobgoblin, etc.) — choose
  two parent races. For each characteristic, average the two parents' **table averages**
  (rounding down) and express the result as `2d6+N` where N = average − 7; if that average is
  7 or less, use `2d6`. Working from the averages rather than the dice expressions avoids the
  problem that parents may roll different dice entirely (Goblin SIZ is `1d4+5`, Orc SIZ is
  `2d6+6`). *Example — Orc × Goblin:* STR (15+8)/2 = 11 → `2d6+4`; SIZ (13+8)/2 = 10 →
  `2d6+3`. Take darkvision from the better parent, light sensitivity from the worse, and
  movement from the smaller. Choose one parent's special rule; the other is lost.
- **Passion, all mixed heritage:** *No Clan Will Have Me* — starts at the standard passion
  value. It augments any roll to survive alone, endure contempt, or make common cause with
  another outcast. In Gobtown, and only in Gobtown, it begins to wane.

### 5.4 Culture packages

**Kazhrun Tribal** *(available — this is what everyone has)*

- Free skills: Customs (Kazhrun) +40, Native Tongue +40
- Standard: Athletics, Brawn, Endurance, Evade, Perception, Stealth, plus one of Ride or Swim
- Professional: Craft (any), Intimidation, Survival, Track, plus one of Healing or Navigate
- Illiterate. Passions from the tribal menu (§5.5). Alignment typically Chaotic Evil;
  hobgoblins and orogs typically Lawful Evil.

**Gobtown-Born** *(written, but NOT available at character creation)*

Requires being raised in the settlement from early childhood. In year eight the oldest
qualifying child is seven years old. No PC can take this package. It is printed so players can
read the future they are building, and **the first child to come of age with it is a campaign
milestone.**

- Free skills: Customs (Gobtown) +40, Native Tongue +40, Language (one other goblinoid) +40
- Standard: Athletics, Deceit, Endurance, Influence, Insight, Locale, Perception
- Professional: Commerce, Craft (any), Engineering, Lore (any), Streetwise
- **Literate.** Passions drawn from a different menu entirely: *This Place Must Not Fail*,
  *My Neighbour Is Not Meat*, *I Have Never Seen The Sky And I Am Fine*.

### 5.5 Passions — the five virtues

The five goblinoid virtues become the standard tribal passion menu. Starting values per
`cfi/alignment/passion-table`. Each augments rolls taken in accordance with it.

| Passion | Augments |
|---|---|
| *Shut Up And Get On With It* | Enduring hardship without complaint; completing a task under pressure; refusing to be delayed by ceremony, rank, or feelings |
| *Be The Biggest Bastard You Can* | Intimidation; claiming credit; any act that deters future challenges |
| *Extra Points For Comedy Value* | Any action that is both effective and humiliating to the target; improvised cruelty with an audience |
| *Don't Be A Picky Eater* | Resisting disgust, poison, spoiled food, or starvation; making use of what others discard |
| *Everyone Hates Us* | Acting against the smug and self-declared righteous; resisting Influence from other races |

**The Concord's effect:** *Be The Biggest Bastard* and *Extra Points For Comedy Value* wane
when their targets are fellow settlers, because the Concord has quietly redrawn who is fair
game. Players will notice their passions sliding and will not be told why.

### 5.6 The alignment rider

Goblinoid PCs are Evil. The Concord does not make anyone Good — it **redraws the boundary of
who counts as fair game** to include fellow settlers.

A Gobtown goblin is still Evil by any Valdenmark cleric's reckoning: cruel to outsiders,
contemptuous of weakness, delighted by others' misfortune. He simply does not rob his
neighbours any more, and **could not tell you why not.** That is the angel's work expressed as
an alignment rule, and it is the single most important mechanical statement in this document.

Ethical axis drifts Lawful under the Concord. Drakmoor is Lawful Evil and drifting further —
which he experiences as exhaustion.

### 5.7 Classes

CFI's four classes carry the v0 concept list as goblinoid re-skins:

| CFI class | Goblinoid expressions |
|---|---|
| Fighter | warrior, wolf-rider, beast handler, pit-fighter |
| Rogue | sneak, agent, hunter, scout, acrobat |
| Cleric | priest, shaman, prevaricator (Vykthar) |
| Magic-User | hedge-wizard, alchemist, ritualist |

Merchant/crafter/miner concepts are Professional skill loadouts, not separate classes.

**Restriction:** no PC may be a cleric of Ehrendil Beldroth. Obviously.

---

## 6. The scenario: "The Pilgrim"

### 6.1 The party — the Fixers

PCs are trusted early settlers, Drakmoor's problem-solvers, **deliberately kept ignorant.**
Orders arrive with holes in them: *turn her back; do not let her near the deep galleries; do
not ask why.* Their loyalty is the campaign's real stat, and the dramatic irony runs the whole
arc — the player works it out long before the character is permitted to.

Each Fixer needs: race, class, why they fled the Kazhrun, and what they owe Drakmoor.

### 6.2 The situation

A cleric of Ehrendil Beldroth has reached the pass. She felt something from a hundred miles
away that should not be there, and she has walked to the edge of the world to find out what.

The party must turn her back **without killing her** — a dead Ehrendil cleric in the north
brings Valdenmark — and **without letting her near the water**, because she will know it on
sight.

Every available tool is a different kind of failure: lying invites her to stay and investigate
the inconsistencies; robbing her leaves a victim who reports; frightening her confirms there
is something to hide. And the worst complication is that she is **genuinely kind to them**,
treats them as people, thanks them for the food — and they have no idea what to do about that.
The Concord is, quietly, making them worse at being hostile to her.

### 6.3 Resolutions

- **Pyrrhic:** she leaves convinced, and tells someone about the surprisingly decent goblins.
- **Compromise:** she is escorted out believing the settlement is a mining camp; a clock starts.
- **Spectacular failure:** she reaches the water.
- **Surprising success:** she leaves knowing exactly what is down there, and decides — for her
  own reasons — to say nothing. She becomes the party's most dangerous asset.

---

## 7. Database plan

Target: `myth-campaign-f0745885c38a` in `alh_mythras`.

1. **Switch system flag** from `mythras` to `classic-fantasy` (direct TypeDB attribute edit;
   `create-campaign` sets it but no update command exists). Enables the 348-piece CFI rules
   graph for this campaign.
2. **Rewind era** — game date to year eight of the settlement; opening scene set to the Fixers
   receiving an order with holes in it.
3. **Relabel Year 12 material** — existing lore, NPCs, factions, and locations get a
   founding-era note marking them as future canon, not present. No deletions.
4. **New lore entries** — the Kazhrun, Valdenmark, Khorvenn, the Wellspring (gm), the Concord
   with its decay clock (gm), Thekla's narrator frame, the six races, half-breed rules, the two
   culture packages, the five virtues, the alignment rider.
5. **New NPCs** — founding-era Drakmoor (exhausted, ~50, Lawful Evil drifting); the angel;
   Thekla Morvani; Duke Aldric Kessarin; a traditionalist ringleader agitating for a return to
   raiding; the pilgrim.
6. **New factions** — the surviving Ironspear, the traditionalists, Valdenmark, the Kazhrun
   tribes, the mixed-heritage settlers.
7. **Scenario entry** — "The Pilgrim" as gm-visibility lore.

---

## 8. Open questions

1. **Population ceiling.** The prior draft's instinct was 300–400 for a settlement that must
   stay hidden. Remoteness argues for the low end. Needs a number before the scenario is run.
2. **Who carved Khorvenn?** The caves predate Drakmoor. Either Ehrendil placed the spirit in
   anticipation, or it is a much older site repurposed — the second is more interesting and
   raises the question of who cut the musical notation into the walls.
3. **Cult politics.** Vykthar's myth-making, Velthara's theft-as-art, and Razak's systematic
   pillage all have opinions about a settlement that has stopped raiding. Gobtown should be
   theologically contested; that is a chapter in itself.
4. **Does the angel have a name?** It has a voice and comic timing but no name in any source
   document. It may refuse to give one, which is characterful.
5. **Proxy names** are provisional. Kazhrun, Valdenmark, Kessarin, and Khorvenn can all be
   swapped at no cost before the lore is written.
