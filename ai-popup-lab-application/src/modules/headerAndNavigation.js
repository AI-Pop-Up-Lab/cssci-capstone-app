import { useState, React, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
// eslint-disable-next-line
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';

import './headerAndNavigation.css';
import LanguageSwitch from './languageSwitch';

function HeaderAndNavigation() {

  const { t } = useTranslation();

  const [navOpen, setNavOpen] = useState(false);
  const [darkModeOn, setDarkModeOn] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // detecting if scrolled at all
  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 0);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
      <header className={`${scrolled ? 'header-scrolled' : ''} ${navOpen ? 'nav-menu-open' : ''}`}>

        <div id='header-left'>

          <div id="header-text-left">
            <h1 className="unbounded-weight300">MECHANICAL <span>POLLSTER</span></h1>
            <p className="unbounded-weight300">{t('header.tagline')}</p>
          </div>

          <div id='hamburger-and-nav'>

            <div id="hamburger-container" className={navOpen  ? 'nav-open' : ''} onClick={() => setNavOpen(!navOpen)}>
              <div id="hamburger-left"></div>
              <div id="hamburger-right"></div>
            </div>

            <div id='nav-links' className='unbounded-weight400'>
              <Link to="/" onClick={() => setNavOpen(!navOpen)}>{t('header.links.home')}</Link>
              <Link to="/polling" onClick={() => setNavOpen(!navOpen)}>{t('header.links.polling')}</Link>
              <Link to="/personas" onClick={() => setNavOpen(!navOpen)}>{t('header.links.personas')}</Link>
              <Link to="/about" onClick={() => setNavOpen(!navOpen)}>{t('header.links.about')}</Link>
              <Link to="/ethics" onClick={() => setNavOpen(!navOpen)}>{t('header.links.ethics')}</Link>
            </div>
          </div>
        
        </div>

        <div id='header-right'>

          <div id='lang-and-modeswitch'>
            <LanguageSwitch />
            {/* <div className={darkModeOn ? 'modeslideon' : ''} id="modeswitch" onClick={() => setDarkModeOn(!darkModeOn)}>
              <div id="modeswitch-slider"></div>
            </div> */}
          </div>
        </div>  
      </header>
  );
}

export default HeaderAndNavigation;