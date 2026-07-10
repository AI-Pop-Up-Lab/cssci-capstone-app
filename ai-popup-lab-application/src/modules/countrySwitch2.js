// Component to show the options for countries and let the user select one
// pages/parents it is used in must pass in a variable and its setter from the React useState hook
// so that it can which to indicate being selected, and to update the selection
import { useState, useEffect } from "react";

// options for countries and their abbreviations to display
import './countrySwitch2.css';

const countryOptions = [
  { name: "netherlands", abbreviation: "NL" },
  { name: "sweden", abbreviation: "SE" },
  { name: "denmark", abbreviation: "DK" },
  { name: "usa", abbreviation: "USA"}
];

function CountrySwitch2({setCountry, selectedCountry, include_usa_TEMPORARY}) {

  const options = include_usa_TEMPORARY
    ? countryOptions
    : countryOptions.filter(c => c.name !== "usa");

  // maps the country options to buttons, and uses its name to retrieve the flag from the assets folder
  return (
    <div className="CountrySwitch2">
      {options.map(({ name, abbreviation }) => (
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
