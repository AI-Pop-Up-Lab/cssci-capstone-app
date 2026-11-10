// component that retrieves columns from country data to filter on
// specifically for the persona chat as it includes the next general election prediction column to filter on

import { useState, useEffect } from "react";
import axios from "axios";

import './demographicChooserForPersona.css';

import Loader from '../loader';
import DemographicChoiceDropdown from './demographicChoiceDropdown';
import { getMidtermAttributes } from '../../utils/fetch_data';

function DemographicChooserForPersona({setChosenDemographic, setRelevantColumns, country}) {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [dataCountry, setDataCountry] = useState(null); 

  const [selectedValues, setSelectedValues] = useState({});

  const [columnToRename, setColumnToRename] = useState(null);
  const [columnToRenameError, setColumnToRenameError] = useState(null); 

  const [loading, setLoading] = useState(false);

  async function getColumnToRename(countryName){
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/dynamicdata/nextGE_col_name?country=${countryName}`);
      const response_data = response.data;
      const next_GE_colname = response_data.column_to_rename;
      setColumnToRename(next_GE_colname);
      setColumnToRenameError(null);
    } catch (err) {
      setColumnToRenameError(err.message);
      setColumnToRename(null);
    }
  };

  // function to get country sample data from backend
  async function getColumnsAndUniqueVals(countryName){
    setLoading(true);   
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/samples/columns_and_uniques?country=${countryName}`);
      
      const modifiedData = {
        ...response.data,
        column_unique_vals: Object.fromEntries(
          Object.entries(response.data.column_unique_vals).map(([column, vals]) => [
            column,
            ["all", ...vals]  // prepend "all" to a new array
          ])
        )
      };

      Object.freeze(modifiedData.relevant_columns);

      // initialising values of all dropdowns to 'all'
      const initialValues = {};
      modifiedData.relevant_columns.forEach((column) => {
        initialValues[column] = "all";
      });

      setSelectedValues(initialValues);
      setChosenDemographic(initialValues);

      setRelevantColumns([...modifiedData.relevant_columns]);
      setData({
        ...modifiedData,
        relevant_columns: [...modifiedData.relevant_columns]
      });
      setDataCountry(countryName);
      setError(null);
    } catch (err) {
      setError(err.message);
      setRelevantColumns(null);
      setData(null);
      setDataCountry(null);
    } finally{
      setLoading(false);   
    }
  };

  async function loadDemographics(countryName) {
    setData(null);
    setSelectedValues({});
    setRelevantColumns(null);
    setColumnToRename(null);
    setLoading(true);

    if (countryName === "usa") {
      try {
        const attrData = await getMidtermAttributes();
        const stateNames = attrData.state_names || {};
        const column_unique_vals = {};

        attrData.attributes.forEach((col) => {
          const vals = attrData.values[col] || [];
          if (col === "state") {
            column_unique_vals[col] = [
              "all",
              ...vals.map((st) => ({
                value: st,
                label: stateNames[st] ? `${st} - ${stateNames[st]}` : st,
              })),
            ];
          } else {
            column_unique_vals[col] = ["all", ...vals];
          }
        });

        const initialValues = {};
        attrData.attributes.forEach((col) => {
          initialValues[col] = "all";
        });

        setSelectedValues(initialValues);
        setChosenDemographic(initialValues);
        setRelevantColumns([...attrData.attributes]);
        setData({
          relevant_columns: [...attrData.attributes],
          column_unique_vals,
        });
        setColumnToRename("none");
        setDataCountry(countryName);
        setError(null);
      } catch (err) {
        console.error("Failed to load midterm attributes:", err);
        setError(err.message);
        setRelevantColumns(null);
        setData(null);
        setDataCountry(null);
      } finally {
        setLoading(false);
      }
      return;
    }

    // fallback for other legacy countries
    getColumnToRename(countryName);
    getColumnsAndUniqueVals(countryName);
  }
  
  function handleDropdownChange(column, value) {
    if (selectedValues[column] === value) return; 

    const updated = { ...selectedValues, [column]: value };
    setSelectedValues(updated);
    setChosenDemographic(updated);
  }

  useEffect(() => {
    loadDemographics(country);
  }, [country]);

  const allNotNull = (...args) => args.every(v => v != null);

  return (
    <div className="DemographicChooserForPersona">
      {allNotNull(data, columnToRename) && !loading && dataCountry === country ?

      (
        <>
        {data.relevant_columns.map((column) => (
          <DemographicChoiceDropdown 
          key={`${dataCountry}_${column}`} 
          column={column} 
          choices={data.column_unique_vals[column] ?? []}
          onChange={(value) => handleDropdownChange(column, value)}
          columnToRename={columnToRename}
          />
        ))}
        </>
      )

      : (<Loader />)}
    </div>
  );
};

export default DemographicChooserForPersona;
