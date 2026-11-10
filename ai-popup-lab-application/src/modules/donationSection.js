import { useTranslation } from 'react-i18next';

import './donationSection.css';
import pollie from '../assets/svgs/pollie.svg';

function DonationSection() {

  const { t } = useTranslation();

  return (
    <section className="DonationSection unbounded-weight300">

      <div className="donation-heading">
        <img
          className="donation-pollie"
          src={pollie}
          alt=""
        />

        <div className="donation-title">
          <h1>{t('donationSection.title')}</h1>
          <h2>{t('donationSection.subtitle')}</h2>
        </div>
      </div>

      <div className="donation-text">
        <p>{t('donationSection.description')}</p>
        <p>{t('donationSection.donationMessage')}</p>
      </div>

      <a
        className="donation-link"
        href="https://www.illc.uva.nl/Forms/Mechanical-Pollster-Donation-Form/"
        target="_blank"
        rel="noopener noreferrer"
      >
        <button>{t('donationSection.button')}</button>
      </a>

    </section>
  );
}

export default DonationSection;