// d3.js chart which shows party vote share over time amongst likely voters,
// broken down by demographic filters

import { useRef, useEffect, useState } from "react";
import { useTranslation, Trans } from 'react-i18next';
import * as d3 from "d3";
import './voteLongitudinalDemographics.css';
import exportIcon from '../../assets/images/export.png';
import axios from "axios";
import Loader from '../loader';
import { parseDemographicCsv, aggregateToSeries, lookupColour, formatWeekDate, formatWeekRange, formatRangeStartingAt, weekAnchorDate, buildWeekTicks, splitByPipeline, isOldPipelineWeek } from "../../utils/longitudinal_transformation";
// import partyColours from '../../assets/partyColours';

// Series that should not be drawn. Names are compared after lower-casing and
// stripping everything except letters/digits, so "Did not vote", "Did Not Vote"
// and "did_not_vote" all match "didnotvote". Add other spellings here if needed.
// Covers the same labels as the pollsters chart ("did not vote", "will not
// vote", "non-voter(s)").
const HIDDEN_SERIES = new Set(["didnotvote", "willnotvote", "nonvoter", "nonvoters"]);
const normaliseName = name => String(name ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");

// When likelyVotersOnly is true: drop the "did not vote" series, then
// renormalise what's left so the remaining series sum to 100% for each week
// (i.e. amongst likely voters). Each week is divided by the sum of the
// visible series for that week. When the full set sums to 100 this equals the
// pollsters chart's share / (100 - nonVoterShare) * 100, but it also stays
// correct if a filter leaves the totals slightly off 100.
// When false: the unconditional series (including "did not vote") are
// returned untouched.
const buildVisibleSeries = (rows, filters, likelyVotersOnly = true) => {
  const all = aggregateToSeries(rows, filters);
  if (!likelyVotersOnly) return all;
  const voters = all.filter(s => !HIDDEN_SERIES.has(normaliseName(s.party)));

  const totalByWeek = new Map();
  voters.forEach(s =>
    s.values.forEach(v =>
      totalByWeek.set(v.week, (totalByWeek.get(v.week) ?? 0) + v.share)
    )
  );

  return voters.map(s => ({
    ...s,
    values: s.values.map(v => {
      const total = totalByWeek.get(v.week) ?? 0;
      return { ...v, share: total > 0 ? +(v.share / total * 100).toFixed(2) : 0 };
    }),
  }));
};

// Builds a CSV from an array of rows and triggers a browser download.
function downloadCsv(filename, rows) {
  const csvContent = rows
    .map(row => row.map(cell => {
      const str = String(cell ?? "");
      // quote any cell containing a comma, quote, or newline, escaping embedded quotes
      return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
    }).join(","))
    .join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function VoteLongitudinalDemographics({ country, countryData }) {

  const { t } = useTranslation();

  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  // Party colours come from the country data object fetched once by the
  // parent page and passed down as a prop -- not fetched separately here.
  const partyColours = countryData?.party_colours ?? null;

  const [rawRows, setRawRows] = useState(null);  
  const [filters, setFilters] = useState({});
  // 'Amongst likely voters' toggle (default on): drops "did not vote" and
  // renormalises the remaining parties to 100%. Purely client-side, no refetch.
  const [likelyVotersOnly, setLikelyVotersOnly] = useState(true);
  const [error, setError] = useState(null);

  const demographicKeys = ["gender", "age_group", "education_level", "state", "race"];
  const chartData = rawRows ? buildVisibleSeries(rawRows, filters, likelyVotersOnly) : null;
  const filterOptions = rawRows
  ? Object.fromEntries(
      demographicKeys.map(key => [
        key,
        ["all", ...new Set(rawRows.map(r => r[key]))]
      ])
    )
  : null;

  const [rangeIdx, setRangeIdx] = useState(null);

  // fetch chart data
  async function getChartData(countryName){
    setRawRows(null);
    setError(null);
    axios.get(`${process.env.REACT_APP_API_URL}/api/longitudinal/country_longitudinal_aggregated_demographics?country=${countryName}`, {
      responseType: "text",
    })
      .then(res => setRawRows(parseDemographicCsv(res.data)))
      .catch(err => setError(err.message));
  }

  useEffect(() => {

    setRawRows(null);
    setRangeIdx(null);

    getChartData(country);

  }, [country]);

  useEffect(() => {
    if (!rawRows) return;
    const series = buildVisibleSeries(rawRows, {}, true);
    if (!series[0]) return;
    setRangeIdx([0, series[0].values.length - 1]);
  }, [rawRows]);

  // A filter can drop weeks, shrinking the series. Keep the slider range
  // inside the new length so the slice can't run out of bounds.
  const seriesLen = chartData?.[0]?.values.length ?? 0;
  useEffect(() => {
    if (!seriesLen) return;
    setRangeIdx(prev => {
      if (!prev) return prev;
      const max = seriesLen - 1;
      const hi = Math.min(prev[1], max);
      const lo = Math.min(prev[0], Math.max(0, hi - 1));
      return lo === prev[0] && hi === prev[1] ? prev : [lo, hi];
    });
  }, [seriesLen]);

  const slicedData = chartData && rangeIdx
    ? chartData.map(series => ({
        ...series,
        values: series.values.slice(rangeIdx[0], rangeIdx[1] + 1),
      }))
    : null;

  // Export the raw rows received from the backend (every demographic cell,
  // including "did not vote"), clipped to the week range currently selected
  // on the slider. Demographic dropdowns and the "amongst likely voters"
  // toggle are deliberately ignored. The slider indexes into the (possibly
  // filtered) series, so we translate it to start/end weeks and clip by week
  // key (ISO week keys like "2025-W01" sort correctly as strings).
  const handleExport = () => {
    if (!rawRows || !rawRows.length || !slicedData || !slicedData.length || !slicedData[0].values.length) return;

    const startWeek = slicedData[0].values[0]?.week;
    const endWeek = slicedData[0].values[slicedData[0].values.length - 1]?.week;

    const rows = rawRows.filter(r => r.week >= startWeek && r.week <= endWeek);
    if (!rows.length) return;

    // Header = every column present in the raw rows, in original order
    const columns = [...new Set(rows.flatMap(r => Object.keys(r)))];

    downloadCsv(
      `vote_share_demographics_raw_${country}_${startWeek}_to_${endWeek}.csv`,
      [columns, ...rows.map(r => columns.map(c => r[c] ?? ""))]
    );
  };

  const hasOldPipelinePoints = !!slicedData && slicedData.some(s => s.values.some(v => isOldPipelineWeek(v.week)));

  useEffect(() => {

    if (!slicedData || !slicedData[0]?.values.length || !partyColours) return; 

    const drawChart = () => {
      const containerWidth = containerRef.current?.getBoundingClientRect().width;
      if (!containerWidth || containerWidth === 0) return;

      const svgW   = containerWidth;

      // Bottom/left margins leave room for the tilted date-range tick labels
      const margin = { top: 30, right: 180, bottom: 120, left: 100 };
      const PLOT_H = 260;
      const svgH   = margin.top + PLOT_H + margin.bottom;
      const width  = svgW - margin.left - margin.right;
      const height = svgH - margin.top  - margin.bottom;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      svg
        .attr("width",  svgW)
        .attr("height", svgH);

      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

      const weeks = slicedData[0].values.map(v => v.week);

      // x — time scale. Each week is placed at its anchor date (the start of the
      // 7-day range it represents), so a gap of N weeks between data points
      // takes up N weeks' worth of horizontal space.
      const DAY = 86400000;
      const dates = weeks.map(weekAnchorDate).filter(Boolean);
      const minDate = d3.min(dates);
      const maxDate = d3.max(dates);
      const x = d3.scaleUtc()
        .domain([new Date(minDate.getTime() - 3 * DAY), new Date(maxDate.getTime() + 3 * DAY)])
        .range([0, width]);

      const xMid = week => {
        const d = weekAnchorDate(week);
        return d ? x(d) : null;
      };

      // y — linear, padded around actual data range
      const allShares = slicedData.flatMap(d => d.values.map(v => v.share));
      const yPad = 4;
      const y = d3.scaleLinear()
        .domain([
          Math.max(0,   d3.min(allShares) - yPad),
          Math.min(100, d3.max(allShares) + yPad),
        ])
        .range([height, 0])
        .nice();

      // Grid lines
      g.append("g")
        .attr("class", "vp-grid")
        .call(
          d3.axisLeft(y)
            .ticks(5)
            .tickSize(-width)
            .tickFormat("")
        )
        .select(".domain").remove();

      // X axis ticks: one label every `stride` weeks, starting at the first
      // week of data and always landing on a real anchor date. Each label shows
      // the 7-day range ending on that date, tilted so more of them fit.
      const tickValues = buildWeekTicks(weeks, width, 30);

      // X axis
      const xAxis = g.append("g")
        .attr("class", "vp-xaxis")
        .attr("transform", `translate(0,${height})`)
        .call(
          d3.axisBottom(x)
            .tickValues(tickValues)
            .tickSize(0)
            .tickFormat(formatRangeStartingAt)
        );

      xAxis.select(".domain").remove();
      xAxis.selectAll("text")
        .attr("font-size", "11px")
        .attr("font-weight", "700")
        .attr("fill", "#111")
        .attr("text-anchor", "end")
        .attr("dy", "0.5em")
        .attr("transform", "rotate(-45)");

      // --- Year-boundary markers: a divider at 1 January for every year
      // boundary that falls inside the visible range ---
      const [d0, d1] = x.domain();
      const yearG = g.append("g").attr("class", "vp-year-markers");

      for (let yr = d0.getUTCFullYear() + 1; yr <= d1.getUTCFullYear(); yr++) {
        const jan1 = new Date(Date.UTC(yr, 0, 1));
        if (jan1 <= d0 || jan1 >= d1) continue;
        const lineX = x(jan1);

        yearG.append("line")
          .attr("x1", lineX)
          .attr("x2", lineX)
          .attr("y1", 0)
          .attr("y2", height)
          .attr("stroke", "#888")
          .attr("stroke-width", 1.5)
          .attr("stroke-dasharray", "4,3")
          .attr("opacity", 0.7);

        yearG.append("text")
          .attr("x", lineX + 6)
          .attr("y", 12)
          .attr("font-size", "12px")
          .attr("font-weight", "700")
          .attr("fill", "#666")
          .text(yr);
      }

      // Y axis
      g.append("g")
        .call(
          d3.axisLeft(y)
            .ticks(5)
            .tickFormat(d => `${d.toFixed(0)}%`)
        )
        .select(".domain").remove()
        .selection().selectAll("text")
          .attr("font-size", "13px")
          .attr("fill", "#111");

      const tooltip = d3.select(tooltipRef.current);

      // Triangle marker for old-pipeline points
      const triangle = d3.symbol().type(d3.symbolTriangle).size(36);

      // Line generator
      const lineGen = d3.line()
        .x(d => xMid(d.week))
        .y(d => y(d.share))
        .curve(d3.curveMonotoneX);

      // One path + dots + end label per party
      slicedData.forEach(series => {
        const colour = lookupColour(partyColours, series.party);

        // Split at the pipeline cutoff so old-pipeline weeks (triangles) are
        // never joined to updated-model weeks (circles).
        const { old: oldVals, current: newVals } = splitByPipeline(series.values);

        [oldVals, newVals].forEach(segment => {
          if (!segment.length) return;
          g.append("path")
            .datum(segment)
            .attr("fill", "none")
            .attr("stroke", colour)
            .attr("stroke-width", 2.5)
            .attr("stroke-linejoin", "round")
            .attr("stroke-linecap", "round")
            .attr("d", lineGen);
        });

        const attachTooltip = (sel, isOld) => sel
          .on("mouseover", (event, d) => {
            tooltip
              .style("opacity", 1)
              .html(`<strong>${series.party}</strong><br/>${formatWeekRange(d.week)}: ${d.share.toFixed(1)}%` +
                (isOld ? `<br/><span style="font-size:11px">Deprecated methodology</span>` : ""));
          })
          .on("mousemove", event => {
            tooltip
              .style("left", `${event.clientX + 12}px`)
              .style("top",  `${event.clientY + 12}px`);
          })
          .on("mouseout", () => tooltip.style("opacity", 0));

        // Dots (updated model): circles
        attachTooltip(
          g.selectAll(null)
            .data(newVals)
            .join("circle")
              .attr("cx", d => xMid(d.week))
              .attr("cy", d => y(d.share))
              .attr("r", 2)
              .attr("fill", colour),
          false
        );

        // Markers (old pipeline): triangles
        attachTooltip(
          g.selectAll(null)
            .data(oldVals)
            .join("path")
              .attr("d", triangle())
              .attr("transform", d => `translate(${xMid(d.week)},${y(d.share)})`)
              .attr("fill", colour),
          true
        );

        // End-of-line label (sits in right margin)
        const last = series.values.at(-1);
        g.append("text")
          .attr("x",  xMid(last.week) + 10)
          .attr("y",  y(last.share))
          .attr("dy", "0.35em")
          .attr("font-size",   "12px")
          .attr("font-weight", "600")
          .attr("fill", colour)
          .text(series.party);
      });
    };

    drawChart();

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          clearTimeout(observer._debounce);
          observer._debounce = setTimeout(() => {
            drawChart();
          }, 100);
        }
      }
    });

    if (!containerRef.current) return;
    observer.observe(containerRef.current);
    return () => observer.disconnect();

  }, [slicedData, partyColours]);


  return (
    <div className="VoteLongitudinalDemographics">
      <div className="vld-header-row">
        <h3 className="vld-title">{t('pollingResults.voteLongitudinalDemographic.title')}</h3>

        {chartData && partyColours && rangeIdx && !error && (
          <label className="vld-likely-toggle">
            <input
              type="checkbox"
              checked={likelyVotersOnly}
              onChange={e => setLikelyVotersOnly(e.target.checked)}
            />
            {t('pollingResults.voteLongitudinal.likelyVotersOnly', 'Amongst likely voters')}
          </label>
        )}
      </div>
      {error ? (
        <p className="vld-error">{error}</p>
      ) : chartData && partyColours && rangeIdx ? (
        <>

          <div className="vld-demographic-choices">
            
            {filterOptions && demographicKeys.map(key => (
              <div className="vld-dc" key={key}>
                <p>{key.replace(/_/g, " ")}</p>
                <select
                  value={filters[key] || "all"}
                  onChange={e => {
                    const val = e.target.value;
                    setFilters(prev => ({
                      ...prev,
                      [key]: val === "all" ? undefined : val,
                    }));
                  }}
                >
                  {filterOptions[key].map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </div>
            ))}
            
          </div>

          <div className="vld-chart-wrapper" ref={containerRef}>
            <svg ref={svgRef} />
            <div ref={tooltipRef} className="chart-tooltip" />
          </div>

          {hasOldPipelinePoints && (
            <p className="vld-footnote">
              {t('pollingResults.voteLongitudinalDemographic.oldPipelineFootnote', '▲ Triangle-marked parts of the series are from the old pipeline and are incorrect.')}
            </p>
          )}

          <p className="vld-footnote">
            {t('pollingResults.voteLongitudinalDemographic.intervalsFootnote', 'Chart derived from cell-level point estimates ignoring uncertainty for computational expediency. Point estimates of aggregates may differ from those derived under the full posterior as above.')}
          </p>

          {/* time range slider */}
          <div className="vld-slider-wrapper">
            <input
              type="range"
              min={0}
              max={chartData[0].values.length - 1}
              value={rangeIdx[0]}
              onChange={e => {
                const val = Math.min(Number(e.target.value), rangeIdx[1] - 1);
                setRangeIdx([val, rangeIdx[1]]);
              }}
              className="vld-range vld-range-left"
            />
            <input
              type="range"
              min={0}
              max={chartData[0].values.length - 1}
              value={rangeIdx[1]}
              onChange={e => {
                const val = Math.max(Number(e.target.value), rangeIdx[0] + 1);
                setRangeIdx([rangeIdx[0], val]);
              }}
              className="vld-range vld-range-right"
            />
            <div className="vld-range-background"></div>
          </div>

          <div className="vld-slider-labels">
            <p>{t('pollingResults.voteLongitudinalDemographic.selected')}: <span>{formatWeekDate(chartData[0].values[rangeIdx[0]]?.week)}</span> {t('pollingResults.voteLongitudinalDemographic.to')} <span>{formatWeekDate(chartData[0].values[rangeIdx[1]]?.week)}</span></p>
          </div>

          <div className="vld-export unbounded-weight300">
            <p>{t('pollingResults.voteLongitudinalDemographic.export.title')}</p>
            <br></br>
            <p>{t('pollingResults.voteLongitudinalDemographic.export.description')}</p>
            <button onClick={handleExport}>
              <p>Export</p>
              <img src={exportIcon}></img>
            </button>
          </div>
        </>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default VoteLongitudinalDemographics;