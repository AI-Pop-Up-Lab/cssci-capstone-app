import { useRef, useEffect, useState } from "react";

import closeCross from '../assets/images/closeCross.png';
import './popupDisclaimer.css';

function PopupDisclaimer() {

  const [closed, setClosed] = useState(false);
  const popupRef = useRef(null);

  useEffect(() => {
    if (popupRef.current) {
      const width = popupRef.current.offsetWidth;
      const height = popupRef.current.offsetHeight;

      popupRef.current.style.left = `calc(50% - ${width / 2}px)`;
      popupRef.current.style.top = `calc(50% - ${height / 2}px)`;
    }
  }, []);

  function closePopup(){
    if (popupRef.current) {
      setClosed(true);
    };
  };

  function handleAnimationEnd(){
    if (closed && popupRef.current) {
      popupRef.current.remove();
    };
  };

  return (
    <div ref={popupRef} onAnimationEnd={handleAnimationEnd} className={`PopupDisclaimer ${closed ? 'popupFadeOut' : ''}`}>
        <div id="popupDisclaimerTop">
            <img onClick={closePopup} src={closeCross} alt="button to close disclaimer popup" id="popupDisclaimerClose"/>
        </div>
        <div id="popupDisclaimerContent">
            <p className="unbounded-weight300">This platform uses AI-simulated personas to estimate public opinion based on official census data. These personas are not real human beings, and no personally identifiable data of living individuals is used. Surveys are calibrated to ensure the reliability of the prediction results.</p>
        </div>
    </div>
  );
}

export default PopupDisclaimer;
