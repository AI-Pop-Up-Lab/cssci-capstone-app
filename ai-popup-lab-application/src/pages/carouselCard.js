import { useTranslation, Trans } from 'react-i18next';

function CarouselCard({ card, className }) {

  const { t } = useTranslation();

  return (
    <div className={className}>
      <img alt="card icon" src={card.icon} />
      <h1>{t(`ethicsPage.items.${card.key}.name`)}</h1>
      {card.hasComponents
        ? <p><Trans i18nKey={`ethicsPage.items.${card.key}.text`} components={{ fgwLink: <a href='https://aihr.uva.nl/about-aihr/ethics-committee/ethics-committee.html' target='_blank' rel='noopener noreferrer' /> }} /></p>
        : <p>{t(`ethicsPage.items.${card.key}.text`)}</p>
      }
    </div>
  );
}

export default CarouselCard;