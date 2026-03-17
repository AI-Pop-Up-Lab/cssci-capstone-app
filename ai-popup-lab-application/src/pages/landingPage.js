// import ApiTest from '../modules/apiTest';

import './landingPage.css';
import chartGraphic from '../assets/images/chartGraphic.png'

import PollingResults from '../modules/polling_results_modules/pollingResults';
import PersonaChatExample from '../modules/personaChatExample';

function LandingPage() {
  return (
    <div className="LandingPage unbounded-weight300">
      <div id='landing-intro'>
        <p>LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA. UT ENIM AD MINIM VENIAM, QUIS NOSTRUD EXERCITATION ULLAMCO LABORIS NISI UT ALIQUIP EX EA COMMODO CONSEQUAT. DUIS AUTE IRURE DOLOR IN REPREHENDERIT IN VOLUPTATE VELIT ESSE CILLUM DOLORE EU FUGIAT NULLA PARIATUR. EXCEPTEUR SINT OCCAECAT CUPIDATAT NON PROIDENT, SUNT IN CULPA QUI OFFICIA DESERUNT MOLLIT ANIM ID EST LABORUM.</p>
        <img src={chartGraphic}></img>
      </div>
      
      <p id="landing-explorevotes">EXPLORE THE VOTES IN THE NETHERLANDS</p>
    
      <PollingResults />

      <PersonaChatExample includeLink={true} />

  
    </div>
  );
}

export default LandingPage;
