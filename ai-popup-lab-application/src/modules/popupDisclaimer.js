import { useRef, useEffect, useState } from "react";

import closeCross from '../assets/images/closeCross.png';
import './popupDisclaimer.css';

function PopupDisclaimer() {

  const [closed, setClosed] = useState(false);
  const [unmounted, setUnmounted] = useState(false);
  const popupRef = useRef(null);

  // useEffect(() => {
  //   if (popupRef.current) {
  //     const width = popupRef.current.offsetWidth;
  //     const height = popupRef.current.offsetHeight;

  //     popupRef.current.style.left = `calc(50% - ${width / 2}px)`;
  //     popupRef.current.style.top = `calc(50% - ${height / 2}px)`;
  //   }
  // }, []);

  function closePopup(){
    setClosed(true);
  };

  function handleAnimationEnd(){
    if (closed) {
      setUnmounted(true);
    };
  };

  if (unmounted) return null;

  return (
    <div ref={popupRef} className={`PopupDisclaimer ${closed ? 'popupFadeOut' : ''}`}  onAnimationEnd={handleAnimationEnd}>
      <div id="popupDisclaimerBox" >
        <div id="popupDisclaimerTop">
            <img onClick={closePopup} src={closeCross} alt="button to close disclaimer popup" id="popupDisclaimerClose"/>
        </div>
        <div id="popupDisclaimerContent">
            <p className="unbounded-weight300">This platform uses AI-simulated personae based on public census data. These personae are not real humans, and no personal data of individuals is used.</p>
        </div>
      </div>
    </div>
  );
}

export default PopupDisclaimer;
