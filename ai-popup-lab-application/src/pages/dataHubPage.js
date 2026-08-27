// not part of deployed website yet, page for downloading the data we use. UNFINISHED
import { useState } from 'react';
import { useInView } from "react-intersection-observer"
import { useTranslation, Trans } from 'react-i18next';

import './dataHubPage.css';
import downloadIcon from '../assets/svgs/downloadIcon.svg'

const availableCountries = ['netherlands', 'denmark', 'sweden']

// citation shown in the hover bubble next to the human-benchmark downloads
const interviewCitation = "Fieldhouse, E., Green, J., Evans, G., Mellon, J., Prosser, C., de Geus, R., Bailey, J. (2022). British Election Study, 2019: Post-Election Random Probability Survey. [data collection]. UK Data Service. SN: 8875, DOI: 10.5255/UKDA-SN-8875-1"

// quotation-mark bubble that reveals a citation popup on hover/focus
function CitationBubble({ citation }) {
  return (
    <div className="datahub-citation">
      <button type="button" className="datahub-citation-bubble" aria-label="citation">&rdquo;</button>
      <p className="datahub-citation-popup">{citation}</p>
    </div>
  );
}

// function for downloading a file
const downloadFile = async (filename, data) => {

  const blob = await data.blob();
  
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

function DataHubPage() {

  const { t } = useTranslation();

  // function returning a reference and bool for an element, triggering when in view (to trigger an animation by enabling a class)
  const useInViewAnimation = (threshold = 1) => {
    const [ref, inView] = useInView({ threshold, triggerOnce: true })
    return [ref, inView]
  }

  // function to receive stratification frame file from backend API using country
  const downloadStratificationFrame = async (country) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/download/country_frame_raw?country=${country}`);
      if (!response.ok) throw new Error(`Download failed with status ${response.status}`);

      const filename = `${country}_stratification_frame.csv`;
      await downloadFile(filename, response);
    } catch (error) {
      console.error('Stratification frame download failed:', error);
      alert(t('datahubPage.downloadError'));
    }
  };

  // function to receive fieldwork data file from backend API using the type of study (pilot or main), data type (transcripts or survey) and selected country
  const downloadFieldworkData = async (studyType, dataType, country) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/download/fieldwork_file?studyType=${studyType}&dataType=${dataType}&country=${country}`);
      if (!response.ok) throw new Error(`Download failed with status ${response.status}`);

      const disposition = response.headers.get('Content-Disposition');
      const filename = disposition?.split('filename=')[1]?.replace(/"/g, '') ?? 'download.csv';

      await downloadFile(filename, response);
    } catch (error) {
      console.error('Fieldwork data download failed:', error);
      alert(t('datahubPage.downloadError'));
    }
  };

  const [ref1, inView1] = useInViewAnimation();
  const [ref2, inView2] = useInViewAnimation();
  const [ref3, inView3] = useInViewAnimation();

  const [selectedCountry, setSelectedCountry] = useState(availableCountries[0]);

  // translated display name of the selected country, used to make clear which country's data is shown
  const countryName = t(`datahubPage.countries.${selectedCountry}`);

  return (
    <div className="DataHubPage unbounded-weight300">
        
        <div id="datahub-intro">
            <h1>{t('datahubPage.intro.title')}</h1>
            {/* <p>{t('datahubPage.intro.text')}</p> */}
            <select value={selectedCountry} onChange={e => setSelectedCountry(e.target.value)}>
                {availableCountries.map(opt => (
                    <option key={opt} value={opt}>{t(`datahubPage.countries.${opt}`)}</option>
                ))}
            </select>
        </div>

        <div id="datahub-interview-data" className={`datahub-section`}>
            <h1 ref={ref1} className={`datahub-section-header ${inView1 ? 'header-underline-appear' : ''}`}>{t('datahubPage.interview.title', { country: countryName })}</h1>
            <p className="datahub-country-indicator">{t('datahubPage.interview.subtitle', { country: countryName })}</p>
            <p className="datahub-section-text">
                <Trans
                i18nKey="datahubPage.interview.text"
                components={{ span: <span/> }}
                />
            </p>
            
            <div className="datahub-interview-set">
                <p className='datahub-interview-timeframe'>{t('datahubPage.interview.timeframe1')}</p>
                <div className='datahub-data-buttonrow'>
                    <button onClick={() => downloadFieldworkData('pilot', 'transcript', selectedCountry)} className='datahub-download-button-light'>{t('datahubPage.interview.transcripts')}<img src={downloadIcon} alt="" /></button>
                    <CitationBubble citation={interviewCitation} />
                </div>
                <div className='datahub-data-buttonrow'>
                    <button onClick={() => downloadFieldworkData('pilot', 'survey', selectedCountry)} className='datahub-download-button-light'>{t('datahubPage.interview.surveyData')}<img src={downloadIcon} alt="" /></button>
                    <button className='datahub-download-codebook'>{t('datahubPage.codebook')}<img src={downloadIcon} alt="" /></button>
                    <CitationBubble citation={interviewCitation} />
                </div>
            </div>

            <div className="datahub-interview-set">
                <p className='datahub-interview-timeframe'>{t('datahubPage.interview.timeframe2')}</p>
                <div className='datahub-data-buttonrow'>
                    <button onClick={() => downloadFieldworkData('main', 'transcript', selectedCountry)} className='datahub-download-button-light'>{t('datahubPage.interview.transcripts')}<img src={downloadIcon} alt="" /></button>
                    <CitationBubble citation={interviewCitation} />
                </div>
                <div className='datahub-data-buttonrow'>
                    <button onClick={() => downloadFieldworkData('main', 'survey', selectedCountry)} className='datahub-download-button-light'>{t('datahubPage.interview.surveyData')}<img src={downloadIcon} alt="" /></button>
                    <button className='datahub-download-codebook'>{t('datahubPage.codebook')}<img src={downloadIcon} alt="" /></button>
                    <CitationBubble citation={interviewCitation} />
                </div>
            </div>
        </div>

        <div className='datahub-colour-transition' id="dark-to-pink"></div>

        <div id="datahub-survey-data" className={`datahub-section`}>
            <h1 ref={ref2} className={`datahub-section-header ${inView2 ? 'header-underline-appear' : ''}`}>{t('datahubPage.survey.title')}</h1>
            <p className="datahub-section-text">
                <Trans
                values={{ country: countryName }}
                i18nKey="datahubPage.survey.text"
                components={{ br: <br/> }}
                />
            </p>
        
            <div className='datahub-data-buttonrow'>
                <button className='datahub-download-button-dark'>{t('datahubPage.survey.title')}<img src={downloadIcon} alt="" /></button>
                <button className='datahub-download-codebook'>{t('datahubPage.codebook')}<img src={downloadIcon} alt="" /></button>
            </div>
        </div>

        <div className='datahub-colour-transition' id="pink-to-light"></div>

        <div id="datahub-stratification-frames" className={`datahub-section`}>
            <h1 ref={ref3} className={`datahub-section-header ${inView3 ? 'header-underline-appear' : ''}`}>{t('datahubPage.stratification.title')}</h1>
            <p className="datahub-section-text">{t('datahubPage.stratification.text')}</p>
        
            {availableCountries.map(country => (
              <div key={country} className='datahub-data-buttonrow'>
                <button
                  className='datahub-download-button-light'
                  onClick={() => downloadStratificationFrame(country)}
                >
                  {`${country.charAt(0).toUpperCase() + country.slice(1)} Frame`}
                  <img src={downloadIcon} alt="" />
                </button>
              </div>
            ))}
        </div>

    </div>
  );
}

export default DataHubPage;