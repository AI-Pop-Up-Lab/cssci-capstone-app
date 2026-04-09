import './countrySwitch.css';

const countryOptions = [
  { name: "netherlands", abbreviation: "NL" },
  { name: "sweden", abbreviation: "SE" },
  { name: "denmark", abbreviation: "DK" }
];

function CountrySwitch({setCountry, selectedCountry}) {



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
          <div className="label">{abbreviation}</div>
        </button>
      ))}
    </div>
  );
}

export default CountrySwitch;