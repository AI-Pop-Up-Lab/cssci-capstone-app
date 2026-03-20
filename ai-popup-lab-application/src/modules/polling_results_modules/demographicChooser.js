import { useState, useEffect } from "react";
import axios from "axios";

import './demographicChooser.css';

import Loader from '../loader';

function DemographicChooser({setChosenDemographic, country}) {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [selectedValues, setSelectedValues] = useState({});

  // function to get country sample data from backend
  async function getColumnsAndUniqueVals(countryName){
    try {

      // FastAPI in testing is running on 127.0.0.1:8000
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/samples/columns_and_uniques?country=${countryName}`);
      
      const modifiedData = response.data;
      Object.keys(modifiedData.column_unique_vals).forEach((column) => {
        modifiedData.column_unique_vals[column].unshift("all");
      });

      // initialising values of all dropdowns to 'all'
      const initialValues = {};
      modifiedData.relevant_columns.forEach((column) => {
        initialValues[column] = "all";
      });
      setSelectedValues(initialValues);
      setChosenDemographic(initialValues);

      setData(modifiedData);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  function handleDropdownChange(column, value) {
    const updated = { ...selectedValues, [column]: value };
    setSelectedValues(updated);
    setChosenDemographic(updated);
  }

  useEffect(() => {
    getColumnsAndUniqueVals(country);
  }, []);

  // useEffect(() => {
  //   console.log(data);
  // }, [data]);

  const allLabels = {
    gender:       { all: "all genders" },
    age_group:    { all: "all ages" },
    education:    { all: "all education levels" },
    municipality: { all: "all municipalities" },
  };

  const mkSelect = (col) => {
    const vals = data?.column_unique_vals[col];
    if (!vals) return null;
    return (
      <select
        className="dc-inline-select"
        value={selectedValues[col] || "all"}
        onChange={(e) => handleDropdownChange(col, e.target.value)}
      >
        {vals.map(v => (
          <option key={v} value={v}>
            {allLabels[col]?.[v] ?? v}
          </option>
        ))}
      </select>
    );
  };

  return (
    <div className="DemographicChooser">
      {data ? (
        <p className="dc-sentence">
          What would the results look like if{' '}
          {mkSelect('gender')}{' '}
          voters, aged{' '}
          {mkSelect('age_group')},
          {' '}with{' '}
          {mkSelect('education')}{' '}
          education, from{' '}
          {mkSelect('municipality')}
          {' '}could vote?
        </p>
      ) : (<Loader />)}
    </div>
  );
};

export default DemographicChooser;