/*
Page that shows the results of the synthetic panels
Countries can be picked to see that country's data
Graphs shown:
- bar chart of vote distribution across parties
- a map of the country and the most popular party in each region
- a seat projection chart
- a bar chart that can be filtered by demographics, to show vote distribution across various demographics

Sample and frame data used for charts seen also downloadable here
*/

import { useState, useEffect } from "react";
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';

import './pollPage.css';

import PollingResults from '../modules/polling_results_modules/pollingResults';
import CountrySwitch2 from '../modules/countrySwitch2';

// options for countries to pick from
const countryOptions = [
  'netherlands',
  'sweden',
  'denmark'
]

function PollPage() {

  // getting search parameters
  const [searchParams] = useSearchParams();

  // default selected country is first from countryOptions list, otherwise selected country is the selected country from previous page from URL parameters
  const paramCountry = countryOptions.includes(searchParams.get('country'))
  ? searchParams.get('country')
  : countryOptions[0];
  const [selectedCountry, setSelectedCountry] = useState(paramCountry);

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [responseData, setResponseData] = useState(null);

  // retrieving country sample of selected country from backend API
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

  // when user selects new country, relevant data retrieval function is called
  useEffect(() => {
    setData(null);

    getCountrySample(selectedCountry);
  }, [selectedCountry]);

  useEffect(() => {
    setResponseData(data?.data ?? []);
  }, [data]);

  return (
    <div className="PollPage unbounded-weight300">
      {/* Component for switching country */}
      <CountrySwitch2 
        setCountry={setSelectedCountry} 
        selectedCountry={selectedCountry}
      />
      
      {/* Component which holds the polling result graphs */}
      <PollingResults 
        selectedCountry={selectedCountry}
        setSelectedCountry={setSelectedCountry}  
      />
    </div>
  );
}

export default PollPage;
