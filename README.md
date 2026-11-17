# GTA VI Launch-Day Twitch CCU Forecaster

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/endraputra9/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/endraputra9/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01

An entry for the make.fun bounty
[gta6-twitch-ccu-forecast-01](https://make.fun/bounty/gta6-twitch-ccu-forecast-01):
forecast, hour by hour, how many people watch Grand Theft Auto VI live on
Twitch in each of hours 2–24 of its release day (2026-11-19, UTC), given
everything recorded up to the end of hour 1 — as five quantiles per hour
(5%, 25%, 50%, 75%, 95%), scored by mean pinball loss on the log scale.

## The model

A launch day's hourly viewer curve, divided by its own first hour, has a
shape that depends mostly on **how big the first hour was**:

- A huge first hour means the rolling midnight-local unlock had already swept
  New Zealand (11:00 UTC the day before), Australia, Japan and Europe before
  the UTC day began. The curve then dips gently through the UTC morning and
  builds all day toward the transatlantic evening overlap — US unlocks at
  05:00/08:00 UTC, then European prime time and the US afternoon stacking on
  top of each other — peaking around hours 19–23 at roughly 1.5–3× the first
  hour. This is the shape of Ghost of Tsushima, The Last of Us Part II,
  Resident Evil Requiem and the other big rolling-midnight console launches.
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
   launches whose first hour was a similar size count most,
3. fits a normal in log space (weighted mean and standard deviation of the
   log ratios), lightly smoothed across neighbouring hours,
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

## Validation

The model was tuned by leave-one-out cross-validation over the 37 launch
comparables in the kit's practice data: forecast each launch's hours 2–24
from its first hour, using the other 36 launches as the pool, and score with
the contest's own pinball loss on the log scale.

| forecaster | mean loss, all 37 | mean loss, rolling-midnight launches |
|---|---|---|
| persistence (flat at hour 1) | 0.930 | 0.393 |
| this model | **0.393** | **0.292** |

The kernel bandwidth 0.45 decades was the best of the widths tried
(0.4–1.0). Hand-built class weights (rolling vs simultaneous unlock,
console-only vs PC) and a pre-launch momentum term were also tried and
dropped: once first-hour size is accounted for, they added nothing.

## Running it

Standard library only, no network, fully deterministic (two runs on the
same case write byte-identical output):

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=<dir with .in files> MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Without the environment variables it reads `/input` and writes `/output`,
as the grader runs it. Each `<id>.in` case produces one `<id>.out`:
`{"hours": [{"hour": 2, "q": [q05, q25, q50, q75, q95]}, …]}`, 23 rows for
hours 2–24. A run over the kit's four practice cases takes about 0.2 s in
total, far inside the 8 s per-case cap.
