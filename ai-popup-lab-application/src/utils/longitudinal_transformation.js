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

/**
 * ISO week key -> "dd/mm/yyyy" of that week's Monday, e.g. 2026-W36 -> "31/08/2026".
 * Falls back to the raw key if it can't be parsed.
 */
export function formatWeekDate(weekKey) {
  const d = isoWeekToMonday(weekKey);
  if (!d) return String(weekKey ?? "");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getUTCFullYear()}`;
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
//      The 90% range comes from the law of total variance (Poisson-binomial
//      variance within a shock level + variance of the mean across shocks).
//   4. Republican seats = (number of districts) - Democratic seats.
//
// districtSd and nationalSd are assumptions, not fitted values - tune them.

export const DEFAULT_SEAT_PARAMS = { districtSd: 0.04, nationalSd: 0.02 };

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
 * party entry is { seats, lo, hi } (lo/hi = 90% range) and `districts` is the
 * number of districts that went into the calculation.
 */
export function computeSeatsByWeek(rows, params = {}) {
  const { districtSd, nationalSd } = { ...DEFAULT_SEAT_PARAMS, ...params };

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
    const dLo = Math.max(0, Math.round(meanOfMean - 1.645 * sd));
    const dHi = Math.min(n, Math.round(meanOfMean + 1.645 * sd));

    out.set(week, {
      districts: n,
      democrat:   { seats: dSeats,     lo: dLo,     hi: dHi },
      republican: { seats: n - dSeats, lo: n - dHi, hi: n - dLo },
      other:      { seats: 0,          lo: 0,       hi: 0 },
    });
  }
  return out;
}
