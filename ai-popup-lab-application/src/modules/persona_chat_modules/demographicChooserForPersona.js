import { useState, useEffect } from "react";
import axios from "axios";

import './demographicChooserForPersona.css';

import Loader from '../loader';
import DemographicChoiceDropdown from './demographicChoiceDropdown';

function DemographicChooserForPersona({setChosenDemographic, country}) {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [selectedValues, setSelectedValues] = useState({});

  // useEffect(() => {
  //   console.log(selectedValues);
  // }, [selectedValues])

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

  return (
    <div className="DemographicChooserForPersona">
      {data ? 

      (
        <>
        {data.relevant_columns.map((column) => (
          <DemographicChoiceDropdown 
          key={column} 
          column={column.replace(/_/g, ' ')} 
          choices={data.column_unique_vals[column]}
          onChange={(value) => handleDropdownChange(column, value)}
          />
        ))}
        </>
      )

      : (<Loader />)}
    </div>
  );
};

export default DemographicChooserForPersona;
