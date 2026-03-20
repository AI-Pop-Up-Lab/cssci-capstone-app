import { useState } from 'react';

import './ethicsPage.css';
import carouselArrow from '../assets/images/carouselArrow.png'
import transparencyIcon from '../assets/svgs/transparencyIcon.svg'

function EthicsPage() {

  const cardValues = [
    {
      name: "Transparency1",
      text: "LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA.",
      icon: transparencyIcon
    },
    {
      name: "Transparency2",
      text: "LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA.",
      icon: transparencyIcon
    },
    {
      name: "Transparency3",
      text: "LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA.",
      icon: transparencyIcon
    },
    {
      name: "Transparency4",
      text: "LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA.",
      icon: transparencyIcon
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
      <h1>OUR KEY VALUES</h1>
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