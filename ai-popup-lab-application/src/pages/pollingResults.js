import { useState, useEffect } from "react";
import axios from "axios";

import './pollingResults.css';

function PollingResults() {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [selectedCountry, setSelectedCountry] = useState("sweden"); // setting default selected/selectable country as sweden for now

  async function getCountrySample(countryName){
    try {
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

  return (
    <div className="PollingResults">
        <select id="selected_country" defaultValue="sweden" onChange={(e) => setSelectedCountry(e.target.value)}>
          <option value="sweden">Sweden</option>
        </select>

        <button id="getData" onClick={() => getCountrySample(selectedCountry)}>Get Polling Results</button>
    </div>
  );
};

export default PollingResults;