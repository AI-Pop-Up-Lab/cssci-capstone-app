// d3.js bar chart of the MOST RECENT week's national vote share, amongst likely
// voters: bar height = weekly MRP median, whiskers = 95% interval. Shown on the
// landing page. The latest week is determined by the backend (highest ISO week
// in the national summary aggregate), so nothing here needs updating weekly.

import { useRef, useEffect, useState, useMemo } from "react";
import { useTranslation } from 'react-i18next';
import * as d3 from "d3";
import axios from "axios";
import './latestNationalSummary.css';
import Loader from '../loader';
import { parseNationalSummaryCsv, lookupColour, formatWeekRange } from "../../utils/longitudinal_transformation";

// Same non-voter matching as VoteLongitudinalUSPollsters.
const NON_VOTER_LABEL_RE = /^(did not vote|will not vote|non-?voters?)$/i;
const isNonVoterSeries = party => NON_VOTER_LABEL_RE.test((party ?? "").trim());

// Fixed left-to-right order so bars don't swap places when two parties trade
// the lead; any party not listed goes after these, in data order.
const PARTY_ORDER = ["democrat", "republican", "other"];
const partyRank = party => {
  const i = PARTY_ORDER.indexOf(String(party).trim().toLowerCase());
  return i === -1 ? PARTY_ORDER.length : i;
};

function LatestNationalSummary({ country, countryData }) {

  const { t } = useTranslation();

  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  const [series, setSeries] = useState(null);   // parseNationalSummaryCsv output (one week)
  const [status, setStatus] = useState("loading"); // loading | ready | unavailable

  const partyColours = countryData?.party_colours ?? null;

  // fetch the latest week whenever the country changes
  useEffect(() => {
    let cancelled = false;
    setSeries(null);
    setStatus("loading");

    axios.get(`${process.env.REACT_APP_API_URL}/api/longitudinal/country_latest_national_summary?country=${country}`, {
      responseType: "text",
    })
      .then(res => {
        if (cancelled) return;
        const parsed = parseNationalSummaryCsv(res.data);
        if (!parsed.length) { setStatus("unavailable"); return; }
        setSeries(parsed);
        setStatus("ready");
      })
      .catch(() => { if (!cancelled) setStatus("unavailable"); });

    return () => { cancelled = true; };
  }, [country]);

  // Likely-voters view: drop the non-voter series and rescale the rest so the
  // medians sum to 100%. The same factor is applied to the interval bounds
  // (an approximation: it carries no uncertainty about turnout itself).
  const { week, bars } = useMemo(() => {
    if (!series) return { week: null, bars: null };

    const voters = series
      .filter(s => !isNonVoterSeries(s.party))
      .map(s => ({ party: s.party, v: s.values[s.values.length - 1] })) // one week only
      .filter(d => d.v);
    if (!voters.length) return { week: null, bars: null };

    const total = d3.sum(voters, d => d.v.share);
    const scale = total > 0 ? 100 / total : 0;

    const bars = voters
      .map(({ party, v }) => ({
        party,
        share: v.share * scale,
        low:   v.low  * scale,
        high:  v.high * scale,
      }))
      .sort((a, b) => partyRank(a.party) - partyRank(b.party));

    return { week: voters[0].v.week, bars };
  }, [series]);

  useEffect(() => {
    if (!bars || !partyColours) return;

    let lastWidth = 0;

    const drawChart = () => {
      const containerWidth = containerRef.current?.getBoundingClientRect().width;
      if (!containerWidth) return;
      lastWidth = containerWidth;

      const margin = { top: 34, right: 16, bottom: 62, left: 48 };
      const PLOT_H = 260;
      const svgW = containerWidth;
      const svgH = margin.top + PLOT_H + margin.bottom;
      const width = svgW - margin.left - margin.right;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      svg.attr("width", svgW).attr("height", svgH);

      const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

      const x = d3.scaleBand()
        .domain(bars.map(d => d.party))
        .range([0, width])
        .padding(0.35);

      const maxHigh = d3.max(bars, d => Number.isFinite(d.high) ? d.high : d.share);
      const y = d3.scaleLinear()
        .domain([0, Math.min(100, maxHigh + 6)])
        .range([PLOT_H, 0])
        .nice();

      // grid + y axis
      g.append("g")
        .attr("class", "lns-grid")
        .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(""))
        .select(".domain").remove();

      const yAxis = g.append("g")
        .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d.toFixed(0)}%`));
      yAxis.select(".domain").remove();
      yAxis.selectAll("text")
        .attr("font-size", "13px")
        .attr("fill", "#111");

      const tooltip = d3.select(tooltipRef.current);
      const hasCI = d => Number.isFinite(d.low) && Number.isFinite(d.high);

      const showTip = (event, d) => {
        const ci = hasCI(d) ? `<br/><span style="font-size:11px">95% interval: ${d.low.toFixed(1)}–${d.high.toFixed(1)}%</span>` : "";
        tooltip
          .style("opacity", 1)
          .html(`<strong>${d.party}</strong><br/>${d.share.toFixed(1)}%${ci}`);
      };
      const moveTip = event => tooltip
        .style("left", `${event.clientX + 12}px`)
        .style("top",  `${event.clientY + 12}px`);
      const hideTip = () => tooltip.style("opacity", 0);

      // bars
      g.selectAll(".lns-bar")
        .data(bars)
        .join("rect")
          .attr("class", "lns-bar")
          .attr("x", d => x(d.party))
          .attr("y", d => y(d.share))
          .attr("width", x.bandwidth())
          .attr("height", d => PLOT_H - y(d.share))
          .attr("rx", 3)
          .attr("fill", d => lookupColour(partyColours, d.party))
          .on("mouseover", showTip)
          .on("mousemove", moveTip)
          .on("mouseout", hideTip);

      // 95% interval whiskers (white halo underneath so they read on any bar colour)
      const capHalf = Math.min(14, x.bandwidth() * 0.22);
      const whiskers = g.selectAll(".lns-whisker")
        .data(bars.filter(hasCI))
        .join("g")
          .attr("class", "lns-whisker")
          .attr("transform", d => `translate(${x(d.party) + x.bandwidth() / 2},0)`)
          .on("mouseover", showTip)
          .on("mousemove", moveTip)
          .on("mouseout", hideTip);

      const drawWhisker = (stroke, strokeWidth) => {
        whiskers.append("path")
          .attr("fill", "none")
          .attr("stroke", stroke)
          .attr("stroke-width", strokeWidth)
          .attr("stroke-linecap", "round")
          .attr("d", d => `M0,${y(d.low)}V${y(d.high)}M${-capHalf},${y(d.low)}H${capHalf}M${-capHalf},${y(d.high)}H${capHalf}`);
      };
      drawWhisker("#fff", 5);
      drawWhisker("#111", 2);

      // value labels above the upper whisker (or the bar if there is no interval)
      g.selectAll(".lns-value")
        .data(bars)
        .join("text")
          .attr("class", "lns-value")
          .attr("x", d => x(d.party) + x.bandwidth() / 2)
          .attr("y", d => y(hasCI(d) ? d.high : d.share) - 9)
          .attr("text-anchor", "middle")
          .attr("font-size", "15px")
          .attr("font-weight", "700")
          .attr("fill", "#111")
          .text(d => `${d.share.toFixed(1)}%`);

      // x axis: party name, with the interval underneath so it is readable without hovering
      const labels = g.selectAll(".lns-label")
        .data(bars)
        .join("text")
          .attr("class", "lns-label")
          .attr("x", d => x(d.party) + x.bandwidth() / 2)
          .attr("y", PLOT_H + 22)
          .attr("text-anchor", "middle")
          .attr("fill", "#111");

      labels.append("tspan")
        .attr("font-size", "14px")
        .attr("font-weight", "700")
        .text(d => d.party);

      labels.append("tspan")
        .attr("x", d => x(d.party) + x.bandwidth() / 2)
        .attr("dy", "1.4em")
        .attr("font-size", "11px")
        .attr("fill", "#555")
        .text(d => hasCI(d) ? `${d.low.toFixed(1)}–${d.high.toFixed(1)}%` : "");

      // baseline
      g.append("line")
        .attr("x1", 0).attr("x2", width)
        .attr("y1", PLOT_H).attr("y2", PLOT_H)
        .attr("stroke", "#111").attr("stroke-width", 1.5);
    };

    drawChart();

    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        // only redraw on width changes (drawing changes the height, which would loop)
        if (entry.contentRect.width > 0 && Math.abs(entry.contentRect.width - lastWidth) > 1) {
          clearTimeout(observer._debounce);
          observer._debounce = setTimeout(drawChart, 100);
        }
      }
    });

    if (!containerRef.current) return;
    observer.observe(containerRef.current);
    return () => { clearTimeout(observer._debounce); observer.disconnect(); };

  }, [bars, partyColours]);

  // ---- render ----
  if (status === "unavailable") {
    return (
      <div className="LatestNationalSummary">
        <p className="lns-status">
          {t('landingPage.latestResults.unavailable', 'Latest polling results are not available yet.')}
        </p>
      </div>
    );
  }

  if (status === "loading" || !bars || !partyColours) {
    return (
      <div className="LatestNationalSummary">
        <Loader />
      </div>
    );
  }

  return (
    <div className="LatestNationalSummary">
      <h3 className="lns-title">{t('landingPage.latestResults.title', 'Latest polling result')}</h3>
      <p className="lns-period">
        {t('landingPage.latestResults.period', 'Polling period')}: <span>{formatWeekRange(week)}</span>
      </p>

      <div className="lns-chart-wrapper" ref={containerRef}>
        <svg ref={svgRef} />
        <div ref={tooltipRef} className="lns-tooltip" />
      </div>

      <p className="lns-footnote">
        {t('landingPage.latestResults.footnote', 'Bars show the weekly median vote share amongst likely voters; whiskers show the 95% interval.')}
      </p>
    </div>
  );
}

export default LatestNationalSummary;
