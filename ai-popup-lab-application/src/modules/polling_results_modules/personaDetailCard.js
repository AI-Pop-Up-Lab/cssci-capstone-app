import { useState, useEffect } from "react";

import './personaDetailCard.css';

import Loader from "../loader";

function PersonaDetailCard({ personaDetails, relevantColumnsToShow }) {

  const [index, setIndex] = useState([personaDetails.index]);
  const [filteredPersona, setFilteredPersona] = useState(

    filterColumns(personaDetails, relevantColumnsToShow)

    // relevantColumnsToShow
    //   ? Object.fromEntries(Object.entries(personaDetails).filter(([key]) => relevantColumnsToShow.includes(key)))
    //   : {}
  );

  function filterColumns(persona, relCol){

    if(!relCol){
      return {}
    }

    relCol.push('vote_2030');
    return Object.fromEntries(Object.entries(persona).filter(([key]) => relCol.includes(key)))

  }

  const formatKey = (key) => {
    const withSpaces = key.replace(/_/g, ' ');
    return withSpaces.charAt(0).toUpperCase() + withSpaces.slice(1);
  };

  useEffect(() => {
    console.log(relevantColumnsToShow)
  }, [relevantColumnsToShow]);


  return (
    <div className="PersonaDetailCard">
      <h1 className="unbounded-weight300">Persona {parseInt(index)+1}</h1>

      <div>

        <div className="personaAttributesContainer">
          {filteredPersona ? Object.entries(filteredPersona).map(([key, value]) => (
            <div key={key}><p className="unbounded-weight400">{formatKey(key)}:</p><p className="unbounded-weight300">{value}</p></div>
          )) : <Loader />}
        </div>
        
        <button className="startChatButton">Chat</button>

      </div>
    </div>
  );
};

export default PersonaDetailCard;