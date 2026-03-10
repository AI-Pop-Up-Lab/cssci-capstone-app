import { useState, useEffect } from "react";
import axios from "axios";

import './pollingResults.css';

function PollingResults() {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [selectedCountry, setSelectedCountry] = useState(null); // setting default selected/selectable country as sweden for now

  async function getCountrySample(countryName){
    try {
      console.log(`Getting polling results for ${countryName}...`);
      // FastAPI in testing is running on 127.0.0.1:8000
      const response = await axios.get(`http://127.0.0.1:8000/api/samples/country_sample?country=${countryName}`);
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  useEffect(() => {
    console.log(data);
  }, [data]);

  useEffect(() => {
    const selectElement = document.getElementById('selected_country');
    if (selectElement) {
      setSelectedCountry(selectElement.value);
    }
  }, []);

  return (
    <div className="PollingResults">
        <select id="selected_country" defaultValue="netherlands" onChange={(e) => setSelectedCountry(e.target.value)}>
          <option value="netherlands">The Netherlands</option>
          <option value="sweden">Sweden</option>
        </select>

        <button id="getData" onClick={() => getCountrySample(selectedCountry)}>Get Polling Results</button>
    </div>
  );
};

export default PollingResults;