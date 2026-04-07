// import ApiTest from '../modules/apiTest';
import { useState, useEffect } from "react";

import './landingPage.css';
import chartGraphic from '../assets/images/chartGraphic.png'

import PollingResults from '../modules/polling_results_modules/pollingResults';
import PersonaChatExample from '../modules/personaChatExample';
import CountrySwitch from '../modules/countrySwitch';

function LandingPage() {

  const [selectedCountry, setSelectedCountry] = useState("netherlands");

  function modifyCountryNameEdgeCases(country){
    let modifiedCountry;

    if(country === 'netherlands'){
      modifiedCountry = 'the Netherlands';
    }else{
      modifiedCountry = country;
    }

    return modifiedCountry
  }

  return (
    <div className="LandingPage unbounded-weight300">
      <div id='landing-intro'>
        <p>This is the AI Pollster, where public opinion is visualised through synthetic personas. Explore graphs which visualise the results of the AI polling, and chat with the personas which form the polling data on the persona chat page, to understand intentions and motivations behind polling decisions.</p>
        <img src={chartGraphic}></img>
      </div>

      <CountrySwitch setCountry={setSelectedCountry} selectedCountry={selectedCountry}/>
      
      <p id="landing-explorevotes">EXPLORE THE VOTES IN {modifyCountryNameEdgeCases(selectedCountry).toUpperCase()}</p>
    
      <PollingResults 
        selectedCountry={selectedCountry}
        setSelectedCountry={setSelectedCountry}  
      />

      <PersonaChatExample includeLink={true} country={selectedCountry}  />

  
    </div>
  );
}

export default LandingPage;
