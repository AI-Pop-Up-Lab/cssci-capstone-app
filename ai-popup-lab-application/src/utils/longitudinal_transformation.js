import * as d3 from "d3";

/**
 * Canonical party names, keyed by every spelling seen in the data
 * (lowercased + trimmed). Add new aliases here as they turn up.
 *
 * The canonical value (right-hand side) should match the casing the rest of
 * the app uses for party names (e.g. US_PARTIES in voteLongitudinalUSPollsters).
 */
const VOTE_CHOICE_ALIASES = {
  democrat:   "Democrat",
  democratic: "Democrat",
};

export function normaliseVoteChoice(raw) {
  if (raw == null) return raw;
  const trimmed = String(raw).trim();
  return VOTE_CHOICE_ALIASES[trimmed.toLowerCase()] ?? trimmed;
}

/**
 * Colours that always win over whatever party_colours says, keyed by the
 * lowercased party name. Used so "Other" is the same brown everywhere.
 */
const COLOUR_OVERRIDES = {
  other: "#8B5E3C",
};

/**
 * Case-insensitive lookup into a party_colours object, so a casing
 * difference between the data and the colour keys can't turn a line grey.
 * Overrides in COLOUR_OVERRIDES take precedence.
 */
export function lookupColour(coloursObj, key) {
  if (key == null) return "#888";
  const override = COLOUR_OVERRIDES[String(key).trim().toLowerCase()];
  if (override) return override;
  if (!coloursObj) return "#888";
  const found = Object.keys(coloursObj).find(k => k.toLowerCase() === String(key).toLowerCase());
  return found ? coloursObj[found] : "#888";
}

/**
 * ISO week key -> Date of that week's Monday (UTC).
 * Accepts "2026-W36", "2026_36", "2026-36", "2026_W36".
 * Returns null if the key can't be parsed.
 */
export function isoWeekToMonday(weekKey) {
  const m = /^(\d{4})[-_ ]?W?(\d{1,2})$/i.exec(String(weekKey ?? "").trim());
  if (!m) return null;
  const year = Number(m[1]);
  const week = Number(m[2]);
  // ISO week 1 is the week containing 4 January
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const jan4DayNr = (jan4.getUTCDay() + 6) % 7; // Mon=0 ... Sun=6
  const week1Monday = Date.UTC(year, 0, 4 - jan4DayNr);
  return new Date(week1Monday + (week - 1) * 7 * 86400000);
}

// ======================================================================
// Week anchoring and date ranges
// ======================================================================
//
// Each ISO week key represents the polling for the 7 days BEFORE its anchor
// date, e.g. 2026-W30 is anchored on 20/07/2026 and covers 13/07/2026 -
// 20/07/2026. Charts plot each week at its anchor date and label it with the
// range.
//
// Which weekday is the anchor can change over time. Edit WEEK_ANCHOR_SCHEDULE
// to change it:
//   - from:    the first week the rule applies to. Either an ISO week key
//              ("2026-W40" / "2026_40") or a date ("2026-10-01" or a Date).
//              A date means "the ISO week containing that date".
//   - weekday: ISO weekday of the anchor, 1 = Monday ... 7 = Sunday. The anchor
//              is 00:00 UTC of that weekday, so Thursday (4) is the midnight
//              between Wednesday and Thursday.
// Each week uses the latest entry whose `from` is on or before it. Entries can
// be in any order.
export const WEEK_ANCHOR_SCHEDULE = [
  { from: "2000-W01", weekday: 1 }, // Monday: original behaviour
  { from: "2026-W40", weekday: 4 }, // Thursday: US predictions generated Wed midnight -> Thu (from October 2026)
];

const DAY_MS = 86400000;

// Monday (00:00 UTC) of the ISO week containing `date`.
function mondayOf(date) {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  return new Date(d.getTime() - ((d.getUTCDay() + 6) % 7) * DAY_MS);
}

// Schedule `from` (ISO week key | "YYYY-MM-DD" | Date) -> Monday of that week.
function resolveScheduleFrom(from) {
  if (from instanceof Date) return mondayOf(from);
  const s = String(from ?? "").trim();
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (m) return mondayOf(new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))));
  return isoWeekToMonday(s);
}

const RESOLVED_ANCHOR_SCHEDULE = WEEK_ANCHOR_SCHEDULE
  .map(r => ({ monday: resolveScheduleFrom(r.from), weekday: Number(r.weekday) }))
  .filter(r => r.monday && r.weekday >= 1 && r.weekday <= 7)
  .sort((a, b) => a.monday - b.monday);

// Anchor date for the ISO week starting on `monday`.
function anchorFromMonday(monday) {
  let weekday = 1;
  for (const r of RESOLVED_ANCHOR_SCHEDULE) {
    if (r.monday.getTime() <= monday.getTime()) weekday = r.weekday;
  }
  return new Date(monday.getTime() + (weekday - 1) * DAY_MS);
}

/**
 * ISO week key -> anchor Date (UTC): the END of the 7-day range the week
 * represents. Returns null if the key can't be parsed.
 */
export function weekAnchorDate(weekKey) {
  const monday = isoWeekToMonday(weekKey);
  return monday ? anchorFromMonday(monday) : null;
}

const fmtDate = d => {
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getUTCFullYear()}`;
};

/**
 * ISO week key -> "dd/mm/yyyy" of the week's anchor date (end of its range),
 * e.g. 2026-W30 -> "20/07/2026". Falls back to the raw key if unparseable.
 */
export function formatWeekDate(weekKey) {
  const d = weekAnchorDate(weekKey);
  return d ? fmtDate(d) : String(weekKey ?? "");
}

/**
 * Date -> "dd/mm/yyyy – dd/mm/yyyy", the 7 days ending on that date.
 */
export function formatRangeEndingAt(endDate) {
  return `${fmtDate(new Date(endDate.getTime() - 7 * DAY_MS))} – ${fmtDate(endDate)}`;
}

/**
 * ISO week key -> date range label, e.g. 2026-W30 -> "13/07/2026 – 20/07/2026".
 * Falls back to the raw key if unparseable.
 */
export function formatWeekRange(weekKey) {
  const d = weekAnchorDate(weekKey);
  return d ? formatRangeEndingAt(d) : String(weekKey ?? "");
}

/**
 * Tick dates (anchor dates) for a time x-axis: one tick every `stride` weeks
 * starting at the first week, each landing on a real anchor date even if the
 * anchor weekday changes part-way through. `pitchPx` is the minimum horizontal
 * space allowed per tick (tilted labels need much less than flat ones).
 */
export function buildWeekTicks(weeks, width, pitchPx = 30, thin = 2) {
  const mondays = weeks.map(isoWeekToMonday).filter(Boolean);
  if (!mondays.length) return [];
  const first = d3.min(mondays).getTime();
  const last  = d3.max(mondays).getTime();
  const maxTicks  = Math.max(2, Math.floor(width / pitchPx));
  const spanWeeks = Math.round((last - first) / (7 * DAY_MS));
  // `thin` multiplies the stride: 2 = label every other week (or every other
  // slot when the chart is too narrow for every week), 1 = no thinning.
  const stride    = Math.max(1, Math.ceil(spanWeeks / (maxTicks - 1))) * thin;
  const ticks = [];
  for (let t = first; t <= last; t += stride * 7 * DAY_MS) {
    ticks.push(anchorFromMonday(new Date(t)));
  }
  return ticks;
}

/**
 * Pipeline cutoff. Weeks up to and INCLUDING this one come from the old
 * (incorrect) model pipeline; anything after it is from the updated model.
 * The two parts of each series must never be joined by a line.
 */
export const OLD_PIPELINE_LAST_WEEK = "2026_23";

/**
 * True if the week belongs to the old pipeline (on or before the cutoff week).
 * Compares by date rather than string so it works for any key format that
 * isoWeekToMonday accepts ("2026_23", "2026-W23", ...).
 */
export function isOldPipelineWeek(weekKey) {
  const d = isoWeekToMonday(weekKey);
  const cutoff = isoWeekToMonday(OLD_PIPELINE_LAST_WEEK);
  return !!d && !!cutoff && d.getTime() <= cutoff.getTime();
}

/**
 * Splits a series' values into { old, current } at the pipeline cutoff.
 * Each half keeps its original order.
 */
export function splitByPipeline(values) {
  const old = [];
  const current = [];
  for (const v of values) (isOldPipelineWeek(v.week) ? old : current).push(v);
  return { old, current };
}

/**
 * Calendar year of the week's Monday (as a string). Used for year-boundary
 * markers so they agree with the dates shown on the axis (e.g. 2026-W01 starts
 * on 29/12/2025, so its Monday is still in 2025).
 */
export function weekYear(weekKey) {
  const d = isoWeekToMonday(weekKey);
  return d ? String(d.getUTCFullYear()) : String(weekKey ?? "").slice(0, 4);
}

/**
 * parses the raw base CSV text into d3 series format.
 */
export function parseBaselineCsv(csvText) {
  const rows = d3.csvParse(csvText, d => ({
    week:        d.week,
    vote_choice: normaliseVoteChoice(d.vote_choice),
    share:       +d.share,
  }));
  return rowsToSeries(rows, "share");
}

/**
 * parses the national summary aggregate CSV (week, vote_choice, lower_95,
 * median, upper_95 -- values are fractions, e.g. 0.48) into d3 series format.
 *
 * Each value is { week, share, low, high } on a 0-100 scale, where `share` is
 * the MEDIAN (so anything that already reads `share` keeps working) and
 * low/high are the 95% interval bounds. Rows with no usable median are
 * dropped; a missing bound becomes NaN and is simply not drawn.
 */
export function parseNationalSummaryCsv(csvText) {
  const toPct = v => {
    const n = parseFloat(v);
    return Number.isFinite(n) ? +(n * 100).toFixed(2) : NaN;
  };

  const rows = d3.csvParse(csvText, d => ({
    week:        d.week,
    vote_choice: normaliseVoteChoice(d.vote_choice),
    share:       toPct(d.median),
    low:         toPct(d.lower_95),
    high:        toPct(d.upper_95),
  })).filter(r => Number.isFinite(r.share));

  const parties = [...new Set(rows.map(r => r.vote_choice))];
  return parties.map(party => ({
    party,
    values: rows
      .filter(r => r.vote_choice === party)
      .map(({ week, share, low, high }) => ({ week, share, low, high }))
      .sort((a, b) => a.week.localeCompare(b.week)),
  }));
}

/**
 * parses the raw demographic CSV text into flat rows.
 */
// export function parseDemographicCsv(csvText) {
//   return d3.csvParse(csvText, d => ({
//     week:            d.week,
//     vote_choice:     d.vote_choice,
//     gender:          d.gender,
//     age_group:       d.age_group,
//     education_level: d.education_level,
//     municipality:    d.municipality,
//     weight:          +d.weight,
//   }));
// }

export function parseDemographicCsv(csvText) {
  return d3.csvParse(csvText, d => ({
    week:            d.week,
    vote_choice:     normaliseVoteChoice(d.vote_choice),
    race:            d.race,
    gender:          d.gender,
    age_group:       d.age_group,
    state:           d.state,
    state_cd:        d.state_cd,
    education_level: d.education_level,
    weight:          +d.weight,
  }));
}

/**
 * apply demographic filters to flat rows, re-aggregate weights,
 * and return D3 series format. filters={} to be passed for no filtering.
 */
export function aggregateToSeries(rows, filters = {}) {
  // apply filters
  let filtered = rows;
  for (const [col, val] of Object.entries(filters)) {
    if (val) filtered = filtered.filter(r => r[col] === val);
  }

  // sum weights by week + party
  const byWeekParty = d3.rollup(
    filtered,
    v => d3.sum(v, d => d.weight),
    d => d.week,
    d => d.vote_choice,
  );

  // normalise within each week so shares sum to 100%
  const weeks   = [...new Set(filtered.map(r => r.week))].sort();
  const parties = [...new Set(filtered.map(r => r.vote_choice))];

  const shareRows = [];
  for (const week of weeks) {
    const weekMap   = byWeekParty.get(week) ?? new Map();
    const weekTotal = d3.sum(weekMap.values());
    for (const party of parties) {
      const weight = weekMap.get(party) ?? 0;
      shareRows.push({
        week,
        vote_choice: party,
        share: weekTotal > 0 ? +(weight / weekTotal * 100).toFixed(2) : 0,
      });
    }
  }

  return rowsToSeries(shareRows, "share");
}

/**
 * converts flat {week, vote_choice, share} rows to d3 series array
 */
function rowsToSeries(rows, shareCol) {
  const parties = [...new Set(rows.map(r => r.vote_choice))];
  return parties.map(party => ({
    party,
    values: rows
      .filter(r => r.vote_choice === party)
      .map(r => ({ week: r.week, share: r[shareCol] }))
      .sort((a, b) => a.week.localeCompare(b.week)),
  }));
}

// ======================================================================
// House seat projection
// ======================================================================
//
// Input: the district-level aggregate (week, vote_choice, state_cd, weight),
// where `weight` is the expected number of voters for that party in that
// congressional district. "Did not vote" rows are ignored: seats are decided
// by those who vote, and only the Democratic/Republican contest is modelled.
// "Other" is shown as 0 seats (third parties/independents win ~none).
//
// Method (a "nowcast": the seats each party would win if the election were
// held with that week's vote shares):
//   1. In each district take the Democratic share of the two-party vote.
//   2. Win probability: P(D wins) = Phi((dShare - 0.5 + s) / districtSd)
//      - districtSd: district-level noise in the MRP estimate
//      - s: a national shock shared by ALL districts, ~ N(0, nationalSd^2)
//        (this is what stops district errors averaging out and gives a
//        realistic seat range)
//   3. Expected D seats = sum of win probabilities, averaged over the shock.
//      The 95% range comes from the law of total variance (Poisson-binomial
//      variance within a shock level + variance of the mean across shocks).
//   4. Republican seats = (number of districts) - Democratic seats.
//
// The seat estimate itself is always district-based (state_cd): district
// margins are used exactly as given, never shifted to match the national
// median. The national summary (when passed as `nationalSummary`) is used
// ONLY to size the national shock for that week: nationalSd is derived from
// the width of the 95% interval on the Democratic two-party share, in place
// of the fixed assumption. Weeks with no national summary fall back to the
// default nationalSd.
//
// districtSd (and the fallback nationalSd) are assumptions, not fitted values.

export const DEFAULT_SEAT_PARAMS = { districtSd: 0.04, nationalSd: 0.02 };

// z for the 95% range reported on seats
const RANGE_Z = 1.96;

/**
 * national summary series (from parseNationalSummaryCsv) ->
 * Map<week, nationalSd> : the sd of the Democratic two-party share implied by
 * that week's 95% intervals. D/(D+R) is lowest at (D low, R high) and highest
 * at (D high, R low); using those extremes is deliberately conservative
 * (it treats D and R as moving in perfect opposition). Weeks where the
 * bounds are missing or inconsistent are left out.
 */
function nationalSdByWeek(series) {
  const find = name => series.find(s => String(s.party).trim().toLowerCase() === name);
  const dem = find("democrat");
  const rep = find("republican");
  const out = new Map();
  if (!dem || !rep) return out;

  const repByWeek = new Map(rep.values.map(v => [v.week, v]));
  for (const d of dem.values) {
    const r = repByWeek.get(d.week);
    if (!r) continue;
    const lo = d.low  / (d.low  + r.high);
    const hi = d.high / (d.high + r.low);
    if (Number.isFinite(lo) && Number.isFinite(hi) && hi >= lo) {
      out.set(d.week, (hi - lo) / (2 * RANGE_Z));
    }
  }
  return out;
}

// Abramowitz & Stegun 7.1.26 (|error| < 1.5e-7) - plenty for this purpose.
function erf(x) {
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * ax);
  const poly = ((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592;
  return sign * (1 - poly * t * Math.exp(-ax * ax));
}
const normCdf = x => 0.5 * (1 + erf(x / Math.SQRT2));

// Fixed quadrature over the national shock: z in [-3, 3], weighted by the
// standard normal density and normalised to sum to 1.
const SHOCK_Z = d3.range(-3, 3.0001, 0.5);
const SHOCK_W = (() => {
  const raw = SHOCK_Z.map(z => Math.exp(-0.5 * z * z));
  const total = d3.sum(raw);
  return raw.map(w => w / total);
})();

/**
 * parses the raw district-level CSV text into flat rows.
 */
export function parseDistrictCsv(csvText) {
  return d3.csvParse(csvText, d => ({
    week:        d.week,
    vote_choice: normaliseVoteChoice(d.vote_choice),
    state_cd:    d.state_cd,
    weight:      +d.weight,
  }));
}

/**
 * Projects House seats for every week in the district rows.
 * Returns Map<week, { democrat, republican, other, districts }> where each
 * party entry is { seats, lo, hi } (lo/hi = 95% range) and `districts` is the
 * number of districts that went into the calculation.
 */
export function computeSeatsByWeek(rows, params = {}) {
  const { districtSd, nationalSd: fallbackNationalSd, nationalSummary } = { ...DEFAULT_SEAT_PARAMS, ...params };
  const nationalSdMap = nationalSummary ? nationalSdByWeek(nationalSummary) : new Map();

  // week -> district -> { d, r } expected voters
  const byWeek = new Map();
  for (const row of rows) {
    const party = String(row.vote_choice ?? "").toLowerCase();
    if (party !== "democrat" && party !== "republican") continue;
    if (!row.state_cd || !Number.isFinite(row.weight)) continue;

    let districts = byWeek.get(row.week);
    if (!districts) byWeek.set(row.week, (districts = new Map()));
    let cell = districts.get(row.state_cd);
    if (!cell) districts.set(row.state_cd, (cell = { d: 0, r: 0 }));
    if (party === "democrat") cell.d += row.weight; else cell.r += row.weight;
  }

  const out = new Map();
  for (const [week, districts] of byWeek) {
    // Democratic two-party share minus 0.5, one entry per district with votes
    const margins = [];
    for (const { d, r } of districts.values()) {
      const total = d + r;
      if (total > 0) margins.push(d / total - 0.5);
    }
    const n = margins.length;
    if (!n) continue;

    // national shock size for this week: from the 95% interval if we have one
    const nationalSd = nationalSdMap.get(week) ?? fallbackNationalSd;

    let meanOfMean = 0;   // E_s[ mu(s) ]
    let meanOfSq   = 0;   // E_s[ mu(s)^2 ]
    let meanOfVar  = 0;   // E_s[ sum p(1-p) ]
    for (let k = 0; k < SHOCK_Z.length; k++) {
      const shock = nationalSd * SHOCK_Z[k];
      let mu = 0, variance = 0;
      for (const m of margins) {
        const p = normCdf((m + shock) / districtSd);
        mu += p;
        variance += p * (1 - p);
      }
      meanOfMean += SHOCK_W[k] * mu;
      meanOfSq   += SHOCK_W[k] * mu * mu;
      meanOfVar  += SHOCK_W[k] * variance;
    }

    const sd = Math.sqrt(Math.max(0, meanOfVar + (meanOfSq - meanOfMean * meanOfMean)));
    const dSeats = Math.round(meanOfMean);
    const dLo = Math.max(0, Math.round(meanOfMean - RANGE_Z * sd));
    const dHi = Math.min(n, Math.round(meanOfMean + RANGE_Z * sd));

    out.set(week, {
      districts: n,
      democrat:   { seats: dSeats,     lo: dLo,     hi: dHi },
      republican: { seats: n - dSeats, lo: n - dHi, hi: n - dLo },
      other:      { seats: 0,          lo: 0,       hi: 0 },
    });
  }
  return out;
}
