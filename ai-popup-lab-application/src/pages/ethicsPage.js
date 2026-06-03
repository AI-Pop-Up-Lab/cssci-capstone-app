// page explaining the AI Pop-up Lab's ethical values on a 'carousel'
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import './ethicsPage.css';
import carouselArrow from '../assets/images/carouselArrow.png'
import CarouselCard from '../modules/carouselCard';

// importing icons for each card
import biasIcon from '../assets/images/biasIcon.png'
import privacyIcon from '../assets/images/privacyIcon.png'
import epistemicIcon from '../assets/images/epistemicIcon.png'
import democracyIcon from '../assets/images/democracyIcon.png'
import representationIcon from '../assets/images/representationIcon.png'
import transparencyIcon from '../assets/svgs/transparencyIcon.svg'
import securityIcon from '../assets/images/securityIcon.png'
import governanceIcon from '../assets/images/governanceIcon.png'

function EthicsPage() {

  const { t } = useTranslation();

  // defining the value in the localisation json for i18n, along with the icon for each card
  const cardValues = [
    { key: "algorithmicFairness", icon: biasIcon },
    { key: "ethicalDataUse", icon: privacyIcon, hasComponents: true },
    { key: "epistemicResponsibility", icon: epistemicIcon },
    { key: "preventingDemocraticHarm", icon: democracyIcon },
    { key: "fairRepresentation", icon: representationIcon },
    { key: "transparency", icon: transparencyIcon },
    { key: "robustnessSecurity", icon: securityIcon },
    { key: "transparentGovernance", icon: governanceIcon },
  ]

  const amountOfCards = cardValues.length;

  const [currentCardIndex, setCurrentCardIndex ] = useState(0);
  
  const currentLeftCardIndex = (currentCardIndex - 1 + amountOfCards) % amountOfCards;
  const currentRightCardIndex = (currentCardIndex + 1) % amountOfCards;

  // function for switching the indexes of which cards should be shown
  function switchCard(direction) {
    setCurrentCardIndex(prev =>
      direction === 'left'
        ? (prev - 1 + amountOfCards) % amountOfCards
        : (prev + 1) % amountOfCards
    );
  }


  return (
    <div className="EthicsPage unbounded-weight300">
      <h1>{t('ethicsPage.title')}</h1>
      <div id='values-carousel'>
        <img alt="left arrow" src={carouselArrow} onClick={() => {switchCard('left')}} id="carousel-left"></img>

        {/* Defining three carousel cards, passing the value of the current index cards in */}
        <CarouselCard card={cardValues[currentLeftCardIndex]} className="carousel-card-secondary" />
        <CarouselCard card={cardValues[currentCardIndex]} className="carousel-card-primary" />
        <CarouselCard card={cardValues[currentRightCardIndex]} className="carousel-card-secondary" />

        <img alt="right arrow" src={carouselArrow} onClick={() => {switchCard('right')}} id="carousel-right"></img>
      </div>
    </div>
  );
}

export default EthicsPage;