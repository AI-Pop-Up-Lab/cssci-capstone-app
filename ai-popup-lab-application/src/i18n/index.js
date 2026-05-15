import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import nl from './locales/nl.json';
import swe from './locales/swe.json';
import dk from './locales/dk.json';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      nl: { translation: nl },
      swe: { translation: swe },
      dk: { translation: dk },
    },
    lng: localStorage.getItem('lang') || 'en', // language persisted across reload, otherwise default language set as english
    fallbackLng: 'en', // fallback if key missing
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;