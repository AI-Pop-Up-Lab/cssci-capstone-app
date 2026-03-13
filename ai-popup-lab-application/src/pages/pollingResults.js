import { useState, useEffect } from "react";
import axios from "axios";

import './pollingResults.css';

import PollingMap from '../modules/polling_results_modules/pollingMap';
import SeatVisualisation from '../modules/polling_results_modules/seatVisualisation';
import VoteProjection from '../modules/polling_results_modules/voteProjection';
import DemographicCharts from '../modules/polling_results_modules/demographicCharts';

import DemographicChooserForPersona from '../modules/polling_results_modules/demographicChooserForPersona';
import PersonaChooser from "../modules/polling_results_modules/personaChooser";

import Loader from "../modules/loader";


function PollingResults() {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [selectedCountry, setSelectedCountry] = useState("netherlands"); // setting default selected/selectable country as netherlands for now (in final product there will be a dropdown)

  const [chosenPersonaDemographic, setChosenPersonaDemographic] = useState(null);

  // function to get country sample data from backend
  async function getCountrySample(countryName){
    try {

      // console.log(`Getting polling results for ${countryName}...`);

      // FastAPI in testing is running on 127.0.0.1:8000
      const response = await axios.get(`http://127.0.0.1:8000/api/samples/country_sample?country=${countryName}`);
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  // use to log data when data variable changes if wanted
  // useEffect(() => {
  //   console.log(data);
  // }, [data]);

  useEffect(() => {
    getCountrySample(selectedCountry);
  }, []);


  return (
    <div className="PollingResults">

      {data ? <VoteProjection pollingData={data.data} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <SeatVisualisation pollingData={data.data} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <DemographicCharts pollingData={data.data} country={selectedCountry} /> : <Loader />}
      {/* {data ? <PollingMap /> : <Loader />} */}
      <div id="polling-divider"></div>
      <div id="persona-selection">
        <div id="selection-explanation">
          <h1 className="unbounded-weight400">Chat with a persona</h1>
          <p className="unbounded-weight300">You can choose one of the synthetic persona from the list below to enter a chat, to understand motivations and reasoning behind their polled vote.<br></br>
          <br></br>
          You can select various demographics below to filter through personas.
          </p>
        </div>

        {selectedCountry ? <DemographicChooserForPersona
        setChosenDemographic={setChosenPersonaDemographic}
        country={selectedCountry}
        /> : <Loader />}

        {data && selectedCountry ? <PersonaChooser 
        data={data.data}
        chosenDemographic={chosenPersonaDemographic}
        countryName={selectedCountry}
        /> : <Loader />}

      </div>
    </div>
  );
};

export default PollingResults;