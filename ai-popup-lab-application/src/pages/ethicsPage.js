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
      name: "Algorithmic Bias",
      text: "Post-stratification weighting is applied to align synthetic outputs with real population distributions. Red-teaming tests are run to identify systematic distortions before deployment.",
      icon: biasIcon
    },
    {
      name: "Privacy / Consent",
      text: "Survey data is collected under informed consent protocols following ethical research standards. No personally identifiable information is used in persona construction.",
      icon: privacyIcon
    },
    {
      name: "Epistemic Harm",
      text: "Persona responses are designed to be grounded in stored survey answers, with citation indicators built into the response pipeline. Weak evidence warnings appear automatically when outputs are based on small subgroups.",
      icon: epistemicIcon
    },
    {
      name: "Democratic Harm",
      text: "The tool is designed to democratise access to polling insights, helping users understand why different voter groups hold the views they do. Synthetic status is permanently visible throughout all interactions to prevent misuse.",
      icon: democracyIcon
    },
    {
      name: "Representational Harm",
      text: 'Each demographic group includes multiple personas to show the range of views within it, not just one "typical" voter. Avatars are kept abstract as a reminder that these are simulations, not real people.',
      icon: representationIcon
    },
    {
      name: "Transparency",
      text: "Every result shows where the data comes from, which version of the system produced it, and when. A plain-language methods page explains how the tool works from start to finish.",
      icon: transparencyIcon
    },
    {
      name: "Security / Robustness",
      text: "Automated checks run before and after every response to catch misuse or out-of-scope inputs. The system is regularly stress-tested to find and fix weaknesses.",
      icon: securityIcon
    },
    {
      name: "Governance",
      text: "Who funds the project and the ethical principles behind it are publicly listed in our section on Funding. All changes to the system are logged so decisions can be reviewed and held accountable.",
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