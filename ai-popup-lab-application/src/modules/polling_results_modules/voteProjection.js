import { useRef, useEffect } from "react";
import * as d3 from "d3";
import './voteProjection.css';
import partyColours from '../../assets/partyColours';

function VoteProjection({ pollingData }) {
  const svgRef = useRef();
  const tooltipRef = useRef();

  const total = pollingData?.length || 0;
  const didNotVote = pollingData?.filter(r => r.vote_2030 === "Did not vote").length || 0;
  const voted = total - didNotVote;
  const turnoutPct = total > 0 ? ((voted / total) * 100).toFixed(1) : 0;

  useEffect(() => {
    if (!pollingData || pollingData.length === 0) return;

    const voteCounts = {};
    pollingData.forEach(row => {
      if (row.vote_2030 !== "Did not vote") {
        voteCounts[row.vote_2030] = (voteCounts[row.vote_2030] || 0) + 1;
      }
    });

    const chartData = Object.entries(voteCounts)
      .map(([party, count]) => ({ party, pct: (count / voted) * 100 }))
      .sort((a, b) => b.pct - a.pct);


    let svgW = 820

    if(window.innerWidth <= 900){
      svgW = 600;
    }

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
    g.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(d3.axisBottom(x).tickSize(0))
      .select(".domain").remove()
      .selection().selectAll("text")
      .attr("font-size", "13px")
      .attr("font-weight", "700")
      .attr("fill", "#111");

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

  }, [pollingData]);

  return (
    <div className="VoteProjection">
      <h3 className="vp-title">If the 2030 general election were held today, who would you vote for?</h3>
      <p className="vp-subtitle">Turnout: <strong>{turnoutPct}%</strong> &mdash; {voted} of {total} respondents said they would vote</p>
      <div className="vp-chart-wrapper">
        <svg ref={svgRef} />
        <div ref={tooltipRef} className="chart-tooltip" />
      </div>
    </div>
  );
};

export default VoteProjection;
