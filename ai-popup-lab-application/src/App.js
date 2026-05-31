import { React, useEffect } from 'react';
// eslint-disable-next-line
import { BrowserRouter as Router, Route, Routes, Link, useLocation  } from 'react-router-dom';

import './App.css';
import HeaderAndNavigation from './modules/headerAndNavigation';
import PopupDisclaimer from './modules/popupDisclaimer';
import Footer from './modules/footer.js';

// other pages to route to
import LandingPage from './pages/landingPage';
import AboutPage from './pages/aboutPage';
import MethodsPage from './pages/methodsPage.js'
import PersonaPage from './pages/personaPage.js'
import EthicsPage from './pages/ethicsPage.js'
import PollPage from './pages/pollPage.js';
import DataHubPage from './pages/dataHubPage.js'

function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}

function App() {

  return (
    <Router>
      <ScrollToTop />

      <HeaderAndNavigation />
      <PopupDisclaimer /> 
      {/* Comment PopupDisclaimer out if it gets annoying in dev */}

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/personas" element={<PersonaPage />} />
        <Route path="/ethics" element={<EthicsPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/methods" element={<MethodsPage />} />
        <Route path="/polling" element={<PollPage />} />
        <Route path="/datahub" element={<DataHubPage />} />
      </Routes>

      <Footer />
    </Router>
  );
}

export default App;