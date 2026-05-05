import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import './ethicsPage.css';
import carouselArrow from '../assets/images/carouselArrow.png'
import CarouselCard from './carouselCard';

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

        <CarouselCard card={cardValues[currentLeftCardIndex]} className="carousel-card-secondary" />
        <CarouselCard card={cardValues[currentCardIndex]} className="carousel-card-primary" />
        <CarouselCard card={cardValues[currentRightCardIndex]} className="carousel-card-secondary" />

        <img alt="right arrow" src={carouselArrow} onClick={() => {switchCard('right')}} id="carousel-right"></img>
      </div>
    </div>
  );
}

export default EthicsPage;