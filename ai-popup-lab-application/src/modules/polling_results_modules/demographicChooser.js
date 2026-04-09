import { useState, useEffect } from "react";
import axios from "axios";

import './demographicChooser.css';

import Loader from '../loader';

function DemographicChooser({setChosenDemographic, country}) {

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [dynamicSentences, setDynamicSentences] = useState(null);
  const [dynamicSentencesError, setDynamicSentencesError] = useState(null);

  const [searchSentenceOrder, setSearchSentenceOrder] = useState(null);
  const [searchSentenceOrderError, setSearchSentenceOrderError] = useState(null);

  const [allPlaceholders, setAllPlaceholders] = useState(null);
  const [allPlaceholdersError, setAllPlaceholdersError] = useState(null);

  const [selectedValues, setSelectedValues] = useState({});

  const [allLabels, setAllLabels] = useState(null);
  const [sentenceAndChooser, setSentenceAndChooser] = useState(null);

  const [columnToDrop, setColumnToDrop] = useState(null);
  const [columnToDropError, setColumnToDropError] = useState(null); 

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

  async function getDynamicSentences(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/column_sentences?country=${countryName}`);
      
      const response_data = response.data;

      const dynamicSentencesData = response_data.column_sentences;

      setDynamicSentences(dynamicSentencesData);
      setDynamicSentencesError(null);
    } catch (err) {
      setDynamicSentencesError(err.message);
      setDynamicSentences(null);
    }
  };

  async function getAllPlaceholders(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/all_placeholder?country=${countryName}`);
      
      const response_data = response.data;

      const allPlaceholdersData = response_data.all_placeholder;

      setAllPlaceholders(allPlaceholdersData);
      setAllPlaceholdersError(null);
    } catch (err) {
      setAllPlaceholdersError(err.message);
      setAllPlaceholders(null);
    }
  };

  async function getSearchSentenceOrder(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/search_sentence_order?country=${countryName}`);
      
      const response_data = response.data;

      const searchSentenceOrderData = response_data.search_sentence_order;

      setSearchSentenceOrder(searchSentenceOrderData);
      setSearchSentenceOrderError(null);
    } catch (err) {
      setSearchSentenceOrderError(err.message);
      setSearchSentenceOrder(null);
    }
  };

  async function getColumnToDrop(countryName){
    try {

      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/dynamicdata/nextGE_col_name?country=${countryName}`);
      
      const response_data = response.data;

      const next_GE_colname = response_data.column_to_rename;

      setColumnToDrop(next_GE_colname);
      setColumnToDropError(null);
    } catch (err) {
      setColumnToDropError(err.message);
      setColumnToDrop(null);
    }
  };

  function handleDropdownChange(column, value) {
    const updated = { ...selectedValues, [column]: value };
    setSelectedValues(updated);
    setChosenDemographic(updated);
  }

  useEffect(() => {
    setData(null);
    setDynamicSentences(null);
    setSearchSentenceOrder(null);
    setAllPlaceholders(null);
    setAllLabels(null);
    setSelectedValues({});

    getColumnsAndUniqueVals(country);
    getDynamicSentences(country);
    getSearchSentenceOrder(country);
    getAllPlaceholders(country);
  }, [country]);

  useEffect(() => {

    if(allPlaceholders == null) return;

    const allLabelsObj = Object.fromEntries(
      Object.entries(allPlaceholders).map(([key, value]) => [key, { all: value }])
    );

    setAllLabels(allLabelsObj);

  }, [allPlaceholders]);

  // useEffect(() => {
  //   console.log(data);
  // }, [data]);

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
      {searchSentenceOrder && allLabels && dynamicSentences && data ? (
        <p className="dc-sentence">
          What would the results look like if{" "}
          {searchSentenceOrder.map((col, i) => {
            const [before, after] = dynamicSentences[col].split("REPLACE");
            const isLast = i === searchSentenceOrder.length - 1;
            return (
              <span key={col}>
                {' '}{before}{mkSelect(col)}{after}{isLast ? '' : ','}{' '}
              </span>
            );
          })}
          could vote?
        </p>
      ) : (
        <Loader />
      )}
    </div>
  );
};

export default DemographicChooser;