import { useState, useEffect, useMemo, useCallback } from "react";
import axios from "axios";

import './pollingResults.css';

import PollingMap from './pollingMap';
import SeatVisualisation from './seatVisualisation';
import VoteProjection from './voteProjection';
import DemographicCharts from './demographicCharts';

import DemographicChooserForPersona from './demographicChooserForPersona';
import PersonaChooser from "./personaChooser";

import Loader from "../loader";


function PollingResults() {

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

  const responseData = useMemo(() => data?.data ?? [], [data]);

  return (
    <div className="PollingResults">

      {data ? <VoteProjection pollingData={responseData} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <SeatVisualisation pollingData={responseData} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <DemographicCharts pollingData={responseData} country={selectedCountry} /> : <Loader />}
      {/* {data ? <PollingMap /> : <Loader />} */}
      {/* <div id="polling-divider"></div> */}
      {/* <div id="persona-selection">
        <div id="selection-explanation">
          <h1 className="unbounded-weight400">Chat with a persona</h1>
          <p className="unbounded-weight300">You can choose one of the synthetic persona from the list below to enter a chat, to understand motivations and reasoning behind their polled vote.<br></br>
          <br></br>
          You can select various demographics below to filter through personas.
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

      </div> */}
    </div>
  );
};

export default PollingResults;