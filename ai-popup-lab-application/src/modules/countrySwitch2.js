// Component to show the options for countries and let the user select one
// pages/parents it is used in must pass in a variable and its setter from the React useState hook
// so that it can which to indicate being selected, and to update the selection
import { useState, useEffect } from "react";

import './countrySwitch2.css';

import { COUNTRY_INFO } from '../utils/common_vars'

// Display-only overrides: logic still uses the country key, this just changes what's shown
const DISPLAY_LABELS = {
  usa: { primary: "USA", secondary: "HOUSE 2026" },
};

function CountrySwitch2({setCountry, selectedCountry}) {

  const countryOptions = Object.entries(COUNTRY_INFO).filter(([name]) => name === "usa");

  return (
    <div className="CountrySwitch2">
      {countryOptions.map(([name, { flag_image, abbreviation }]) => {
        const label = DISPLAY_LABELS[name] ?? { primary: abbreviation.toUpperCase() };

        return (
          <button
            key={name}
            type="button"
            className={`countrySwitch2Item ${selectedCountry === name ? "selectedIcon2" : ""}`}
            onClick={() => setCountry(name)}
            title={name.charAt(0).toUpperCase() + name.slice(1)}
          >
            <img
              src={flag_image}
              alt={name}
            />
            <div className="countryswitch2-label unbounded-weight400">{label.primary}</div>
            {label.secondary && (
              <div className="countryswitch2-sublabel unbounded-weight400">{label.secondary}</div>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default CountrySwitch2;