// import { useRef, useEffect, useState } from "react";
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import './footer.css';

function Footer() {

  const { t } = useTranslation();

  return (
    <div className='Footer unbounded-weight300'>
      <div id="footer-left">
        <Link to="/about">{t('footer.links.about')}</Link>
        <Link to="/ethics">{t('footer.links.ethics')}</Link>
        {/* <Link to="/methods">Methods</Link> */}
      </div>
      <div id="footer-right">
        <p id="footer-name">MECHANICAL POLLSTER</p>
        <p id="footer-description">{t('footer.tagline')}</p>
      </div>
    </div>
  );
}

export default Footer;
