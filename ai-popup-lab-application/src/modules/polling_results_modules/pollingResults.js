import { useState, useEffect, useMemo, useCallback } from "react";
import axios from "axios";

import './pollingResults.css';
import exportIcon from '../../assets/images/export.png'

import PollingMap from './pollingMap';
import SeatVisualisation from './seatVisualisation';
import VoteProjection from './voteProjection';
import DemographicCharts from './demographicCharts';

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
      // In deployment, the environment variable REACT_APP_API_URL is in the github repository secrets and gets added in build from the workflow file (deploy-frontend.yml)
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/samples/country_sample?country=${countryName}`);
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



  function exportToCSV(data, filename = 'data.csv') {
    const headers = Object.keys(data[0]);
    const rows = data.map(obj => headers.map(h => `"${obj[h]}"`).join(','));
    const csv = [headers.join(','), ...rows].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="PollingResults">

      {data ? <VoteProjection pollingData={responseData} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <SeatVisualisation pollingData={responseData} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <DemographicCharts pollingData={responseData} country={selectedCountry} /> : <Loader />}
      {/* {data ? <PollingMap /> : <Loader />} */}

      <div id="exportButton" onClick={() => {exportToCSV(responseData)}}>
        <p>Export data</p>
        <img src={exportIcon}></img>
      </div>

      <div id="polling-divider"></div>
    </div>
  );
};

export default PollingResults;