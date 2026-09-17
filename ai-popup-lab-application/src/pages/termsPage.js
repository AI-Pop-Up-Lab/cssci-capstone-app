// page displaying the T&C
import { useTranslation, Trans } from 'react-i18next';

import './termsPage.css';

function TermsPage() {

  const { t } = useTranslation();

  const websiteLink = (
    <a
      href="https://www.mechanical-pollster.com"
      target="_blank"
      rel="noopener noreferrer"
    />
  );

  const emailLink = (
    <a href="mailto:r.cerina@uva.nl" />
  );

  const sections = [
    'licensedUse',
    'retainedRights',
    'acknowledgement',
    'modifyingDatasets',
    'personalData',
    'syntheticData',
    'prohibitedUses',
    'noEndorsement',
    'namesAndLogos',
    'noWarranties',
    'thirdPartyMaterials',
    'modificationDiscontinuation',
    'termination',
    'entireAgreement'
  ];

  return (
    <div className="TermsPage unbounded-weight300">
      <h1>{t('termsPage.title')}</h1>

      <div className="terms-introduction">
        <p>
          <Trans
            i18nKey="termsPage.introduction.0"
            components={{ website: websiteLink }}
          />
        </p>

        <p>
          <Trans
            i18nKey="termsPage.introduction.1"
            components={{ website: websiteLink }}
          />
        </p>

        <p>{t('termsPage.introduction.2')}</p>
      </div>

      <div className="terms-content">
        {sections.map((section, index) => (
          <section className="terms-section" key={section}>
            <h2>
              {index + 1}. {t(`termsPage.sections.${section}.title`)}
            </h2>

            {section === 'personalData' ? (
              <>
                <p>{t('termsPage.sections.personalData.content.0')}</p>

                <p>
                  <Trans
                    i18nKey="termsPage.sections.personalData.content.1"
                    components={{ email: emailLink }}
                  />
                </p>

                <p>{t('termsPage.sections.personalData.content.2')}</p>
              </>
            ) : (
              t(`termsPage.sections.${section}.content`, { returnObjects: true }).map(
                (paragraph, paragraphIndex) => (
                  <p key={paragraphIndex}>{paragraph}</p>
                )
              )
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

export default TermsPage;