// not part of deployed website yet, page for downloading the data we use. UNFINISHED
import { useRef, useState } from 'react';
import { useInView } from "react-intersection-observer"
import { useTranslation, Trans } from 'react-i18next';

import './dataHubPage.css';
import downloadIcon from '../assets/svgs/downloadIcon.svg'

const availableCountries = ['netherlands', 'denmark', 'sweden']

const humanDataCitations = {
  apa7: "Ali, A., Jonaitis, D., Agarwal, S., Roskam, A., Corcoran, B., M\u00fcller, M., Xi, W., Tuls, J., Bleekemolen, S., Truong, P. Q. N., Miao, X., & Cerina, R. (2026). Unstructured interviews and survey responses of Dutch voters: Their views, issues, and media diet (Version 2) [Data set]. Harvard Dataverse. https://doi.org/10.7910/DVN/KOT9XX",
  bibtex: `@data{DVN/KOT9XX_2026,
author = {Ali, Ava and Jonaitis, Danielius and Agarwal, Shriya and Roskam, Alexandra and Corcoran, Brendan and M\u00fcller, Magdolna and Xi, Wenyi and Tuls, Jelle and Bleekemolen, Shanella and Truong, Pham Quynh Nhu and Miao, Xuan and Cerina, Roberto},
publisher = {Harvard Dataverse},
title = {{Unstructured interviews and survey responses of Dutch voters: their views, issues, and media diet}},
UNF = {UNF:6:TZjvp/X+7WUFeMUHKtWQcQ==},
year = {2026},
version = {V2},
doi = {10.7910/DVN/KOT9XX},
url = {https://doi.org/10.7910/DVN/KOT9XX}
}`
};
const stratificationFrameCitations = {
  sweden: {
    apa7: "Jonaitis, D., Agarwal, S., Roskam, A., Corcoran, B., Ali, A., & Cerina, R. (2026). Stratification frame for Sweden, 2026 parliamentary elections [Data set]. Mechanical Pollster. https://mechanical-pollster.com/...data hub",
    bibtex: `@data{jonaitis2026sweden,
  author = {Jonaitis, Danielius and Agarwal, Shriya and Roskam, Alexandra and Corcoran, Brendan and Ali, Ava and Cerina, Roberto},
  publisher = {Mechanical Pollster},
  title = {{Stratification Frame for Sweden, 2026 Parliamentary Elections.}},
  year = {2026},
  url = {mechanical-pollster.com/...data hub}
}`
  },
  netherlands: {
    apa7: "Jonaitis, D., Agarwal, S., Roskam, A., Corcoran, B., Ali, A., & Cerina, R. (2026). Stratification frame for the Netherlands, 2026 parliamentary elections [Data set]. Mechanical Pollster. https://mechanical-pollster.com/...data hub",
    bibtex: `@data{jonaitis2026dutch,
  author = {Jonaitis, Danielius and Agarwal, Shriya and Roskam, Alexandra and Corcoran, Brendan and Ali, Ava and Cerina, Roberto},
  publisher = {Mechanical Pollster},
  title = {{Stratification Frame for the Netherlands, 2026 Parliamentary Elections.}},
  year = {2026},
  url = {mechanical-pollster.com/...data hub}
}`
  },
  denmark: {
    apa7: "Jonaitis, D., Agarwal, S., Roskam, A., Corcoran, B., Ali, A., & Cerina, R. (2026). Stratification frame for Denmark, 2026 parliamentary elections [Data set]. Mechanical Pollster. https://mechanical-pollster.com/...data hub",
    bibtex: `@data{jonaitis2026danish,
  author = {Jonaitis, Danielius and Agarwal, Shriya and Roskam, Alexandra and Corcoran, Brendan and Ali, Ava and Cerina, Roberto},
  publisher = {Mechanical Pollster},
  title = {{Stratification Frame for Denmark, 2026 Parliamentary Elections.}},
  year = {2026},
  url = {mechanical-pollster.com/...data hub}
}`
  }
};

// quotation-mark bubble offering citation formats and pinning its selected citation after a sustained hover
function CitationBubble({ citations }) {
  const [isLoading, setIsLoading] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [isFormatMenuOpen, setIsFormatMenuOpen] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState(null);
  const hoverTimer = useRef(null);

  const clearHoverTimer = () => {
    window.clearTimeout(hoverTimer.current);
    hoverTimer.current = null;
    setIsLoading(false);
    setIsDismissed(false);
    setIsHovered(false);
  };

  const pinCitation = () => {
    setIsHovered(true);
    if (!selectedCitation || isPinned || isDismissed) return;
    setIsLoading(true);
    hoverTimer.current = window.setTimeout(() => {
      setIsPinned(true);
      setIsLoading(false);
      hoverTimer.current = null;
    }, 1000);
  };

  const closeCitation = () => {
    clearHoverTimer();
    setIsPinned(false);
    setIsDismissed(true);
    setSelectedCitation(null);
    setCopied(false);
  };

  const selectCitation = async (citation) => {
    try {
      await navigator.clipboard.writeText(citation);
      setSelectedCitation(citation);
      setIsFormatMenuOpen(false);
      setIsPinned(true);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Citation copy failed:', error);
    }
  };

  return (
    <div className="datahub-citation" onMouseEnter={pinCitation} onMouseLeave={clearHoverTimer}>
      <button type="button" className={`datahub-citation-bubble ${isLoading ? 'datahub-citation-loading' : ''}`} onClick={() => setIsFormatMenuOpen(!isFormatMenuOpen)} aria-label="Choose citation format" aria-expanded={isFormatMenuOpen} title="Choose citation format">&rdquo;</button>
      {isFormatMenuOpen && <div className="datahub-citation-menu">
        <button type="button" onClick={() => selectCitation(citations.apa7)}>APA 7</button>
        <button type="button" onClick={() => selectCitation(citations.bibtex)}>BibTeX</button>
      </div>}
      {selectedCitation && (isHovered || isPinned) && !isDismissed && <div className="datahub-citation-popup">
        <button type="button" className="datahub-citation-close" onClick={closeCitation} aria-label="Close citation" title="Close citation">&times;</button>
        <p>{copied ? 'Citation copied to clipboard.' : selectedCitation}</p>
        {copied && <p>{selectedCitation}</p>}
      </div>}
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
  const hasHumanBenchmarkData = selectedCountry === 'netherlands';

  return (
    <div className="DataHubPage unbounded-weight300">
        
        <div id="datahub-intro" className={hasHumanBenchmarkData ? '' : 'datahub-intro-no-human-benchmark'}>
            <h1>{t('datahubPage.intro.title')}</h1>
            {/* <p>{t('datahubPage.intro.text')}</p> */}
            <select value={selectedCountry} onChange={e => setSelectedCountry(e.target.value)}>
                {availableCountries.map(opt => (
                    <option key={opt} value={opt}>{t(`datahubPage.countries.${opt}`)}</option>
                ))}
            </select>
        </div>

        {hasHumanBenchmarkData && <>
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
                <p className='datahub-interview-timeframe'>{t('datahubPage.interview.timeframe2')}</p>
                <div className='datahub-data-buttonrow'>
                    <button onClick={() => downloadFieldworkData('main', 'transcript', selectedCountry)} className='datahub-download-button-light'>{t('datahubPage.interview.transcripts')}<img src={downloadIcon} alt="" /></button>
                    <CitationBubble citations={humanDataCitations} />
                </div>
                <div className='datahub-data-buttonrow'>
                    <button onClick={() => downloadFieldworkData('main', 'survey', selectedCountry)} className='datahub-download-button-light'>{t('datahubPage.interview.surveyData')}<img src={downloadIcon} alt="" /></button>
                    <button className='datahub-download-codebook'>{t('datahubPage.codebook')}<img src={downloadIcon} alt="" /></button>
                    <CitationBubble citations={humanDataCitations} />
                </div>
            </div>
        </div>

        <div className='datahub-colour-transition' id="dark-to-pink"></div>
        </>}

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
            </div>
        </div>

        <div className='datahub-colour-transition' id="pink-to-light"></div>

                <div id="datahub-stratification-frames" className={`datahub-section`}>
            <h1 ref={ref3} className={`datahub-section-header ${inView3 ? 'header-underline-appear' : ''}`}>{t('datahubPage.stratification.title', { country: countryName })}</h1>
            <p className="datahub-country-indicator">{t('datahubPage.interview.subtitle', { country: countryName })}</p>
            <p className="datahub-section-text">{t('datahubPage.stratification.text')}</p>

            <div className='datahub-data-buttonrow'>
                <button
                  className='datahub-download-button-light'
                  onClick={() => downloadStratificationFrame(selectedCountry)}
                >
                  {`${countryName} Frame`}
                  <img src={downloadIcon} alt="" />
                </button>
                <CitationBubble citations={stratificationFrameCitations[selectedCountry]} />
            </div>
        </div>

    </div>
  );
}

export default DataHubPage;