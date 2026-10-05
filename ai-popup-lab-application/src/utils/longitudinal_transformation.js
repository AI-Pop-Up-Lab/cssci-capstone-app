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