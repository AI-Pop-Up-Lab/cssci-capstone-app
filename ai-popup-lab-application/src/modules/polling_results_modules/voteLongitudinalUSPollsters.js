// d3.js chart which shows party vote share over time, with an optional
// overlay of US pollster-average predictions (dotted mean line + CI band)

import { useRef, useEffect, useState, useMemo } from "react";
import { useTranslation } from 'react-i18next';
import * as d3 from "d3";
import './voteLongitudinalUSPollsters.css';
import exportIcon from '../../assets/images/export.png'
import axios from "axios";
import Loader from '../loader';
import { parseBaselineCsv } from "../../utils/longitudinal_transformation";

const US_PARTIES = ["democrat", "republican", "other"];

// ----------------------------------------------------------------------
// ISO-week helpers: the US pollster feed gives us date-range labels like
// "09 Dec 2024 – 15 Dec 2024". We convert the *start* of that range into
// an ISO week key ("2024-W50") so it can share the same band-scale domain
// as VoteLongitudinal's own `week` field ("2025-W01" etc).
// ----------------------------------------------------------------------
const MONTHS = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };

function parseLabelStartDate(weekLabel) {
  const startStr = weekLabel.split("–")[0].trim(); // "09 Dec 2024"
  const [day, mon, year] = startStr.split(" ");
  return new Date(Date.UTC(Number(year), MONTHS[mon], Number(day)));
}

function isoWeekInfo(date) {
  const target = new Date(date.valueOf());
  const dayNr = (date.getUTCDay() + 6) % 7;
  target.setUTCDate(target.getUTCDate() - dayNr + 3);
  const firstThursday = target.valueOf();
  target.setUTCMonth(0, 1);
  if (target.getUTCDay() !== 4) {
    target.setUTCMonth(0, 1 + ((4 - target.getUTCDay()) + 7) % 7);
  }
  const week = 1 + Math.round((firstThursday - target) / 604800000);
  return { year: new Date(firstThursday).getUTCFullYear(), week };
}

function toISOWeekKey(date) {
  const { year, week } = isoWeekInfo(date);
  return `${year}-W${String(week).padStart(2, "0")}`;
}

function lookupColour(coloursObj, key) {
  if (!coloursObj) return "#888";
  const found = Object.keys(coloursObj).find(k => k.toLowerCase() === key.toLowerCase());
  return found ? coloursObj[found] : "#888";
}

function VoteLongitudinalUSPollsters({ country }) {

  const { t } = useTranslation();

  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  const [chartData, setChartData] = useState(null);
  const [error, setError] = useState(null);

  const [partyColours, setPartyColours] = useState(null);
  const [partyColoursError, setPartyColoursError] = useState(null);

  const [rangeIdx, setRangeIdx] = useState(null);

  // --- US pollster-average overlay state ---
  const [showPollsters, setShowPollsters] = useState(false);
  const [pollsterRaw, setPollsterRaw] = useState(null);
  const [pollsterLoading, setPollsterLoading] = useState(false);
  const [pollsterError, setPollsterError] = useState(null);
  const [usPartyColours, setUsPartyColours] = useState(null);

  // --- legend: series hidden via click-to-toggle ---
  const [hiddenSeries, setHiddenSeries] = useState(() => new Set());

  const toggleSeries = (key) => {
    setHiddenSeries(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  // fetch chart data
  async function getChartData(countryName){
    setChartData(null);
      setError(null);
      axios.get(`${process.env.REACT_APP_API_URL}/api/longitudinal/country_longitudinal_aggregated_simple?country=${countryName}`, {
        responseType: "text",
      })
        .then(res => setChartData(parseBaselineCsv(res.data)))
        .catch(err => setError(err.message));
  }

  // fetch party colours
  async function getPartyColours(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/party_colours?country=${'usa'}`);

      const response_data = response.data;

      const partyColoursData = response_data.party_colours;

      setPartyColours(partyColoursData);
      setPartyColoursError(null);
    } catch (err) {
      setPartyColoursError(err.message);
      setPartyColours(null);
    }
  };

  useEffect(() => {

    setChartData(null);
    setPartyColours(null);
    setRangeIdx(null);

    getPartyColours(country);
    getChartData(country);

  }, [country]);

  useEffect(() => {
    if (!chartData) return;
    setRangeIdx([0, chartData[0].values.length - 1]);
  }, [chartData]);

  // fetch US pollster-average data once, on component mount — independent of
  // the overlay checkbox, so the request is already in flight (or done) by
  // the time the user thinks to toggle it on. If they toggle it on while
  // this is still in flight, `pollsterLoading` is already true and the
  // loading state will reflect that immediately.
  useEffect(() => {
    setPollsterLoading(true);
    setPollsterError(null);

    Promise.all([
      axios.get(`${process.env.REACT_APP_API_URL}/api/longitudinal/us_pollster_predictions`, {
        responseType: "text",
      }),
      axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/party_colours?country=usa`),
    ])
      .then(([predRes, colourRes]) => {
        const parsed = typeof predRes.data === "string" ? JSON.parse(predRes.data) : predRes.data;
        setPollsterRaw(parsed);
        setUsPartyColours(colourRes.data.party_colours);
      })
      .catch(err => setPollsterError(err.message))
      .finally(() => setPollsterLoading(false));

  }, []);

  // --- CSV export helpers ---
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
 
  const handleExport = () => {
    if (!slicedData || !slicedData.length || !slicedData[0].values.length) return;
 
    const startWeek = slicedData[0].values[0]?.week;
    const endWeek = slicedData[0].values[slicedData[0].values.length - 1]?.week;
 
    // --- Main series: always exports every party regardless of hiddenSeries,
    // in wide format (one column per party), clipped to the selected timeframe ---
    const weeks = slicedData[0].values.map(v => v.week);
    const mainHeader = ["week", ...slicedData.map(s => s.party)];
    const mainRows = weeks.map((week, i) => [
      week,
      ...slicedData.map(s => s.values[i]?.share ?? ""),
    ]);
    downloadCsv(`vote_share_${country}_${startWeek}_to_${endWeek}.csv`, [mainHeader, ...mainRows]);
 
    // --- US pollster averages, clipped to the same timeframe, downloaded as a
    // separate file since it's a distinct dataset on its own (possibly sparser) weeks ---
    if (showPollsters && visiblePollsterSeries && visiblePollsterSeries.length) {
      const pollsterHeader = ["week", "party", "mean", "low", "high"];
      const pollsterRows = visiblePollsterSeries.flatMap(series =>
        series.values.map(v => [v.weekKey, series.party, v.mean, v.low, v.high])
      );
      downloadCsv(`us_pollster_averages_${startWeek}_to_${endWeek}.csv`, [pollsterHeader, ...pollsterRows]);
    }
  };

  const slicedData = chartData && rangeIdx
    ? chartData.map(series => ({
        ...series,
        values: series.values.slice(rangeIdx[0], rangeIdx[1] + 1),
      }))
    : null;

  // pollster mean/low/high converted to 0-100 scale + ISO week keys
  const pollsterSeries = useMemo(() => {
    if (!pollsterRaw) return null;
    const { time_lookup, posterior } = pollsterRaw;

    const weekKeyByT = {};
    time_lookup.forEach(({ t, week_label }) => {
      weekKeyByT[t] = toISOWeekKey(parseLabelStartDate(week_label));
    });

    return US_PARTIES
      .filter(party => posterior[party])
      .map(party => {
        const p = posterior[party];
        const values = time_lookup.map(({ t }) => ({
          weekKey: weekKeyByT[t],
          mean: p.mean[t - 1] * 100,
          low:  p.low[t - 1]  * 100,
          high: p.high[t - 1] * 100,
        }));
        return { party, values };
      });
  }, [pollsterRaw]);

  const baseWeekRange = useMemo(() => {
    if (!slicedData) return null;
    const baseWeeks = slicedData[0]?.values.map(v => v.week) ?? [];
    if (!baseWeeks.length) return null;
    // ISO week keys ("2025-W01") sort correctly as plain strings
    return [d3.min(baseWeeks), d3.max(baseWeeks)];
  }, [slicedData]);

  // pollster series, restricted to the base timeframe — recomputes whenever
  // the range sliders move
  const visiblePollsterSeries = useMemo(() => {
    if (!pollsterSeries || !baseWeekRange) return null;
    const [minWeek, maxWeek] = baseWeekRange;
    return pollsterSeries.map(series => ({
        ...series,
        values: series.values.filter(v => v.weekKey >= minWeek && v.weekKey <= maxWeek),
    }));
  }, [pollsterSeries, baseWeekRange]);

  // combined x-axis domain: base weeks ∪ pollster weeks (when overlay is on)
  const combinedWeeks = useMemo(() => {
    if (!slicedData) return null;
    const baseWeeks = slicedData[0]?.values.map(v => v.week) ?? [];
    if (!showPollsters || !visiblePollsterSeries || !visiblePollsterSeries.length) return baseWeeks;
    const overlayWeeks = visiblePollsterSeries[0].values.map(v => v.weekKey);
    return Array.from(new Set([...baseWeeks, ...overlayWeeks])).sort();
  }, [slicedData, showPollsters, visiblePollsterSeries]);

  // unified legend entries (base parties + pollster-average parties)
  const legendItems = useMemo(() => {
    const baseItems = (slicedData || []).map(s => ({
      key: s.party,
      label: s.party,
      colour: lookupColour(partyColours, s.party),
      dashed: false,
    }));

    const overlayItems = (showPollsters && visiblePollsterSeries)
      ? visiblePollsterSeries.map(s => ({
          key: `pollster-${s.party}`,
          label: `${s.party.charAt(0).toUpperCase()}${s.party.slice(1)} (US pollster avg)`,
          colour: lookupColour(usPartyColours, s.party),
          dashed: true,
        }))
      : [];

    return [...baseItems, ...overlayItems];
  }, [slicedData, partyColours, showPollsters, visiblePollsterSeries, usPartyColours]);

  useEffect(() => {

    if (!slicedData || !slicedData[0]?.values.length || !partyColours || !combinedWeeks) return;

    const drawChart = () => {
      const containerWidth = containerRef.current?.getBoundingClientRect().width;
      if (!containerWidth || containerWidth === 0) return;

      const svgW   = containerWidth;
      const svgH   = 340;

      const margin = { top: 30, right: 40, bottom: 50, left: 50 };
      const width  = svgW - margin.left - margin.right;
      const height = svgH - margin.top  - margin.bottom;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      svg
        .attr("width",  svgW)
        .attr("height", svgH);

      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

      const weeks = combinedWeeks;

      // x — band scale, one slot per week across base + (optionally) pollster weeks
      const x = d3.scaleBand()
        .domain(weeks)
        .range([0, width])
        .padding(0.2);

      const xMid = week => {
        const pos = x(week);
        return pos === undefined ? null : pos + x.bandwidth() / 2;
      };

      // y — linear, padded around the *visible* data range (base + overlay if
      // shown), excluding any series the user has toggled off via the legend.
      // This is what lets the axis tighten up when e.g. "Other" is hidden,
      // instead of always reserving room for series that aren't drawn.
      const visibleBaseSeries = slicedData.filter(d => !hiddenSeries.has(d.party));
      const baseShares = visibleBaseSeries.flatMap(d => d.values.map(v => v.share));

      const visibleOverlaySeries = (showPollsters && visiblePollsterSeries)
        ? visiblePollsterSeries.filter(s => !hiddenSeries.has(`pollster-${s.party}`))
        : [];
      const overlayShares = visibleOverlaySeries.flatMap(s => s.values.flatMap(v => [v.mean, v.low, v.high]));

      let allShares = [...baseShares, ...overlayShares];
      // Fallback: if every series is hidden, fall back to the full dataset
      // rather than computing a domain from an empty array (d3.min/max would
      // return undefined and produce a NaN domain, breaking the chart).
      if (!allShares.length) {
        allShares = [
          ...slicedData.flatMap(d => d.values.map(v => v.share)),
          ...(showPollsters && visiblePollsterSeries
            ? visiblePollsterSeries.flatMap(s => s.values.flatMap(v => [v.mean, v.low, v.high]))
            : []),
        ];
      }

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

      // With many weeks, showing every tick label would overlap — thin them out
      // to roughly one label per ~8 weeks, but always keep the very first week.
      const labelStride = Math.max(1, Math.ceil(weeks.length / 14));
      const tickValues = weeks.filter((_, i) => i % labelStride === 0);

      // X axis
      const xAxis = g.append("g")
        .attr("class", "vp-xaxis")
        .attr("transform", `translate(0,${height})`)
        .call(
          d3.axisBottom(x)
            .tickValues(tickValues)
            .tickSize(0)
            .tickFormat(w => w.replace(/^\d{4}-/, ""))
        );

      xAxis.select(".domain").remove();
      xAxis.selectAll("text")
        .attr("font-size", "13px")
        .attr("font-weight", "700")
        .attr("fill", "#111")
        .attr("dy", "1.2em");

      // --- Year-boundary markers ---
      const yearOf = w => w.slice(0, 4);
      const yearBoundaries = [];
      for (let i = 1; i < weeks.length; i++) {
        if (yearOf(weeks[i]) !== yearOf(weeks[i - 1])) {
          yearBoundaries.push({ index: i, year: yearOf(weeks[i]) });
        }
      }

      const dividerX = boundary => x(weeks[boundary.index]) - (x.step() - x.bandwidth()) / 2;

      const yearG = g.append("g").attr("class", "vp-year-markers");

      yearBoundaries.forEach(boundary => {
        const lineX = dividerX(boundary);

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
          .text(boundary.year);
      });

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

      // Line generator (base series)
      const lineGen = d3.line()
        .x(d => xMid(d.week))
        .y(d => y(d.share))
        .curve(d3.curveMonotoneX);

      // --- Base series: one path + dots per party ---
      slicedData.forEach(series => {
        if (hiddenSeries.has(series.party)) return;

        const colour = lookupColour(partyColours, series.party);

        g.append("path")
          .datum(series.values)
          .attr("fill", "none")
          .attr("stroke", colour)
          .attr("stroke-width", 2.5)
          .attr("stroke-linejoin", "round")
          .attr("stroke-linecap", "round")
          .attr("d", lineGen);

        const safeClass = `dot-${series.party.replace(/[^a-zA-Z0-9]/g, "-")}`;

        g.selectAll(`.${safeClass}`)
          .data(series.values)
          .join("circle")
            .attr("cx", d => xMid(d.week))
            .attr("cy", d => y(d.share))
            .attr("r", 2)
            .attr("fill",         colour)
            .on("mouseover", (event, d) => {
              tooltip
                .style("opacity", 1)
                .html(`<strong>${series.party}</strong><br/>${d.week}: ${d.share.toFixed(1)}%`);
            })
            .on("mousemove", event => {
              tooltip
                .style("left", `${event.clientX + 12}px`)
                .style("top",  `${event.clientY + 12}px`);
            })
            .on("mouseout", () => tooltip.style("opacity", 0));
      });

      // --- US pollster-average overlay: dashed mean line + CI ribbon ---
      if (showPollsters && visiblePollsterSeries) {

        const overlayLineGen = d3.line()
          .defined(d => xMid(d.weekKey) !== null)
          .x(d => xMid(d.weekKey))
          .y(d => y(d.mean))
          .curve(d3.curveMonotoneX);

        const overlayAreaGen = d3.area()
          .defined(d => xMid(d.weekKey) !== null)
          .x(d => xMid(d.weekKey))
          .y0(d => y(d.low))
          .y1(d => y(d.high))
          .curve(d3.curveMonotoneX);

        visiblePollsterSeries.forEach(series => {
          const key = `pollster-${series.party}`;
          if (hiddenSeries.has(key)) return;

          const colour = lookupColour(usPartyColours, series.party);

          // CI ribbon
          g.append("path")
            .datum(series.values)
            .attr("fill", colour)
            .attr("opacity", 0.12)
            .attr("d", overlayAreaGen);

          // Dashed mean line
          g.append("path")
            .datum(series.values)
            .attr("fill", "none")
            .attr("stroke", colour)
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "6,4")
            .attr("stroke-linejoin", "round")
            .attr("stroke-linecap", "round")
            .attr("d", overlayLineGen);

          // Hover targets along the mean line
          const safeClass = `pollster-dot-${series.party.replace(/[^a-zA-Z0-9]/g, "-")}`;

          g.selectAll(`.${safeClass}`)
            .data(series.values.filter(d => xMid(d.weekKey) !== null))
            .join("circle")
              .attr("cx", d => xMid(d.weekKey))
              .attr("cy", d => y(d.mean))
              .attr("r", 3)
              .attr("fill", colour)
              .attr("opacity", 0)
              .on("mouseover", (event, d) => {
                tooltip
                  .style("opacity", 1)
                  .html(`<strong>${series.party} (US pollster avg)</strong><br/>${d.weekKey}: ${d.mean.toFixed(1)}%<br/><span style="font-size:11px">CI: ${d.low.toFixed(1)}–${d.high.toFixed(1)}%</span>`);
              })
              .on("mousemove", event => {
                tooltip
                  .style("left", `${event.clientX + 12}px`)
                  .style("top",  `${event.clientY + 12}px`);
              })
              .on("mouseout", () => tooltip.style("opacity", 0));
        });
      }
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

  }, [slicedData, partyColours, showPollsters, visiblePollsterSeries, usPartyColours, hiddenSeries, combinedWeeks]);


  return (
    <div className="VoteLongitudinalUSPollsters">
      <div className="vlup-header-row">
        <h3 className="vlup-title">{t('pollingResults.voteLongitudinal.title')}</h3>

        <label className="vlup-pollster-toggle">
          <input
            type="checkbox"
            checked={showPollsters}
            onChange={e => setShowPollsters(e.target.checked)}
          />
          {t('pollingResults.voteLongitudinal.showPollsterAvg', 'Show US pollster averages')}
        </label>
      </div>

      {showPollsters && pollsterLoading && (
        <p className="vlup-pollster-status">{t('pollingResults.voteLongitudinal.loadingPollsters', 'Loading US pollster averages…')}</p>
      )}
      {showPollsters && pollsterError && (
        <p className="vlup-pollster-status vlup-pollster-status--error">{pollsterError}</p>
      )}

      {chartData && partyColours && rangeIdx ? (
        <>
          <div className="vlup-chart-wrapper" ref={containerRef}>
            <svg ref={svgRef} />
            <div ref={tooltipRef} className="chart-tooltip" />
          </div>

          {/* legend where u can click an item to toggle  series */}
          <div className="vlup-legend">
            {legendItems.map(item => (
              <button
                type="button"
                key={item.key}
                className={`vlup-legend-item${hiddenSeries.has(item.key) ? " vlup-legend-item--hidden" : " vlup-legend-enabled"}`}
                onClick={() => toggleSeries(item.key)}
              >
                <div
                  className={`vlup-legend-swatch${item.dashed ? " vlup-legend-swatch--dashed" : ""}`}
                  style={
                    item.dashed
                      ? {
                          backgroundColor: "transparent",
                          backgroundImage: `repeating-linear-gradient(45deg, ${item.colour}, ${item.colour} 2px, transparent 2px, transparent 4px)`,
                        }
                      : { backgroundColor: item.colour }
                  }
                />
                {item.label}
              </button>
            ))}
          </div>

          {/* Dual-handle range slider */}
          <div className="vlup-slider-wrapper">
            <input
              type="range"
              min={0}
              max={chartData[0].values.length - 1}
              value={rangeIdx[0]}
              onChange={e => {
                const val = Math.min(Number(e.target.value), rangeIdx[1] - 1);
                setRangeIdx([val, rangeIdx[1]]);
              }}
              className="vlup-range vlup-range-left"
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
              className="vlup-range vlup-range-right"
            />
            <div className="vlup-range-background"></div>
          </div>

          <div className="vlup-slider-labels">
            <p>{t('pollingResults.voteLongitudinal.selected')}: <span>{chartData[0].values[rangeIdx[0]]?.week}</span> {t('pollingResults.voteLongitudinal.to')} <span>{chartData[0].values[rangeIdx[1]]?.week}</span></p>
          </div>

          <div className="vlup-export unbounded-weight300">
            <p>Export data within chosen timeframe (if US pollster averages are enabled, this will be downloaded separately):</p>
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

export default VoteLongitudinalUSPollsters;