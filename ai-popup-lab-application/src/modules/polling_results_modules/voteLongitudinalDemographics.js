// d3.js chart which ____

import { useRef, useEffect, useState } from "react";
import { useTranslation, Trans } from 'react-i18next';
import * as d3 from "d3";
import './voteLongitudinalDemographics.css';
import axios from "axios";
import Loader from '../loader';
import { parseDemographicCsv, aggregateToSeries, lookupColour, formatWeekDate, isoWeekToMonday } from "../../utils/longitudinal_transformation";
// import partyColours from '../../assets/partyColours';

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
  const [error, setError] = useState(null);

  const demographicKeys = ["gender", "age_group", "education_level", "state", "race"];
  const chartData = rawRows ? aggregateToSeries(rawRows, filters) : null;
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
    const series = aggregateToSeries(rawRows, {});
    setRangeIdx([0, chartData[0].values.length - 1]);
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

  useEffect(() => {

    if (!slicedData || !slicedData[0]?.values.length || !partyColours) return; 

    const drawChart = () => {
      const containerWidth = containerRef.current?.getBoundingClientRect().width;
      if (!containerWidth || containerWidth === 0) return;

      const svgW   = containerWidth;
      const svgH   = 340;

      const margin = { top: 30, right: 180, bottom: 50, left: 50 };
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

      // x — time scale. Each week is placed at its Monday, so a gap of N weeks
      // between data points takes up N weeks' worth of horizontal space.
      const DAY = 86400000;
      const dates = weeks.map(isoWeekToMonday).filter(Boolean);
      const minDate = d3.min(dates);
      const maxDate = d3.max(dates);
      const x = d3.scaleUtc()
        .domain([new Date(minDate.getTime() - 3 * DAY), new Date(maxDate.getTime() + 3 * DAY)])
        .range([0, width]);

      const xMid = week => {
        const d = isoWeekToMonday(week);
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

      // X axis ticks: one label every `stride` weeks, always starting at the
      // first week of data and always landing on a Monday (the same dates the
      // data points sit on). Full dd/mm/yyyy labels are ~85px wide, so size the
      // stride to the chart width.
      const maxTicks = Math.max(2, Math.floor(width / 95));
      const spanWeeks = Math.round((maxDate - minDate) / (7 * DAY));
      const stride = Math.max(1, Math.ceil(spanWeeks / (maxTicks - 1)));
      const tickValues = [];
      for (let t = minDate.getTime(); t <= maxDate.getTime(); t += stride * 7 * DAY) {
        tickValues.push(new Date(t));
      }

      // X axis
      const xAxis = g.append("g")
        .attr("class", "vp-xaxis")
        .attr("transform", `translate(0,${height})`)
        .call(
          d3.axisBottom(x)
            .tickValues(tickValues)
            .tickSize(0)
            .tickFormat(d3.utcFormat("%d/%m/%Y"))
        );

      xAxis.select(".domain").remove();
      xAxis.selectAll("text")
        .attr("font-size", "13px")
        .attr("font-weight", "700")
        .attr("fill", "#111")
        .attr("dy", "1.2em");

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

      // Line generator
      const lineGen = d3.line()
        .x(d => xMid(d.week))
        .y(d => y(d.share))
        .curve(d3.curveMonotoneX);

      // One path + dots + end label per party
      slicedData.forEach(series => {
        const colour = lookupColour(partyColours, series.party);

        // Line
        g.append("path")
          .datum(series.values)
          .attr("fill", "none")
          .attr("stroke", colour)
          .attr("stroke-width", 2.5)
          .attr("stroke-linejoin", "round")
          .attr("stroke-linecap", "round")
          .attr("d", lineGen);

        // Dots
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
                .html(`<strong>${series.party}</strong><br/>${formatWeekDate(d.week)}: ${d.share.toFixed(1)}%`);
            })
            .on("mousemove", event => {
              tooltip
                .style("left", `${event.clientX + 12}px`)
                .style("top",  `${event.clientY + 12}px`);
            })
            .on("mouseout", () => tooltip.style("opacity", 0));

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
      <h3 className="vld-title">{t('pollingResults.voteLongitudinalDemographic.title')}</h3>
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
        </>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default VoteLongitudinalDemographics;