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
| | Good and Evil for Goblinoids | ✅ **designed** — five virtues, contextual hatred, Evil-is-not-psychopathy |
| | Origins and Mythology | ⛔ **seed only** — see §4 |
| | Goblinoid Races | ✅ **designed** — six races, real stats, conversion method |
| | Half Breeds and Mixed Heritage | ✅ **designed** |
| | Relations with Giant-Kin | ⛔ not started |
| **Two** | Character Creation | 🟡 races + cultures done; class packages outstanding |
| | Goblinoid Character Classes | 🟡 **decided, not written** — see §5 |
| | Organizations and Cults | 🟡 10 cults digested; theological politics outstanding |
| | Equipment and Magic | ⛔ **seed only** — anti-craftsmanship, see §6 |
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
| War — military campaign against smug elves and humans | — | catalogued |
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

1. **Vykthar: Cleric or Bard?** (§5.2) Blocks Thekla's final sheet and the cult chapter.
2. **Vykthar's CHA 14 prerequisite** is unreachable for the races it accepts (§5.3).
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
