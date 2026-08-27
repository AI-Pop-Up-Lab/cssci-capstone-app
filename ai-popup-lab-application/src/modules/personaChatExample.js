// component that shows an example of what the persona chat looks like and can be used for

import './personaChatExample.css';

import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import personaPic_1 from '../assets/svgs/personaPic_1.svg'
import personaPic_2 from '../assets/svgs/personaPic_2.svg'
import linkArrow from '../assets/images/linkArrow.png'

function PersonaChatExample({includeLink, countryData}) {

  const { t } = useTranslation();

  let countryName = countryData.alias
  countryName = countryName.charAt(0).toUpperCase() + countryName.slice(1);


  return (
    <div className={`PersonaChatExample unbounded-weight300 ${includeLink ? '' : 'addExampleMargin'}`}>
        <div id='land-expl-pers-top'>
          

          <div id="example-persona-card">
            <img src={personaPic_1}></img>
            <p className='unbounded-weight400' id="example-persona-name">{t('personaChatExample.exampleName')}</p>
            <p className='example-persona-attr'>{t('personaChatExample.exampleAge')}</p>
            <p className='example-persona-attr'>{t('personaChatExample.exampleEducation')}</p>
            <p className='example-persona-attr'>{t('personaChatExample.exampleOccupation')}</p>
          
            <div id="persona-warning-hover">
              <p className='unbounded-weight400'>!</p>
            </div>

            <div id="persona-warning-overlay">
              <p className='unbounded-weight400'>{t('personaChatExample.warningPart1')}<span style={{fontWeight: 600}}>{t('personaChatExample.warningPart2')}</span>{t('personaChatExample.warningPart3')}</p>
            </div>
          </div>

          <div id="example-persona-chat">
            <div id='example-user-message-container'>
              <div id="example-user-message">
                <p>{t('personaChatExample.exampleUserMessage', { country: countryName})}</p>
                <div id="example-user-message-bubbletick"></div>
              </div>
            </div>
            <div id='example-response-message-container'>
              <div id="example-response-message">
                <p>{t('personaChatExample.exampleResponse', { country: countryName})}</p>
                <div id="example-response-message-bubbletick"></div>
              </div>
            </div>
          </div>

        </div>

        {/* 
        when added as child component, includeLink parameter can be passed which 
        determines if the link to the persona chat page is shown or not
        for this example being shown on the persona page itself for example, not necessary. confusing even. flabbergasting. gives me shudders.
        */}
        <div id='land-expl-pers-bottom' className={includeLink ? '' : 'dontShowPersonaLink'}>
          <Link to={`/personas`}><button className='unbounded-weight300'>{t('personaChatExample.explorePersonas')} <img alt='right facing arrow' src={linkArrow}></img></button></Link>
        </div>
    </div>
  );
}

export default PersonaChatExample;