/*
popup that is shown when the page is entered, but not when switching pages
must be clicked away, so that users must look at it
explains that the personae are not real people
*/

import { useRef, useEffect, useState } from "react";
import { useTranslation } from 'react-i18next';

import closeCross from '../assets/images/closeCross.png';
import './popupDisclaimer.css';

function PopupDisclaimer() {

  const { t } = useTranslation();

  const [closed, setClosed] = useState(false);
  const [unmounted, setUnmounted] = useState(false);
  const popupRef = useRef(null);

  // OLD CODE WHICH TRIED TO CENTER IT WITH CSS position:fixed BUT WAS REPLACED WITH FLEXBOX IN CSS USING A PARENT ELEMENT
  // useEffect(() => {
  //   if (popupRef.current) {
  //     const width = popupRef.current.offsetWidth;
  //     const height = popupRef.current.offsetHeight;

  //     popupRef.current.style.left = `calc(50% - ${width / 2}px)`;
  //     popupRef.current.style.top = `calc(50% - ${height / 2}px)`;
  //   }
  // }, []);

  // close popup when called
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
            <p className="unbounded-weight300">{t('disclaimerPopup')}</p>
        </div>
      </div>
    </div>
  );
}

export default PopupDisclaimer;
