import { useState, useRef, useEffect } from "react";
import * as d3 from "d3";
import { parliamentChart } from 'd3-parliament-chart';
import './seatVisualisation.css';
import axios from "axios";
import Loader from '../loader';
// import partyColours from '../../assets/partyColours';

// const TOTAL_SEATS = 150;

// D'Hondt proportional seat allocation
function dhondt(votes, totalSeats) {

  const seats = {};
  Object.keys(votes).forEach(p => { seats[p] = 0; });
  for (let i = 0; i < totalSeats; i++) {
    const winner = Object.entries(votes).reduce((best, [party, v]) => {
      const score = v / (seats[party] + 1);
      return score > best.score ? { party, score } : best;
    }, { party: null, score: -1 });
    seats[winner.party]++;
  }
  return seats;
}

function chooseSeatAllocationFunction(method) {
  if(method === 'dhondt'){
    return dhondt;
  } else{
    return dhondt; // cause don't have any other method specified yet
  }
};

function SeatVisualisation({ pollingData, country }) {

  const [total_seats, set_total_seats] = useState(null);
  const [total_seats_error, set_total_seats_error] = useState(null);

  const [partyColours, setPartyColours] = useState(null);
  const [partyColoursError, setPartyColoursError] = useState(null); 

  const [partyInfo, setPartyInfo] = useState(null);
  const [partyInfoError, setPartyInfoError] = useState(null); 

  const [partyInfoAlternative, setPartyInfoAlternative] = useState(null);
  const [partyInfoAlternativeError, setPartyInfoAlternativeError] = useState(null); 

  const [seatAllocationMethod, setSeatAllocationMethod] = useState(null);
  const [seatAllocationMethodError, setSeatAllocationMethodError] = useState(null); 

  const [nextGEcolname, setNextGEcolname] = useState(null);
  const [nextGEcolnameError, setNextGEcolnameError] = useState(null); 

  const svgRef = useRef(null);
  const tooltipRef = useRef(null);

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

  async function getTotalSeats(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/total_seats?country=${countryName}`);
      
      const response_data = response.data;

      const total_seats_data = response_data.total_seats;

      set_total_seats(total_seats_data);
      set_total_seats_error(null);
    } catch (err) {
      set_total_seats_error(err.message);
      set_total_seats(null);
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

  async function getSeatAllocationMethod(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/seat_allocation_method?country=${countryName}`);
      
      const response_data = response.data;

      const seatAllocationMethodData = response_data.seat_allocation_method;

      setSeatAllocationMethod(seatAllocationMethodData);
      setSeatAllocationMethodError(null);
    } catch (err) {
      setSeatAllocationMethodError(err.message);
      setSeatAllocationMethod(null);
    }
  };

  useEffect(() => {
    set_total_seats(null);
    setPartyColours(null);
    setSeatAllocationMethod(null);
    setNextGEcolname(null);
    setPartyInfo(null);
    setPartyInfoAlternative(null);

    getTotalSeats(country);
    getPartyColours(country);
    getSeatAllocationMethod(country);
    getNextGEcolname(country);
    getPartyInfo(country);

  }, [country]);

  useEffect(() => {
    if (!pollingData || pollingData.length === 0 || !svgRef.current) return;
    if (!total_seats || !partyColours || !seatAllocationMethod) return;

    let isTablet = false;
    let isMobile = false;
    let isSmallMobile = false;

    let seatRadiusMultiplier = 1;

    if(country==="sweden"){seatRadiusMultiplier = 0.7};

    if (window.innerWidth <= 390) {
      isSmallMobile = true;
    } else if (window.innerWidth <= 545) {
      isMobile = true;
    } else if (window.innerWidth <= 930) {
      isTablet = true;
    }

    const seatAllocationFunction = chooseSeatAllocationFunction(seatAllocationMethod);

    const renderChart = () => {
      const voteCounts = {};

      pollingData.forEach((row) => {
        if (row[nextGEcolname] && row[nextGEcolname] !== "Did not vote") {
          voteCounts[row[nextGEcolname]] = (voteCounts[row[nextGEcolname]] || 0) + 1;
        }
      });

      if (Object.keys(voteCounts).length === 0) return;

      const seatsByParty = seatAllocationFunction(voteCounts, total_seats);

      const SPECTRUM = Object.keys(partyColours); 

      const aggregated = Object.entries(seatsByParty)
        .filter(([, seats]) => seats > 0)
        .sort((a, b) => {
          const ai = SPECTRUM.indexOf(a[0]);
          const bi = SPECTRUM.indexOf(b[0]);
          return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
        })
        .map(([party, seats]) => ({
          seats,
          color: partyColours[party] || "#aaa",
          party,
        }));

      let svgW = 760;
      let seatRadius = 11;

      if (isSmallMobile) {
        svgW = 300;
        seatRadius = 4;
      } else if (isMobile) {
        svgW = 320;
        seatRadius = 5;
      } else if (isTablet) {
        svgW = 570;
        seatRadius = 9;
      }
      
      const rowHeight = window.innerWidth <= 930 ? 30 : 35;

      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();

      const g = svg.append("g").attr("transform", "translate(0, 10)");
      const tooltip = d3.select(tooltipRef.current);

      const pc = parliamentChart()
        .width(svgW)
        .aggregatedData(aggregated)
        .sections(1)
        .sectionGap(44)
        .seatRadius(seatRadius * seatRadiusMultiplier)
        .rowHeight(rowHeight);

      g.call(pc);

      // Measure the actual rendered parliament so the SVG is never too short
      const chartBox = g.node().getBBox();
      const chartBottom = chartBox.y + chartBox.height;


      // Tooltips
      g.selectAll("circle")
        .on("mouseover", function (event) {
          const d = d3.select(this).datum();
          const entry = aggregated.find((a) => a.color === d.color);
          if (!entry) return;

          tooltip
            .style("opacity", 1)
            .html(
              `<strong>${entry.party}</strong><br/>${seatsByParty[entry.party]} seats`
            );
        })
        .on("mousemove", function (event) {
          tooltip
            .style("left", `${event.pageX + 12}px`)
            .style("top", `${event.pageY - 36}px`);
        })
        .on("mouseout", function () {
          tooltip.style("opacity", 0);
        });

      // Legend
      const legendData = Object.entries(seatsByParty)
        .filter(([, seats]) => seats > 0)
        .sort((a, b) => b[1] - a[1]);

      const tempText = svg.append("text").attr("font-size", "12px");

      // for dynamically measuring how much the width of legend labels shuld be
      const maxLabelWidth = d3.max(legendData, ([party, seats]) => {
        tempText.text(`${party} — ${seats}`);
        return tempText.node().getComputedTextLength();
      }) ?? 120;;
      tempText.remove();

      const colW = maxLabelWidth + 30; // 30 for swatch, gap and padding
      // const colW = window.innerWidth <= 930 ? 120 : 145;

      const rowH = 22;
      const maxLegendWidth = svgW - 60;
      const columns = Math.max(1, Math.floor(maxLegendWidth / colW));
      const perCol = Math.ceil(legendData.length / columns);
      const legendY = chartBottom + 30;

      const legendG = svg
        .append("g")
        .attr("transform", `translate(30, ${legendY})`);

      legendData.forEach(([party, seats], i) => {
        const col = Math.floor(i / perCol);
        const row = i % perCol;

        legendG
          .append("rect")
          .attr("x", col * colW)
          .attr("y", row * rowH)
          .attr("width", 13)
          .attr("height", 13)
          .attr("rx", 0)
          .attr("fill", partyColours[party] || "#aaa");

        legendG
          .append("text")
          .attr("x", col * colW + 18)
          .attr("y", row * rowH + 11)
          .attr("font-size", "12px")
          .attr("fill", "#333")
          .text(`${party} — ${seats}`);
      });

      const legendHeight = perCol * rowH;
      const totalHeight = legendY + legendHeight + 20;

      svg
        .attr("viewBox", `0 0 ${svgW} ${totalHeight}`)
        .attr("width", "100%")
        .attr("height", totalHeight);
    };

    renderChart();
    window.addEventListener("resize", renderChart);

    return () => {
      window.removeEventListener("resize", renderChart);
    };
  }, [pollingData, total_seats, partyColours, seatAllocationMethod]);

  return (
    <div className="SeatVisualisation">
      <h3>Seat Projection</h3>
      {total_seats && partyColours && seatAllocationMethod && nextGEcolname ? (
        <div className="sv-chart-wrapper">
          <svg ref={svgRef} />
          <div ref={tooltipRef} className="chart-tooltip" />
        </div>
      ) : (
        <Loader />
      )}
    </div>
    
  );
}


export default SeatVisualisation;
