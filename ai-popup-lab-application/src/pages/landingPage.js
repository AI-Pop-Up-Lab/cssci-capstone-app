import PopupDisclaimer from '../modules/popupDisclaimer';
import ApiTest from '../modules/apiTest';

import './landingPage.css';


function LandingPage() {
  return (
    <div className="LandingPage">
      <p>hey</p>
      <br></br>
      <ApiTest />

      <PopupDisclaimer />
    </div>
  );
}

export default LandingPage;
