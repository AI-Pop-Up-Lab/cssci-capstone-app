import { useState, useEffect, useMemo, useCallback } from "react";
import axios from "axios";

import './personaPage.css';

import PersonaChatExample from '../modules/personaChatExample.js';
import DemographicChooserForPersona from '../modules/persona_chat_modules/demographicChooserForPersona.js';
import PersonaChooser from "../modules/persona_chat_modules/personaChooser.js";
import CountrySwitch from '../modules/countrySwitch';

import Loader from "../modules/loader";

function PersonaPage() {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [selectedCountry, setSelectedCountry] = useState("netherlands"); // setting default selected/selectable country as netherlands for now (in final product there will be a dropdown)

  const [chosenPersonaDemographic, setChosenPersonaDemographic] = useState({});

  const handleSetChosenPersonaDemographic = useCallback((value) => {
    setChosenPersonaDemographic(value);
  }, []);

  // function to get country sample data from backend
  async function getCountrySample(countryName){
    try {

      // console.log(`Getting polling results for ${countryName}...`);

      // FastAPI in testing is running on 127.0.0.1:8000
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/samples/country_sample?country=${countryName}`);
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  useEffect(() => {
    getCountrySample(selectedCountry);
  }, []);
  
  const responseData = useMemo(() => data?.data ?? [], [data]);

  // scroll to top of page when loads, as many personas puts you at bottom of massive page
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="PersonaPage">

      <CountrySwitch setCountry={setSelectedCountry} selectedCountry={selectedCountry}/>

      { selectedCountry && 
        <PersonaChatExample includeLink={false} country={selectedCountry} />
      }


      <div id="persona-selection">
        <div id="selection-explanation">
          <h1 className="unbounded-weight400">Chat with a persona</h1>
          <p className="unbounded-weight300">You can choose one of the synthetic persona from the list below to enter a chat, to understand motivations and reasoning behind their polled vote.<br></br>
          <br></br>
          You can select various demographics below to filter through personas. Hover over a persona icon to view its details and if you wish to, then enter a chat.
          </p>
        </div>

        {selectedCountry ? <DemographicChooserForPersona
        setChosenDemographic={handleSetChosenPersonaDemographic}
        country={selectedCountry}
        /> : <Loader />}

        {data && selectedCountry ? <PersonaChooser 
        data={responseData}
        chosenDemographic={chosenPersonaDemographic}
        countryName={selectedCountry}
        /> : <Loader />}

      </div>
    </div>
  );
}

export default PersonaPage;
