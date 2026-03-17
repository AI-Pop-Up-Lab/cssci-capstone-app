import { useState, React, useEffect } from 'react';
// eslint-disable-next-line
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';

import './headerAndNavigation.css';

function HeaderAndNavigation() {

  const [navOpen, setNavOpen] = useState(false);

  const [darkModeOn, setDarkModeOn] = useState(false);

  useEffect(() => {
    console.log(darkModeOn)
  }, [darkModeOn]);

  return (
      <header className={navOpen ? 'nav-menu-open' : ''}>

        <div id='header-left'>
          <h1 className="unbounded-weight300">AI POLLSTER</h1>
          <p className="unbounded-weight300">Reporting survey-style opinion estimates generated from synthetic personas</p>
        </div>

        <div id='header-right'>

          <div id='hamburger-and-nav'>

            <div id="hamburger-container" className={navOpen  ? 'nav-open' : ''} onClick={() => setNavOpen(!navOpen)}>
              <div id="hamburger-left"></div>
              <div id="hamburger-right"></div>
            </div>

            <div id='nav-links' className='unbounded-weight400'>
              <Link to="/" onClick={() => setNavOpen(!navOpen)}>homepage</Link>
              <Link to="/personas" onClick={() => setNavOpen(!navOpen)}>persona explorer</Link>
              <Link to="/ethics" onClick={() => setNavOpen(!navOpen)}>ethics statement</Link>
              <Link to="/about" onClick={() => setNavOpen(!navOpen)}>about us</Link>
            </div>
          </div>

          <div id='lang-and-modeswitch'>
            <button className='unbounded-weight300'>ENGLISH</button>
            <div className={darkModeOn ? 'modeslideon' : ''} id="modeswitch" onClick={() => setDarkModeOn(!darkModeOn)}>
              <div id="modeswitch-slider"></div>
            </div>
          </div>
        </div>  
      </header>
  );
}

export default HeaderAndNavigation;