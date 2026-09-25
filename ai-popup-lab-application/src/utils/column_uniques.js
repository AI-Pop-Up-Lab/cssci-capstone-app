/**
 *
 * Given an array of "row" objects (each object's keys are column names,
 * e.g. rows from a parsed CSV), returns an object mapping each column
 * name to an array of that column's unique values, in first-seen order.
 *
 * Example:
 *   const rows = [
 *     { gender: 'Female', age_group: '18-29' },
 *     { gender: 'Male',   age_group: '18-29' },
 *     { gender: 'Female', age_group: '30-44' },
 *   ];
 *   getColumnUniques(rows);
 *   // => { gender: ['Female', 'Male'], age_group: ['18-29', '30-44'] }
 */

/**
 * @param {Array<Object>} rows - array of row objects, all sharing the same shape
 * @param {Object} [options]
 * @param {string[]} [options.columns] - restrict to these column keys instead of inferring from the data
 * @param {boolean} [options.sort] - sort each column's unique values (default: true, keeps first-seen order)
 * @param {boolean} [options.dropNullish] - exclude null/undefined values from the result (default: true)
 * @returns {Object<string, Array>} map of column name -> array of unique values
 */
export function getColumnUniques(rows, options = {}) {
  const { columns, sort = true, dropNullish = true } = options;

  if (!Array.isArray(rows) || rows.length === 0) {
    return {};
  }

  // Infer columns from the union of keys across all rows, unless explicitly given.
  // Using a union (not just Object.keys(rows[0])) protects against rows with missing/sparse keys.
  const columnKeys = columns ?? Array.from(
    rows.reduce((keys, row) => {
      Object.keys(row).forEach((k) => keys.add(k));
      return keys;
    }, new Set())
  );

  // One Set per column to track uniqueness while preserving first-seen insertion order
  const uniqueSets = Object.fromEntries(columnKeys.map((col) => [col, new Set()]));

  for (const row of rows) {
    for (const col of columnKeys) {
      const value = row[col];
      if (dropNullish && (value === null || value === undefined)) continue;
      uniqueSets[col].add(value);
    }
  }

  const result = {};
  for (const col of columnKeys) {
    const values = Array.from(uniqueSets[col]);
    result[col] = sort ? values.slice().sort() : values;
  }

  return result;
}