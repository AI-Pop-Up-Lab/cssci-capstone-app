import { useState, React } from 'react';
// eslint-disable-next-line
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';

import './headerAndNavigation.css';

function HeaderAndNavigation() {

  const [navOpen, setNavOpen] = useState(false);

  return (
      <header>
        <h1 className="unbounded-weight300">AI POLLSTER</h1>
        <div id="hamburger-container" className={navOpen  ? 'nav-open' : ''} onClick={() => setNavOpen(!navOpen)}>
          <div id="hamburger-left"></div>
          <div id="hamburger-right"></div>
        </div>

        <div id="nav-menu" className={navOpen ? 'nav-menu-open' : ''}>
            <div id="nav-menu-links" className='unbounded-weight400'>
                <Link to="/" onClick={() => setNavOpen(!navOpen)}>Home</Link>
                <Link to="/about" onClick={() => setNavOpen(!navOpen)}>About</Link>
                <Link to="/data" onClick={() => setNavOpen(!navOpen)}>Data (placeholder name)</Link>
            </div>
        </div>
      </header>
  );
}

export default HeaderAndNavigation;