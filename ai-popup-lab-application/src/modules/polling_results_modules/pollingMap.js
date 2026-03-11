import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import './pollingMap.css';

const GEOJSON_URL = '/gemeente_2025.geojson';

function PollingMap() {
  const svgRef = useRef();
  const tooltipRef = useRef();
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(GEOJSON_URL)
      .then(r => {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(geoData => {
        const W = 500, H = 600, PAD = 20;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();
        svg.attr('width', W).attr('height', H);

        svg.append('rect').attr('width', W).attr('height', H).attr('fill', '#b8d4e8');

        const projection = d3.geoMercator()
          .fitExtent([[PAD, PAD], [W - PAD, H - PAD]], geoData);

        const path = d3.geoPath().projection(projection);
        const tooltip = d3.select(tooltipRef.current);

        svg.append('g')
          .selectAll('path')
          .data(geoData.features)
          .join('path')
          .attr('d', path)
          .attr('fill', '#dce8c8')
          .attr('stroke', '#8aac6a')
          .attr('stroke-width', 0.6)
          .on('mouseover', (event, d) => {
            d3.select(event.currentTarget).attr('fill', '#7aab5a');
            tooltip.style('opacity', 1).html('<strong>' + d.properties.statnaam + '</strong>');
          })
          .on('mousemove', event => {
            tooltip.style('left', (event.pageX + 12) + 'px').style('top', (event.pageY - 36) + 'px');
          })
          .on('mouseout', event => {
            d3.select(event.currentTarget).attr('fill', '#dce8c8');
            tooltip.style('opacity', 0);
          });
      })
      .catch(err => {
        console.error('PollingMap:', err);
        setError(err.message);
      });
  }, []);

  return (
    <div className="PollingMap">
      <h3>Netherlands — Municipalities</h3>
      {error && <p className="map-error">Failed to load map: {error}</p>}
      <div className="map-wrapper">
        <svg ref={svgRef} />
        <div ref={tooltipRef} className="chart-tooltip" />
      </div>
    </div>
  );
}

export default PollingMap;
