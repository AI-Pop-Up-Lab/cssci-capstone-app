import { useState, useEffect } from "react";

import './countrySwitch2.css';

const countryOptions = [
  { name: "netherlands", abbreviation: "NL" },
  { name: "sweden", abbreviation: "SE" },
  { name: "denmark", abbreviation: "DK" }
];

function CountrySwitch2({setCountry, selectedCountry}) {

  return (
    <div className="CountrySwitch2">
      {countryOptions.map(({ name, abbreviation }) => (
        <button
          key={name}
          type="button"
          className={`countrySwitch2Item ${selectedCountry === name ? "selectedIcon2" : ""}`}
          onClick={() => setCountry(name)}
          title={name.charAt(0).toUpperCase() + name.slice(1)}
        >
          <img
            src={require(`../assets/images/flags/${name}.png`)} // flag icons must be stored in this directory
            alt={name}
          />
          <div className="countryswitch2-label unbounded-weight400">{abbreviation}</div>
        </button>
      ))}
    </div>
  );
}

export default CountrySwitch2;
