import { useState } from 'react';

import './ethicsPage.css';
import carouselArrow from '../assets/images/carouselArrow.png'

import biasIcon from '../assets/images/biasIcon.png'
import privacyIcon from '../assets/images/privacyIcon.png'
import epistemicIcon from '../assets/images/epistemicIcon.png'
import democracyIcon from '../assets/images/democracyIcon.png'
import representationIcon from '../assets/images/representationIcon.png'
import transparencyIcon from '../assets/svgs/transparencyIcon.svg'
import securityIcon from '../assets/images/securityIcon.png'
import governanceIcon from '../assets/images/governanceIcon.png'

function EthicsPage() {

  const cardValues = [
    {
      name: "Algorithmic Fairness",
      text: "Subgroup predictions are calibrated to minimise errors for granular segments of the population. A constitutional AI approach is implemented in the chat to ensure our personae behave in ways that are representative but not stereotypical.",
      icon: biasIcon
    },
    {
      name: "Ethical Data Use",
      text: <>Survey data is collected to calibrate our AI under informed consent protocols following the ethical research standards of the <a href='https://aihr.uva.nl/about-aihr/ethics-committee/ethics-committee.html' target='_blank' rel='noopener noreferrer'>FGw</a> at the UvA. No personally identifiable information is used in persona construction.</>,
      icon: privacyIcon
    },
    {
      name: "Epistemic Responsibility",
      text: "Persona responses are designed to be grounded in stored synthetic profiles, with epistemic boundaries built in to the chat pipeline.",
      icon: epistemicIcon
    },
    {
      name: "Preventing Democratic Harm",
      text: "The tool is designed to democratise access to polling insights, helping users understand why different voter groups hold the views they do. Synthetic status is permanently visible throughout all interactions to prevent misuse. Avatars are kept abstract as a reminder that these are simulations, not real people.",
      icon: democracyIcon
    },
    {
      name: "Fair Representation",
      text: 'Census data and other representative surveys are used to generate random samples of the population of interest, these are then analysed with statistical tools such as MrP (multi-level regression and post-stratification) to ensure representative inference across demographic subgroups.',
      icon: representationIcon
    },
    {
      name: "Transparency",
      text: "Every result shows where the data comes from, which version of the system produced it, and when. A plain-language methods page explains how the tool works from start to finish.",
      icon: transparencyIcon
    },
    {
      name: "Robustness & Security",
      text: "Automated checks powered by LLMs are embedded in the chat interface to detect misuse or out-of-scope inputs.  The system is regularly stress tested via redteaming to find and fix  vulnerabilities.",
      icon: securityIcon
    },
    {
      name: "Transparent Governance",
      text: "Our work is non-commercial and is best understood as a form of digital activism. We work with a selected number of partners who help us deliver for the public.",
      icon: governanceIcon
    }
  ]

  const amountOfCards = cardValues.length;

  const [currentCardIndex, setCurrentCardIndex ] = useState(0);
  
  const currentLeftCardIndex = (currentCardIndex - 1 + amountOfCards) % amountOfCards;
  const currentRightCardIndex = (currentCardIndex + 1) % amountOfCards;

  function switchCard(direction) {
    setCurrentCardIndex(prev =>
      direction === 'left'
        ? (prev - 1 + amountOfCards) % amountOfCards
        : (prev + 1) % amountOfCards
    );
  }


  return (
    <div className="EthicsPage unbounded-weight300">
      <h1>ETHICAL CONSIDERATIONS</h1>
      <div id='values-carousel'>
        <img alt="left arrow" src={carouselArrow} onClick={() => {switchCard('left')}} id="carousel-left"></img>

        <div className='carousel-card-secondary'>
          <img alt="card icon" src={cardValues[currentLeftCardIndex].icon}></img>
          <h1>{cardValues[currentLeftCardIndex].name}</h1>
          <p>{cardValues[currentLeftCardIndex].text}</p>
        </div>

        <div className='carousel-card-primary'>
          <img alt="card icon" src={cardValues[currentCardIndex].icon}></img>
          <h1>{cardValues[currentCardIndex].name}</h1>
          <p>{cardValues[currentCardIndex].text}</p>
        </div>

        <div className='carousel-card-secondary'>
          <img alt="card icon" src={cardValues[currentRightCardIndex].icon}></img>
          <h1>{cardValues[currentRightCardIndex].name}</h1>
          <p>{cardValues[currentRightCardIndex].text}</p>
        </div>

        <img alt="right arrow" src={carouselArrow} onClick={() => {switchCard('right')}} id="carousel-right"></img>
      </div>
    </div>
  );
}

export default EthicsPage;