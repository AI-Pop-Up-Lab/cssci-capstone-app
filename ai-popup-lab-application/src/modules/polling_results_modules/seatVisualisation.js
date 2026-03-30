import { useState, useRef, useEffect } from "react";
import * as d3 from "d3";
import { parliamentChart } from 'd3-parliament-chart';
import './seatVisualisation.css';
import partyColours from '../../assets/partyColours';

// const TOTAL_SEATS = 150;

// D'Hondt proportional seat allocation
function dhondt(votes, total_seats) {
  const seats = {};
  Object.keys(votes).forEach(p => { seats[p] = 0; });
  for (let i = 0; i < total_seats; i++) {
    const winner = Object.entries(votes).reduce((best, [party, v]) => {
      const score = v / (seats[party] + 1);
      return score > best.score ? { party, score } : best;
    }, { party: null, score: -1 });
    seats[winner.party]++;
  }
  return seats;
}

function SeatVisualisation({ pollingData, total_seats = 150 }) {
  const svgRef = useRef(null);
  const tooltipRef = useRef(null);

  useEffect(() => {
    if (!pollingData || pollingData.length === 0 || !svgRef.current) return;

    const renderChart = () => {
      const voteCounts = {};

      pollingData.forEach((row) => {
        if (row.vote_2030 && row.vote_2030 !== "Did not vote") {
          voteCounts[row.vote_2030] = (voteCounts[row.vote_2030] || 0) + 1;
        }
      });

      const seatsByParty = dhondt(voteCounts, total_seats);

      const SPECTRUM = [
        "GL-PvdA",
        "SP",
        "PvdD",
        "D66",
        "FNP",
        "BBB",
        "CDA",
        "VVD",
        "SGP",
        "PVV",
        "50PLUS",
      ];

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
  }, [pollingData, total_seats]);

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
