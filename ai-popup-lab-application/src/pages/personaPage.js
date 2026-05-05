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

const countryOptions = [
  'netherlands',
  'sweden',
  'denmark'
]

function modifyCountryNameEdgeCases(country){
  let modifiedCountry;

  if(country === 'netherlands'){
    modifiedCountry = 'the Netherlands';
  }else{
    modifiedCountry = country;
  }

  return modifiedCountry
}

function PersonaPage() {

  const { t } = useTranslation();

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [responseData, setResponseData] = useState(null);

  const [modifiedCountry, setModifiedCountry] = useState(null);
  const dataLength = useMemo(() => responseData?.length ?? 0, [responseData]);

  const [searchParams] = useSearchParams();

  const paramCountry = countryOptions.includes(searchParams.get('country'))
  ? searchParams.get('country')
  : countryOptions[0];
  const [selectedCountry, setSelectedCountry] = useState(paramCountry); 

  const [relevantColumns, setRelevantColumns] = useState(null);

  const [chosenPersonaDemographic, setChosenPersonaDemographic] = useState({});

  const handleSetChosenPersonaDemographic = useCallback((value) => {
    setChosenPersonaDemographic(value);
  }, []);

  // function to get country sample data from backend
  async function getCountrySample(countryName){
    try {

      // console.log(`Getting polling results for ${countryName}...`);

      // FastAPI in testing is running on 127.0.0.1:8000
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/samples/country_sample?country=${countryName}`);
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  useEffect(() => {
    setData(null);      
    setResponseData([]); 
    getCountrySample(selectedCountry);
  }, [selectedCountry]);

  useEffect(() => {

    let modCountry = modifyCountryNameEdgeCases(selectedCountry);
    modCountry = modCountry.charAt(0).toUpperCase() + modCountry.slice(1);

    setModifiedCountry(modCountry);

  }, [selectedCountry])
  
  useEffect(() => {
    setResponseData(data?.data ?? []);
  }, [data]);

  // scroll to top of page when loads, as many personas puts you at bottom of massive page
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="PersonaPage">

      <CountrySwitch2 setCountry={setSelectedCountry} selectedCountry={selectedCountry}/>

      { selectedCountry && 
        <PersonaChatExample includeLink={false} country={selectedCountry} />
      }


      <div id="persona-selection">
        <div id="selection-explanation">
          <h1 className="unbounded-weight400">{t('personaPage.title')}</h1>
          <p className="unbounded-weight300">
            <Trans
              i18nKey="personaPage.description"
              values={{ dataLength, modifiedCountry }}
              components={{ br: <br/> }}
            />
          </p>
        </div>

        {selectedCountry ? <DemographicChooserForPersona
        key={selectedCountry}
        setChosenDemographic={handleSetChosenPersonaDemographic}
        country={selectedCountry}
        setRelevantColumns={setRelevantColumns}
        /> : <Loader />}

        {data && selectedCountry ? <PersonaChooser 
        data={responseData}
        chosenDemographic={chosenPersonaDemographic}
        countryName={selectedCountry}
        relevantColumns={relevantColumns ? [...relevantColumns] : null}
        /> : <Loader />}

      </div>
    </div>
  );
}

export default PersonaPage;
