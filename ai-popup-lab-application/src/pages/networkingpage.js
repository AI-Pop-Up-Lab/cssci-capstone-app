import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import './networkingPlatformPage.css';

const availableCountries = ['netherlands', 'denmark', 'sweden'];
const researchFields = ['politicalScience', 'sociology', 'psychology', 'economics', 'communication'];
const experimentTypes = ['doorToDoor', 'phoneBank', 'labInField', 'surveyExperiment', 'observational'];

const API = process.env.REACT_APP_API_URL;
const STORAGE_KEY = 'networking-supervisor';

// local YYYY-MM-DD key; toISOString() would shift the day for negative UTC offsets
const dateKey = (date) => {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
};

// month grid padded to whole weeks, Monday first; null = empty cell
const buildMonthGrid = (year, month) => {
  const offset = (new Date(year, month, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = Array(offset).fill(null);
  for (let day = 1; day <= daysInMonth; day++) cells.push(new Date(year, month, day));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
};

const requestJson = async (path, options = {}) => {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
  return response.json();
};

// -------------------------------------------------------------------------

// registration form for a supervising professor and the students they bring
function SupervisorSignup({ supervisor, onRegistered }) {

  const { t } = useTranslation();

  const [form, setForm] = useState({
    name: supervisor?.name ?? '',
    email: supervisor?.email ?? '',
    institution: supervisor?.institution ?? '',
    country: supervisor?.country ?? availableCountries[0],
    field: supervisor?.field ?? researchFields[0],
    studentCount: supervisor?.studentCount ?? 1,
    experimentTypes: supervisor?.experimentTypes ?? [],
    notes: supervisor?.notes ?? '',
  });
  const [saving, setSaving] = useState(false);

  const setField = (key, value) => setForm(prev => ({ ...prev, [key]: value }));

  const toggleExperimentType = (type) => setForm(prev => ({
    ...prev,
    experimentTypes: prev.experimentTypes.includes(type)
      ? prev.experimentTypes.filter(item => item !== type)
      : [...prev.experimentTypes, type],
  }));

  const submit = async (event) => {
    event.preventDefault();
    if (form.experimentTypes.length === 0) {
      alert(t('networkingPage.signup.pickOneType'));
      return;
    }

    setSaving(true);
    try {
      const payload = { ...form, studentCount: Number(form.studentCount) };
      const saved = supervisor
        ? await requestJson(`/api/network/supervisors/${supervisor.id}`, { method: 'PUT', body: JSON.stringify(payload) })
        : await requestJson('/api/network/supervisors', { method: 'POST', body: JSON.stringify(payload) });
      onRegistered(saved);
    } catch (error) {
      console.error('Supervisor sign-up failed:', error);
      alert(t('networkingPage.saveError'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="netplat-form" onSubmit={submit}>

      <label className="netplat-field">
        <span>{t('networkingPage.signup.name')}</span>
        <input required value={form.name} onChange={e => setField('name', e.target.value)} />
      </label>

      <label className="netplat-field">
        <span>{t('networkingPage.signup.email')}</span>
        <input required type="email" value={form.email} onChange={e => setField('email', e.target.value)} />
      </label>

      <label className="netplat-field">
        <span>{t('networkingPage.signup.institution')}</span>
        <input required value={form.institution} onChange={e => setField('institution', e.target.value)} />
      </label>

      <label className="netplat-field">
        <span>{t('networkingPage.signup.country')}</span>
        <select value={form.country} onChange={e => setField('country', e.target.value)}>
          {availableCountries.map(country => (
            <option key={country} value={country}>{t(`networkingPage.countries.${country}`)}</option>
          ))}
        </select>
      </label>

      <label className="netplat-field">
        <span>{t('networkingPage.signup.field')}</span>
        <select value={form.field} onChange={e => setField('field', e.target.value)}>
          {researchFields.map(field => (
            <option key={field} value={field}>{t(`networkingPage.fields.${field}`)}</option>
          ))}
        </select>
      </label>

      <label className="netplat-field">
        <span>{t('networkingPage.signup.studentCount')}</span>
        <input
          required
          type="number"
          min="1"
          max="200"
          value={form.studentCount}
          onChange={e => setField('studentCount', e.target.value)}
        />
      </label>

      <fieldset className="netplat-field netplat-field-wide">
        <legend>{t('networkingPage.signup.experimentTypes')}</legend>
        <div className="netplat-checkbox-grid">
          {experimentTypes.map(type => (
            <label key={type} className="netplat-checkbox">
              <input
                type="checkbox"
                checked={form.experimentTypes.includes(type)}
                onChange={() => toggleExperimentType(type)}
              />
              {t(`networkingPage.experimentTypes.${type}`)}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="netplat-field netplat-field-wide">
        <span>{t('networkingPage.signup.notes')}</span>
        <textarea rows="4" value={form.notes} onChange={e => setField('notes', e.target.value)} />
      </label>

      <button type="submit" className="netplat-button-primary" disabled={saving}>
        {saving
          ? t('networkingPage.signup.saving')
          : supervisor ? t('networkingPage.signup.update') : t('networkingPage.signup.submit')}
      </button>
    </form>
  );
}

// -------------------------------------------------------------------------

// month calendar where a supervisor marks the days their students can run fieldwork
function AvailabilityCalendar({ supervisor }) {

  const { t } = useTranslation();

  const today = useMemo(() => new Date(), []);
  const [view, setView] = useState({ year: today.getFullYear(), month: today.getMonth() });
  const [selected, setSelected] = useState(() => new Set());
  const [saving, setSaving] = useState(false);

  const grid = useMemo(() => buildMonthGrid(view.year, view.month), [view]);

  // load the days already stored for this supervisor
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await requestJson(`/api/network/availability?supervisorId=${supervisor.id}`);
        if (!cancelled) setSelected(new Set(data.dates ?? []));
      } catch (error) {
        console.error('Availability load failed:', error);
      }
    })();
    return () => { cancelled = true; };
  }, [supervisor.id]);

  const toggleDay = (date) => {
    const key = dateKey(date);
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const shiftMonth = (delta) => setView(prev => {
    const shifted = new Date(prev.year, prev.month + delta, 1);
    return { year: shifted.getFullYear(), month: shifted.getMonth() };
  });

  const save = async () => {
    setSaving(true);
    try {
      await requestJson('/api/network/availability', {
        method: 'PUT',
        body: JSON.stringify({ supervisorId: supervisor.id, dates: [...selected].sort() }),
      });
      alert(t('networkingPage.calendar.saved'));
    } catch (error) {
      console.error('Availability save failed:', error);
      alert(t('networkingPage.saveError'));
    } finally {
      setSaving(false);
    }
  };

  const monthLabel = new Date(view.year, view.month, 1)
    .toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  return (
    <div className="netplat-calendar">

      <div className="netplat-calendar-header">
        <button type="button" onClick={() => shiftMonth(-1)} aria-label={t('networkingPage.calendar.previous')}>&lsaquo;</button>
        <h3>{monthLabel}</h3>
        <button type="button" onClick={() => shiftMonth(1)} aria-label={t('networkingPage.calendar.next')}>&rsaquo;</button>
      </div>

      <div className="netplat-calendar-grid">
        {['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map(day => (
          <span key={day} className="netplat-calendar-weekday">{t(`networkingPage.weekdays.${day}`)}</span>
        ))}

        {grid.map((date, index) => {
          if (!date) return <span key={`empty-${index}`} className="netplat-calendar-cell is-empty" />;
          const key = dateKey(date);
          const past = date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
          return (
            <button
              key={key}
              type="button"
              disabled={past}
              aria-pressed={selected.has(key)}
              className={`netplat-calendar-cell ${selected.has(key) ? 'is-selected' : ''}`}
              onClick={() => toggleDay(date)}
            >
              {date.getDate()}
            </button>
          );
        })}
      </div>

      <div className="netplat-calendar-footer">
        <p>{t('networkingPage.calendar.count', { count: selected.size })}</p>
        <button type="button" className="netplat-button-primary" onClick={save} disabled={saving}>
          {saving ? t('networkingPage.calendar.saving') : t('networkingPage.calendar.save')}
        </button>
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------

// supervisors whose field, country and free days line up with yours
function MatchList({ supervisor }) {

  const { t } = useTranslation();

  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await requestJson(`/api/network/matches?supervisorId=${supervisor.id}`);
      setMatches(data.matches ?? []);
    } catch (error) {
      console.error('Match load failed:', error);
      alert(t('networkingPage.matches.loadError'));
    } finally {
      setLoading(false);
    }
  }, [supervisor.id, t]);

  useEffect(() => { load(); }, [load]);

  const sendRequest = async (match) => {
    setPending(match.id);
    try {
      await requestJson('/api/network/requests', {
        method: 'POST',
        body: JSON.stringify({ fromSupervisorId: supervisor.id, toSupervisorId: match.id }),
      });
      setMatches(prev => prev.map(item => item.id === match.id ? { ...item, requestStatus: 'sent' } : item));
    } catch (error) {
      console.error('Collaboration request failed:', error);
      alert(t('networkingPage.matches.requestError'));
    } finally {
      setPending(null);
    }
  };

  if (loading) return <p className="netplat-empty">{t('networkingPage.matches.loading')}</p>;
  if (matches.length === 0) return <p className="netplat-empty">{t('networkingPage.matches.empty')}</p>;

  return (
    <ul className="netplat-match-list">
      {matches.map(match => (
        <li key={match.id} className="netplat-match-card">

          <div className="netplat-match-head">
            <h3>{match.name}</h3>
            <span className="netplat-match-score">{t('networkingPage.matches.score', { score: match.score })}</span>
          </div>

          <p className="netplat-match-meta">
            {match.institution} &middot; {t(`networkingPage.countries.${match.country}`)} &middot; {t(`networkingPage.fields.${match.field}`)}
          </p>

          <p className="netplat-match-meta">
            {t('networkingPage.matches.students', { count: match.studentCount })} &middot;{' '}
            {t('networkingPage.matches.sharedDays', { count: match.sharedDates?.length ?? 0 })}
          </p>

          <ul className="netplat-tag-row">
            {(match.experimentTypes ?? []).map(type => (
              <li key={type} className="netplat-tag">{t(`networkingPage.experimentTypes.${type}`)}</li>
            ))}
          </ul>

          <button
            type="button"
            className="netplat-button-primary"
            disabled={match.requestStatus === 'sent' || pending === match.id}
            onClick={() => sendRequest(match)}
          >
            {match.requestStatus === 'sent'
              ? t('networkingPage.matches.requested')
              : t('networkingPage.matches.request')}
          </button>
        </li>
      ))}
    </ul>
  );
}

// -------------------------------------------------------------------------

function NetworkingPlatformPage() {

  const { t } = useTranslation();

  // registered supervisor is kept locally so a refresh does not force a re-signup
  const [supervisor, setSupervisor] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [tab, setTab] = useState('signup');

  const onRegistered = (saved) => {
    setSupervisor(saved);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
    } catch (error) {
      console.error('Could not store supervisor locally:', error);
    }
    setTab('calendar');
  };

  const tabs = [
    { key: 'signup', locked: false },
    { key: 'calendar', locked: !supervisor },
    { key: 'matches', locked: !supervisor },
  ];

  return (
    <div className="NetworkingPlatformPage unbounded-weight300">

      <div id="netplat-intro">
        <h1>{t('networkingPage.intro.title')}</h1>
        <p>{t('networkingPage.intro.text')}</p>
      </div>

      <nav className="netplat-tabs">
        {tabs.map(({ key, locked }) => (
          <button
            key={key}
            type="button"
            disabled={locked}
            className={`netplat-tab ${tab === key ? 'is-active' : ''}`}
            onClick={() => setTab(key)}
          >
            {t(`networkingPage.tabs.${key}`)}
          </button>
        ))}
      </nav>

      <section className="netplat-section">
        {tab === 'signup' && <SupervisorSignup supervisor={supervisor} onRegistered={onRegistered} />}
        {tab === 'calendar' && supervisor && <AvailabilityCalendar supervisor={supervisor} />}
        {tab === 'matches' && supervisor && <MatchList supervisor={supervisor} />}
      </section>

    </div>
  );
}

export default NetworkingPlatformPage;