import { useState, useEffect, useRef} from "react";

import './personaDetailCard.css';

import Loader from "../loader";
import PersonaChat from "./personaChat";

import personaPic_1 from '../../assets/svgs/personaPic_1.svg'
import personaPic_2 from '../../assets/svgs/personaPic_2.svg'

function PersonaDetailCard({ personaDetails, relevantColumnsToShow, personaCountry }) {

  const [index, setIndex] = useState(personaDetails.index);
  const [filteredPersona, setFilteredPersona] = useState(

    filterColumns(personaDetails, relevantColumnsToShow)

    // relevantColumnsToShow
    //   ? Object.fromEntries(Object.entries(personaDetails).filter(([key]) => relevantColumnsToShow.includes(key)))
    //   : {}
  );

  const [showPersonaChat, setShowPersonaChat] = useState(false);

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

  // useEffect(() => {
  //   console.log(relevantColumnsToShow)
  // }, [relevantColumnsToShow]);

  useEffect(() => {
    setFilteredPersona(filterColumns(personaDetails, relevantColumnsToShow));
  }, [relevantColumnsToShow]);

  function randomSvgPFP(){
    const randNum = Math.random();
    if(randNum < 0.25){
      return personaPic_1
    } else if (randNum < 0.5){
      return personaPic_2
    } else if (randNum < 0.75){
      return personaPic_1
    } else{
      return personaPic_2
    }
  }

  // code to check if persona attribute direction needs to be flipped (for if potentially offscreen)

  const cardRef = useRef(null);
  const [flipBubble, setFlipBubble] = useState(false);

  const [randompfp] = useState(randomSvgPFP);

  useEffect(() => {
    const rect = cardRef.current.getBoundingClientRect();
    const middle = rect.left + rect.width / 2;
    setFlipBubble((middle + 370) > window.innerWidth); // 370px is set min-width of attribute bubble (.persona-info-bubble)
  }, []);

  return (
    <div className="PersonaDetailCardContainer">

      <div ref={cardRef} className={`PersonaDetailCard ${flipBubble ? 'flip' : ''}`}>

        <div className="personacard-fakeborder"></div>

        <img src={randompfp}></img>

        <div className="unbounded-weight300 persona-info-bubble">
          {filteredPersona ? Object.entries(filteredPersona).map(([key, value]) => (
              <div key={key}><p>{formatKey(key)}:</p><p>{value}</p></div>
            )) : <Loader />}

            <button onClick={() => setShowPersonaChat(!showPersonaChat)} className="unbounded-weight300 enter-personachat-button">START THE CHAT <span>{'\u{1F782}'}</span></button>
        </div>

      </div>

      {showPersonaChat && <PersonaChat 
          personaDetails={{ ...filteredPersona, index: index }}
          personaCountry={personaCountry}
          showChat={setShowPersonaChat}
        />}

    </div>
  );
};

export default PersonaDetailCard;