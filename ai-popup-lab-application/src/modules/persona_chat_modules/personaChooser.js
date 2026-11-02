// renders and is parent of all personae that match chosen filters. 
// if no personae match, it shows text explaining so

import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";

import './personaChooser.css';

import Loader from "../loader";
import PersonaDetailCard from "./personaDetailCard";

const INITIAL_BATCH_SIZE = 120;
const BATCH_INCREMENT = 60;

function getAttributeValue(row, column) {
  if (row.attributes && row.attributes[column] !== undefined) {
    return row.attributes[column];
  }
  return row[column];
}

function normalizePersona(persona, idx) {
  const personaId = persona.id || `us_${String((persona.index ?? idx) + 1).padStart(4, '0')}`;
  const rawDigits = personaId.replace(/\D+/g, '');
  const numericIndex = rawDigits ? parseInt(rawDigits, 10) - 1 : (persona.index ?? idx);
  const displayName = persona.display_name || `Persona ${numericIndex + 1}`;

  const attrs = persona.attributes ? { ...persona.attributes } : {};
  // Copy top-level props if not in attributes
  for (const [key, value] of Object.entries(persona)) {
    if (!['attributes', 'extra', 'profile', 'source_file', 'opinion_style'].includes(key) && attrs[key] === undefined) {
      attrs[key] = value;
    }
  }

  return {
    ...attrs,
    id: personaId,
    index: numericIndex,
    display_name: displayName,
    // Keep opinion_style and extra internal for LLM chat only
    _extra: persona.extra || {},
  };
}

function PersonaChooser({ data = [], chosenDemographic, countryName, relevantColumns }) {

  const { t } = useTranslation();

  const [filteredData, setFilteredData] = useState([]);
  const [displayLimit, setDisplayLimit] = useState(INITIAL_BATCH_SIZE);
  const [isLoading, setIsLoading] = useState(false);

  // filter data through chosen demographics
  useEffect(() => {
    if (!chosenDemographic || Object.keys(chosenDemographic).length === 0) return;

    setIsLoading(true);

    const timeout = setTimeout(() => {
      const result = (data || []).filter((row) =>
        Object.entries(chosenDemographic).every(([column, filterValue]) => {
          if (!filterValue || filterValue === 'all') return true;
          const val = getAttributeValue(row, column);
          return val === filterValue;
        })
      );
      setFilteredData(result);
      setDisplayLimit(INITIAL_BATCH_SIZE);
      setIsLoading(false);
    }, 0);

    return () => clearTimeout(timeout);
  }, [data, chosenDemographic]);

  const visiblePersonas = useMemo(() => {
    return filteredData.slice(0, displayLimit).map((persona, i) => normalizePersona(persona, i));
  }, [filteredData, displayLimit]);

  const cards = useMemo(() =>
    visiblePersonas.map((persona) => (
      <PersonaDetailCard
        key={`${countryName}_${persona.id || persona.index}`}
        personaDetails={persona}
        relevantColumnsToShow={relevantColumns}
        personaCountry={countryName}
      />
    )),
    [visiblePersonas, relevantColumns, countryName]
  );

  const handleLoadMore = () => {
    setDisplayLimit((prev) => Math.min(prev + BATCH_INCREMENT, filteredData.length));
  };

  return (
    <div className="PersonaChooserContainer">
      {!isLoading && filteredData.length > 0 && (
        <p className="persona-results-summary unbounded-weight300">
          Showing {visiblePersonas.length} of {filteredData.length} matching personas
          {data.length > filteredData.length ? ` (filtered from ${data.length} total)` : ''}
        </p>
      )}

      <div className="PersonaChooser">
        {!isLoading && cards}
        {(isLoading || (data && data.length === 0)) && <Loader />}
        {filteredData.length < 1 && !isLoading && data && data.length > 0 && (
          <h2 className="unbounded-weight300">{t('personaPage.noPersonaMatch')}</h2>
        )}
      </div>

      {!isLoading && displayLimit < filteredData.length && (
        <div className="load-more-container">
          <button
            type="button"
            className="load-more-button unbounded-weight300"
            onClick={handleLoadMore}
          >
            LOAD MORE (+{Math.min(BATCH_INCREMENT, filteredData.length - displayLimit)})
          </button>
        </div>
      )}
    </div>
  );
};

export default PersonaChooser;
