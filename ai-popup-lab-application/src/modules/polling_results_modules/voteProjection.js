// d3.js bar chart which shows the total vote distribution
// fetches party info, party colours and name of next general election prediction column because it should not be on the bar chart

import { useRef, useEffect, useState } from "react";
import { useTranslation, Trans } from 'react-i18next';
import * as d3 from "d3";
import './voteProjection.css';
import axios from "axios";
import Loader from '../loader';
// import partyColours from '../../assets/partyColours';

function VoteProjection({ pollingData, country }) {

  const { t } = useTranslation();

  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  const [nextGEcolname, setNextGEcolname] = useState(null);
  const [nextGEcolnameError, setNextGEcolnameError] = useState(null); 

  const total = pollingData?.length || 0;
  const didNotVote = (nextGEcolname && pollingData)
  ? pollingData.filter(r => r[nextGEcolname] === "Did not vote").length
  : 0;
  const voted = total - didNotVote;
  const turnoutPct = total > 0 ? ((voted / total) * 100).toFixed(1) : 0;

  const [partyColours, setPartyColours] = useState(null);
  const [partyColoursError, setPartyColoursError] = useState(null); 

  const [partyInfo, setPartyInfo] = useState(null);
  const [partyInfoError, setPartyInfoError] = useState(null); 

  const [partyInfoAlternative, setPartyInfoAlternative] = useState(null);
  const [partyInfoAlternativeError, setPartyInfoAlternativeError] = useState(null); 

  async function getNextGEcolname(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/nextGE_col_name?country=${countryName}`);
      
      const response_data = response.data;

      const next_GE_colname = response_data.column_to_rename;

      setNextGEcolname(next_GE_colname);
      setNextGEcolnameError(null);
    } catch (err) {
      setNextGEcolnameError(err.message);
      setNextGEcolname(null);
    }
  };

  async function getPartyColours(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/party_colours?country=${countryName}`);
      
      const response_data = response.data;

      const partyColoursData = response_data.party_colours;

      setPartyColours(partyColoursData);
      setPartyColoursError(null);
    } catch (err) {
      setPartyColoursError(err.message);
      setPartyColours(null);
    }
  };

  async function getPartyInfo(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/party_info?country=${countryName}`);
      
      const response_data = response.data;

      const partyInfoData = response_data.data;
      const partyInfoAlternativeData = response_data.alternative_data;

      setPartyInfo(partyInfoData);
      setPartyInfoAlternative(partyInfoAlternativeData);
      setPartyInfoError(null);
    } catch (err) {
      setPartyInfo(null);
      setPartyInfoAlternative(null);
      setPartyInfoError(err);
    }
  };

  // useEffect(() => {
  //   console.log("Party info and alternative format (outputted from voteprojection.js)")
  //   console.log(partyInfo);
  //   console.log(partyInfoAlternative);
  // }, [partyInfo])

  useEffect(() => {

    setPartyColours(null);
    setNextGEcolname(null);
    setPartyInfo(null);
    setPartyInfoAlternative(null);

    getPartyColours(country);
    getNextGEcolname(country);
    getPartyInfo(country);

  }, [country]);

  useEffect(() => {
    if (!pollingData || pollingData.length === 0) return;
    if (!partyColours) return;
    if (!nextGEcolname) return;
    if (!containerRef.current) return;

    const drawChart = () => {

      // console.log(pollingData)

      // console.log("drawing chart with:", {
      //   country,
      //   nextGEcolname,
      //   partyColourKeys: Object.keys(partyColours),
      //   sampleVotes: [...new Set(pollingData.map(r => r[nextGEcolname]))]
      // });
      
      const containerWidth = containerRef.current?.getBoundingClientRect().width;
      if (!containerWidth || containerWidth === 0) return;

      const svgW = containerWidth;

      const voteCounts = {};
      pollingData.forEach(row => {
        if (row[nextGEcolname] !== "Did not vote") {
          voteCounts[row[nextGEcolname]] = (voteCounts[row[nextGEcolname]] || 0) + 1;
        }
      });

      const chartData = Object.entries(voteCounts)
        .map(([party, count]) => ({ party, pct: (count / voted) * 100 }))
        .sort((a, b) => b.pct - a.pct);

      const margin = { top: 30, right: 20, bottom: 80, left: 50 };
      const width = svgW - margin.left - margin.right;
      const height = 340 - margin.top - margin.bottom;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      svg
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom);

      const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

      const x = d3.scaleBand().domain(chartData.map(d => d.party)).range([0, width]).padding(0.25);
      const y = d3.scaleLinear().domain([0, d3.max(chartData, d => d.pct)]).range([height, 0]).nice();

      // Grid lines
      g.append("g")
        .attr("class", "vp-grid")
        .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(""))
        .select(".domain").remove();

      // X axis
      const xAxis = g.append("g")
        .attr("class", "vp-xaxis")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x).tickSize(0));

      xAxis.select(".domain").remove();

      xAxis.selectAll("text")
        .attr("font-size", "13px")
        .attr("font-weight", "700")
        .attr("fill", "#111")
        .attr("transform", "rotate(-45)")
        .style("text-anchor", "end")
        .attr("dx", "-0.6em")
        .attr("dy", "0.15em");

      // BELOW CODE WAS FOR CHANGING X AXIS LABEL IF DEVICE WAS SMALLER, BUT DECIDED TO ALWAYS TO SO AS LONGER NAMES OF DANISH PARTIES MADE ME RETHINK

      //  if(isMobile || isSmallMobile){
      //   const xAxis = g.append("g")
      //     .attr("transform", `translate(0,${height})`)
      //     .call(d3.axisBottom(x).tickSize(0));

      //   xAxis.select(".domain").remove();

      //   xAxis.selectAll("text")
      //     .attr("font-size", "13px")
      //     .attr("font-weight", "700")
      //     .attr("fill", "#111")
      //     .attr("transform", "rotate(-45)")
      //     .style("text-anchor", "end")
      //     .attr("dx", "-0.6em")
      //     .attr("dy", "0.15em");

      // } else{
      //   g.append("g")
      //   .attr("transform", `translate(0,${height})`)
      //   .call(d3.axisBottom(x).tickSize(0))
      //   .select(".domain").remove()
      //   .selection().selectAll("text")
      //   .attr("font-size", "13px")
      //   .attr("font-weight", "700")
      //   .attr("fill", "#111");
      // }

      // Y axis
      g.append("g")
        .call(d3.axisLeft(y).tickFormat(d => `${d.toFixed(0)}%`).ticks(5))
        .select(".domain").remove();

      const tooltip = d3.select(tooltipRef.current);

      // Bars
      g.selectAll(".bar")
        .data(chartData)
        .join("rect")
        .attr("class", "bar")
        .attr("x", d => x(d.party))
        .attr("width", x.bandwidth())
        .attr("y", height)
        .attr("height", 0)
        .attr("rx", 0)
        .attr("fill", d => partyColours[d.party] || "#aaa")
        .on("mouseover", (event, d) => {
          tooltip.style("opacity", 1)
            .html(`<strong>${d.party}</strong><br/>${d.pct.toFixed(1)}% of votes cast`);
        })
        .on("mousemove", event => {
          tooltip.style("left", `${event.pageX + 12}px`).style("top", `${event.pageY - 36}px`);
        })
        .on("mouseout", () => tooltip.style("opacity", 0))
        .transition().duration(800).ease(d3.easeCubicOut)
        .attr("y", d => y(d.pct))
        .attr("height", d => height - y(d.pct));

      // Value labels above bars
      g.selectAll(".vp-label")
        .data(chartData)
        .join("text")
        .attr("class", "vp-label")
        .attr("x", d => x(d.party) + x.bandwidth() / 2)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("fill", "#111")
        .attr("font-weight", "600")
        .attr("opacity", 0)
        .attr("y", d => y(d.pct) - 5)
        .text(d => `${d.pct.toFixed(1)}%`)
        .transition().delay(800).duration(200)
        .attr("opacity", 1);
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

    observer.observe(containerRef.current);
    return () => observer.disconnect();

  }, [pollingData, partyColours, nextGEcolname]);

  return (
    <div className="VoteProjection">
      <h3 className="vp-title">{t('pollingResults.voteProjection.title')}</h3>
      {partyColours && nextGEcolname ? (
        <>
          <p className="vp-subtitle">
            <Trans
              i18nKey="pollingResults.voteProjection.subtitle"
              values={{ turnoutPct, voted, total }}
              components={{ strong: <strong /> }}
            />
          </p>
          <div className="vp-chart-wrapper" ref={containerRef}>
            <svg ref={svgRef} />
            <div ref={tooltipRef} className="chart-tooltip" />
          </div>
        </>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default VoteProjection;
