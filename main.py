"""Launch-day Twitch audience forecaster (make.fun gta6-twitch-ccu-forecast-01).

The model, in one paragraph: a launch day's hourly viewer curve, divided by its
own first hour, has a shape that depends mostly on how big the first hour was.
A first hour that is already huge means the rolling midnight unlock had already
swept New Zealand, Australia, Japan and Europe before the UTC day began, and the
day then builds toward the transatlantic evening overlap; a small first hour
means the unlock was still to come inside the UTC day, and the curve is a steep
climb from near zero. So this program pools the launch-day curves of the past
big launches the case itself supplies (its `comparables`), weights each by how
close its first hour sits to this case's first hour in log space, and reads the
five quantiles of each future hour from the weighted distribution of the pool's
log ratios to their own first hours, fitted as a normal in log space and
lightly smoothed across neighbouring hours. The forecast is the case's hour-1
print times those ratio quantiles. Everything is computed from the case file:
no network, no randomness, no clock, so two runs write the same bytes.

Validation while building: leave-one-out over the 37 launch comparables in the
kit's practice data (forecast each launch from the other 36) gives a mean
pinball loss of about 0.39, against about 0.93 for the flat persistence
forecast on the same pool; on the rolling-midnight targets alone it gives
about 0.29 against persistence's 0.39.

Run by the grader as `python3 -P -s /bot/main.py` (Python 3.13, standard
library only). Outside the grader, MAKEFUN_INPUT_DIR and MAKEFUN_OUTPUT_DIR
stand in for /input and /output.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist

# The grader's -P leaves /bot off sys.path: put this file's directory back
# first, so a module shipped beside main.py would import cleanly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# Bandwidth of the first-hour similarity kernel, in decades (log10 units).
# Chosen by leave-one-out cross-validation over the practice comparables:
# 0.45 forecast the held-out launches best of the widths tried (0.4 to 1.0).
SIZE_BANDWIDTH = 0.45

# A comparable counts as a launch only if its release-day curve is nearly
# whole: its first hour present and at least 20 of the day's 24 hours. This
# keeps the one non-launch comparable (the GTA VI category's own pre-release
# history, whose "release day" is a trailer premiere with a handful of
# sampled hours) out of the pool on the data alone.
MIN_DAY_HOURS = 20

# Fallback spread if the pool somehow comes up empty: the forecast falls back
# to persistence, a flat median at hour 1's print with a log spread growing
# like a random walk's, 0.15 per square-root hour.
FALLBACK_SIGMA = 0.15


def parse_instant(text):
    """An ISO 8601 timestamp from a case file, as an aware datetime."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def launch_day_curve(comparable):
    """The comparable's release-day hours: {hour 1..24: viewers}.

    The hourly points run from 14 days before the release day to 3 days
    after; the day's hours are the ones starting inside
    [day_start, day_start + 24 h).
    """
    start = parse_instant(comparable["day_start"])
    curve = {}
    for point in comparable.get("hourly", []):
        offset = (parse_instant(point["from"]) - start).total_seconds()
        if 0 <= offset < 24 * 3600:
            viewers = point.get("viewers")
            if viewers is not None and viewers > 0:
                curve[int(offset // 3600) + 1] = float(viewers)
    return curve


def comparable_pool(case):
    """The pool of past launches usable as shape evidence for this case.

    Each entry carries the launch's first-hour viewers and, for every later
    hour, the log of that hour's ratio to the first hour.
    """
    pool = []
    for comparable in case.get("comparables", []):
        curve = launch_day_curve(comparable)
        if 1 not in curve or len(curve) < MIN_DAY_HOURS:
            continue
        first = curve[1]
        log_ratios = {
            hour: math.log(viewers / first)
            for hour, viewers in curve.items()
            if hour >= 2
        }
        pool.append({"first": first, "log_ratios": log_ratios})
    # A fixed order keeps the floating-point sums identical on every run.
    pool.sort(key=lambda entry: entry["first"])
    return pool


def similarity_weights(pool, first_hour):
    """Gaussian weights on the log10 distance between first hours."""
    target = math.log10(max(1.0, first_hour))
    weights = []
    for entry in pool:
        distance = math.log10(entry["first"]) - target
        weights.append(math.exp(-0.5 * (distance / SIZE_BANDWIDTH) ** 2))
    return weights


def weighted_mean_sd(pairs):
    """Mean and standard deviation of values with weights [(value, weight)]."""
    total = sum(weight for _, weight in pairs)
    mean = sum(value * weight for value, weight in pairs) / total
    var = sum(weight * (value - mean) ** 2 for value, weight in pairs) / total
    return mean, math.sqrt(var)


def smooth(values):
    """One [0.25, 0.5, 0.25] pass over a list, ends weighted toward the edge."""
    if len(values) < 3:
        return list(values)
    out = [0.75 * values[0] + 0.25 * values[1]]
    for i in range(1, len(values) - 1):
        out.append(0.25 * values[i - 1] + 0.5 * values[i] + 0.25 * values[i + 1])
    out.append(0.25 * values[-2] + 0.75 * values[-1])
    return out


def round2(value):
    """Round to 2 decimals, half up; whole numbers come back as ints."""
    scaled = value * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    result = whole / 100
    return int(result) if float(result).is_integer() else result


def hour1_print(case):
    """Hour 1's print from the case's `known` row (a dict or a one-row list)."""
    known = case["known"]
    if isinstance(known, dict):
        rows = [known]
    else:
        rows = known
    for row in rows:
        if row.get("hour") == 1:
            return max(1.0, float(row["viewers"]))
    raise ValueError("case has no hour-1 print")


def forecast_case(case):
    """The forecast object for one case: 23 rows of five quantiles."""
    p1 = hour1_print(case)
    levels = case.get("levels", [0.05, 0.25, 0.5, 0.75, 0.95])
    zscores = [NormalDist().inv_cdf(level) for level in levels]
    hours = [row["hour"] for row in case["forecast"]]

    pool = comparable_pool(case)
    mus, sigmas = [], []
    if pool:
        weights = similarity_weights(pool, p1)
        stats = {}
        for hour in hours:
            pairs = [
                (entry["log_ratios"][hour], weight)
                for entry, weight in zip(pool, weights)
                if hour in entry["log_ratios"]
            ]
            if pairs:
                stats[hour] = weighted_mean_sd(pairs)
        if not stats:
            pool = []
        else:
            # An hour no pool launch sampled takes the nearest sampled
            # hour's shape rather than crashing the run: a crashed case is
            # an invalid case, and an invalid case takes no prize.
            for hour in hours:
                if hour not in stats:
                    nearest = min(stats, key=lambda other: (abs(other - hour), other))
                    stats[hour] = stats[nearest]
            mus = smooth([stats[hour][0] for hour in hours])
            sigmas = smooth([stats[hour][1] for hour in hours])
    if not pool:
        for hour in hours:
            mus.append(0.0)
            sigmas.append(FALLBACK_SIGMA * math.sqrt(hour - 1))

    rows = []
    for i, hour in enumerate(hours):
        quantiles = []
        for z in zscores:
            value = p1 * math.exp(mus[i] + z * sigmas[i])
            quantiles.append(round2(min(1_000_000_000.0, max(0.01, value))))
        # Rounding can only flatten, never invert, but enforce the order.
        for j in range(1, len(quantiles)):
            if quantiles[j] < quantiles[j - 1]:
                quantiles[j] = quantiles[j - 1]
        rows.append({"hour": hour, "q": quantiles})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case)
        text = json.dumps(forecast, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
