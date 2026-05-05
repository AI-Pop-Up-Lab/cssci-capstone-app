import { useInView } from "react-intersection-observer"
import { useTranslation, Trans } from 'react-i18next';

import './aboutPage.css';

import personaGeneration from '../assets/svgs/personaGeneration.svg'
import publicAccess from '../assets/svgs/publicAccess.svg'
import scientificGrounding from '../assets/svgs/scientificGrounding.svg'

import popupLabLogo from '../assets/images/pop_up_logo.png' 

function AboutPage() {

  const { t } = useTranslation();

  const useInViewAnimation = (threshold = 1) => {
    const [ref, inView] = useInView({ threshold, triggerOnce: true })
    return [ref, inView]
  }

  const [ref1, inView1] = useInViewAnimation();
  const [ref2, inView2] = useInViewAnimation();
  const [ref3, inView3] = useInViewAnimation();
  const [ref4, inView4] = useInViewAnimation();


  return (
    <div className="AboutPage unbounded-weight300">
      {/* <h1>About Us</h1>
      <p>This project is a collaboration between Computational Social Science and Cultural Data & AI students at the University of Amsterdam, under the supervision of Dr. Roberto Cerina.</p>
      <p>Opinion polls are at dire straits. Nonresponse rates are as high as 94%, and nonignorable nonresponse plagues the field. This means that it is increasingly more difficult to build get representative samples of public opinion. We believe getting a good sense of the public's views on politics is important for the quality of democracy. It informs researchers of societal trends, politicians of public sentiment, and citizens of where they stand relative to those around them.</p>
      <h2>The mechanical pollster</h2>
      <p>To this end, we have developed a mechanical pollster that uses data collected from national statistics offices and national election studies. We then use large language models to synthesise a persona who responds to a series of questions about political issues. These personas are sampled randomly from a pool of synthetic individuals, meaning we can generate a diverse set of opinions without some of the issues inherent in traditional polling methods. The sample is then post-stratified to produce a granular, area-level representation of public opinion on certain questions.</p>
      <p>This website also offers the ability to talk to the synthetic personas with a chat interface. This means that a user can gain insights into not just what a certain demographic of people think, but why they might hold those views, thus enriching the opinion poll beyond a simple answer.</p>
      <h2>The team</h2>
      <p>Ava Ali, Alexandra Roskam, Brendan Corcoran, Danielius Jonaitis, Jelle Tuls, Maddy Müller, Shriya Agrawal, Shanella Bleekemolen, Nhu Truong, Wenyi Xi, and Xuan Miao.</p> */}
    
      <div id="about-intro">
        <div id='about-title'>
          <h1>DATA <span className='unbounded-weight300'>The AI Pop-Up Lab</span> AND</h1>
          <h1>TRANSPARENCY</h1>
          <h1>THROUGH AI</h1>
          <div id='about-briefing'>{t('aboutPage.description')}</div>
        </div>
      </div>
    
      <h1 ref={ref1} className={`about-header ${inView1 ? 'header-underline-appear' : ''}`}>{t('aboutPage.mission.title')}</h1>
      <div id="about-first-paragraph">
        <p className='about-sectiontext'>
          <Trans
              i18nKey="aboutPage.mission.content"
              components={{ br: <br/> }}
            />
        </p>
        <img src={popupLabLogo}></img>
      </div>

      <h1 ref={ref2} className={`about-header ${inView2 ? 'header-underline-appear' : ''}`}>{t('aboutPage.whatwedo.title')}</h1>
      <p className='about-sectiontext'>
        <Trans
              i18nKey="aboutPage.whatwedo.content"
              components={{ strong: <strong/> }}
        />
      </p>
      
      <div id='about-whatwedo'>
        <div className='about-whatwedo-item'>
          <div className='whatwedo-item-photo'><img src={personaGeneration} alt='persona generation'></img></div>
          <div className='whatwedo-item-text'>
            <h2>{t('aboutPage.whatwedo.items.personaGeneration.title')}</h2>
            <p>{t('aboutPage.whatwedo.items.personaGeneration.content')}</p>
          </div>
        </div>
        <div className='about-whatwedo-item'>
          <div className='whatwedo-item-photo'><img src={scientificGrounding} alt='scientific grounding'></img></div>
          <div className='whatwedo-item-text'>
            <h2>{t('aboutPage.whatwedo.items.scientificGrounding.title')}</h2>
            <p>{t('aboutPage.whatwedo.items.scientificGrounding.content')}</p>
          </div>
        </div>
        <div className='about-whatwedo-item'>
          <div className='whatwedo-item-photo'><img src={publicAccess} alt='public access'></img></div>
          <div className='whatwedo-item-text'>
            <h2>{t('aboutPage.whatwedo.items.publicAccess.title')}</h2>
            <p>{t('aboutPage.whatwedo.items.publicAccess.content')}</p>
          </div>
        </div>
      </div>

      <h1 ref={ref4} className={`about-header ${inView4 ? 'header-underline-appear' : ''}`}>{t('aboutPage.commitments.title')}</h1>
      
      <div id='about-commitments'>
        <p>
          <span>{t('aboutPage.commitments.items.privacy.title')}</span>
          {t('aboutPage.commitments.items.privacy.content')}
        </p>
        <p>
          <span>{t('aboutPage.commitments.items.partisanship.title')}</span>
          {t('aboutPage.commitments.items.partisanship.content')}
        </p>
        <p>
          <span>{t('aboutPage.commitments.items.openScience.title')}</span>
          {t('aboutPage.commitments.items.openScience.content')}
        </p>
      </div>

      <h1 ref={ref3} className={`about-header ${inView3 ? 'header-underline-appear' : ''}`}>{t('aboutPage.team.title')}</h1>
      <p id='about-team' className='about-sectiontext'>
        <Trans
              i18nKey="aboutPage.team.content"
              components={{ br: <br/> }}
            />
      </p>

    </div>
  );
}

export default AboutPage;