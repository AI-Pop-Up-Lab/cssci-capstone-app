/**
 * simple read/write helpers for persisting the user's currently
 * selected country to localStorage under the key "chosen_country".
 */

const STORAGE_KEY = 'chosen_country';

/**
 * reads the chosen country from localStorage.
 * @returns {string|null} the stored country key (e.g. "denmark"), or null if none is set
 */
export function getChosenCountry() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch (err) {
    // localStorage can throw in private-browsing/quota-exceeded edge cases
    console.warn('Could not read chosen country from localStorage:', err);
    return null;
  }
}

/**
 * sets the chosen country in localStorage.
 * @param {string} country - the country key to store (e.g. "denmark")
 */
export function setChosenCountry(country) {
  try {
    localStorage.setItem(STORAGE_KEY, country);
  } catch (err) {
    console.warn('Could not save chosen country to localStorage:', err);
  }
}