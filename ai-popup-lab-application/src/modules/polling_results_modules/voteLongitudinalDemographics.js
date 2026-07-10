// d3.js chart which ____

import { useRef, useEffect, useState } from "react";
import { useTranslation, Trans } from 'react-i18next';
import * as d3 from "d3";
import './voteLongitudinalDemographics.css';
import axios from "axios";
import Loader from '../loader';
import { parseDemographicCsv, aggregateToSeries } from "../../utils/longitudinal_transformation";
// import partyColours from '../../assets/partyColours';

function VoteLongitudinalDemographics({ country }) {

  const { t } = useTranslation();

  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  const [partyColours, setPartyColours] = useState(null);
  const [partyColoursError, setPartyColoursError] = useState(null); 

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

    setRawRows(null);
    setPartyColours(null);
    setRangeIdx(null);

    getPartyColours(country);
    getChartData(country);

  }, [country]);

  useEffect(() => {
    if (!rawRows) return;
    const series = aggregateToSeries(rawRows, {});
    setRangeIdx([0, chartData[0].values.length - 1]);
  }, [rawRows]);

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

      // x — band scale, one slot per week; use bandwidth() midpoint for line/dot x position
      const x = d3.scaleBand()
        .domain(weeks)
        .range([0, width])
        .padding(0.2);

      const xMid = week => x(week) + x.bandwidth() / 2;

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
      // Find every week index where the year changes from the previous week
      // (e.g. "...-W52"/"...-W53" -> "...-W01") and draw a vertical divider
      // there, labelled with the new year, so multi-year trends are easy to
      // read at a glance.
      const yearOf = w => w.slice(0, 4);
      const yearBoundaries = [];
      for (let i = 1; i < weeks.length; i++) {
        if (yearOf(weeks[i]) !== yearOf(weeks[i - 1])) {
          yearBoundaries.push({ index: i, year: yearOf(weeks[i]) });
        }
      }

      // Place the divider in the gap immediately before the boundary week's band,
      // i.e. halfway between the end of last year's last band and the start of
      // this year's first band.
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

      // Line generator
      const lineGen = d3.line()
        .x(d => xMid(d.week))
        .y(d => y(d.share))
        .curve(d3.curveMonotoneX);

      // One path + dots + end label per party
      slicedData.forEach(series => {
        const colour = partyColours[series.party] ?? "#888";

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
                .html(`<strong>${series.party}</strong><br/>${d.week}: ${d.share.toFixed(1)}%`);
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
      {chartData && partyColours && rangeIdx ? (
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
            <p>{t('pollingResults.voteLongitudinalDemographic.selected')}: <span>{chartData[0].values[rangeIdx[0]]?.week}</span> {t('pollingResults.voteLongitudinalDemographic.to')} <span>{chartData[0].values[rangeIdx[1]]?.week}</span></p>
          </div>
        </>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default VoteLongitudinalDemographics;