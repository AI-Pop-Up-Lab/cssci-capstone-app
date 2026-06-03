// component which shows the total vote turnout of the data passed in, checking how many have value 'did not vote' or similar

import { useRef, useEffect } from "react";
import * as d3 from "d3";
import './voterTurnout.css';

function VoterTurnout({ pollingData }) {
  const svgRef = useRef();
  const tooltipRef = useRef();

  useEffect(() => {
    if (!pollingData || pollingData.length === 0) return;

    const total = pollingData.length;
    const didNotVote = pollingData.filter(r => r.vote_2030 === "Did not vote").length;
    const voted = total - didNotVote;
    const turnoutPct = (voted / total) * 100;

    const pieData = [
      { label: "Voted", value: voted, color: "#2c7be5" },
      { label: "Did not vote", value: didNotVote, color: "#d0d7de" },
    ];

    const width = 260, height = 260;
    const outerR = 100, innerR = 62;
    const cx = width / 2, cy = height / 2;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("width", width).attr("height", height);

    const pie = d3.pie().value(d => d.value).sort(null);
    const arc = d3.arc().innerRadius(innerR).outerRadius(outerR);
    const arcHover = d3.arc().innerRadius(innerR).outerRadius(outerR + 6);

    const tooltip = d3.select(tooltipRef.current);
    const g = svg.append("g").attr("transform", `translate(${cx},${cy})`);

    g.selectAll("path")
      .data(pie(pieData))
      .join("path")
      .attr("d", arc)
      .attr("fill", d => d.data.color)
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .on("mouseover", function(event, d) {
        d3.select(this).transition().duration(150).attr("d", arcHover);
        tooltip.style("opacity", 1)
          .html(`<strong>${d.data.label}</strong><br/>${((d.data.value / total) * 100).toFixed(1)}%`);
      })
      .on("mousemove", event => {
        tooltip.style("left", `${event.pageX + 12}px`).style("top", `${event.pageY - 28}px`);
      })
      .on("mouseout", function() {
        d3.select(this).transition().duration(150).attr("d", arc);
        tooltip.style("opacity", 0);
      });

    // Centre label
    g.append("text")
      .attr("text-anchor", "middle").attr("dy", "-0.15em")
      .attr("font-size", "22px").attr("font-weight", "bold").attr("fill", "#2c7be5")
      .text(`${turnoutPct.toFixed(1)}%`);
    g.append("text")
      .attr("text-anchor", "middle").attr("dy", "1.2em")
      .attr("font-size", "11px").attr("fill", "#666")
      .text("turnout");

  }, [pollingData]);

  return (
    <div className="VoterTurnout">
      <h3>Voter Turnout</h3>
      <div className="vt-chart-wrapper">
        <svg ref={svgRef} />
        <div ref={tooltipRef} className="chart-tooltip" />
      </div>
    </div>
  );
};

export default VoterTurnout;