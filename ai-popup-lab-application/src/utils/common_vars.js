import netherlandsFlag from '../assets/images/flags/netherlands.png';
import denmarkFlag from '../assets/images/flags/denmark.png';
import swedenFlag from '../assets/images/flags/sweden.png';
import usaFlag from '../assets/images/flags/usa.png';

export const COUNTRY_INFO = {
  netherlands: {
    country_code: 'nl',
    abbreviation: 'NL',
    flag_image: netherlandsFlag,
    is_in_development: true
  },
  denmark: {
    country_code: 'dk',
    abbreviation: 'DK',
    flag_image: denmarkFlag,
    is_in_development: true
  },
  sweden: {
    country_code: 'se',
    abbreviation: 'SE',
    flag_image: swedenFlag,
    is_in_development: true
  },
  usa: {
    country_code: 'us',
    abbreviation: 'USA',
    flag_image: usaFlag,
    is_in_development: false
  },
};