// Team page showcasing the project team members
import { useInView } from "react-intersection-observer"
import { useTranslation } from 'react-i18next';

import './teamPage.css';

// core team members: role/description texts live in the locale files, names and emails here
// TODO: fill in the contact email addresses
const coreTeamMembers = [
  { key: 'policog', name: 'Danielius Jonaitis', email: '' },
  { key: 'personaSampling', name: 'Ava Ali', email: '' },
  { key: 'infrastructure', name: 'Brendan Corcoran', email: '' },
]

function TeamPage() {

  const { t } = useTranslation();

  // using react useInView hook to trigger function when an element becomes visible
  const useInViewAnimation = (threshold = 1) => {
    const [ref, inView] = useInView({ threshold, triggerOnce: true })
    return [ref, inView]
  }

  // reference hooks to add to elements for animations
  const [ref1, inView1] = useInViewAnimation();
  const [ref2, inView2] = useInViewAnimation(0.2);

  return (
    <div className="TeamPage unbounded-weight300">

      {/* Page Header Section */}
      <div id="team-intro">
        <h1>{t('teamPage.title')}</h1>
        <p>{t('teamPage.description')}</p>
      </div>

      {/* Core Team Section */}
      <div id="team-core" className="team-section">
        <h2 ref={ref1} className={`team-section-header ${inView1 ? 'team-header-underline-appear' : ''}`}>{t('teamPage.coreTeam.title')}</h2>

        <div ref={ref2} className={`team-core-grid ${inView2 ? 'team-fade-in-up' : ''}`}>
          {coreTeamMembers.map(member => (
            <div key={member.key} className="team-core-card">
              <p className="team-core-role">{t(`teamPage.coreTeam.members.${member.key}.role`)}</p>
              <h3 className="team-core-name">{member.name}</h3>
              <p className="team-core-text">{t(`teamPage.coreTeam.members.${member.key}.text`)}</p>
              {member.email && (
                <a className="team-core-contact" href={`mailto:${member.email}`} aria-label={`${t('teamPage.coreTeam.contact')} — ${member.name}`}>{t('teamPage.coreTeam.contact')}</a>
              )}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

export default TeamPage;
