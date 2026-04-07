import './personaChatExample.css';

import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';

import personaPic_1 from '../assets/svgs/personaPic_1.svg'
import personaPic_2 from '../assets/svgs/personaPic_2.svg'
import linkArrow from '../assets/images/linkArrow.png'

function PersonaChatExample({includeLink, country}) {

  function modifyCountryNameEdgeCases(country){
    let modifiedCountry;

    if(country === 'netherlands'){
      modifiedCountry = 'the Netherlands';
    }else{
      modifiedCountry = country;
    }

    return modifiedCountry
  }

  let modifiedCountry = modifyCountryNameEdgeCases(country)
  modifiedCountry = modifiedCountry.charAt(0).toUpperCase() + modifiedCountry.slice(1);


  return (
    <div className="PersonaChatExample unbounded-weight300">
        <div id='land-expl-pers-top'>
          

          <div id="example-persona-card">
            <img src={personaPic_1}></img>
            <p className='unbounded-weight400' id="example-persona-name">Synthetic Persona</p>
            <p className='example-persona-attr'>Age: 26</p>
            <p className='example-persona-attr'>Education: High school</p>
            <p className='example-persona-attr'>Occupation: Unemployed</p>
          
            <div id="persona-warning-hover">
              <p className='unbounded-weight400'>!</p>
            </div>

            <div id="persona-warning-overlay">
              <p className='unbounded-weight400'>THESE PERSONAS ARE  <span style={{fontWeight: 600}}>NOT REAL HUMAN BEINGS</span>, AND NO PERSONALLY IDENTIFIABLE DATA OF LIVING INDIVIDUALS IS USED. </p>
            </div>
          </div>

          <div id="example-persona-chat">
            <div id='example-user-message-container'>
              <div id="example-user-message">
                <p>How do you feel about current economic situation in {modifiedCountry}?</p>
                <div id="example-user-message-bubbletick"></div>
              </div>
            </div>
            <div id='example-response-message-container'>
              <div id="example-response-message">
                <p>Honestly, it feels pretty stressful right now. As someone who’s unemployed, it seems like everything is getting more expensive while finding stable work is still tough. I worry a lot about paying rent and basic things like groceries. {modifiedCountry} is still a good country in many ways, but the economic situation makes it feel uncertain and a bit overwhelming sometimes.</p>
                <div id="example-response-message-bubbletick"></div>
              </div>
            </div>
          </div>

        </div>

        <div id='land-expl-pers-bottom' className={includeLink ? '' : 'dontShowPersonaLink'}>
          <Link to="/personas"><button className='unbounded-weight300'>EXPLORE MORE PERSONAS <img alt='right facing arrow' src={linkArrow}></img></button></Link>
        </div>
    </div>
  );
}

export default PersonaChatExample;