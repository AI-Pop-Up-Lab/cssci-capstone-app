// import { useRef, useEffect, useState } from "react";
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';


import './footer.css';

function Footer() {

  

  return (
    <div className='Footer unbounded-weight300'>
      <div id="footer-left">
        <Link to="/about">About Us</Link>
        <Link to="/ethics">Ethics</Link>
        {/* <Link to="/methods">Methods</Link> */}
      </div>
      <div id="footer-right">
        <p id="footer-name">MECHANICAL POLLSTER</p>
        <p id="footer-description">Estimating public opinion from synthetic personae</p>
      </div>
    </div>
  );
}

export default Footer;
