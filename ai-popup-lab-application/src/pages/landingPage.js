// import ApiTest from '../modules/apiTest';

import './landingPage.css';
import chartGraphic from '../assets/images/chartGraphic.png'
import personaPic_1 from '../assets/svgs/personaPic_1.svg'
import personaPic_2 from '../assets/svgs/personaPic_2.svg'

import PollingResults from '../modules/polling_results_modules/pollingResults';

function LandingPage() {
  return (
    <div className="LandingPage unbounded-weight300">
      <div id='landing-intro'>
        <p>LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA. UT ENIM AD MINIM VENIAM, QUIS NOSTRUD EXERCITATION ULLAMCO LABORIS NISI UT ALIQUIP EX EA COMMODO CONSEQUAT. DUIS AUTE IRURE DOLOR IN REPREHENDERIT IN VOLUPTATE VELIT ESSE CILLUM DOLORE EU FUGIAT NULLA PARIATUR. EXCEPTEUR SINT OCCAECAT CUPIDATAT NON PROIDENT, SUNT IN CULPA QUI OFFICIA DESERUNT MOLLIT ANIM ID EST LABORUM.</p>
        <img src={chartGraphic}></img>
      </div>
      
      <p id="landing-explorevotes">EXPLORE THE VOTES IN THE NETHERLANDS</p>
    
      <PollingResults />

      <div id='landing-explore-personas'>

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
                <p>How do you feel about current economic situation in The Netherlands?</p>
                <div id="example-user-message-bubbletick"></div>
              </div>
            </div>
            <div id='example-response-message-container'>
              <div id="example-response-message">
                <p>Honestly, it feels pretty stressful right now. As someone who’s unemployed, it seems like everything is getting more expensive while finding stable work is still tough. I worry a lot about paying rent and basic things like groceries. The Netherlands is still a good country in many ways, but the economic situation makes it feel uncertain and a bit overwhelming sometimes.</p>
                <div id="example-response-message-bubbletick"></div>
              </div>
            </div>
          </div>

        </div>

        <div id='land-expl-pers-bottom'>
          <button className='unbounded-weight300'>EXPLORE MORE PERSONAS <span>{'\u{1F782}'}</span></button>
        </div>

      </div>
    
    </div>
  );
}

export default LandingPage;
