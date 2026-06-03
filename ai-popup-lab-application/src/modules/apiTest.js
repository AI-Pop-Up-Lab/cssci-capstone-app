// function that is not used in app but was an initial test of the API, kept if somebody ever wants a simple example

import { useState, useEffect } from "react";
import axios from "axios";

function ApiTest() {
  

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  async function fetchData(){
    try {
      // FastAPI in testing is running on 127.0.0.1:8000
      const response = await axios.get("http://127.0.0.1:8000/api/test_endpoint/");
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="ApiTest">
      {data && (
        <p>{data.message}</p>
      )}
      {error && (
        <p>{error}</p>
      )}
    </div>
  );
};

export default ApiTest;
