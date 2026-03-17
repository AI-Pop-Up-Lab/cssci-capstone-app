// import { useRef, useEffect, useState } from "react";
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';


import './footer.css';

function Footer() {

  

  return (
    <div className='Footer unbounded-weight300'>
      <div id="footer-left">
        <Link to="/ethics">Ethical Statement</Link>
        <Link to="/methods">Methods</Link>
        <Link to="/about">About Us</Link>
      </div>
      <div id="footer-right">
        <p id="footer-name">AI POLLSTER</p>
        <p id="footer-description">Reporting survey-style opinion estimates generated from synthetic personas</p>
      </div>
    </div>
  );
}

export default Footer;
