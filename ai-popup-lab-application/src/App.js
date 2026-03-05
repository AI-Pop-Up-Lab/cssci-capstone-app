import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';

import './App.css';
import LandingPage from './pages/landingPage';

function App() {
  return (
    <Router>
      {/* <nav>
        <ul>
          <li><Link to="/">Home</Link></li>
          <li><Link to="/other-page">Page 2</Link></li>
          <li><Link to="/other-other-page">Page 3</Link></li>
        </ul>
      </nav> 
        This would be how the navigation would work once multiple pagers exist
      */}
      <header>
        <h1 className="unbounded-weight300">AI POLLSTER</h1>
        <div>
          
        </div>
      </header>
      <Routes>
        <Route path="/" element={<LandingPage />} />
      </Routes>
    </Router>
  );
}

export default App;