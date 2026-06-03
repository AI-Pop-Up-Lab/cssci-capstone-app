// Landing page, explains the purpose of website, shows one polling result graph as an example, and a mockup of the persona chat.

// import ApiTest from '../modules/apiTest';
import { useState, useEffect, useRef } from "react";
import { useInView } from 'react-intersection-observer';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

import './landingPage.css';
import chartGraphic from '../assets/images/chartGraphic.png'
import linkArrow from '../assets/images/linkArrow.png'
import pollie from '../assets/svgs/pollie.svg'

// components used on this page
import PollingResults from '../modules/polling_results_modules/pollingResults';
import PersonaChatExample from '../modules/personaChatExample';
import CountrySwitch from '../modules/countrySwitch';
import Loader from "../modules/loader";
import VoteProjection from "../modules/polling_results_modules/voteProjection";
import CountrySwitch2 from "../modules/countrySwitch2";


function LandingPage() {

  const [selectedCountry, setSelectedCountry] = useState("netherlands");

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const [responseData, setResponseData] = useState(null);

  const { t, i18n } = useTranslation();
  const [typingKey, setTypingKey] = useState(i18n.language);

  // for country names that are different in data than its real name, this function corrects it
  function modifyCountryNameEdgeCases(country){
    let modifiedCountry;

    if(country === 'netherlands'){
      modifiedCountry = 'the Netherlands';
    }else{
      modifiedCountry = country;
    }

    return modifiedCountry
  }

  // gets the synthetical panel results for a selected country from the backend API
  async function getCountrySample(countryName){
    try {
      

      // console.log(`Getting polling results for ${countryName}...`);

      // FastAPI in testing is running on 127.0.0.1:8000
      // In deployment, the environment variable REACT_APP_API_URL is in the github repository secrets and gets added in build from the workflow file (deploy-frontend.yml)
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/samples/country_sample?country=${countryName}`);
      setData(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  // updates data when selected country chages
  useEffect(() => {
    setData(null);

    getCountrySample(selectedCountry);
  }, [selectedCountry]);

  // when data is received, properly store it and avoid cases where data is null
  useEffect(() => {
    setResponseData(data?.data ?? []);
  }, [data]);

  // retrigger typing animation when language is changed
  useEffect(() => {
    setTypingKey(i18n.language);
  }, [i18n.language]);


  // code for typing effect on elements
  const [bottomDelayed, setBottomDelayed] = useState(false);
  const [bottomRef, bottomInView] = useInView({ threshold: 0.7, triggerOnce: true, skip: !bottomDelayed });

  function useTypingEffect(text, speed = 18, startDelay = 0, trigger = true, resetKey = '') {
    const [displayed, setDisplayed] = useState('');
    const timeoutRef = useRef(null);
    const intervalRef = useRef(null);

    useEffect(() => {
      clearTimeout(timeoutRef.current);
      clearInterval(intervalRef.current);
      setDisplayed('');

      if (!trigger) return;

      let i = 0;
      timeoutRef.current = setTimeout(() => {
        intervalRef.current = setInterval(() => {
          setDisplayed(text.slice(0, i + 1));
          i++;
          if (i >= text.length) clearInterval(intervalRef.current);
        }, speed);
      }, startDelay);

      return () => {
        clearTimeout(timeoutRef.current);
        clearInterval(intervalRef.current);
      };
    }, [text, trigger, resetKey]);

    return displayed;
  }

  // delay to stop lower messages begin typing on load, for the second where the graph is not loaded so it takes the lower text as being in vie
  useEffect(() => {
    const t = setTimeout(() => setBottomDelayed(true), 1000);
    return () => clearTimeout(t);
  }, []);

  // text for elements from localisation json
  const msg1 = t('landingPage.msg1');
  const msg2 = t('landingPage.msg2');
  const msg3 = t('landingPage.msg3');
  const msg4 = t('landingPage.msg4');

  const speed = 30; // speed of each letter types in ms
  const gap = 300; // ms pause between messages

  const typed1 = useTypingEffect(msg1, speed, 0, typingKey);
  const typed2 = useTypingEffect(msg2, speed, msg1.length * speed + gap, typingKey);
  const typed3 = useTypingEffect(msg3, speed, 0, bottomInView, typingKey);
  const typed4 = useTypingEffect(msg4, speed, msg3.length * speed + gap, bottomInView, typingKey);


  return (
    <div className="LandingPage unbounded-weight300">
      {/*
      
      OLD HTML
      <div id='landing-intro'>
        <p>This is the AI Pollster, where public opinion is visualised through synthetic personas. Explore graphs which visualise the results of the AI polling, and chat with the personas which form the polling data on the persona chat page, to understand intentions and motivations behind polling decisions.</p>
        <img src={chartGraphic}></img>
      </div> 

       <CountrySwitch setCountry={setSelectedCountry} selectedCountry={selectedCountry}/>
      
      <p id="landing-explorevotes">EXPLORE THE VOTES IN {modifyCountryNameEdgeCases(selectedCountry).toUpperCase()}</p>
    
      <PollingResults 
        selectedCountry={selectedCountry}
        setSelectedCountry={setSelectedCountry}  
      />

      <PersonaChatExample includeLink={true} country={selectedCountry}  /> 
      */}

      <div className="landingPageTop">
        <img className='pollie' src={pollie}></img>
        <div className="landingPageMessageSection">
          <p className="landingPageMessage">{typed1}</p>
          <p className="landingPageMessage">{typed2}&nbsp;</p>
          <CountrySwitch2 selectedCountry={selectedCountry} setCountry={setSelectedCountry}/>
        </div>
      </div>

      <div id="landingVoteProjContainer">
        {data ? <VoteProjection pollingData={responseData} country={selectedCountry} /> : <Loader />}
        <Link to={`/polling/?country=${selectedCountry}`}><button className='unbounded-weight300'>{t('landingPage.explorePolls')}<img alt='right facing arrow' src={linkArrow}></img></button></Link>
      </div>

      <div id="landingPageBottomMessages">
        <img className='pollie' src={pollie}></img>
        <div className="landingPageMessageSection" ref={bottomRef}>
          <p className="landingPageMessage">{typed3}</p>
          <p className="landingPageMessage">{typed4}&nbsp;</p>
        </div>
      </div>

      <PersonaChatExample includeLink={true} country={selectedCountry} />

    </div>
  );
}

export default LandingPage;
