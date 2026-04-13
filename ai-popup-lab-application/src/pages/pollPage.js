import { useState, useEffect } from "react";
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';

import './pollPage.css';

import PollingResults from '../modules/polling_results_modules/pollingResults';
import CountrySwitch2 from '../modules/countrySwitch2';

const countryOptions = [
  'netherlands',
  'sweden',
  'denmark'
]

function PollPage() {

  const [searchParams] = useSearchParams();

  const paramCountry = countryOptions.includes(searchParams.get('country'))
  ? searchParams.get('country')
  : countryOptions[0];
  const [selectedCountry, setSelectedCountry] = useState(paramCountry);

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [responseData, setResponseData] = useState(null);

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

  useEffect(() => {
    setData(null);

    getCountrySample(selectedCountry);
  }, [selectedCountry]);

  useEffect(() => {
    setResponseData(data?.data ?? []);
  }, [data]);

  return (
    <div className="PollPage unbounded-weight300">
      <CountrySwitch2 
        setCountry={setSelectedCountry} 
        selectedCountry={selectedCountry}
      />
      
      <PollingResults 
        selectedCountry={selectedCountry}
        setSelectedCountry={setSelectedCountry}  
      />
    </div>
  );
}

export default PollPage;
