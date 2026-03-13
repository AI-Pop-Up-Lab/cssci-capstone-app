import { useState, useEffect } from "react";
import axios from "axios";

import './personaChooser.css';

import Loader from "../loader";
import PersonaDetailCard from "./personaDetailCard";


function PersonaChooser({ data, chosenDemographic, countryName }) {

  const [filteredData, setFilteredData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const [relevantColumns, setRelevantColumns] = useState(null);
  const [error, setError] = useState(null);

  // useEffect(() => {
  //   console.log(data)
  // }, [data])


  // filter data through chosen demographics
  useEffect(() => {

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


  async function getRelevantColumns(){
    try {

      // FastAPI in testing is running on 127.0.0.1:8000
      const response = await axios.get(`http://127.0.0.1:8000/api/samples/columns_and_uniques?country=${countryName}`);


      setRelevantColumns(response.data.relevant_columns);
      setError(null);
    } catch (err) {
      setRelevantColumns(err.message);
      setRelevantColumns(null);
    }
  }

  useEffect(() => {
    getRelevantColumns(countryName);
  }, []);


  return (
    <div className="PersonaChooser">
      {!isLoading && 
      
        <>
        {filteredData.map((persona) => (
          <PersonaDetailCard
            key={persona.index}
            personaDetails={persona}
            relevantColumnsToShow={relevantColumns}
          />
        ))}
        </>
      
      }
      {isLoading && <Loader />}
      {Object.keys(filteredData).length < 1 && !isLoading && <h2 className="unbounded-weight300">No personas match your filters.</h2>}
    </div>
  );
};

export default PersonaChooser;