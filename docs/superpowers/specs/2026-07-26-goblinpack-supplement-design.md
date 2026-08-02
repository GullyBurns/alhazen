# GoblinPack — Supplement Design Spec

**Date:** 2026-07-26
**System:** Mythras **Classic Fantasy** (TDM500 core — *not* the Imperative SRD; see §3)
**Status:** Skeleton + progress tracker. Chapter specs hang off this document.
**Chapter spec:** Gobtown founding era → [`2026-07-26-gobtown-origins-design.md`](2026-07-26-gobtown-origins-design.md)

> **Scope correction (2026-07-26).** Earlier work treated Gobtown as the whole project. It is not.
> GoblinPack is a **full Classic Fantasy supplement**; Gobtown is one setting inside Part Three.
> This document is the supplement; the Gobtown spec is a chapter of it.

---

## 1. What the supplement is

A Classic Fantasy supplement in which goblinoids are **protagonists** rather than battle-fodder.

> "Rather than thinking of them as simple, flat monsters that we whet the edges of our blades
> upon, we will watch them, talk to them, become them." — v0 draft

Dedication, from v0: *for those who have been misunderstood, reviled, and oppressed.*

**Narrated throughout by Thekla Morvani**, half-orc Grand Prevaricator of Vykthar and advisor on
goblinoid matters to Duke Aldric Kessarin. A Prevaricator is a professional myth-maker, so the
narrator is **unreliable by doctrine** — every chapter is advocacy aimed at a hostile human court
by a priestess whose goddess rewards the tale told well.

**Terminology (v0):** *goblinoid* = goblins, hobgoblins, koolinth, bugbears, orcs, orogs.
Deliberately excludes gnolls, flinds, kobolds, giants, ogres, ettins, trolls, though they are
often found together. *Gobbo* is the colloquial term used throughout.

---

## 2. Structure and progress

Skeleton follows v0's table of contents. Status is honest: most of this is not written.

| Part | Chapter | Status |
|---|---|---|
| **One** | Overview & Introduction | ✅ framing + Thekla's voice settled |
| | Good and Evil for Goblinoids | ✅ **designed + playtested** — five virtues, contextual hatred, Evil-is-not-psychopathy; waning record from play (§4.1a) |
| | Origins and Mythology | ⛔ **seed only** — see §4 |
| | Goblinoid Races | ✅ **designed** — six races, real stats, conversion method |
| | Half Breeds and Mixed Heritage | ✅ **designed** |
| | Relations with Giant-Kin | ⛔ not started |
| **Two** | Character Creation | 🟡 races + cultures done; **CHA re-baseline designed + playtested (§5A)**; class packages outstanding |
| | Goblinoid Character Classes | 🟡 3 of 8 drafted (§5C): Prevaricator Bard, Wolf Rider, Crafter |
| | Organizations and Cults | 🟡 10 cults digested; **Vrakvenn written + playtested (§5D)**; theological politics outstanding |
| | Equipment and Magic | 🟡 anti-craftsmanship now has a mechanism (§5C.3 *Fast and Filthy*) |
| **Three** | Goblinoid Territories | 🟡 Kazhrun sketched, tribal lands outstanding |
| | Tribal Lands | ⛔ not started |
| | **GobTown** | ✅ **full chapter spec + database populated** |
| | Gobbo Adventures | 🟡 frames catalogued; two scenarios written — see §7 |

---

## 3. System decision: full Classic Fantasy, not the Imperative

**Decided 2026-07-26.** The supplement targets **CF core (TDM500)**.

The deciding evidence was v0's own class list, which contains **Bard** and **Thief-Acrobat** —
classes that exist in CF core and *not* in the four-class Imperative SRD. Writing to CFI would
have silently deleted two of the eight archetypes already designed.

**What this costs, and must be honoured downstream:**

- **Single-axis Moral Philosophy** (Good / Neutral / Evil + one or two traits), not CFI's two-axis
  Ethical + Moral alignment. Any rule written against the two-axis model needs rewriting. *Done —
  both the Gobtown roster and the chapter spec (rev. 3).*
- **Infravision**, not Darkvision.
- **Not ORC-licensed.** Publishing needs TDM clearance — likely available given the existing
  relationship, but it is no longer automatic.
- **The loaded rules graph is CFI**, 348 pieces in `alh_mythras` tagged `classic-fantasy`. It will
  answer with Imperative rules, which now diverge from the target system. Loading CF core as a
  second rules corpus is an open task (§9).

---

## 4. Part One — Good and Evil, and the origins gap

### 4.1 Designed: the moral psychology

The supplement's intellectual core, and the strongest existing material. Goblinoids are not
immoral; they weight the moral foundations differently. The five virtues:

| Virtue | Expression |
|---|---|
| Shut up and get on with it | Actions over ideals. Do your job or I'll kill you. |
| Be the biggest / sneakiest bastard you can | Rewards go to those who take and hold them |
| Have fun — extra points for comedy value | Cruelty is funnier when well-timed |
| Don't be a picky eater | Scarcity is permanent. Cannibalism is normal; squeamishness is contemptible |
| Everyone hates us | So it is delicious to outthink, crush, or eat those who think themselves better |

Two load-bearing clarifications, both from the user's design notes:

- **Tribal hatred is contextual, not innate.** How hate-filled a group is depends on leadership,
  scarcity and history — not species. Two warbands over one valley will slaughter each other; the
  same two under a competent captain may not.
- **The Evil passion is not psychopathy.** Pre-modern humans enjoyed public executions without
  being unable to love their children. Cruelty is a spectator taste and a tool, directed by
  cultural rules about *who is fair game*.

Goblinoids reject the label "evil" as effete elvish propaganda, and given the historical conduct
of elves and humans toward them, the reader is not obliged to disagree.

### 4.1a The moral psychology in play — the waning record

Playtest lore from the goblinpak campaign (sessions 1–3), now canon. This is the §4.1 design and
the §5C.2a dosage mechanic producing table results, and it belongs in the supplement as the worked
example of how Moral Philosophy runs for goblinoid characters.

**Moral Philosophy is a passion, and the Concord erodes it.** CF core: base 30 + POW×2; if reduced
to 0, a new philosophy replaces it per recent actions. Three data points from Khorvenn, year 8:

| Character | Moral Philosophy | Base | Current | Why |
|---|---|---|---|---|
| Drakmoor (chief) | Evil (Heartless and Slaver) | 58 | **39** | Eight years of the dawn ritual — most-dosed resident |
| Ozmek (Fixer) | Evil (Spiteful) | 52 | **33** | Settlement resident; closest of the Fixers to losing it entirely |
| Vek (PC, wolf-rider) | Evil (Bloodthirsty and Spiteful) | 54 | **54** | Entirely unwaned — away from the water more than anyone his age |

Rules of the record:

- **Waning is invisible from inside.** Nobody experiences their number dropping. Drakmoor
  experiences his as *exhaustion*; the outriders experience everyone else's as *going soft*. The
  least-dosed character in the settlement is mechanically its least civilised — and reads himself
  as the only one still seeing clearly.
- **The Evil passion never produces mercy — it produces reclassification.** The played proof: Vek
  speared an unarmed cleric from behind, then saved her life — not out of pity, but because his
  wolf sat down beside her and the only category his culture offered for "thing I will now protect"
  was *property*. Every humane act that followed ("she's ours now", the infirmary, the speech at
  the cave mouth) came from moving one person from *meat* to *mine*, and he would be insulted to
  hear it called kindness. The five virtues stayed fully intact throughout. **This is the pattern
  GMs should run:** under the Concord, goblinoids do not soften their values; they widen the circle
  of who counts as *ours*, one grudging reclassification at a time.
- **New passions form as chains of possession.** Vek's passion for the cleric wrote itself as *The
  Healer Is Mine (And I Am Vosh's)* — attachment expressed as ownership, ownership embedded in a
  hierarchy of belonging. Goblinoid passions about people should take this shape; "I love X" is an
  elvish sentence.
- **Replacement is not redemption, and it is mourned.** When Evil hits 0 it is replaced per recent
  actions — in the Concord's gravity, with Neutral (still greedy, dishonest, self-centred; no
  longer cruel or enslaving). A traditionalist would call that a death, and from inside the culture
  he is not entirely wrong. Ozmek is the settlement's live case: at 33 and falling, closest to the
  threshold, and nobody — including Ozmek — knows what is coming.

### 4.2 Seed only: Origins and Mythology

v0 gives one line, and it is a good one:

> "Goblinoids have a pragmatic view of their origins, preferring comedic, bawdy creation myths
> involving raucous sex and or defecation to harmonious stories involving beauty."

**Undeveloped.** Needs at least: two or three competing creation myths (mutually contradictory and
cheerfully so), how they explain the relationship to giant-kin, and what they say about why
everyone hates them. **Design note:** these myths should be *funny and load-bearing* — Vykthar's
cult exists to keep telling them, and the Gobtown chapter turns on who controls the story.

---

## 5. Part Two — Classes

v0's eight archetypes, mapped against CF core:

| v0 archetype | CF class | Status |
|---|---|---|
| Bard / Entertainer / Courtesan / Jester / Fool | **Bard** | exists — needs goblinoid write-up |
| Cleric / Priest / Shaman | **Cleric** | exists |
| Fighter / Warrior | **Fighter** | exists |
| Magic User / Alchemist | **Magic-User** | exists |
| Thief / Agent / Hunter / Scout | **Thief** | exists |
| Thief Acrobat | **Thief-Acrobat** | exists |
| Beast Handler / Wolf Rider | — | 🆕 **new class** |
| Merchant / Crafter / Miner | — | 🆕 **new class** |

**Closed to goblinoids:** **Paladin** (Lawful Good is unreachable) and **Druid** — the rulebook
states it directly: *"most monster races cannot be Druids in a typical Classic Fantasy campaign"*;
convert to Cleric.

### 5.1 The two new classes carry the supplement's argument

**Wolf Rider (Beast Handler).** Goblins are canonically dire-wolf cavalry and no CF class covers
mounted beast-partnership. This is a genuinely goblinoid contribution — and it is a **Kazhrun**
class: it needs open ground and a wolf.

**Merchant / Crafter / Miner.** No CF class covers the productive civilian, because adventurers do
not have jobs. This is the **Gobtown** class — barely meaningful in the tribal lands, and the
entire basis of a settlement that has stopped raiding. It already has a god in Grottendacz.

**The two are a matched pair, and the pair is the supplement's thesis in mechanical form.** Wolf
Rider is what goblinoids *were*; Crafter is what a goblinoid civilisation *requires*. A campaign
that moves from the tribal lands to Gobtown is a campaign in which the first class becomes
obsolete and the second becomes essential — and a traditionalist is mechanically just a character
who refuses to spend Experience Rolls on retraining. (Worked through in the Gobtown chapter, where
Ghazrek's grievance is professional rather than ideological, and he is not wrong.)

### 5.2 Open: are Vykthar's clergy Clerics or Bards?

Vykthar governs boasting, tall tales and myth-making; her cult skills are Oratory, Performance,
Influence, Insight, Carousing, Boast. Her v0 gifts are Command, Charm Being, Inspiration. **That
is a Bard, wearing a Cleric's title.** v0 writes her up with cleric prerequisites and a Rank-based
gift ladder, which is the Cleric chassis. Needs a decision: Cleric, Bard, or a Bard variant with
Devotion. Thekla Morvani is currently statted as a Cleric pending the call.

### 5.3 Rules snag — Vykthar's prerequisites are unreachable

v0 sets Vykthar's requirements at **POW 12, CHA 14**. But *every goblinoid rolls CHA 2d6*, maximum
12, and even a half-orc caps at 13. **By RAW no pure goblinoid can ever qualify for the cult of the
goddess of goblinoid storytelling.** Options: lower to CHA 12; treat the excess as a divine gift
that raises the characteristic; or keep it and make Prevaricators near-mythical — currently
recorded as the third, which is why Thekla is extraordinary.

---

## 5A. The CHA re-baseline — the supplement's signature rule

**Decided 2026-07-26.** This is the mechanical statement of the whole supplement, and it is a
*decomposition of the printed numbers rather than an invention*.

### The evidence

Across the six statted goblinoids, **CHA is the only characteristic that is uniformly floored.**

| | Goblin | Hobgoblin | Orc | Bugbear | Gnoll |
|---|---|---|---|---|---|
| STR | 8 | 13 | 14 | 19 | 15 |
| SIZ | 8 | 17 | 14 | 21 | 20 |
| INT | 12 | 13 | 11 | 10 | 10 |
| **CHA** | **7** | **7** | **7** | **7** | **7** |

Strength spans 8–19, size 8–21, intellect 10–13. Every species is differentiated on every axis
except one, where all five collapse to an identical `2d6`. That is not a physiological observation.
**It is a measurement taken from outside.**

### The rule

> **Goblinoid CHA is `3d6`.** Apply **−4 CHA** for all purposes when dealing with a culture not
> your own. The penalty is **symmetric**: non-goblinoids take the same −4 toward goblinoids.

`3d6` averages 11. Less 4 is 7 — **exactly the printed value.** A GM running vanilla Classic
Fantasy sees an unchanged goblin. The book is not wrong; it is *incomplete*, having recorded
goblinoids as their enemies experience them.

Mutual incomprehension, not goblinoid deficiency: a human noble is as tongue-tied in a warren as a
goblin is at court. "Everyone hates us" becomes a two-way mechanical fact rather than a complaint.

### What it repairs

CHA drives Influence (CHA×2), Deceit and Commerce (INT+CHA), Sing (POW+CHA), Dance, Courtesy,
Native Tongue, and the Experience Modifier.

1. **The learning penalty.** Experience Modifier is +1 at CHA 13–18. At `2d6` a goblinoid **caps at
   12** — so under the printed numbers no goblinoid of any species could ever have a positive
   learning modifier, while humans routinely do. The re-baseline removes a quiet claim that
   goblinoids are worse at learning.
2. **Vykthar's prerequisite.** CHA 14 was unreachable at `2d6` (max 12) — by RAW nobody could join
   the cult of the goddess of goblinoid storytelling. At `3d6` it is reachable, and reachable
   precisely by those compelling *among their own people*, which is what a boast-singer is. The
   requirement was never broken; we were measuring with the wrong ruler. **Closes open question 2.**
3. **The goblinoid Bard becomes viable** — the first class on the v0 list, previously impossible.
4. **Thekla Morvani, explained.** Raised across both cultures, she takes **no penalty in either
   direction**. In any room containing both species she is functionally the most charismatic person
   present — not because her CHA is high, but because everyone else's collapses. That is why a duke
   who despises goblinoids keeps one at his elbow, and it is a far better warrant for the narrator
   than "she is persuasive."

### Scope note

Applies to CHA only. The other characteristics are differentiated across species and show no sign
of the same flattening, so there is no evidence to justify extending the treatment.

### The re-baseline in play (sessions 1–3)

The rule was not a paper decision; it was built into Vek's sheet and ran at the table across the
first three sessions. What play established, for GMs adopting it:

- **The two numbers live on one line.** Vek's CHA is recorded as **12** — his rating *among his own
  people*. Against a caravan guard, a duke's man, or Sister Ilenne it is **8** (12 − 4). Both are
  the same characteristic seen from two sides; the sheet carries the 12 and the GM subtracts the 4
  at the moment of a cross-culture roll. Never write the 8 down as if it were the goblin.
- **The floor is real, not gifted.** At CHA 12 Vek's **Experience Modifier is still 0** — the `3d6`
  re-baseline makes the +1 band *reachable* (CHA 13+), it does not hand it over. This matters: the
  rule repairs a systematic slander (no goblinoid could ever clear the band) without making
  goblinoids quietly better learners than the numbers earn. A goblinoid who wants the modifier still
  has to have rolled for it.
- **Within-culture speech pays full price.** When Vek stood on the rock and shouted the settlement
  down ("OI!!! GOBBOS!…"), that was an Influence roll *among his own people* — **no penalty**, the
  full **27** (CHA 12 × 2 = 24, +3 house-ruled from experience). The identical speech aimed at
  Ilenne or at the duke's emissary would resolve at an effective CHA of 8. **The stage a goblinoid
  is most persuasive on is the one facing inward** — which is exactly what a boast-singer, an
  Outrider rallying the line, or a chief holding a warren together actually does.
- **The penalty is a two-way fact, and the table felt it.** Ilenne, a human cleric dropped into
  Khorvenn, is as tongue-tied among the gobbos as they are at court — her −4 toward them and theirs
  toward her are the *same* wall from opposite sides. "Everyone hates us" stops being a passion the
  players recite and becomes a number that bites in both directions every time an outsider is in the
  room. This is the mechanical spine under the whole "Wrong Cathedral" premise.

**GM guidance:** carry CHA as the in-culture value, apply −4 the instant a roll crosses the cultural
line (either direction), and let players feel the difference between rallying their own and
bargaining with the enemy. That felt gap *is* the supplement.

---

## 5B. Why goblinoid classes are structurally different

Human and demi-human classes are **vocational**: you trained, you joined, you swore an oath.
Goblinoid classes are **functional**, following directly from the first virtue — *to be valued in a
goblinoid community is primarily utilitarian: do something well and you may live a little longer.*
Nobody trains a goblin. A goblin becomes useful, or dies.

| | Demi-human classes | Goblinoid classes |
|---|---|---|
| Entry | training, guild, apprenticeship | demonstrated usefulness |
| Oaths | sworn, binding, class-defining | none — cult *favour* instead, which is withdrawn not broken |
| Tenure | permanent once earned | **provisional; lost when your function is not needed** |
| Naming | vocation (Fighter, Cleric) | function (Wolf Rider, Crafter, Boast-singer) |

**Provisional tenure is the load-bearing difference.** A class you can lose turns the Wolf Rider's
obsolescence in Khorvenn's tunnels and Ghazrek's grievance into the same mechanic, and it makes
retraining — Experience Rolls spent on new Professional skills — a status question rather than a
bookkeeping one. A traditionalist is simply someone who refuses to spend them.

---

## 5C. Class drafts

Written against the CF class template (prose → weapon/armour restriction → Standard Skills →
Professional Skills → Combat Style → Rank Structure → Prerequisite Skills → Abilities & Talents).
The rank ladder follows the book's own progression: **5 skills @50%, 5 @70%, 4 @90%, 3 @110%,
2 @130%**, with **+1 Luck Point per Rank**.

### 5C.1 Bard — the Prevaricator Order (Vykthar)

**Decided: Vykthar's clergy are Bards, not Clerics.** The chassis fits without modification —
Oratory, Sing, Influence, Acting, Seduction, Sleight, and a talent ladder ending in Inspiration is
a description of a boast-singer. The book already splits bards into an **Arcane College** and a
**Druidic Order**, each with its own Professional list and magical source; GoblinPack adds a third.

> **The Prevaricator Order.** Where civilised bards attend colleges and druidic bards keep The Old
> Ways, Vykthar's boast-singers hold that a deed unremembered did not happen, and that a deed
> remembered *badly* is a theft. They are the only institution in goblinoid society that reliably
> outlives the chief who founded it, because they are the ones who decide what he was.

**Standard Skills:** Athletics, Combat Style (Prevaricator), Deceit, Evade, Influence, Insight,
Locale, Sing, Stealth

**Professional Skills (Prevaricator):** Acting, Boast, Carousing, Channel, Lore (Goblinoid
Histories), Musicianship (All), Oratory, Piety (Vykthar), Seduction, Streetwise

Max 3 Professional skills and no extra Skill Points, as per all bards — master of none.

**Combat Style (Prevaricator):** club, dagger, javelin, knife, shortsword, sling, spear, staff.
Light armour only; a Prevaricator who cannot be heard is not working.

**Divine casting** via Piety (Vykthar), on the druidic-bard pattern. Starting Rank 1 spells equal to
1/20th Piety. **Spheres:** All, Charm, Protection — matching v0's cult entry.

| Rank | Title | Max Spell | Prerequisites | Luck |
|---|---|---|---|---|
| 0 | Hanger-On | — | — | — |
| 1 | Listener | Rank 1 | 5 skills at 50% | +1 |
| 2 | Braggard | Rank 1 | 5 skills at 70% | +2 |
| 3 | Warsinger | Rank 2 | 4 skills at 90% | +3 |
| 4 | Scarkeeper | Rank 2 | 3 skills at 110% | +4 |
| 5 | Grand Prevaricator | Rank 3 | 2 skills at 130% | +5 |

**Prerequisite Skills:** Influence, Oratory, Piety (Vykthar), Sing, and either Boast or Acting.

**Talents.** *Inspiration* and *Artful Dodger* as per the core Bard. Plus:

- **Safe Conduct** (Rank 1). Vykthar extends protection to any audience, *including non-goblinoids*,
  so that her stories may be heard in safety. While a Prevaricator is actively telling, violence
  against the audience is sacrilege. This does not stop anyone — it makes them pay for it, and every
  goblinoid present knows the price.
- **The Version That Sticks** (Rank 2). Spend 3 Magic Points and succeed at Oratory to establish
  your account of an event as the one the community remembers. Contradicting witnesses must overcome
  your Oratory with an opposed roll to be believed, *even when they are telling the truth*.
- **Name The Fool** (Rank 3). Name a target in a tale before an audience. Their Influence and
  Courtesy operate one grade harder within that community until they do something worth retelling.
  Goblinoid society has no legal punishment worse than this.
- **Truthkeeper** (Rank 4, optional, secret). Access to the cult's hidden archives and the coded
  scripts that maintain them. Members pose as ordinary storytellers while preserving histories that
  would be destroyed if found. *Taking this talent is a GM-facing commitment, not a public rank.*

> **Thekla Morvani is Rank 3 (Warsinger) and uses the Rank 5 title at the Valdenmark court.** She
> has not earned it. Inflating your own legend is not a violation of Vykthar's doctrine — it is an
> act of worship, and the only sin is being dull or getting caught.

### 5C.2 Wolf Rider 🆕

The Kazhrun class. Goblins are canonically dire-wolf cavalry and no CF class covers mounted
beast-partnership; the Ranger comes closest and is wrong in every particular that matters.

**Standard Skills:** Athletics, Combat Style (Wolf Rider), Endurance, Evade, Locale, Perception,
Ride, Survival, Track

**Professional Skills:** Animal Training, Commerce, Craft (Harness), Healing, Lore (Beasts),
Navigate, Streetwise, Survival (Mountains)

**Combat Style (Wolf Rider):** javelin, lance (light), net, shortbow, shortsword, sling, spear.
Light armour only — anything heavier and the wolf will not carry you far enough to matter.

| Rank | Title | Prerequisites | Luck |
|---|---|---|---|
| 0 | Whelp-tender | — | — |
| 1 | Outrider | 5 skills at 50% | +1 |
| 2 | Pack-second | 5 skills at 70% | +2 |
| 3 | Wolf Rider | 4 skills at 90% | +3 |
| 4 | Pack-leader | 3 skills at 110% | +4 |
| 5 | Wolf-mother / Wolf-father | 2 skills at 130% | +5 |

**Prerequisite Skills:** Animal Training, Athletics, Perception, Ride, Track.

**Talents.**

- **Bonded Mount** (Rank 1). A dire wolf companion with its own stat block. It is not equipment; it
  has passions and will act on them. If it dies you lose all Wolf Rider talents until you raise
  another from a whelp, which takes a season.
- **Ride-By** (Rank 1). Move, attack and move again in one turn without granting a free attack,
  provided the wolf ends outside engagement range.
- **Pack Tactics** (Rank 2). When two or more Wolf Riders engage the same target, each gains an
  augment. Goblinoids who cannot cooperate get nothing from this talent, which is exactly the point.
- **Speak Wolf** (Rank 3). Not magic — fluency. Communicate complex intent to any canid.
- **The Long Ride** (Rank 4). Mounted travel at forced pace without Endurance penalty for a number
  of days equal to CON/3.

> **This class is Gobtown's outer wall.** The settlement survives by not being found, and not
> being found requires knowing who is coming. The outriders hold the approaches — the pass mouth,
> the goat tracks, the lower valleys, the road where caravans move — and they are away for days at
> a stretch. Every talent above works exactly as written, because open country is where these
> characters actually spend their working lives. Khorvenn's galleries are where they sleep.

**What is constrained is permission, not capability.** An outrider sees a fat merchant train on the
low road and is forbidden to touch it, because a raid brings a punitive expedition and the whole
experiment ends. He has the strength to take and standing orders not to.

**That is Ghazrek's grievance, and it is far worse than uselessness.** He is a warrior employed as
a watchman. He does his job perfectly and it earns him nothing, because *Be The Biggest Bastard You
Can* cannot be satisfied by withdrawing quietly and reporting accurately, and Vykthar has no song
for a man who watched. His passion is unexercisable in his own profession. A goblinoid whose
defining virtue has no outlet is not merely frustrated — by his own culture's reckoning he is
becoming nobody.

### 5C.2a The dosage problem — why the outriders are the traditionalists

**The Concord is in the water** (Gobtown chapter §4). Outriders spend days at a time away from it,
carrying skins filled before they left and drinking from streams once those run out.

They come back **edgy, quarrelsome, and hungry in the wrong way.** The decay clock from the Gobtown
chapter runs on individuals as well as the settlement, and the outriders are the only residents who
routinely trigger it.

The consequence is a faction that assembles itself without anyone deciding to found one:

- The outriders are the **least civilised goblinoids in Gobtown** — not by conviction, but by
  *exposure*. They are the least-dosed members of the population.
- They are also the ones with **weapons, mounts, mobility, and knowledge of every route in and out**.
- They have the **best reason to distrust the dawn ritual**, since they feel the difference between
  being home and being away most sharply, and nobody has ever explained it to them.
- And **none of them understands why they feel this way**, including Ghazrek. They experience it as
  clarity — as being the only ones who have not gone soft. From inside, waning is invisible; what
  you notice is other people changing.

> **This is the traditionalist faction, and it is a public-health problem wearing an ideology.**
> Drakmoor cannot fix it without explaining the water. Rotating outriders home more often would
> work, and he cannot order it without giving a reason.

### 5C.3 Crafter / Miner 🆕

The Gobtown class, and the one that barely exists in the tribal lands. No CF class covers the
productive civilian because adventurers do not have jobs. Patron: **Grottendacz** — build 'em fast,
and if they break, so what.

**Standard Skills:** Athletics, Brawn, Combat Style (Crafter), Endurance, Locale, Perception,
Willpower, and either Evade or Swim

**Professional Skills:** Commerce, Craft (any two), Engineering, Lore (Minerals), Mechanisms,
Navigate (Underground), Piety (Grottendacz), Survival

**Combat Style (Crafter):** hammer, mattock, pick, shortsword, shield, sling, staff. Tools, held
the wrong way round. No armour restriction — you already work in it.

| Rank | Title | Prerequisites | Luck |
|---|---|---|---|
| 0 | Hand | — | — |
| 1 | Digger | 5 skills at 50% | +1 |
| 2 | Shaper | 5 skills at 70% | +2 |
| 3 | Crafter | 4 skills at 90% | +3 |
| 4 | Master of Works | 3 skills at 110% | +4 |
| 5 | Deepwright | 2 skills at 130% | +5 |

**Prerequisite Skills:** Brawn, Craft (chosen), Engineering, Lore (Minerals), Mechanisms.

**Talents.**

- **Fast and Filthy** (Rank 1). *This is the anti-craftsmanship rule, and it belongs here.* Produce
  any item you could normally craft in **one quarter** the time. The result has **half AP and half
  HP**, and **breaks outright on a fumble**. Goblinoids do not regard this as inferior work. It is
  correct work: the thing existed when it was needed, and a spear that survives one battle has
  served its whole purpose.
- **Read the Rock** (Rank 1). Assess structural soundness, load-bearing walls, gas pockets and
  collapse risk at a glance. In Khorvenn this is the difference between a settlement and a grave.
- **Improvise** (Rank 2). Substitute available junk for proper materials at one grade harder, with
  no quality loss beyond what *Fast and Filthy* already imposes.
- **Field Repair** (Rank 3). Restore a broken item to working order in minutes rather than hours.
  Given the above, this talent sees constant use.
- **Deep Sense** (Rank 4). Navigate unfamiliar tunnel systems without light and without becoming
  lost; know your depth and bearing.

> **This class is the settlement.** At 50–100 people every trade is one or two deep. Gobtown has
> perhaps two competent Crafters, and if both are lost the tunnels stop being maintained, the
> cisterns silt, and the fungus beds fail within a season. A traditionalist who sneers at diggers is
> sneering at the reason he ate this morning.

### 5C.4 Retraining and provisional tenure

Following §5B, class is **provisional**. A character whose function is no longer needed may retrain
by spending **Experience Rolls** on the new class's Prerequisite Skills; rank is recalculated
against the new ladder and will usually drop, leaving the character publicly demoted.

**Note what Gobtown does and does not make obsolete.** No class here is useless — the settlement
needs outriders, diggers, singers and fighters, and needs them all badly at a population of a
hundred. What changed is not which skills are wanted but **which skills earn status**. Raiding
produced loot, songs and bragging rights; scouting produces a report. Mining keeps everyone alive
and produces nothing anyone will sing about.

**So the friction is a reward-structure problem, not a competence problem**, which is why it cannot
be solved by retraining and why it festers. Ghazrek does not need new skills. He needs his existing
ones to mean what they used to mean, and Gobtown cannot give him that without ceasing to be
Gobtown.

---

## 5D. The Cult of Vrakvenn the Wolf-Singer 🆕

**Founded in play, session 6.** This is the supplement's second signature piece after the CHA
re-baseline, and like that rule it was *discovered* rather than designed — it fell out of a PC with
INT 8 being physically unable to learn an elven rite.

> **The claim.** The elves say his name is Ehrendil Beldroth and that goblinoids have stolen him.
> The cult's position is that the elves only ever *put their name on him like a mark on a sack* —
> that he sat in their stone halls for a thousand years being sung the same song every night, and
> **left**. A god who walks out on the elves is not an elf god. They did not lose him. He *went*.

### The doctrine, and why it is unlike any other cult in the book

Every other faith in Classic Fantasy is founded on **transmission** — the rite is old, it is correct,
and the priest's job is to perform it without error. Vrakvenn inverts every part of that:

| Ordinary cult | Vrakvenn |
|---|---|
| The rite is ancient and fixed | The rite is **made new every time**; repetition is the sin |
| Correct performance matters | Performance quality is **irrelevant** — the first three tellers were all terrible |
| The priest performs *for* the congregation | The priest performs *at* them and **they finish it** |
| Sacrifice is given up | The god **refuses payment** and gives back |
| Worship is human/demi-human | **Wolves take part in the responses** |

The theology in one line: **he is the maker and the singer, so what he wants is what is *made* and
what is *sung*.** He does not want blood, gold, or obedience. He wants a thing that did not exist
before, sung badly, by a room.

**The Gap.** The god's own voice in the deep water rises at the end and leaves a silence. It has
done this, unanswered, for longer than anyone can date. Every rite therefore *leaves the gap* — and
the congregation fills it. This is not a stylistic choice. It is the entire mechanism of the faith:
**a single voice is not worship, it is a man muttering in a cave.**

### The three sins

1. **Singing it the same way twice.** A boast repeated word-for-word is a dead thing offered to a
   god of making. Lay members are expected to *change it*, and improving on the truth is worship,
   not deceit — the doctrinal overlap with Vykthar's Prevaricators is deliberate and unresolved.
2. **Worshipping alone.** Solitary devotion is not merely ineffective, it is the specific error that
   nearly killed Magnificus Drakmoor: eight years of private transaction with a god who was asking
   for a chorus. Any rite performed by one voice is void.
3. **Paying in blood.** Formally heretical, and named as such *because the founder did it* for eight
   years in good faith. The cult's origin story is its chief prohibition.

### Rite of the Fire

Performed at the settlement fire, not in any built temple. Four movements:

1. **The Spit.** Any celebrant spits on the stone before naming him. Improvised on the night of the
   founding and adopted instantly, without discussion. It is the only formal act of reverence in the
   cult and it is an insult.
2. **The Naming.** *Vrakvenn* — never the elven name in a goblinoid mouth.
3. **The Boast.** A newly-composed telling, climbing through runs, delivered from the teller's rock.
4. **The Refrain.** *"AND WE KEPT HIM."* The room roars it into the gap at the end of every run.
   Note what this line actually does: eighty voices are not *describing* an event, they are
   **performing an annexation** — the claim of ownership is the sacrament.

**The wolves answer.** Bonded mounts and picketed dire wolves respond to the refrain unprompted and
untrained. No one has explained this. Treat it as GM-facing and true.

### Holy sites are water

Vrakvenn is present in **the singing water**: the drowned chamber beneath Khorvenn, the cistern that
runs off it, and the seep on the north shoulder. There is no shrine, no altar and no building. This
gives the cult a unique logistical problem — **its holiest place can only be reached by something
that can swim under a mountain**, which makes an aquatic goblinoid (koolinth) the single most
important office-holder in the faith, regardless of rank or piety.

### Joining

**Requirements:** POW 9. No CHA minimum — deliberately, and in pointed contrast to Vykthar (§5.3).
Vrakvenn will take anyone who can be heard, and the founding priest is INT 8 and cannot hold a tune.

**Cult Skills:** Boast, Devotion (Vrakvenn), Influence, Lore (the Keeping), Musicianship, Oratory,
Sing, **Swim**, Animal Training (dire wolf)

**Spheres:** All, Charm, Healing, Protection — *Healing* because the water closed the founder's
wounds and refused further payment; *Protection* because the Concord is the observed effect of his
presence. ⚠ Final sphere list to be checked against the CF cult chapter before publication.

| Rank | Title | Prerequisites | Notes |
|---|---|---|---|
| 0 | **Spitter** | Spit, and shout the refrain | Every goblinoid in the settlement, automatically |
| 1 | **Teller** | Boast 30, Devotion 30 | May compose and deliver a new boast |
| 2 | **Gap-Keeper** | 4 cult skills at 50% | Knows how to *leave the space* and hold a room in it |
| 3 | **Room-Raiser** | 4 cult skills at 70% | Can raise a hostile or frightened gallery to the refrain |
| 4 | **Waterspeaker** | 3 cult skills at 90%, **Swim 60** | May address the pool directly |
| 5 | **First Voice** | 2 cult skills at 110% | Begins the rite for the whole people |

### Talents

- **The Gap** (Rank 1). Leave a deliberate silence at the end of a run. Any hearer who wishes to
  join may do so without a roll, however hostile they were a moment before. The refrain is
  contagious and does not care about your politics.
- **Kept** (Rank 2). While a rite is in progress, everyone taking part counts as *ours* for as long
  as they are shouting — including non-goblinoids and animals. A practical and much-abused mechanism
  for making outsiders temporarily un-killable.
- **The Made Thing** (Rank 3). Offer something newly made or newly sung. The god answers. What he
  answers *with* is not under the celebrant's control and never has been.
- **Wolf-Chorus** (Rank 4). The responses of nearby dire wolves count toward the congregation. A
  Waterspeaker alone with a wolf-line is not, technically, alone.

### Open design questions

1. **What class are its clergy?** Vykthar's are Bards (§5C.1). Vrakvenn's first priest is a **Wolf
   Rider with Devotion 24**, and the cult has no clerical class at all — arguably correct for an
   eight-day-old religion, and arguably the most interesting thing about it. Options: keep it
   class-agnostic; build a *Roarer* variant on the Bard chassis; or make it the first CF cult whose
   clergy are defined by **rite-role** (teller, gap-keeper, diver) rather than class.
2. **The Vykthar overlap.** Both faiths hold that improving on the truth is virtuous. Is the
   Prevaricator Order a rival, a parent, or the cult's inevitable future institution — the body that
   will eventually decide what Drakmoor *was*?
3. **The human problem.** The cult's only trained theologian is a human cleric of Ehrendil who has
   chosen the god over her church. Nothing in the doctrine forbids this. Everything in goblinoid
   society does.

---

## 6. Part Two — Equipment and Magic (seed only)

The one genuinely original idea here is **anti-craftsmanship**, implicit in Grottendacz's doctrine:
*build 'em fast and if they break, so what.*

**Undeveloped, and worth real attention.** Goblinoid manufacture optimises for speed, disposability
and immediate advantage rather than durability or beauty — which is not incompetence, it is a
different objective function, and it follows directly from the five virtues. Needs: mechanical
treatment (reduced AP/HP on goblinoid-made gear, offset by cost and availability? breakage on a
fumble?), what goblinoids consider *good* work, and why their weapons are nonetheless prized
exports in the Year 12 city.

---

## 7. Part Three — Territories and adventures

### 7.1 The five campaign frames

From v0 and the game-types document, reconciled:

| Frame | Template | Status |
|---|---|---|
| Reverse dungeoneering — adventurers attack *your* home | *Leverage* | catalogued |
| In the service of the dark lord — disposable PCs, insane overlord | *Paranoia* / *Better Call Saul* | catalogued |
| Crime capers | *Ocean's Eleven* / Guy Ritchie | catalogued |
| War — military campaign against smug elves and humans | — | 🟡 **the Standing and the Tithe** drafted in the Gobtown chapter §4.5 — goblinoid units that hold formation, obey cross-species orders and retrieve their wounded |
| **Goblinball** — the closest thing to a recreational sport | — | ⛔ **undeveloped, and a shame** |

### 7.2 Territories

- **The Kazhrun** — the mountain heartland. Chaotic, disorganised, permanently at war with itself;
  no institution outlives the chief who founded it. **Tribal Lands chapter not started.**
- **Gobtown** — the founding-era settlement, 50–100 souls in the caves of Khorvenn. **Fully specced
  and populated in the database.** See the chapter spec.

### 7.3 Written scenarios

Both belong to Gobtown; see the chapter spec for detail.

- **"The Wrong Cathedral"** (cold open) — a cleric of Ehrendil arrives expecting a grove and a
  choir, and finds a goblin warren with her god unmistakably inside it.
- **"The Emissary"** — Thekla walks in. She cannot be eaten because she decides whether Gobtown
  becomes a legend, and the secret leaks through vanity rather than spycraft.

---

## 8. Database state

Campaign `goblinpak` = `myth-campaign-f0745885c38a` in `alh_mythras`, flag `classic-fantasy`.

**Populated 2026-07-26:** 12 founding-era characters with CF single-axis Moral Philosophy, CF class
names, derived stats computed from the validated tables, and narratives in `content`.

| Character | Race | Class | Moral Philosophy |
|---|---|---|---|
| Magnificus Drakmoor | hobgoblin | Fighter | Evil (Heartless and Slaver) **39** — heavily waned |
| The Wellspring | celestial | — | Good (Saintly) 90 — *GM only, never roll against it* |
| Thekla Morvani | half-orc | Cleric | Evil (Chaotic and Spiteful) 60 |
| Duke Aldric Kessarin | human | Fighter | Neutral (Unbiased and Pompous) 54 |
| Ghazrek | orc | Fighter | Evil (Bloodthirsty and Slaver) **62** — has *not* waned |
| Sister Ilenne Vasch | human | Cleric | Good (Kind and Honest) 62 |
| Vharza | hobgoblin | Fighter | Evil (Heartless) 44 |
| Nubrik | goblin | Thief | Evil (Spiteful and Cannibalistic) 47 |
| Brogg | bugbear | Fighter | Evil (Heartless and Murderous) 46 |
| Skell | koolinth | Thief | Evil (Cannibalistic and Heartless) 50 |
| Ozmek | orc × goblin | Thief | Evil (Spiteful) **33** — closest to losing it |
| Zhara | goblin | Magic-User | Evil (Wicked and Chaotic) 55 |

The 13 Year 12 NPCs are retained and tagged `[YEAR 12 FUTURE CANON]`.

**The Moral Philosophy numbers are the campaign, told in one column.** Ghazrek's is elevated;
Drakmoor's and Ozmek's are collapsing. CF's own rule — *"if the chosen philosophy is reduced to 0,
a new one replaces it at base level, per the character's recent actions"* — means the Concord does
not redeem anyone. It erases their Evil and installs Neutral: still Greedy, Dishonest, Self-centred,
no longer Cruel and Slaver. **Civilisation without redemption, entirely RAW.** Ghazrek would
correctly regard it as a death.

---

## 9. Open questions

1. ~~**Vykthar: Cleric or Bard?**~~ **Resolved: Bard**, as a third bardic order alongside the
   Arcane College and the Druidic Order. Drafted at §5C.1.
2. ~~**Vykthar's CHA 14 prerequisite**~~ **Resolved by the CHA re-baseline** (§5A) — reachable at
   `3d6`, and reachable exactly by those compelling among their own people.
3. **Load CF core rules into the graph.** The 348 loaded pieces are Imperative and now diverge from
   the target system.
4. **Origins and Mythology** needs writing from a one-line seed (§4.2).
5. **Equipment: anti-craftsmanship** needs a mechanical treatment (§6).
6. **Tribal Lands** chapter not started — and the supplement needs it, since it is the *default*
   goblinoid setting and Gobtown is the exception.
7. **Goblinball.** Undeveloped and the single most likely thing in this document to sell the
   supplement to a browsing reader.
8. **Relations with Giant-Kin** not started.
9. ~~Gobtown spec §5.8~~ **Done** — chapter spec retargeted to CF core at rev. 3; the alignment
   rider is now sourced from the core book's own Moral Philosophy replacement rule.
