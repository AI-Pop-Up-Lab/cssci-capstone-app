import { useRef, useEffect, useState } from "react";
import * as d3 from "d3";
import './demographicCharts.css';
import axios from "axios";
// import partyColours from '../../assets/partyColours';
import DemographicChooser from './demographicChooser';
import Loader from '../loader';


function DemographicCharts({ pollingData, country }) {
  const svgRef = useRef();
  const tooltipRef = useRef();
  const [chosenDemographic, setChosenDemographic] = useState(null);

  const [partyColours, setPartyColours] = useState(null);
  const [partyColoursError, setPartyColoursError] = useState(null); 

  const [nextGEcolname, setNextGEcolname] = useState(null);
  const [nextGEcolnameError, setNextGEcolnameError] = useState(null); 

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

  useEffect(() => {

    setPartyColours(null);
    setNextGEcolname(null);

    getPartyColours(country);
    getNextGEcolname(country);

  }, [country]);

  useEffect(() => {
    if (!pollingData || pollingData.length === 0) return;
    if (!partyColours) return;

    let isTablet = false;
    let isMobile = false;
    let isSmallMobile = false;

    if (window.innerWidth <= 390) {
      isSmallMobile = true;
    } else if (window.innerWidth <= 545) {
      isMobile = true;
    } else if (window.innerWidth <= 930) {
      isTablet = true;
    }


    // Filter rows based on chosen demographic values (skip "all")
    const filtered = chosenDemographic
      ? pollingData.filter(row =>
          Object.entries(chosenDemographic).every(([col, val]) =>
            val === "all" || row[col] === val
          )
        )
      : pollingData;

    if (filtered.length === 0) return;

    const voteCounts = {};
    filtered.forEach(row => {
      if (row[nextGEcolname] !== "Did not vote") {
        voteCounts[row[nextGEcolname]] = (voteCounts[row[nextGEcolname]] || 0) + 1;
      }
    });

    const voters = filtered.filter(r => r[nextGEcolname] !== "Did not vote").length;
    if (voters === 0) return;
    const chartData = Object.entries(voteCounts)
      .map(([party, count]) => ({ party, pct: (count / voters) * 100 }))
      .sort((a, b) => b.pct - a.pct);

      
    let svgW = 820

    if(isSmallMobile){
      svgW = 310;
    } else if(isMobile){
      svgW = 370;
    } else if(isTablet){
      svgW = 570;
    };

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
      .attr("class", "dc-grid")
      .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(""))
      .select(".domain").remove();

    // X axis
    const xAxis = g.append("g")
      .attr("class", "dc-xaxis")
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

    // if(isMobile || isSmallMobile){
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
      .data(chartData, d => d.party)
      .join(
        enter => enter.append("rect")
          .attr("class", "bar")
          .attr("x", d => x(d.party))
          .attr("width", x.bandwidth())
          .attr("y", height)
          .attr("height", 0)
          .attr("rx", 0)
          .attr("fill", d => partyColours[d.party] || "#aaa"),
        update => update,
        exit => exit.transition().duration(300).attr("height", 0).attr("y", height).remove()
      )
      .on("mouseover", (event, d) => {
        tooltip.style("opacity", 1)
          .html(`<strong>${d.party}</strong><br/>${d.pct.toFixed(1)}% of votes (${Math.round(d.pct * voters / 100)} of ${voters} voters)`);
      })
      .on("mousemove", event => {
        tooltip.style("left", `${event.pageX + 12}px`).style("top", `${event.pageY - 36}px`);
      })
      .on("mouseout", () => tooltip.style("opacity", 0))
      .transition().duration(600).ease(d3.easeCubicOut)
      .attr("x", d => x(d.party))
      .attr("width", x.bandwidth())
      .attr("y", d => y(d.pct))
      .attr("height", d => height - y(d.pct));

    g.selectAll(".dc-label")
      .data(chartData)
      .join("text")
      .attr("class", "dc-label")
      .attr("x", d => x(d.party) + x.bandwidth() / 2)
      .attr("text-anchor", "middle")
      .attr("font-size", "12px")
      .attr("fill", "#111")
      .attr("font-weight", "600")
      .attr("opacity", 0)
      .attr("y", d => y(d.pct) - 5)
      .text(d => `${d.pct.toFixed(1)}%`)
      .transition().delay(600).duration(200)
      .attr("opacity", 1);

  }, [pollingData, chosenDemographic, partyColours]);

  return (
    <div className="DemographicCharts">
      <h3 className="dc-title">Vote by Demographic</h3>
      {country && (
        <DemographicChooser
          setChosenDemographic={setChosenDemographic}
          country={country}
        />
      )}
      {partyColours && nextGEcolname ? (
      <div className="dc-chart-wrapper">
        <svg ref={svgRef} />
        <div ref={tooltipRef} className="chart-tooltip" />
      </div>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default DemographicCharts;