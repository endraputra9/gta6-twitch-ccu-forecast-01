# GTA VI Launch-Day Twitch CCU Forecaster — v2

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/endraputra9/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/endraputra9/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An entry for the make.fun bounty
[gta6-twitch-ccu-forecast-01](https://make.fun/bounty/gta6-twitch-ccu-forecast-01):
forecast, hour by hour, how many people watch Grand Theft Auto VI live on
Twitch in each of hours 2–24 of its release day (2026-11-19, UTC), given
everything recorded up to the end of hour 1 — as five quantiles per hour
(5%, 25%, 50%, 75%, 95%), scored by mean pinball loss on the log scale.

This is v2 of the "Launch Curve Forecaster" entry. It keeps v1's model —
a size-kernel pool of past launches' day curves — and corrects three
things v1 got wrong about *which* past launches are evidence for a launch
like GTA VI's, and how wide an honest spread is once that is accounted
for. Every change was gated on out-of-sample validation (below); nothing
was changed for cosmetics.

## The model

A launch day's hourly viewer curve, divided by its own first hour, has a
shape that depends mostly on **how big the first hour was**:

- A huge first hour means the rolling midnight-local unlock had already swept
  New Zealand (11:00 UTC the day before), Australia, Japan and Europe before
  the UTC day began. The curve then dips gently through the UTC morning and
  builds all day toward the transatlantic evening overlap — US unlocks at
  05:00/08:00 UTC, then European prime time and the US afternoon stacking on
  top of each other — peaking around hours 19–23 at roughly 1.4–1.7× the first
  hour.
- A small first hour means the unlock was still to come inside the UTC day
  (a single global unlock at 14:00 UTC, say), and the curve is a steep climb
  from near zero to a spike at the unlock hour — a completely different shape
  that no single fixed curve can describe.

So the program pools the launch-day curves of the past big launches **the
case itself supplies** (its `comparables`: 42 launches in the final, each
with hourly Twitch category averages from SullyGnome around its release
day), and for each future hour it:

1. takes every comparable's log ratio `ln(viewers_h / viewers_1)`,
2. weights each comparable by a Gaussian kernel on the distance between its
   first hour and this case's first hour, `exp(-0.5 · (Δlog10 / 0.45)²)` —
   launches whose first hour was a similar size count most — times the
   two v2 factors below,
3. fits a normal in log space (weighted mean and standard deviation of the
   log ratios), lightly smoothed across neighbouring hours, with the
   standard deviation scaled by the v2 calibration factor,
4. writes the case's hour-1 print times the fitted quantiles,
   `q_τ = p1 · exp(μ_h + z_τ · σ_h)`.

Comparables whose release-day curve is nearly absent (fewer than 20 of the
day's 24 hours, or no first hour) are left out on the data alone; that is
what keeps the one non-launch comparable — the GTA VI category's own
pre-release history, whose "release day" is a trailer premiere — out of the
pool. If the pool ever came up empty, the program falls back to persistence
(a flat median at hour 1's print with a slowly widening log spread) rather
than failing: a crashed case is an invalid case, and an invalid case takes
no prize.

## What v2 changes, and why

**1. Early-access-contaminated comparables keep only 0.3 of their weight.**
Nine of the pool's launches (Hogwarts Legacy, Diablo IV, Starfield,
Borderlands 4, …) opened to deluxe early access days before their nominal
release date. Their recorded "release-day" curve is therefore not a launch
curve at all: the launch spike happened during early access, and the
release day is a second, flatter peak. GTA VI has no early access, and
neither does any practice launch — every graded target in this contest is
a true launch day — so those curves are the wrong shape evidence, at full
weight they drag the forecast's peak down and flatten it. The
contamination is read off each comparable's own record (its research tier
in the `unlock` note), never assumed from the game's name.

**2. An unlock shape known to differ from the target's keeps 0.3.**
A single simultaneous global unlock (Black Myth: Wukong at 02:00 UTC,
Silksong at 14:00 UTC) produces a spike-and-decay day; a rolling
midnight-local unlock produces the long build. v1 let the size kernel
proxy for this; v2 reads the shape directly: each comparable's `unlock`
note is classified (simultaneous / rolling / unstated), the target's shape
is read from the case's own `notes`, which state its real unlock, and a
comparable whose shape is known and different is cut to 0.3. When either
side is unstated, no cut is applied — the kernel alone decides, exactly
as v1.

**3. The fitted log-spread is scaled by 0.85.**
The pool's cross-sectional spread mixes two things: genuine uncertainty
about this launch, and predictable differences between launches that the
size and shape weights have already accounted for. Pricing the quantiles
off the raw spread therefore over-covers. Leave-one-out chose 0.85 as the
calibration minimising the contest's own loss; the factor is applied to
the standard deviation only, the median is untouched.

## Validation

Two honest out-of-sample tests, both with the contest's own pinball loss
on the log scale:

- **Leave-one-out over the 37 launch comparables** in the kit's practice
  data: forecast each launch's hours 2–24 from its first hour, using the
  other 36 as the pool.
- **The four practice cases themselves** (Marvel's Wolverine, Red Dead
  Redemption 2, God of War Ragnarök, Marvel's Spider-Man 2), run end to
  end through the shipped program and scored against the same public
  SullyGnome series the kit was built from (fetched again from
  SullyGnome's chart API on 2026-11-18; the series reproduces each case's
  frozen hour-1 print exactly).

| forecaster | LOO, all 37 launches | LOO, rolling & uncontaminated launches | practice cases p00–p03 |
|---|---|---|---|
| persistence (flat at hour 1) | 0.930 | — | — |
| v1 | 0.393 | 0.301 | 0.218 |
| **v2** | **0.395** | **0.278** | **0.193** |

Read the columns for what they are. The graded targets of this contest —
all four practice launches and GTA VI itself — are rolling-midnight,
uncontaminated launches, and on exactly that class v2 improves clearly:
−8% on the leave-one-out subset, −11% on the practice cases, with **every
one of the four practice cases improving individually** (0.325→0.286,
0.214→0.167, 0.133→0.124, 0.200→0.196). Over all 37 launches — a pool
that also contains early-access and simultaneous-unlock targets this
contest never grades — v2 and v1 are level (0.395 vs 0.393): the changes
trade nothing away there, they simply stop pricing GTA-shaped launches
off dissimilar ones. The kernel bandwidth 0.45 was re-checked with the v2
weights in place and stayed the best of the widths tried.

## The target: GTA VI demand signals

The program reads only its case file (it runs offline), but the design
choices above were made against the actual target. Public demand signals,
read on 2026-11-18, the day before release:

- The reveal trailer (December 2023) stands at **305.6M views** on
  YouTube; Trailer 2 (May 2025) at **189.8M** — roughly half a billion
  trailer views before launch, a demand level no comparable in the pool
  matches.
- Twitch's own directory count for the Grand Theft Auto VI category,
  read through Twitch's public GraphQL API on 2026-11-18 (~01:15 UTC),
  was **7,868 viewers across 418 live channels** — a day before release,
  with nothing to play yet. The same read on 2026-11-17 had been 1,240
  viewers: the category is already ramping into the unlock.
- The unlock rolls at midnight local (New Zealand first, 2026-11-18
  11:00 UTC; US Eastern 05:00 UTC, Pacific 08:00 UTC), on PS5 and Xbox
  Series only, with no early access and no PC version — the exact profile
  of the pool's rolling, uncontaminated console launches (Ghost of
  Tsushima, The Last of Us Part II, the three Sony first-party practice
  launches), which is why v2 weights that class at full strength.

## What the forecast looks like

The forecast is a function of hour 1's print, which only exists once the
release day begins. Run on a reconstruction of the final pool (the 38
practice comparables plus the four practice launches the final adds), the
v2 model's median curve dips to ≈0.75× the first hour around midday UTC,
then builds to a peak at hours 20–21:

| if hour 1 prints | peak hour | peak median | peak 90% band |
|---|---|---|---|
| 250,000 | 21 | ≈433,000 (1.73×) | 216,000 – 869,000 |
| 500,000 | 21 | ≈764,000 (1.53×) | 414,000 – 1,409,000 |
| 1,000,000 | 20 | ≈1,360,000 (1.36×) | 786,000 – 2,354,000 |

(v1 on the same pool peaks lower — 1.36× and 1.22× at the two larger
prints — because the contaminated and simultaneous curves pull its
evening down.) The reasoning chain is the model's: the first hour will
already hold New Zealand, Australia, Japan and Europe; the US unlocks at
hours 6 and 9 add a second wave; the transatlantic evening overlap —
European prime time on top of the US afternoon — is where every large
rolling console launch in the pool tops out, at 1.4–1.7× its first hour,
and the spread around that is honestly wide because the pool's launches
disagree by that much.

## Running it

Standard library only, no network, fully deterministic (two runs on the
same case write byte-identical output):

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=<dir with .in files> MAKEFUN_OUTPUT_DIR=out python3 main.py
```
