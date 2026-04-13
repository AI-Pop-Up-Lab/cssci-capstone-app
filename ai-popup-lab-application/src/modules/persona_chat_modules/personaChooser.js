import { useState, useEffect, memo, useMemo } from "react";
import axios from "axios";

import './personaChooser.css';

import Loader from "../loader";
import PersonaDetailCard from "./personaDetailCard";


function PersonaChooser({ data, chosenDemographic, countryName, relevantColumns }) {

  const [filteredData, setFilteredData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const [error, setError] = useState(null);

  // filter data through chosen demographics
  useEffect(() => {

    if (!chosenDemographic || Object.keys(chosenDemographic).length === 0) return; // skips if data isn't ready yet

    setIsLoading(true);

    const timeout = setTimeout(() => { // small timeout of 0ms lets the render of the loader take place
      const result = data.filter(row =>
        Object.entries(chosenDemographic).every(([column, filterValue]) =>
          filterValue === 'all' || row[column] === filterValue
        )
      );
      setFilteredData(result);
      setIsLoading(false);
    }, 0);

    return () => clearTimeout(timeout); // cleanup if chosenDemographic changes mid-filter, gets called if data or chosenDemographic updates
  }, [data, chosenDemographic]);


  // async function getRelevantColumns(){
  //   try {

  //     // FastAPI in testing is running on 127.0.0.1:8000
  //     const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/samples/columns_and_uniques?country=${countryName}`);


  //     setRelevantColumns(response.data.relevant_columns);
  //     setError(null);
  //   } catch (err) {
  //     setError(err.message);
  //     setRelevantColumns(null);
  //   }
  // }

  // useEffect(() => {
  //   setFilteredData([]);
  // }, [countryName]);

  const cards = useMemo(() =>
    filteredData.map((persona) => (
      <PersonaDetailCard
        key={`${countryName}_${persona.index}`}
        personaDetails={persona}
        relevantColumnsToShow={relevantColumns}
        personaCountry={countryName}
      />
    )),
    [filteredData, relevantColumns, countryName]
  );

  return (
    <div className="PersonaChooser">
      {!isLoading && 
      
        <>
        {cards}
        </>
      
      }
      {(isLoading || data.length === 0) && <Loader />}
      {filteredData.length < 1 && !isLoading && data.length > 0 && (
        <h2 className="unbounded-weight300">No personas match your filters.</h2>
      )}
    </div>
  );
};

export default PersonaChooser;
