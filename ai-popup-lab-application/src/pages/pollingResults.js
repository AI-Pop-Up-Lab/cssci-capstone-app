import { useState, useEffect } from "react";
import axios from "axios";

import './pollingResults.css';

import PollingMap from '../modules/polling_results_modules/pollingMap';
import SeatVisualisation from '../modules/polling_results_modules/seatVisualisation';
import VoteProjection from '../modules/polling_results_modules/voteProjection';
import DemographicCharts from '../modules/polling_results_modules/demographicCharts';
import Loader from "../modules/loader";


function PollingResults() {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [selectedCountry, setSelectedCountry] = useState("netherlands"); // setting default selected/selectable country as netherlands for now (in final product there will be a dropdown)

  // Map
  // Seat visualisation (would need an algorithm across municipalities/constituencies to count)
  // Vote projection (simple bar chart)
  // Tables/charts to view elections by demographic

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
      {data ? <SeatVisualisation pollingData={data.data} /> : <Loader />}
      {data ? <DemographicCharts pollingData={data.data} country={selectedCountry} /> : <Loader />}
      {data ? <PollingMap /> : <Loader />}
    </div>
  );
};

export default PollingResults;