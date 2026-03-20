// import ApiTest from '../modules/apiTest';

import './landingPage.css';
import chartGraphic from '../assets/images/chartGraphic.png'

import PollingResults from '../modules/polling_results_modules/pollingResults';
import PersonaChatExample from '../modules/personaChatExample';

function LandingPage() {
  return (
    <div className="LandingPage unbounded-weight300">
      <div id='landing-intro'>
        <p>This is the AI Pollster, where public opinion is visualised through synthetic personas. Explore graphs which visualise the results of the AI polling, and chat with the personas which form the polling data on the persona chat page, to understand intentions and motivations behind polling decisions.</p>
        <img src={chartGraphic}></img>
      </div>
      
      <p id="landing-explorevotes">EXPLORE THE VOTES IN THE NETHERLANDS</p>
    
      <PollingResults />

      <PersonaChatExample includeLink={true} />

  
    </div>
  );
}

export default LandingPage;
