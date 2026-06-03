// interactive map chart using d3.js. uses .geojson files from assets for map structure and keys
// could never get the netherlands one working...
// or the sweden map not to look weird...
// TODO! 

import { useRef, useEffect, useState } from 'react';
import * as d3 from "d3";
import './pollingMap.css';

// GEOJSONs for countries are hardcoded at the moment
// Sweden | kom_namn | https://github.com/okfse/sweden-geojson | se.geojson
// Denmark | label_en or label_dk | https://github.com/magnuslarsen/geoJSON-Danish-municipalities/tree/master | dk.geojson
// Netherlands | name | https://www.webuildinternet.com/2015/07/09/geojson-data-of-the-netherlands/ | nl.geojson
// all geojsons are located in public/geojson/

const GEO_CONFIG = {
  netherlands: {
    file: "/geojson/nl.geojson",
    labelField: "name",
    projection: "mercator",
  },
  sweden: {
    file: "/geojson/se.geojson",
    labelField: "kom_namn",
    projection: "identity",
  },
  denmark: {
    file: "/geojson/dk.geojson",
    labelField: "label_en",
    projection: "mercator",
  },
};

function PollingMap({ pollingData, country }) {
  const svgRef = useRef(null);
  const [aspectRatio, setAspectRatio] = useState("4 / 3");

  const normalizeMunicipality = (value) =>
    (value ?? "").toString().trim().toLowerCase().normalize("NFKC");

  useEffect(() => {
    if (!country || !GEO_CONFIG[country]) return;

    const { file, labelField, projection: projectionType } = GEO_CONFIG[country];

    const svg = d3.select(svgRef.current);

    svg.selectAll("*").remove();

    d3.selectAll(".polling-map-tooltip").remove();
    const tooltip = d3
      .select("body")
      .append("div")
      .attr("class", "polling-map-tooltip")
      .style("position", "absolute")
      .style("pointer-events", "none")
      .style("z-index", "9999")
      .style("display", "none")
      .style("background", "rgba(24, 24, 24, 0.95)")
      .style("color", "#fff")
      .style("border", "1px solid #999")
      .style("border-radius", "6px")
      .style("padding", "8px 10px")
      .style("font-size", "12px")
      .style("max-width", "280px")
      .style("line-height", "1.35")
      .style("font-family", '"Unbounded", sans-serif');

    

    Promise.all([
      d3.json(file),
      d3.json(`${process.env.REACT_APP_API_URL}/api/samples/map_aggregates?country=${country}`),
      d3.json(`${process.env.REACT_APP_API_URL}/api/dynamicdata/party_colours?country=${country}`),
    ])
      .then(([geojson, mapAggregateResponse, partyColoursResponse]) => {
        const tempWidth = 1000;
        const tempHeight = 1000;
        const padding = 16;

        const projection =
          projectionType === "identity"
            ? d3.geoIdentity().reflectY(true).fitSize([tempWidth, tempHeight], geojson)
            : d3.geoMercator().fitSize([tempWidth, tempHeight], geojson);

        const path = d3.geoPath(projection);

        const mapAggregateRows = mapAggregateResponse?.data ?? [];
        const partyColours = partyColoursResponse?.party_colours ?? {};

        const aggregateRowsByMunicipality = new Map();
        const aggregateMunicipalityLabels = new Map();

        mapAggregateRows.forEach((row) => {
          const municipality = normalizeMunicipality(row.municipality);
          const pct = Number(row.pct);

          if (!municipality || Number.isNaN(pct)) return;

          if (!aggregateRowsByMunicipality.has(municipality)) {
            aggregateRowsByMunicipality.set(municipality, []);
            aggregateMunicipalityLabels.set(municipality, row.municipality);
          }

          aggregateRowsByMunicipality.get(municipality).push({
            party: row.party,
            pct,
          });
        });

        aggregateRowsByMunicipality.forEach((rows) => {
          rows.sort((a, b) => b.pct - a.pct);
        });

        const geoMunicipalityLabels = new Map();
        geojson.features.forEach((feature) => {
          const rawLabel = feature?.properties?.[labelField];
          const normalized = normalizeMunicipality(rawLabel);
          if (!normalized) return;
          if (!geoMunicipalityLabels.has(normalized)) {
            geoMunicipalityLabels.set(normalized, rawLabel);
          }
        });

        const aggregatesNotInGeo = [...aggregateMunicipalityLabels.keys()]
          .filter((municipality) => !geoMunicipalityLabels.has(municipality))
          .map((municipality) => aggregateMunicipalityLabels.get(municipality))
          .sort((a, b) => a.localeCompare(b));

        const geoNotInAggregates = [...geoMunicipalityLabels.keys()]
          .filter((municipality) => !aggregateMunicipalityLabels.has(municipality))
          .map((municipality) => geoMunicipalityLabels.get(municipality))
          .sort((a, b) => a.localeCompare(b));

        console.log(`[PollingMap:${country}] In aggregates but not in geojson`, aggregatesNotInGeo);
        console.log(`[PollingMap:${country}] In geojson but not in aggregates`, geoNotInAggregates);

        const topPartyByMunicipality = new Map();
        aggregateRowsByMunicipality.forEach((rows, municipality) => {
          if (!rows.length) return;

          const winner = rows[0];
          if (!winner) return;

          topPartyByMunicipality.set(municipality, {
            party: winner.party,
            pct: winner.pct,
          });
        });

        const mapGroup = svg.append("g");

        const paths = mapGroup
          .selectAll("path")
          .data(geojson.features)
          .join("path")
          .attr("d", path)
          .attr("fill", (d) => {
            const municipality = normalizeMunicipality(d.properties[labelField]);
            const winner = topPartyByMunicipality.get(municipality);

            if (!winner) return "#e0e0e0";
            return partyColours[winner.party] ?? "#8a8a8a";
          })
          .attr("stroke", "rgba(28, 46, 58, 0.45)")
          .attr("stroke-width", 0.55)
          .attr("vector-effect", "non-scaling-stroke")
          .on("mouseenter", function (event, d) {
            const municipalityLabel = d.properties[labelField] ?? "Unknown";
            const municipality = normalizeMunicipality(municipalityLabel);
            const rows = aggregateRowsByMunicipality.get(municipality) ?? [];

            const rowsHtml = rows.length
              ? rows
                  .map(
                    (row) =>
                      `<div>${row.party}: ${(row.pct * 100).toFixed(1)}%</div>`
                  )
                  .join("")
              : "<div>No aggregate data</div>";

            tooltip
              .style("display", "block")
              .html(
                `<div style="font-weight:700; margin-bottom:6px;">${municipalityLabel}</div>${rowsHtml}`
              )
              .style("left", `${event.pageX + 12}px`)
              .style("top", `${event.pageY + 12}px`);

            d3.select(this).attr("stroke-width", 3);
            
          })
          .on("mousemove", function (event) {
            tooltip
              .style("left", `${event.pageX + 12}px`)
              .style("top", `${event.pageY + 12}px`);
          })
          .on("mouseleave", function () {
            tooltip.style("display", "none");
            d3.select(this).attr("stroke-width", 0.5);
          });

        paths.append("title").text((d) => {
          const municipalityLabel = d.properties[labelField] ?? "Unknown";
          const municipality = normalizeMunicipality(municipalityLabel);
          const winner = topPartyByMunicipality.get(municipality);

          if (!winner) return `${municipalityLabel}: No aggregate data`;
          return `${municipalityLabel}: ${winner.party} (${(winner.pct * 100).toFixed(1)}%)`;
        });

        const bounds = mapGroup.node().getBBox();
        const viewBoxX = bounds.x - padding;
        const viewBoxY = bounds.y - padding;
        const viewBoxWidth = bounds.width + padding * 2;
        const viewBoxHeight = bounds.height + padding * 2;

        svg.attr(
          "viewBox",
          `${viewBoxX} ${viewBoxY} ${viewBoxWidth} ${viewBoxHeight}`
        );

        setAspectRatio(`${viewBoxWidth} / ${viewBoxHeight}`);
      })
      .catch((error) => {
        console.error("Error loading polling map data", error);
      });

    return () => {
      tooltip.remove();
    };
  }, [country, pollingData]);

  return (
    <div
  style={{
    width: "100%",
    maxWidth: country === "sweden" ? "700px" : "1000px",
    margin: "0 auto",
    aspectRatio,
  }}
>
      {/* couldn't get it centered lmfao */}
      {/* <h3 className="vp-title">Results by Municipality</h3> */}

      <svg
        ref={svgRef}
        preserveAspectRatio="xMidYMid meet"
        style={{
          width: "100%",
          height: "100%",
          display: "block",
        }}
      />
    </div>
  );
}

export default PollingMap;