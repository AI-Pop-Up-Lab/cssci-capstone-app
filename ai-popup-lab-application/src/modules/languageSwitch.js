// button and code for switching languages

import { useState, useRef, React, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import './languageSwitch.css';
import closeCross from '../assets/images/closeCross.png';

const languageOptions = [
  { name: "english", abbreviation: "en", flagFile: require(`../assets/images/flags/united_kingdom.png`)},
  { name: "nederlands", abbreviation: "nl", flagFile: require(`../assets/images/flags/netherlands.png`)},
  { name: "sweden", abbreviation: "swe", flagFile: require(`../assets/images/flags/sweden.png`)},
  { name: "denmark", abbreviation: "dk", flagFile: require(`../assets/images/flags/denmark.png`)},
]

function LanguageSwitch() {

  const { i18n } = useTranslation();
  const [popupOpen, setPopupOpen] = useState(false);

  // using i18n library to switch language using locale .jsons
  const changeLanguage = (lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('lang', lang);
    setPopupOpen(false);
  };

  // flips the popupOpen bool which if true shows the popup for selecting a language
  const togglePopup = () => {
    setPopupOpen(!popupOpen);
  };

  return (
      <div className='LanguageSwitch'>
        {/* button displayed always */}
        <button className='unbounded-weight300' onClick={togglePopup}>{i18n.language.toUpperCase()}</button>

        {/* popup that opens with options for available languages */}
        <div className={popupOpen ? "langPopupOpen" : ""} id='langSwitch-popup'>

          <div id='langSwitch-popup-top'>
            <img onClick={togglePopup} src={closeCross} alt="button to close language selection popup" />
          </div>

          <div className='unbounded-weight400' id='langSwitch-popup-bottom'>
            {languageOptions.map((lang) => (
              <div onClick={() => changeLanguage(lang.abbreviation)} className='langOption' key={lang.abbreviation} onClick={() => changeLanguage(lang.abbreviation)}>
                <img src={lang.flagFile} alt={lang.name} />
                <p>{lang.name.toUpperCase()}</p>
              </div>
            ))}
          </div>

          <div id='langSwitch-popup-connector'></div>

        </div>
      </div>
  );
}

export default LanguageSwitch;