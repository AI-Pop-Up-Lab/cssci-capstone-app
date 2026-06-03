// OLDER VERSION, see 'countrySwitch2.js' - real original and well though out naming convention... just you wait for 3!!!!
// Component to show the options for countries and let the user select one
// pages/parents it is used in must pass in a variable and its setter from the React useState hook
// so that it can which to indicate being selected, and to update the selection
import './countrySwitch.css';

// options for countries and their abbreviations to display
const countryOptions = [
  { name: "netherlands", abbreviation: "NL" },
  { name: "sweden", abbreviation: "SE" },
  { name: "denmark", abbreviation: "DK" }
];

function CountrySwitch({setCountry, selectedCountry}) {


  // maps the country options to buttons, and uses its name to retrieve the flag from the assets folder
  return (
    <div className="CountrySwitch">
      {countryOptions.map(({ name, abbreviation }) => (
        <button
          key={name}
          type="button"
          className={`countrySwitchItem ${selectedCountry === name ? "selectedIcon" : ""}`}
          onClick={() => setCountry(name)}
          title={name.charAt(0).toUpperCase() + name.slice(1)}
        >
          <img
            src={require(`../assets/images/flags/${name}.png`)} // flag icons must be stored in this directory
            alt={name}
          />
          <div className="countryswitch-label">{abbreviation}</div>
        </button>
      ))}
    </div>
  );
}

export default CountrySwitch;