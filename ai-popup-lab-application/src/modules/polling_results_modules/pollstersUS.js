// d3.js chart which is specifically for the US, showing the averages and intervals of US pollster predictions

import { useRef, useEffect, useState, useMemo } from "react";
import { useTranslation, Trans } from 'react-i18next';
import * as d3 from "d3";
import './pollstersUS.css';
import axios from "axios";
import Loader from '../loader';
// import partyColours from '../../assets/partyColours';

function PollstersUS() {

  const { t } = useTranslation();

  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  const [chartData, setChartData] = useState(null);
  const [error, setError] = useState(null);

  const [partyColours, setPartyColours] = useState(null);
  const [partyColoursError, setPartyColoursError] = useState(null);

  const [rangeIdx, setRangeIdx] = useState(null);

  const parsedData = useMemo(
    () => (typeof chartData === "string" ? JSON.parse(chartData) : chartData),
    [chartData]
  );

  // fetch chart data
  async function getChartData(){
    setChartData(null);
      setError(null);
      axios.get(`${process.env.REACT_APP_API_URL}/api/longitudinal/us_pollster_predictions`, {
        responseType: "text",
      })
        .then(res => setChartData(res.data))
        .catch(err => setError(err.message));
  }

  // fetch party colours
  async function getPartyColours(){
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

    getPartyColours();
    getChartData();

  }, []);

  useEffect(() => {
    if (!parsedData) return;
    setRangeIdx([0, parsedData.time_lookup.length - 1]);
  }, [parsedData]);

  // useEffect(() => {
  //   console.log(chartData)
  // }, [chartData]);

  useEffect(() => {

    if (!parsedData || !partyColours || !rangeIdx) return;

    const drawChart = () => {
      const containerWidth = containerRef.current?.getBoundingClientRect().width;
      if (!containerWidth || containerWidth === 0) return;

      const parsed = typeof chartData === "string" ? JSON.parse(chartData) : chartData;

      const { parties, time_lookup, posterior, observations } = parsed;

      // Apply range slice
      const [r0, r1] = rangeIdx;
      const slicedLookup = time_lookup.slice(r0, r1 + 1);
      const tValues = slicedLookup.map(d => d.t);
      const tSet = new Set(tValues);

      const svgW   = containerWidth;
      const svgH   = 420.69;
      const margin = { top: 30, right: 120, bottom: 70, left: 55 };
      const width  = svgW - margin.left - margin.right;
      const height = svgH - margin.top  - margin.bottom;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      svg.attr("width", svgW).attr("height", svgH);

      const g = svg.append("g")
          .attr("transform", `translate(${margin.left},${margin.top})`);

      // x scale — one band per t value in range
      const x = d3.scaleBand()
          .domain(tValues)
          .range([0, width])
          .padding(0.1);

      const xMid = t => x(t) + x.bandwidth() / 2;

      // y scale — across all mean/low/high and observations in range
      const allY = parties.flatMap(party => {
          const p = posterior[party];
          return tValues.flatMap(t => [p.mean[t - 1], p.low[t - 1], p.high[t - 1]]);
      }).concat(
          observations
          .filter(o => tSet.has(o.t))
          .map(o => o.share)
      );

      const y = d3.scaleLinear()
          .domain([
          Math.max(0,   d3.min(allY) - 0.02),
          Math.min(1,   d3.max(allY) + 0.02),
          ])
          .range([height, 0])
          .nice();

      // Grid
      g.append("g")
          .attr("class", "vp-grid")
          .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(""))
          .select(".domain").remove();

      // X axis — thin out labels
      const labelStride = Math.max(1, Math.ceil(tValues.length / 10));
      const tickVals = tValues.filter((_, i) => i % labelStride === 0);
      const tToLabel = Object.fromEntries(slicedLookup.map(d => [d.t, d.week_label]));

      const xAxis = g.append("g")
          .attr("class", "vp-xaxis")
          .attr("transform", `translate(0,${height})`)
          .call(
          d3.axisBottom(x)
              .tickValues(tickVals)
              .tickSize(0)
              .tickFormat(t => {
              const label = tToLabel[t] ?? "";
              // show just "Mon YYYY" from the start of the range label
              return label.split("–")[0].trim();
              })
          );

      xAxis.select(".domain").remove();
      xAxis.selectAll("text")
          .attr("font-size", "11px")
          .attr("font-weight", "600")
          .attr("fill", "#111")
          .attr("transform", "rotate(-40)")
          .style("text-anchor", "end")
          .attr("dx", "-0.5em")
          .attr("dy", "0.3em");

      // Y axis
      g.append("g")
          .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${(d * 100).toFixed(0)}%`))
          .select(".domain").remove()
          .selection().selectAll("text")
          .attr("font-size", "12px")
          .attr("fill", "#111");

      const tooltip = d3.select(tooltipRef.current);

      const lineGen = d3.line()
          .x(d => xMid(d.t))
          .y(d => y(d.v))
          .curve(d3.curveMonotoneX);

      const areaGen = d3.area()
          .x(d => xMid(d.t))
          .y0(d => y(d.low))
          .y1(d => y(d.high))
          .curve(d3.curveMonotoneX);

      parties.forEach(party => {
          const colourKey = Object.keys(partyColours).find(
            k => k.toLowerCase() === party.toLowerCase()
          );
          const colour = partyColours[colourKey] ?? "#5f5f5f";
          const p = posterior[party];

          // Build arrays for only the t values in range
          const meanData = tValues.map(t => ({ t, v: p.mean[t - 1] }));
          const bandData = tValues.map(t => ({ t, low: p.low[t - 1], high: p.high[t - 1] }));

          // CI ribbon
          g.append("path")
          .datum(bandData)
          .attr("fill", colour)
          .attr("opacity", 0.15)
          .attr("d", areaGen);

          // Mean line
          g.append("path")
          .datum(meanData)
          .attr("fill", "none")
          .attr("stroke", colour)
          .attr("stroke-width", 2.5)
          .attr("stroke-linejoin", "round")
          .attr("stroke-linecap", "round")
          .attr("d", lineGen);

          // Pollster observation dots
          const obsForParty = observations.filter(o => o.party === party && tSet.has(o.t));

          g.selectAll(`.dot-${party}`)
          .data(obsForParty)
          .join("circle")
              .attr("class", `dot-${party}`)
              .attr("cx", d => xMid(d.t))
              .attr("cy", d => y(d.share))
              .attr("r", 3)
              .attr("fill", colour)
              .attr("opacity", 0.25)
              .attr("stroke", "none")
              .on("mouseover", (event, d) => {
              tooltip.style("opacity", 1)
                  .html(`<strong>${d.pollster}</strong><br/>${party}: ${(d.share * 100).toFixed(1)}%<br/><span style="font-size:11px">${tToLabel[d.t] ?? ""}</span>`);
              })
              .on("mousemove", event => {
              tooltip
                  .style("left", `${event.clientX + 12}px`)
                  .style("top",  `${event.clientY + 12}px`);
              })
              .on("mouseout", () => tooltip.style("opacity", 0));

          // End label
          const lastT = tValues.at(-1);
          g.append("text")
          .attr("x", xMid(lastT) + 8)
          .attr("y", y(p.mean[lastT - 1]))
          .attr("dy", "0.35em")
          .attr("font-size", "12px")
          .attr("font-weight", "600")
          .attr("fill", colour)
          .text(party.charAt(0).toUpperCase() + party.slice(1));
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

  }, [parsedData, partyColours, rangeIdx]);


  return (
    <div className="PollstersUS">
      <h3 className="pollus-title">{t('pollingResults.pollstersUS.title')}</h3>
      {chartData && partyColours && rangeIdx ? (
        <>
          <div className="pollus-chart-wrapper" ref={containerRef}>
            <svg ref={svgRef} />
            <div ref={tooltipRef} className="chart-tooltip" />
          </div>

          {/* dual-handle range slider */}
          <div className="pollus-slider-wrapper">
            <input
              type="range"
              min={0}
              max={parsedData ? parsedData.time_lookup.length - 1 : 0}
              value={rangeIdx[0]}
              onChange={e => {
                const val = Math.min(Number(e.target.value), rangeIdx[1] - 1);
                setRangeIdx([val, rangeIdx[1]]);
              }}
              className="pollus-range pollus-range-left"
            />
            <input
              type="range"
              min={0}
              max={parsedData ? parsedData.time_lookup.length - 1 : 0}
              value={rangeIdx[1]}
              onChange={e => {
                const val = Math.max(Number(e.target.value), rangeIdx[0] + 1);
                setRangeIdx([rangeIdx[0], val]);
              }}
              className="pollus-range pollus-range-right"
            />
            <div className="pollus-range-background"></div>
          </div>

          <div className="pollus-slider-labels">
            <p>{t('pollingResults.pollstersUS.selected')}: <span>{parsedData.time_lookup[rangeIdx[0]]?.week_label}</span> {t('pollingResults.pollstersUS.to')} <span>{parsedData.time_lookup[rangeIdx[1]]?.week_label}</span></p>
          </div>
        </>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default PollstersUS;