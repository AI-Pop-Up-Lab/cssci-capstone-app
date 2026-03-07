import { React } from 'react';
// eslint-disable-next-line
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';

import './App.css';
import HeaderAndNavigation from './modules/headerAndNavigation';
import PopupDisclaimer from './modules/popupDisclaimer';

// other pages to route to
import LandingPage from './pages/landingPage';
import AboutPage from './pages/aboutPage';

function App() {

  return (
    <Router>

      <HeaderAndNavigation />
      <PopupDisclaimer />

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/data" element={<LandingPage />} />
      </Routes>
    </Router>
  );
}

export default App;