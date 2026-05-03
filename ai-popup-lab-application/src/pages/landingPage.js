// import ApiTest from '../modules/apiTest';
import { useState, useEffect } from "react";
import { useInView } from 'react-intersection-observer';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import axios from 'axios';

import './landingPage.css';
import chartGraphic from '../assets/images/chartGraphic.png'
import linkArrow from '../assets/images/linkArrow.png'
import pollie from '../assets/svgs/pollie.svg'

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

  function modifyCountryNameEdgeCases(country){
    let modifiedCountry;

    if(country === 'netherlands'){
      modifiedCountry = 'the Netherlands';
    }else{
      modifiedCountry = country;
    }

    return modifiedCountry
  }

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

  useEffect(() => {
    setData(null);

    getCountrySample(selectedCountry);
  }, [selectedCountry]);

  useEffect(() => {
    setResponseData(data?.data ?? []);
  }, [data]);

  // code for typing effect on elements

  const [bottomDelayed, setBottomDelayed] = useState(false);
  const [bottomRef, bottomInView] = useInView({ threshold: 0.7, triggerOnce: true, skip: !bottomDelayed });

  function useTypingEffect(text, speed = 18, startDelay = 0, trigger = true) {
    const [displayed, setDisplayed] = useState('');

    useEffect(() => {
      if (!trigger) return;
      setDisplayed('');
      let i = 0;
      const timeout = setTimeout(() => {
        const interval = setInterval(() => {
          setDisplayed(text.slice(0, i + 1));
          i++;
          if (i >= text.length) clearInterval(interval);
        }, speed);
        return () => clearInterval(interval);
      }, startDelay);
      return () => clearTimeout(timeout);
    }, [text, trigger]);

    return displayed;
  }

  // delay to stop lower messages begin typing won load, for the second where the graph is not loaded so it takes the lower text as being in vie
  useEffect(() => {
    const t = setTimeout(() => setBottomDelayed(true), 1000);
    return () => clearTimeout(t);
  }, []);

  // text for elements

  const msg1 = "Hello! Welcome to Mechanical Pollster. We use AI to explore how people think about important issues, so voters can better understand public opinion and the perspectives around them.";
  const msg2 = "Choose a country to explore the votes:";
  const msg3 = "You can also chat with one of synthetically generated personae to discover the reasoning behind their vote.";
  const msg4 = "Here is an example:";

  const speed = 30; // speed of each letter types in ms
  const gap = 300; // ms pause between messages

  const typed1 = useTypingEffect(msg1, speed, 0);
  const typed2 = useTypingEffect(msg2, speed, msg1.length * speed + gap);
  const typed3 = useTypingEffect(msg3, speed, 0, bottomInView);
  const typed4 = useTypingEffect(msg4, speed, msg3.length * speed + gap, bottomInView);


  return (
    <div className="LandingPage unbounded-weight300">
      {/* <div id='landing-intro'>
        <p>This is the AI Pollster, where public opinion is visualised through synthetic personas. Explore graphs which visualise the results of the AI polling, and chat with the personas which form the polling data on the persona chat page, to understand intentions and motivations behind polling decisions.</p>
        <img src={chartGraphic}></img>
      </div> */}

      {/* <CountrySwitch setCountry={setSelectedCountry} selectedCountry={selectedCountry}/>
      
      <p id="landing-explorevotes">EXPLORE THE VOTES IN {modifyCountryNameEdgeCases(selectedCountry).toUpperCase()}</p>
    
      <PollingResults 
        selectedCountry={selectedCountry}
        setSelectedCountry={setSelectedCountry}  
      />

      <PersonaChatExample includeLink={true} country={selectedCountry}  /> */}

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
        <Link to={`/polling/?country=${selectedCountry}`}><button className='unbounded-weight300'>EXPLORE MORE POLLS <img alt='right facing arrow' src={linkArrow}></img></button></Link>
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
