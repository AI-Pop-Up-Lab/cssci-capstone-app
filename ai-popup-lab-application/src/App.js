import { React } from 'react';
// eslint-disable-next-line
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';

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

function App() {

  return (
    <Router>

      <HeaderAndNavigation />
      {/* <PopupDisclaimer />  */}
      {/* Comment PopupDisclaimer out if it gets annoying in dev */}

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/personas" element={<PersonaPage />} />
        <Route path="/ethics" element={<EthicsPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/methods" element={<MethodsPage />} />
      </Routes>

      <Footer />
    </Router>
  );
}

export default App;