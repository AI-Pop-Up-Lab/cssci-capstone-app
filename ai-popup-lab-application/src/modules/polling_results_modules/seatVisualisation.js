import { useState, useRef, useEffect } from "react";
import * as d3 from "d3";
import { parliamentChart } from 'd3-parliament-chart';
import './seatVisualisation.css';
import axios from "axios";
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

  const [seatAllocationMethod, setSeatAllocationMethod] = useState(null);
  const [seatAllocationMethodError, setSeatAllocationMethodError] = useState(null); 

  const svgRef = useRef(null);
  const tooltipRef = useRef(null);

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

    getTotalSeats(country);
    getPartyColours(country);
    getSeatAllocationMethod(country);

  }, [country]);

  useEffect(() => {
    if (!pollingData || pollingData.length === 0 || !svgRef.current) return;
    if (!total_seats || !partyColours || !seatAllocationMethod) return;

    const seatAllocationFunction = chooseSeatAllocationFunction(seatAllocationMethod);

    const renderChart = () => {
      const voteCounts = {};

      pollingData.forEach((row) => {
        if (row.vote_2030 && row.vote_2030 !== "Did not vote") {
          voteCounts[row.vote_2030] = (voteCounts[row.vote_2030] || 0) + 1;
        }
      });

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

      const svgW = window.innerWidth <= 930 ? 570 : 760;
      const seatRadius = window.innerWidth <= 930 ? 12 : 15;
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
        .seatRadius(seatRadius)
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

      const rowH = 22;
      const colW = window.innerWidth <= 930 ? 120 : 145;
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
      <div className="sv-chart-wrapper">
        <svg ref={svgRef} />
        <div ref={tooltipRef} className="chart-tooltip" />
      </div>
    </div>
  );
}


export default SeatVisualisation;
