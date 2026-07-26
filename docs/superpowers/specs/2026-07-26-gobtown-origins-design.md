# Gobtown: Founding Era — Design Spec

**Date:** 2026-07-26 (rev. 2 — race stats sourced from the rulebook; scenario reworked)
**Campaign:** `goblinpak` — `myth-campaign-f0745885c38a` (TypeDB `alh_mythras`)
**System:** Mythras Classic Fantasy Imperative (CFI)
**Status:** Draft for review

**Source note.** All race numbers in §5 are transcribed from *Classic Fantasy* (TDM500) Chapter 11,
extracted from the user's own copy. Full extraction with page/line citations:
`scratchpad/cf/EXTRACT.md`. No Greymyr manuscript material was read (see §2).

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
cultural rules about who is fair game. This distinction is load-bearing; see §5.7.

**Design test for every rule in this document:** does the pressure come from goblinoid values,
or from human ones smuggled in? The first draft of the opening scenario failed this test (§6).

### Scope boundary

Founding era only. The Year 12 material already in the database (the full city, the Accords,
the inner circle) is retained as GM-visibility *future canon* — it tells the GM what is at
stake, and is not playable content here.

---

## 2. Canon boundaries

Greymyr setting material is under NDA and has **not** been read. Nothing here derives from it.

| Keep (published TDM / user's own work) | Proxy (Greymyr gazetteer) |
|---|---|
| Ehrendil Beldroth — elven god of music and creation | the mountain range |
| Garex Blood-Drinker, Grumash, Thaogg Axefang, Zulfang | the human realm |
| The user's cults: Vykthar, Velthara, Grottendacz, Mawhunger Gnawbone, Khorthak, Sniktch, Razak, Skarrak | the duke |
| Drakmoor, the Ironspear Clan, Thekla Morvani, Gobtown | any named site from the manuscripts |

**Coined proxy names** (provisional; cheap to change):

- **The Kazhrun** — the mountain spine east of human lands; goblinoid heartland, permanently at
  war with itself. Humans call it the Eastern Wall.
- **The Duchy of Valdenmark** — the human realm to the west. Wealthy, hostile, under low-grade
  pressure from Kazhrun raiding.
- **Duke Aldric Kessarin** — its ruler; advised on goblinoid matters by Thekla Morvani.
- **Khorvenn**, *the humming* — the cave system Gobtown grows inside.

Location is deliberately loose: a high pass at the cold northern end of the Kazhrun, outside the
tribal lands, reachable only by routes that kill the careless. **Remoteness is the city's first
wall**, and the reason a secret this large can be kept.

---

## 3. Thekla Morvani as narrator

Thekla Morvani, Grand Prevaricator of Vykthar, advisor on goblinoid matters to Duke Aldric
Kessarin, narrates the supplement. Each chapter is framed by her commentary.

A Grand Prevaricator is a professional myth-maker, which makes the narrator **unreliable by
doctrine**: she is not neutrally describing goblinoid society, she is selling it to a hostile
human court. Every framing is advocacy by a priestess whose goddess rewards the tale told well.

**Thekla does not know about the Wellspring.** Her narration is honest as far as it goes; she
argues for goblinoid complexity from evidence, not to protect a secret. Her eventual discovery
of what actually underwrites Gobtown is a real event.

**Race:** half-orc. This matches Vykthar's own iconography (the goddess appears as a half-orc of
indiscernible mixture) and makes Thekla the road not taken for every mixed-heritage settler in
Gobtown — a half-breed who found status in a human court because no goblinoid clan would have
her. See §5.4.

**Title reconciliation:** the cult's internal ranks are Scarkeeper, Warsinger, Braggard, and
Listener. "Grand Prevaricator" is the formal title she uses at court, because "Warsinger" would
not survive a Valdenmark audience chamber.

Her established voice, from the v0 draft:

> "Your Grace — it might be wiser to stop thinking of your adversaries in the mountains as just
> chaotic and 'evil.' It is true that they want nothing more in life than to wade through the
> blood of your countrymen... But you must also remember that the only reason they would
> contemplate these actions is that it would make a fantastic drinking song. Please… at least
> try to see it from their point of view."

---

## 4. The Wellspring

### 4.1 What it is

In the deepest chamber of Khorvenn, a natural cathedral of stone holds a pool that sings. Bound
in chains of crystallised song is an angelic spirit of Ehrendil Beldroth — and the spring and
the spirit are **one entity, two aspects**. The water is the angel's presence made physical.
Ancient carvings cover the approach: spiralling patterns that shift in torchlight, musical
notation in an unreadable script. Objects left overnight are found arranged in geometric
patterns by morning.

The water carries the harmony through the settlement — drunk, bathed in, irrigating the fungus
beds. This answers how a hidden cave feeds several hundred people: **it feeds them because the
god is in the water.** Cutting the water is cutting the god.

### 4.2 The four-layer irony

| Party | Believes |
|---|---|
| Drakmoor | He captured and bound a celestial being and forces it to serve. Daily ritual maintains the binding. |
| The angel | It was assigned by cosmic bureaucracy to a degrading rehabilitation project among creatures it finds crude and aesthetically offensive. It suffers from the company, not the chains — and is personally insulted that second-rate goblin hedge-wizards imagine their ritual could hold it. (It could leave at any time. It has not mentioned this.) |
| Ehrendil Beldroth | Goblinoids are part of creation and currently outside the Song. They cannot be commanded into harmony without destroying what makes them themselves. So they must be brought in through their own cunning and self-interest — offered civilisation as a prize they think they stole. |
| Everyone else | Will be horrified on discovery, and will not understand what they are looking at. |

The binding ritual is theatre. It is also a daily meditation that gradually attunes Drakmoor to
reciprocity, deferred gratification, and mutual benefit. The angel's grudging advice
consistently steers him toward solutions that strengthen the community rather than his grip.

### 4.3 The Concord (mechanics)

Within Gobtown:

- Cooperative actions (assisting, coordinated effort, shared labour) gain an **augment**.
- Inter-species friction checks run **one difficulty grade easier**.
- Passions pulling toward communal benefit **deepen** faster; passions pulling toward predation
  on fellow settlers **wane** faster (uses `cfi/alignment/deepening-waning`).

**The decay clock.** If the dawn ritual is missed:

| Elapsed | Effect |
|---|---|
| Day 1 | Augment lost. Bickering, old grudges resurface. |
| Day 2 | Friction checks return to normal grade. Hoarding begins; shared stores are raided. |
| Day 3 | Friction checks one grade *harder* than baseline. Knives. |
| Day 4+ | The settlement disassembles along tribal lines. |

Players feel the divine presence through their own dice long before anyone explains it.

### 4.4 Discovery vectors

- A cleric of Ehrendil senses **one** presence, unmistakably, at considerable range.
- The water tastes wrong to anyone who has drunk from a real spring.
- Anyone who follows wet stone downhill far enough arrives.
- **Koolinth can enter the pool** (§5.3). They are the only settlers who can physically swim in
  the god — a standing risk and a standing story opportunity.
- **Someone brags.** This is the likeliest vector by a wide margin, and it drives §6.

---

## 5. Character generation

### 5.1 The structural key: Race vs Culture

CFI separates **Race** (physiology: characteristic dice, darkvision, movement, lifespan) from
**Culture** (skill package, alignment, passions — what you were raised into).

In year eight, **Gobtown culture does not exist yet.** Every adult in the caves was raised in
the Kazhrun, so every PC arrives with tribal skills, tribal passions, and tribal instincts about
who is fair game — all wrong for the place they now live. That friction is on the sheet, and it
is the campaign.

### 5.2 Which rules format to write in

The books contain **two incompatible PC race formats**:

| | Format 1 — CF core (TDM500 Ch. 2) | Format 2 — CFI SRD (ORC-licensed) |
|---|---|---|
| Alignment | Single-axis Moral Philosophy (Good/Neutral/Evil) | **Two-axis: Ethical Code + Moral Code** |
| Vision trait | Infravision | **Darkvision** |
| Free Skills line | implicit | **explicit** |
| Literacy | not addressed in race entry | **explicit Illiterate rule** |
| NPC stat block | included in race entry | absent |

**Decision: write in Format 2 (CFI SRD).** Three reasons — it matches the campaign's CFI setting
and the 348-piece rules graph already loaded in `alh_mythras`; it carries the two-axis alignment
the design in §5.7 depends on; and it is **ORC-licensed**, which means goblinoid race write-ups
built against it are publishable without TDM clearance.

Terminology consequence: creature entries say *Infravision*; PC entries say *Darkvision*. Port
accordingly.

### 5.3 The races (as printed in TDM500 Ch. 11)

Characteristics transcribed verbatim from the creature entries. **These replace the invented
table in rev. 1 entirely.**

| Stat | Goblin | Hobgoblin | Orc | Bugbear |
|:--|:--:|:--:|:--:|:--:|
| STR | 1d6+4 (8) | 2d6+6 (13) | 2d6+7 (14) | 2d6+12 (19) |
| CON | 3d6 (11) | 3d6+3 (14) | 3d6+2 (13) | 2d6+8 (15) |
| SIZ | 1d6+4 (8) | 1d6+13 (17) | 2d6+7 (14) | 2d6+14 (21) |
| DEX | 4d6 (14) | 3d6 (11) | 3d6 (11) | 3d6 (11) |
| INT | 2d6+5 (12) | 2d6+6 (13) | 2d6+4 (11) | 2d6+3 (10) |
| POW | 3d6 (11) | 3d6 (11) | 3d6 (11) | 3d6 (11) |
| CHA | 2d6 (7) | 2d6 (7) | 2d6 (7) | 2d6 (7) |
| Damage Mod | −1d2 | +1d2 | +1d2 | +1d6 |
| Movement | 15 ft | 15 ft | 20 ft | 15 ft |
| Lifespan | ~50 yrs | ~60 yrs | ~40 yrs | not given |
| Traits | Darkvision, **Light Sensitive** | Darkvision, **Tunnel Sense** | Darkvision, **Light Sensitive** | Darkvision |

Every goblinoid shares POW `3d6 (11)` and CHA `2d6 (7)`. Magic Points 11 across the board.

**Variants, written as deltas exactly as the book writes them:**

- **Koolinth** — sub-species of **Hobgoblin**. Inherits everything; overrides colouration and
  language, Combat Style becomes spears/tridents/pikes, and adds the **Aquatic** and **Swimmer**
  traits, Swim 66%, and 20 ft underwater movement. *A Koolinth PC is mechanically a hobgoblin
  who can swim into the Wellspring.*
- **Orog** — variant of **Orc** ("great orcs", 6–6½ ft, possibly part ogre). Overrides STR
  `2d6+10`, CON `3d6+6`, SIZ `1d6+12`, DEX `2d6+2` (**the book prints no averages for these — do
  not compute them into the Points Build column without flagging**); +10% to Athletics, Brawn,
  Endurance, Unarmed and Combat Style; 2 points of tough skin. "Treated in all other ways as
  orcs." Rare — roughly one per ten orc warriors.

### 5.4 Half-breeds and mixed heritage

Orcs "will breed with anything," and half-breeds are common throughout the Kazhrun. Crucially,
**a half-breed belongs to no clan** — a permanent disqualification from status, protection, and
inheritance in tribal society.

Which is exactly why they came. The people with no tribe are the first to arrive at a place that
does not ask what tribe you are from. **Mixed-heritage characters are a disproportionate share
of founding-era Gobtown and a large part of why the settlement cohered at all** — the historical
root of the Mixed District that dominates the Year 12 city.

- **Half-Orc** — use the SRD entry **as printed** (`cfi_srd.txt` p. 21–22). It is the only
  playable goblinoid-descended race in the books and needs no conversion. Gobtown rider: a
  half-orc raised among orcs takes Kazhrun Tribal culture (§5.6) rather than a human culture.
- **Goblinoid mixed heritage** (orc×goblin, hobgoblin×orc, bugbear×hobgoblin…) — choose two
  parent races. For each characteristic, average the two parents' **printed averages** (rounding
  down) and express as `2d6+N` where N = average − 7; if the average is 7 or less, use `2d6`.
  Work from averages, not dice expressions, because parents often roll different dice entirely
  (Goblin SIZ is `1d6+4`, Orc SIZ is `2d6+7`). *Example — Orc × Goblin:* STR (14+8)/2 = 11 →
  `2d6+4`; SIZ (14+8)/2 = 11 → `2d6+4`. Take Darkvision from the better parent, Light Sensitive
  from the worse, movement from the smaller. Choose one parent's special trait; the other is lost.
- **Passion, all mixed heritage:** *No Clan Will Have Me*, at the standard starting value. It
  augments any roll to survive alone, endure contempt, or make common cause with another outcast.
  In Gobtown, and only in Gobtown, it begins to wane.

### 5.5 Conversion methodology (creature entry → PC race)

**No monster-PC subsystem exists in any of the four books** — no level adjustment, no racial hit
dice, no procedure. What exists is permission, in TDM500's "Human vs. Non-Human Races":

> "…it is possible to play just about any sapient race in Classic Fantasy, because all creatures,
> regardless of type, are defined in a consistent and compatible way. As such, Chapter 11:
> Monsters! offers a number of other possibilities for challenging character concepts."

Permission without procedure. **Defining that procedure is GoblinPack's central mechanical
contribution.** The method below is recovered empirically from Orc → Half-Orc, the one species
the books stat in both formats.

| PC-race field | Source in the creature entry |
|---|---|
| Characteristic dice | Copy the seven dice + averages verbatim |
| Starting age | Derive from prose lifespan (orc ~40 → half-orc 14+1d4) |
| Movement | Copy from the creature's Movement line |
| Free Skills | Customs +40, Native Tongue +40, Language (Common) +40 |
| Standard Skills | Six fixed + one "choose one of", drawn from the creature's Skills list |
| Professional Skills | Authored from the creature's role; orc list is the model |
| Language limits | From the creature's `Languages (...)` entry |
| Alignment / Passions | Creature's Passions become the *typical* alignment; add the Loyalty/Love/Hate triplet |
| Special Rules | Creature's `Abilities:` line → bulleted talents, **Movement always first** |
| Average Lair / Treasure | Dropped — becomes N/A with a footnote |
| Classes | Authored. Note: "most monster races cannot be Druids"; use Cleric |

**Two deliberate departures from the Half-Orc precedent**, both flagged as design choices rather
than oversights:

1. **Keep Light Sensitive.** The book strips it when making the playable Half-Orc ("unlike their
   orcish parent, half-orcs do not suffer light sensitivity") — but half-orcs have human blood
   and pure goblinoids do not. More importantly, in this campaign the trait is *load-bearing
   worldbuilding*: light sensitivity costs a goblin nothing underground and everything above it.
   **It is a large part of why Gobtown is a cave city at all**, and removing it would erase that.
2. **Do not inflate INT and CHA.** The book nudged both up by 1 going Orc → Half-Orc. We keep the
   creature numbers as printed. The premise of the supplement is that goblinoids are interesting
   as they are; buffing them toward human averages to make them "playable" contradicts the thesis,
   and the dice ranges already permit an exceptional individual.

**Supporting evidence that goblinoid PCs are intended:** the Cosmology chapter writes cleric
prerequisites as *"must be goblin or hobgoblin"* (Garex Blood-Drinker) and *"must be orc or
half-orc"* (Thaogg Axefang), in the identical format used for dwarf and halfling deities. The
book already assumes these characters exist; it simply never wrote them up.

### 5.6 Culture packages

**Kazhrun Tribal** *(available — this is what everyone has)*

- Free Skills: Customs (Kazhrun) +40, Native Tongue +40
- Standard: Athletics, Brawn, Endurance, Evade, Perception, Stealth, plus one of Ride or Swim
- Professional: Craft (any), Intimidation, Survival, Track, plus one of Healing or Navigate
- Illiterate (per the SRD rule: 1 Experience Roll + 1 month for half-skill literacy)
- Additional languages limited to goblin, hobgoblin, orc, gnoll
- Passions from the tribal menu (§5.7). Alignment typically Chaotic Evil; hobgoblins and orogs
  typically Lawful Evil.

**Gobtown-Born** *(written, but NOT available at character creation)*

Requires being raised in the settlement from early childhood. In year eight the oldest qualifying
child is seven. No PC can take this package. It is printed so players can read the future they
are building, and **the first child to come of age with it is a campaign milestone.**

- Free Skills: Customs (Gobtown) +40, Native Tongue +40, Language (one other goblinoid) +40
- Standard: Athletics, Deceit, Endurance, Influence, Insight, Locale, Perception
- Professional: Commerce, Craft (any), Engineering, Lore (any), Streetwise
- **Literate.** Passions from a different menu entirely: *This Place Must Not Fail*, *My
  Neighbour Is Not Meat*, *I Have Never Seen The Sky And I Am Fine*.

### 5.7 Passions — the five virtues

| Passion | Augments |
|---|---|
| *Shut Up And Get On With It* | Enduring hardship without complaint; completing a task under pressure; refusing delay for ceremony, rank, or feelings |
| *Be The Biggest Bastard You Can* | Intimidation; claiming credit; any act that deters future challenges |
| *Extra Points For Comedy Value* | Any action both effective and humiliating to its target; improvised cruelty with an audience |
| *Don't Be A Picky Eater* | Resisting disgust, poison, spoiled food, starvation; using what others discard |
| *Everyone Hates Us* | Acting against the smug and self-declared righteous; resisting Influence from other races |

**The Concord's effect:** *Be The Biggest Bastard* and *Extra Points For Comedy Value* wane when
their targets are fellow settlers, because the Concord has quietly redrawn who is fair game.
Players will notice their passions sliding and will not be told why.

### 5.8 The alignment rider

Goblinoid PCs are Evil. The Concord does not make anyone Good — it **redraws the boundary of who
counts as fair game** to include fellow settlers.

A Gobtown goblin is still Evil by any Valdenmark cleric's reckoning: cruel to outsiders,
contemptuous of weakness, delighted by others' misfortune. He simply does not rob his neighbours
any more, and **could not tell you why not.** That is the angel's work expressed as an alignment
rule, and it is the most important mechanical statement in this document.

The SRD's Evil trait list (Abusive, Cruel, Domineering, Enjoys Harming Innocents, Hates Good,
Merciless, Sadistic, Slaver, Spiteful) is used unchanged. Only the *target set* narrows.

Ethical axis drifts Lawful under the Concord. Drakmoor is Lawful Evil and drifting further —
which he experiences as exhaustion.

### 5.9 Classes

| CFI class | Goblinoid expressions |
|---|---|
| Fighter | warrior, wolf-rider, beast handler, pit-fighter |
| Rogue | sneak, agent, hunter, scout, acrobat |
| Cleric | priest, shaman, Prevaricator (Vykthar) |
| Magic-User | hedge-wizard, alchemist, ritualist |

Merchant/crafter/miner concepts are Professional skill loadouts, not classes. **Druid is
unavailable** to goblinoid races, per the book's own conversion note; use Cleric.

**Restriction:** no PC may be a cleric of Ehrendil Beldroth. Obviously.

---

## 6. The scenario: "The Emissary"

> **Rev. 1 discarded a scenario built on a pilgrim the party had to keep alive to avoid human
> reprisals. That was wrong.** Goblinoids do not fear retribution and would eat her. The
> constraint was human prudence smuggled into a goblinoid setting — exactly the failure mode
> §1's design test exists to catch. The replacement generates its pressure from goblinoid
> virtues instead.

### 6.1 The party — the Fixers

PCs are trusted early settlers, Drakmoor's problem-solvers, **deliberately kept ignorant.**
Orders arrive with holes in them: *keep her happy; keep her out of the deep galleries; do not ask
why.* Their loyalty is the campaign's real stat, and the dramatic irony runs the whole arc — the
player works it out long before the character is permitted to.

Each Fixer needs: race, class, why they fled the Kazhrun, and what they owe Drakmoor.

### 6.2 The situation

**Thekla Morvani walks into Gobtown.** She did not follow a map — a Prevaricator follows tales,
and a rumour of a chief who makes tribes cooperate was too good to ignore. She came to see
whether the story is true.

**Why they cannot simply eat her.** Two reasons, both native to goblinoid culture:

1. She is clergy of Vykthar, whose doctrine holds that goblinoid deeds deserve proper telling and
   who "favors those who refuse to let their people be dismissed as worthless." Killing her is
   sacrilege against a goddess whose favour every warrior in that cave wants.
2. More powerfully: **she decides whether Gobtown becomes a legend or is forgotten.** To a people
   whose second virtue is bragging rights, the storyteller is the most powerful visitor they will
   ever receive. Eating her means the greatest thing any gobbo has ever done goes untold — which
   is worse than death, and every resident knows it.

**The inverted threat vector.** The secret does not leak through spycraft. It leaks through
**vanity**. Everyone in Gobtown wants to be in the story. The Fixers' job is not to keep her out —
she is an honoured guest — but to manage what three hundred people tell her while she is inside.
Every gobbo they silence is incandescent about being left out of the tale of the age. *That* is
the pressure, and it is generated entirely by goblinoid values.

### 6.3 Is she spying?

Three loyalties, and the best version is that **she has not resolved it either**:

- **Duke Kessarin** sent her to assess whether this settlement is a threat.
- **Vykthar** obliges her to carry a tale this good back to the campfires.
- **The Truthkeepers** — the cult's secret strand, who "maintain secret libraries in ruins,
  caves, and abandoned settlements… posing as simple storytellers while gathering evidence" —
  would have her *archive* Gobtown rather than report it. Preserve the history; publish nothing.

Drakmoor cannot tell which. Neither can the party. Possibly neither can she.

### 6.4 Resolutions

- **Pyrrhic:** she leaves with a story that makes Gobtown legendary — and therefore findable.
- **Compromise:** she leaves believing it is a mining camp, and a different clock starts.
- **Spectacular failure:** someone brags about the deep water, and she goes looking.
- **Surprising success:** she works it out, and chooses to archive rather than publish. She
  becomes the party's most dangerous asset — and Drakmoor is denied the fame he craves, by a
  woman protecting him from it.

### 6.5 Later, and bluntly

The Ehrendil cleric from rev. 1 remains a valid *discovery vector* but is not this scenario. If
one arrives, the gobbos kill and eat her, exactly as they should. What that generates is a
missing cleric and the search party that follows — a blunter, later problem.

---

## 7. Database plan

Target: `myth-campaign-f0745885c38a` in `alh_mythras`.

1. **Switch system flag** `mythras` → `classic-fantasy` (direct TypeDB attribute edit; no update
   command exists). Enables the CFI rules graph for this campaign.
2. **Rewind era** — game date to year eight; opening scene: the Fixers receiving an order with
   holes in it, hours before Thekla arrives.
3. **Relabel Year 12 material** — existing lore, NPCs, factions, locations get a founding-era note
   marking them future canon. No deletions.
4. **New lore** — the Kazhrun, Valdenmark, Khorvenn, the Wellspring (gm), the Concord + decay
   clock (gm), Thekla's narrator frame, the four races + two variants, half-breed rules, the
   conversion methodology, both culture packages, the five virtues, the alignment rider.
5. **New NPCs** — founding-era Drakmoor (~50, exhausted, Lawful Evil drifting); the angel; Thekla
   Morvani (half-orc); Duke Aldric Kessarin; a traditionalist ringleader.
6. **New factions** — the surviving Ironspear, the traditionalists, Valdenmark, the Kazhrun
   tribes, the mixed-heritage settlers.
7. **Scenario** — "The Emissary" as gm-visibility lore.
8. **Templates** — spawnable stat blocks for goblin/hobgoblin/orc/bugbear using the real
   Chapter 11 numbers, replacing the invented ones seeded on 2026-07-25.

---

## 8. Open questions

1. **Population ceiling.** Prior instinct was 300–400 for a settlement that must stay hidden;
   remoteness argues for the low end. Needs a number before "The Emissary" is run.
2. **Who carved Khorvenn?** The caves predate Drakmoor. Either Ehrendil placed the spirit in
   anticipation, or it is a much older site repurposed — the second is more interesting and asks
   who cut the musical notation into the walls.
3. **Cult politics.** Vykthar's myth-making, Velthara's theft-as-art, and Razak's systematic
   pillage all have opinions about a settlement that has stopped raiding. Gobtown should be
   theologically contested; that is a chapter in itself.
4. **Does the angel have a name?** It has a voice and comic timing but no name in any source. It
   may refuse to give one, which is characterful.
5. **Orog derived attributes.** The book prints no averages for the overridden characteristics and
   says orogs are "treated in all other ways as orcs" — leaving it ambiguous whether Damage
   Modifier, Action Points and hit-point totals should be recomputed from the higher values. House
   ruling needed; recomputing is the defensible reading.
6. **Proxy names** remain provisional. Kazhrun, Valdenmark, Kessarin, Khorvenn all swappable at no
   cost until the lore is written.
