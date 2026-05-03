import { useInView } from "react-intersection-observer"

import './aboutPage.css';

import personaGeneration from '../assets/svgs/personaGeneration.svg'
import publicAccess from '../assets/svgs/publicAccess.svg'
import scientificGrounding from '../assets/svgs/scientificGrounding.svg'

import popupLabLogo from '../assets/images/pop_up_logo.png' 

function AboutPage() {

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
          <div id='about-briefing'>We are a team of researchers and students dedicated to making public opinion transparent, auditable, and easy to understand through AI.</div>
        </div>
      </div>
    
      <h1 ref={ref1} className={`about-header ${inView1 ? 'header-underline-appear' : ''}`}>Our Mission</h1>
      <div id="about-first-paragraph">
        <p className='about-sectiontext'>Opinion polls are at dire straits. Nonresponse rates are as high as 94%, and nonignorable nonresponse plagues the field. This means that it is increasingly more difficult to build get representative samples of public opinion. We believe getting a good sense of the public's views on politics is important for the quality of democracy. It informs researchers of societal trends, politicians of public sentiment, and citizens of where they stand relative to those around them.<br></br><br></br>
        Our work is non-commercial by design and is best understood as a form of digital activism. Our core premise is that a polity that is better informed about the shape of public opinion is better equipped to address collective action problems. We also hope this work can foster greater understanding across social groups.
        We are committed to research that is transparent, socially useful, and guided by the public good.
        </p>
        <img src={popupLabLogo}></img>
      </div>

      <h1 ref={ref2} className={`about-header ${inView2 ? 'header-underline-appear' : ''}`}>What We Do</h1>
      <p className='about-sectiontext'>We bridge the gap between complex social science and everyday conversation. By using <strong>synthetic personas</strong>, we create a "living" representation of census data that users can interact with directly.</p>
      
      <div id='about-whatwedo'>
        <div className='about-whatwedo-item'>
          <div className='whatwedo-item-photo'><img src={personaGeneration} alt='persona generation'></img></div>
          <div className='whatwedo-item-text'>
            <h2>Persona Generation</h2>
            <p>We build a panel of thousands of simulated individuals based on official, non-identifiable census and survey data.</p>
          </div>
        </div>
        <div className='about-whatwedo-item'>
          <div className='whatwedo-item-photo'><img src={scientificGrounding} alt='scientific grounding'></img></div>
          <div className='whatwedo-item-text'>
            <h2>Scientific Grounding</h2>
            <p>The synthetic respondents are treated under the same real-world survey science we would use with real participants. Survey data is post-stratified with MrP to produce rich estimates.</p>
          </div>
        </div>
        <div className='about-whatwedo-item'>
          <div className='whatwedo-item-photo'><img src={publicAccess} alt='public access'></img></div>
          <div className='whatwedo-item-text'>
            <h2>Public Access</h2>
            <p>We provide a free, interactive web app where anyone can explore results, chat with personas, and download the data for their own research.</p>
          </div>
        </div>
      </div>

      <h1 ref={ref4} className={`about-header ${inView4 ? 'header-underline-appear' : ''}`}>Our Commitments</h1>
      
      <div id='about-commitments'>
        <p>
          <span>Privacy First</span>
          We never use personally identifiable data about living individuals. All our personas are simulated models.
        </p>
        <p>
          <span>Non-Partisanship</span>
          Our visual identity and data reporting are strictly neutral. We do not provide political recommendations or targeted calls to action.
        </p>
        <p>
          <span>Open Science</span>
          We share our methods, our version history, and our source data to ensure the project remains fully reproducible.
        </p>
      </div>

      <h1 ref={ref3} className={`about-header ${inView3 ? 'header-underline-appear' : ''}`}>Our Team</h1>
      <p id='about-team' className='about-sectiontext'>
        The Mechanical Pollster is a tool developed by the AI Pop-up Lab @ the University of Amsterdam, an academic, not-for-profit teaching and research hub within the Computational Social Science (CSSci) Programme.
        We teach, study, and build AI for public opinion research with a clear public purpose: to create tools that support democratic functioning for the benefit of the public.<br></br><br></br>
        Ava Ali, Alexandra Roskam, Roberto Cerina, Brendan Corcoran, Danielius Jonaitis, Jelle Tuls, Maddy Müller, Shriya Agrawal, Shanella Bleekemolen, Nhu Truong, Wenyi Xi, and Xuan Miao.</p>

    </div>
  );
}

export default AboutPage;