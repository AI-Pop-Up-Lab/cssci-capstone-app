// Team page showcasing the project team members 
import { useTranslation } from 'react-i18next';

import './teamPage.css';
import robertoPhoto from '../assets/images/team/roberto.jpeg';
import danieliusPhoto from '../assets/images/team/danielius.jpg';
import maliahPhoto from '../assets/images/team/maliah.png';
import danielPhoto from '../assets/images/team/daniel.jpg';
import group1Photo from '../assets/images/team/group1.jpg';
import group3Photo from '../assets/images/team/group3.jpg';
import group2Photo from '../assets/images/team/group2.jpg';
import lorijnPhoto from '../assets/images/team/lorijn.jpeg';
import group4Photo from '../assets/images/team/group4.jpg';

const MEMBERS = [
  { id: 'member1', team: 'poliCog', name: 'Danielius Jonaitis', email: 'd.jonaitis@uva.nl', linkedin: 'https://www.linkedin.com/in/danielius-jonaitis/', x: 'https://x.com/dan_jonaitis' },
  { id: 'member2', team: 'poliCog', name: 'Maliah Balancier', email: 'mjnbalancier@gmail.com' , linkedin: 'https://www.linkedin.com/in/maliahbalancier/' },
  { id: 'member3', team: 'poliCog', name: 'Daniel Kvores', email: 'daniel.kvores@student.uva.nl', linkedin: 'https://www.linkedin.com/in/daniel-kvores/' },
  { id: 'member4', team: 'poliCog', name: 'Antonin Tesar', email: 'tes.antonin@gmail.com', linkedin: 'http://linkedin.com/in/antonintesar' },
  { id: 'member5', team: 'humanBenchmark', name: 'Ava Ali', email: 'avaalan2005@gmail.com', linkedin: 'https://www.linkedin.com/in/avaali/'},
  { id: 'member6', team: 'humanBenchmark', name: 'Shriya Agrawal', email: 'shriy.agra@gmail.com', linkedin: 'https://www.linkedin.com/in/shriya-agrawal17'},
  { id: 'member7', team: 'humanBenchmark', name: 'Madeleine Hoffman', email: 'madeleine.hoffman@student.uva.nl', linkedin: 'https://www.linkedin.com/in/madeleine-hoffman-3a97981b6' },
  { id: 'member8', team: 'infrastructure', name: 'Alexandra Roskam', email: 'a.m.i.roskam@uva.nl', linkedin: 'https://www.linkedin.com/in/alexandraroskam/'},
  { id: 'member9', team: 'infrastructure', name: 'Brendan Corcoran', email: 'brendan.corcoran@mechanical-pollster.com', linkedin: 'https://www.linkedin.com/in/brendan-corcoran-a87b71237'},
  { id: 'member10', team: 'infrastructure', name: 'Lorijn van Leeuwen', linkedin: 'https://www.linkedin.com/in/lorijn-van-leeuwen-5a1355278/'},
  { id: 'member11', team: 'infrastructure', name: 'Oliwia Wolska', email: 'oliwia.wolska@student.uva.nl'},

];

const PRINCIPAL_INVESTIGATOR = {
  name: 'Roberto Cerina',
  email: 'r.cerina@uva.nl',
  x: 'https://x.com/RobertoCerina',
  photo: robertoPhoto,
};

const teamsData = [
  { id: 'poliCog', theme: 'pink', images: [danieliusPhoto, maliahPhoto, danielPhoto] },
  { id: 'humanBenchmark', theme: 'teal', images: [group1Photo, group3Photo, group2Photo] },
  { id: 'infrastructure', theme: 'mint', images: [lorijnPhoto, { src: group4Photo, uncropped: true }] },
];

const LinkedInIcon = () => (
  <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
  </svg>
);

const XIcon = () => (
  <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

function TeamSection({ team }) {
  const { t } = useTranslation();
  const teamName = t(`teamPage.teams.${team.id}.name`);
  const members = MEMBERS.filter((member) => member.team === team.id);
  const areas = t(`teamPage.teams.${team.id}.areas`, { returnObjects: true });

  return (
    <section id={`team-${team.id}`} className={`team-section team-theme-${team.theme}`}>
      <div className="team-section-inner">
        <h2 className="team-section-header unbounded-weight400">{teamName}</h2>

        <div className="team-columns">
          <div className="team-info">
            <div className="team-section-description">
              <p>{t(`teamPage.teams.${team.id}.intro`)}</p>
              {Array.isArray(areas) && areas.length > 0 && (
                <ul className="team-areas">
                  {areas.map((area) => (
                    <li key={area.title}>
                      <strong>{area.title}:</strong> {area.text}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {members.map((member) => (
              <div className="team-member" key={member.id}>
                <h3 className="team-member-name unbounded-weight400">{member.name}</h3>
                <p className="team-member-text">{t(`teamPage.members.${member.id}.text`)}</p>

                <div className="team-member-links">
                  {member.email && (
                    <a className="team-contact unbounded-weight400" href={`mailto:${member.email}`} aria-label={`${t('teamPage.contact')} — ${member.name}`}>
                      {t('teamPage.contact')}
                    </a>
                  )}
                  {member.linkedin && (
                    <a className="team-social" href={member.linkedin} target="_blank" rel="noopener noreferrer" aria-label={`LinkedIn — ${member.name}`}>
                      <LinkedInIcon />
                    </a>
                  )}
                  {member.x && (
                    <a className="team-social" href={member.x} target="_blank" rel="noopener noreferrer" aria-label={`X — ${member.name}`}>
                      <XIcon />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="team-images">
            {team.images.map((image, i) => {
              const { src, uncropped } = typeof image === 'string' ? { src: image } : image;
              return (
                <img key={i} src={src} alt={teamName} loading="lazy" className={uncropped ? 'team-img-uncropped' : undefined} />
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

function TeamPage() {

  const { t } = useTranslation();

  return (
    <div className="TeamPage unbounded-weight300">

      <div id="team-intro">
        <h1>{t('teamPage.title')}</h1>
        <p>{t('teamPage.description')}</p>

        <div className="team-pi">
          <img className="team-pi-photo" src={PRINCIPAL_INVESTIGATOR.photo} alt={PRINCIPAL_INVESTIGATOR.name} />
          <div>
            <p className="team-pi-label">{t('teamPage.pi.label')}</p>
            <h3 className="team-pi-name unbounded-weight400">{PRINCIPAL_INVESTIGATOR.name}</h3>
            <p className="team-pi-role">{t('teamPage.pi.role')}</p>
            <div className="team-member-links">
              <a
                className="team-contact unbounded-weight400"
                href={`mailto:${PRINCIPAL_INVESTIGATOR.email}`}
                aria-label={`${t('teamPage.contact')} — ${PRINCIPAL_INVESTIGATOR.name}`}
              >
                {t('teamPage.contact')}
              </a>
              <a
                className="team-social"
                href={PRINCIPAL_INVESTIGATOR.x}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`X — ${PRINCIPAL_INVESTIGATOR.name}`}
              >
                <XIcon />
              </a>
            </div>
          </div>
        </div>
      </div>

      {teamsData.map((team) => (
        <TeamSection key={team.id} team={team} />
      ))}

    </div>
  );
}

export default TeamPage;