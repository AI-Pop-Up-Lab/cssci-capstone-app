// The footer of every page, including links to the about and ethics page, and the name and tagline of the project/site.

// import { useRef, useEffect, useState } from "react";
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import './footer.css';
import xLogo from '../assets/svgs/xLogo.svg';
import instagramLogo from'../assets/svgs/instagramLogo.svg';

const footerSocialLinks = {
  instagram: {
    "src": instagramLogo,
    "alt": "Link to our instagram page",
    "href": "https://www.instagram.com/aipopuplab/"
  },
  x: {
    "src": xLogo,
    "alt": "Link to our X page",
    "href": "https://x.com/aipopuplab"
  }
}

function Footer() {

  const { t } = useTranslation();

  return (
    <div className='Footer unbounded-weight300'>
      <div id="footer-left">
        {/* <Link to="/about">{t('footer.links.about')}</Link> */}
        <Link to="/ethics">{t('footer.links.ethics')}</Link>
        <Link to="/terms">{t('footer.links.terms')}</Link>
        {/* <Link to="/methods">Methods</Link> */}
        <div id="footer-social">
          {Object.entries(footerSocialLinks).map(([key, { src, alt, href }]) => (
            <a key={key} href={href} target="_blank" rel="noopener noreferrer">
              <img src={src} alt={alt} />
            </a>
          ))}
        </div>
      </div>
      <div id="footer-right">
        <p id="footer-name">MECHANICAL POLLSTER</p>
        <p id="footer-description">{t('footer.tagline')}</p>
      </div>
    </div>
  );
}

export default Footer;
