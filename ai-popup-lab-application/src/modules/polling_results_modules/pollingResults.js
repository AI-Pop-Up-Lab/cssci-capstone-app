import { useState, useEffect, useMemo, useCallback, use } from "react";
import axios from "axios";

import './pollingResults.css';
import exportIcon from '../../assets/images/export.png'

import PollingMap from './pollingMap';
import SeatVisualisation from './seatVisualisation';
import VoteProjection from './voteProjection';
import DemographicCharts from './demographicCharts';

import Loader from "../loader";


function PollingResults({ selectedCountry, setSelectedCountry }) {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [responseData, setResponseData] = useState(null);
  const [stratframeResponseData, setStratframeResponseData] = useState(null);


  const [stratFrameData, setStratFrameData] = useState(null);
  const [stratFrameDataError, setStratFrameDataError] = useState(null);

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

  async function getCountryStratFrame(countryName){
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/samples/country_stratification_frame?country=${countryName}`);
      
      setStratFrameData(response.data);
      setStratFrameDataError(null);
    } catch (err) {
      setStratFrameDataError(err.message);
      setStratFrameData(null);
    }
  };

  // use to log data when data variable changes if wanted
  // useEffect(() => {
  //   console.log(data);
  // }, [data]);

  useEffect(() => {
    setData(null);
    setStratFrameData(null);

    getCountrySample(selectedCountry);
    getCountryStratFrame(selectedCountry);
  }, [selectedCountry]);

  useEffect(() => {
    setResponseData(data?.data ?? []);
  }, [data]);

  useEffect(() => {
    setStratframeResponseData(stratFrameData?.data ?? []);
  }, [stratFrameData]);


  function exportToCSV(data, filename='data.csv') {
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

      {data ? <VoteProjection pollingData={responseData} country={selectedCountry} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <SeatVisualisation pollingData={responseData} country={selectedCountry} /> : <Loader />}
      <div id="polling-divider"></div>
      {data ? <DemographicCharts pollingData={responseData} country={selectedCountry} /> : <Loader />}
      {/* {data ? <PollingMap /> : <Loader />} */}

      <div id="polling-divider"></div>

      {data && stratFrameData ? (
        <div id="exportButtons">
          <div className="exportButton" onClick={() => {exportToCSV(responseData, `${selectedCountry}_sample_data.csv`)}}>
            <p>Export sample data</p>
            <img src={exportIcon}></img>
          </div>
          <div className="exportButton" onClick={() => {exportToCSV(stratframeResponseData, `${selectedCountry}_frame_data.csv`)}}>
            <p>Export frame data</p>
            <img src={exportIcon}></img>
          </div>
        </div>
      ) : (
        <Loader />
      )}

      <div id="polling-divider"></div>
    </div>
  );
};

export default PollingResults;