// Component to show the options for countries and let the user select one
// pages/parents it is used in must pass in a variable and its setter from the React useState hook
// so that it can which to indicate being selected, and to update the selection
import { useState, useEffect } from "react";

// options for countries and their abbreviations to display
import './countrySwitch2.css';

import { COUNTRY_INFO } from '../utils/common_vars'

function CountrySwitch2({setCountry, selectedCountry}) {

  // maps the country options to buttons, and uses its name to retrieve the flag from the assets folder
  return (
    <div className="CountrySwitch2">
      {Object.entries(COUNTRY_INFO).map(([name, { country_code, flag_image, abbreviation }]) => (
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
          <div className="countryswitch2-label unbounded-weight400">{abbreviation.toUpperCase()}</div>
        </button>
      ))}
    </div>
  );
}

export default CountrySwitch2;
