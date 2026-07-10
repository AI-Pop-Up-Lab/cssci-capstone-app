// Component which takes the selected country, retrieves its data and passed that data to chart components
// also the data can be downloaded on this page but in the future there shall be a data hub page, halfway there with that

import { useState, useEffect, useMemo, useCallback, use } from "react";
import axios from "axios";

import './pollingResults.css';
import exportIcon from '../../assets/images/export.png'

import PollingMap from './pollingMap';
import SeatVisualisation from './seatVisualisation';
import VoteProjection from './voteProjection';
import DemographicCharts from './demographicCharts';
import VoteLongitudinal from "./voteLongitudinal";
import VoteLongitudinalDemographics from "./voteLongitudinalDemographics";
import PollstersUS from "./pollstersUS";
import VoteLongitudinalUSPollsters from "./voteLongitudinalUSPollsters";

import Loader from "../loader";
import { useTranslation } from "react-i18next";


function PollingResults({ selectedCountry, setSelectedCountry }) {

  const { t } = useTranslation();

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

      {/* {selectedCountry !== "usa" && (
        <>
          {data ? <VoteLongitudinal country={selectedCountry} /> : <Loader />}
          <div id="polling-divider"></div>
        </>
      )} */}

      {selectedCountry === "usa" && (
        <>
          {data ? <VoteLongitudinalUSPollsters country={selectedCountry} /> : <Loader />}
          <div id="polling-divider"></div>
        </>
      )}

      {selectedCountry !== "usa" && (
        <>
        {data ? <VoteProjection pollingData={responseData} country={selectedCountry} /> : <Loader />}
        <div id="polling-divider"></div>
        </>
      )}

      {selectedCountry !== "netherlands" && selectedCountry !== "usa" && (
        <>
        {data ? <PollingMap pollingData={responseData} country={selectedCountry} /> : <Loader />}
        <div id="polling-divider"></div>
        </>
      )}

      {selectedCountry !== "usa" && (
        <>
        {data ? <SeatVisualisation pollingData={responseData} country={selectedCountry} /> : <Loader />}
        <div id="polling-divider"></div>
        </>
      )}

      {selectedCountry === "usa" && (
        <>
        {data ? <VoteLongitudinalDemographics country={selectedCountry} /> : <Loader />}
        <div id="polling-divider"></div>
        </>
      )}

      {selectedCountry !== "usa" && (
        <>
        {data ? <DemographicCharts pollingData={responseData} country={selectedCountry} /> : <Loader />}
        </>
      )}

      {selectedCountry === "usa" && (
        <>
        {/* <div id="polling-divider"></div> */}
        {data ? <PollstersUS /> : <Loader />}
        </>
      )}
      
      {selectedCountry !== "usa" && (
        <>
        {data && stratFrameData ? (
          <div id="exportButtons">
            <div className="exportButton" onClick={() => {exportToCSV(responseData, `${selectedCountry}_sample_data.csv`)}}>
              <p>{t('pollingResults.sampleExport')}</p>
              <img src={exportIcon}></img>
            </div>
            <div className="exportButton" onClick={() => {exportToCSV(stratframeResponseData, `${selectedCountry}_frame_data.csv`)}}>
              <p>{t('pollingResults.frameExport')}</p>
              <img src={exportIcon}></img>
            </div>
          </div>
        ) : (
          <Loader />
        )}
        </>
      )}

    </div>
  );
};

export default PollingResults;