/* 
Page where the user can select a country, and filter through demographics of the synthetic sample of that country. 
They can then enter a chat with the selected persona, to ask questions through an LLM acting as the
persona about political motivation and voting behaviour.
*/
import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from 'react-router-dom';
import { useTranslation, Trans } from 'react-i18next';
import axios from "axios";

import './personaPage.css';

import PersonaChatExample from '../modules/personaChatExample.js';
import DemographicChooserForPersona from '../modules/persona_chat_modules/demographicChooserForPersona.js';
import PersonaChooser from "../modules/persona_chat_modules/personaChooser.js";
import CountrySwitch2 from '../modules/countrySwitch2';
import Loader from "../modules/loader";

import { getCountryData } from '../utils/fetch_data';
import { getChosenCountry, setChosenCountry } from '../utils/set_country';

function PersonaPage() {

  const { t } = useTranslation();

  const [selectedCountry, setSelectedCountry] = useState(() => getChosenCountry() ?? "usa");
  const [countryData, setCountryData] = useState(null);
  
  const [chosenPersonaDemographic, setChosenPersonaDemographic] = useState({});

  useEffect(() => {
    let cancelled = false;

    getCountryData(selectedCountry)
      .then((data) => {
        if (!cancelled) setCountryData(data);
      })
      .catch((err) => {
        console.error('Failed to load country data:', err);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedCountry]);

  function handleCountryChange(country) {
    setChosenCountry(country);
    setSelectedCountry(country);
  }

  // callback to call the function for setting the demographic chosen from the options in the select elements
  const handleSetChosenPersonaDemographic = useCallback((value) => {
    setChosenPersonaDemographic(value);
  }, []);

  // scroll to top of page when loads, as many personas puts you at bottom of massive page
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="PersonaPage">

      {/* componnent to switch country */}
      <CountrySwitch2 
        setCountry={handleCountryChange} 
        selectedCountry={selectedCountry}
      />

      {/* exmaple of persona chat */}
      {countryData ? (
        <PersonaChatExample includeLink={false} countryData={countryData} />
      ) : (
        <Loader />
      )}


      <div id="persona-selection">
        <div id="selection-explanation">
          <h1 className="unbounded-weight400">{t('personaPage.title')}</h1>
          {/* <p className="unbounded-weight300">
            <Trans
              i18nKey="personaPage.description"
              values={{ dataLength, modifiedCountry }}
              components={{ br: <br/> }}
            />
          </p> */}
          <p>Coming soon...</p>
        </div>

        {/* dropdowns to filter demographic */}
        {/* {selectedCountry ? <DemographicChooserForPersona
        key={selectedCountry}
        setChosenDemographic={handleSetChosenPersonaDemographic}
        country={selectedCountry}
        setRelevantColumns={setRelevantColumns}
        /> : <Loader />} */}

        {/* Display of personae that match demographic */}
        {/* {data && selectedCountry ? <PersonaChooser 
        data={responseData}
        chosenDemographic={chosenPersonaDemographic}
        countryName={selectedCountry}
        relevantColumns={relevantColumns ? [...relevantColumns] : null}
        /> : <Loader />} */}

      </div>
    </div>
  );
}

export default PersonaPage;
