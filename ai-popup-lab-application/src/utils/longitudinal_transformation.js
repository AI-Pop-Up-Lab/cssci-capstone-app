import * as d3 from "d3";

/**
 * parses the raw base CSV text into d3 series format.
 */
export function parseBaselineCsv(csvText) {
  const rows = d3.csvParse(csvText, d => ({
    week:        d.week,
    vote_choice: d.vote_choice,
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
    vote_choice:     d.vote_choice,
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