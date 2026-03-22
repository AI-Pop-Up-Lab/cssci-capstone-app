import { useState, useRef, useEffect } from "react";
import * as d3 from "d3";
import { parliamentChart } from 'd3-parliament-chart';
import './seatVisualisation.css';
import partyColours from '../../assets/partyColours';

const TOTAL_SEATS = 150;

// D'Hondt proportional seat allocation
function dhondt(votes) {
  const seats = {};
  Object.keys(votes).forEach(p => { seats[p] = 0; });
  for (let i = 0; i < TOTAL_SEATS; i++) {
    const winner = Object.entries(votes).reduce((best, [party, v]) => {
      const score = v / (seats[party] + 1);
      return score > best.score ? { party, score } : best;
    }, { party: null, score: -1 });
    seats[winner.party]++;
  }
  return seats;
}

function SeatVisualisation({ pollingData }) {

  const svgRef = useRef();
  const tooltipRef = useRef();

  useEffect(() => {
    if (!pollingData || pollingData.length === 0) return;

    const voteCounts = {};
    pollingData.forEach(row => {
      if (row.vote_2030 !== "Did not vote") {
        voteCounts[row.vote_2030] = (voteCounts[row.vote_2030] || 0) + 1;
      }
    });

    const seatsByParty = dhondt(voteCounts);

    // Build aggregated data for d3-parliament-chart (sorted left to right)
    const SPECTRUM = ["GL-PvdA", "SP", "PvdD", "D66", "FNP", "BBB", "CDA", "VVD", "SGP", "PVV", "50PLUS"];
    const aggregated = Object.entries(seatsByParty)
      .filter(([, s]) => s > 0)
      .sort((a, b) => {
        const ai = SPECTRUM.indexOf(a[0]);
        const bi = SPECTRUM.indexOf(b[0]);
        return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
      })
      .map(([party, seats]) => ({ seats, color: partyColours[party] || "#aaa", party }));

    
    let svgW = 760

    if(window.innerWidth <= 930){
      svgW = 570;
    }


    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", svgW).attr("height", svgW / 2 + 120);

    const g = svg.append("g");

    const tooltip = d3.select(tooltipRef.current);

    // Call parliament chart on the group
    const pc = parliamentChart()
      .width(svgW)
      .aggregatedData(aggregated)
      .sections(1)
      .sectionGap(44)
      .seatRadius(15)
      .rowHeight(35);

    g.call(pc);

    const svgH = svgW / 2 + 44 / 4 + 16 + 20;
    svg.attr("height", svgH);

    // Add tooltips to the rendered circles
    g.selectAll("circle")
      .on("mouseover", function(event) {
        const d = d3.select(this).datum();
        const entry = aggregated.find(a => a.color === d.color);
        if (!entry) return;
        tooltip.style("opacity", 1)
          .html(`<strong>${entry.party}</strong><br/>${seatsByParty[entry.party]} seats`);
      })
      .on("mousemove", event => {
        tooltip.style("left", `${event.pageX + 12}px`).style("top", `${event.pageY - 36}px`);
      })
      .on("mouseout", () => tooltip.style("opacity", 0));

    // Legend below the chart
    const legendData = Object.entries(seatsByParty)
      .filter(([, s]) => s > 0)
      .sort((a, b) => b[1] - a[1]);

    const legendG = svg.append("g").attr("transform", `translate(30, ${svgW / 2 + 44 / 4 + 16 + 30})`);
    const colW = 145, rowH = 22, perCol = Math.ceil(legendData.length / 4);

    legendData.forEach(([party, seats], i) => {
      const col = Math.floor(i / perCol);
      const row = i % perCol;
      legendG.append("rect")
        .attr("x", col * colW).attr("y", row * rowH)
        .attr("width", 13).attr("height", 13).attr("rx", 0)
        .attr("fill", partyColours[party] || "#aaa");
      legendG.append("text")
        .attr("x", col * colW + 18).attr("y", row * rowH + 11)
        .attr("font-size", "12px").attr("fill", "#333")
        .text(`${party} — ${seats}`);
    });

    const legendRows = Math.ceil(legendData.length / 4);
    svg.attr("height", svgW / 2 + 44 / 4 + 16 + 40 + legendRows * rowH);

  }, [pollingData]);

  return (
    <div className="SeatVisualisation">
      <h3>Seat Projection</h3>
      <div className="sv-chart-wrapper">
        <svg ref={svgRef} />
        <div ref={tooltipRef} className="chart-tooltip" />
      </div>
    </div>
  );
};

export default SeatVisualisation;
