import './countrySwitch.css';

const countryOptions = [
  "netherlands",
  "sweden",
  "denmark"
];

function CountrySwitch({setCountry, selectedCountry}) {



  return (
    <div className="CountrySwitch">
      {countryOptions.map((country) => (
        <img
          key={country}
          src={require(`../assets/images/flags/${country}.png`)} // flag icons must be stored in this directory
          alt={country}
          className={selectedCountry === country ? "selectedIcon" : ""}
          onClick={() => setCountry(country)}
          title={country.charAt(0).toUpperCase() + country.slice(1)}
        />
      ))}
    </div>
  );
}

export default CountrySwitch;