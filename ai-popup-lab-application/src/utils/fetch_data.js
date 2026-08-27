/**
 *
 * single source of truth for fetching the country data object from the
 * fastAPI backend, with localStorage caching keyed by ISO week.
 *
 * Usage in a component:
 *   import { getCountryData } from '../utils/fetch_data';
 *   const data = await getCountryData('denmark');
 */

const CACHE_PREFIX = 'countryData_';

/**
 * returns the current ISO week as a string like "2026_32".
 * ISO weeks run Mon-Sun; week 1 is the week containing the year's first Thursday.
 */
function getCurrentIsoWeek() {
  const now = new Date();

  // Copy date, set to nearest Thursday (ISO 8601 rule: week belongs to the year of its Thursday)
  const target = new Date(now.getTime());
  target.setHours(0, 0, 0, 0);
  // getDay(): Sun=0 ... Sat=6. ISO weekday: Mon=1 ... Sun=7
  const isoWeekday = target.getDay() === 0 ? 7 : target.getDay();
  target.setDate(target.getDate() + (4 - isoWeekday)); // move to this week's Thursday

  const isoYear = target.getFullYear();
  const yearStart = new Date(isoYear, 0, 1);
  const weekNumber = Math.ceil((((target - yearStart) / 86400000) + 1) / 7);

  return `${isoYear}_${String(weekNumber).padStart(2, '0')}`;
}

/**
 * Compares two "YYYY_WW" iso-week strings.
 * Returns true if `cachedWeek` is strictly earlier than `currentWeek`.
 */
function isWeekStale(cachedWeek, currentWeek) {
  if (!cachedWeek) return true;
  return cachedWeek < currentWeek; // safe string comparison given zero-padded WW and fixed YYYY_WW format
}

function readCache(country) {
  try {
    const raw = localStorage.getItem(CACHE_PREFIX + country);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (err) {
    // corrupt cache entry - treat as empty
    return null;
  }
}

function writeCache(country, data) {
  try {
    const payload = {
      isoWeek: getCurrentIsoWeek(),
      data,
    };
    localStorage.setItem(CACHE_PREFIX + country, JSON.stringify(payload));
  } catch (err) {
    // localStorage can throw (quota exceeded, private browsing, etc.) - fail silently,
    // the app still works, it just re-fetches next time
    console.warn('Could not cache country data:', err);
  }
}

async function fetchCountryData(country) {
  const res = await fetch(`${process.env.REACT_APP_API_URL}/api/country_data/country_object?country=${encodeURIComponent(country)}`);

  if (!res.ok) {
    throw new Error(`Failed to fetch country data for "${country}": ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * gets the country data object, either from cache (if fresh) or from the API.
 *
 * @param {string} country - lowercase country key, e.g. "denmark", "usa"
 * @param {object} [options]
 * @param {boolean} [options.forceRefresh] - bypass cache and always re-fetch
 * @returns {Promise<object>} the country data object
 */
export async function getCountryData(country, options = {}) {
  const { forceRefresh = false } = options;
  const currentWeek = getCurrentIsoWeek();

  if (!forceRefresh) {
    const cached = readCache(country);
    if (cached && !isWeekStale(cached.isoWeek, currentWeek)) {
      return cached.data;
    }
  }

  const data = await fetchCountryData(country);
  writeCache(country, data);
  return data;
}

// clears the cached entry for a single country, or all cached country data if no arg given.
export function clearCountryDataCache(country) {
  if (country) {
    localStorage.removeItem(CACHE_PREFIX + country);
    return;
  }
  Object.keys(localStorage)
    .filter((key) => key.startsWith(CACHE_PREFIX))
    .forEach((key) => localStorage.removeItem(key));
}