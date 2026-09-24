import { useCallback, useEffect, useMemo, useState } from 'react';
import { useInView } from 'react-intersection-observer';
import { useTranslation } from 'react-i18next';

import './networkingpage.css';

const availableCountries = ['netherlands', 'denmark', 'sweden'];
const projectTypes = ['bachelorThesis', 'masterThesis', 'otherGraded', 'somethingElse'];
const steps = ['signup', 'calendar', 'matches'];

const API = process.env.REACT_APP_API_URL;
const STORAGE_KEY = 'networking-session';
const DESCRIPTION_MAX = 600;

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

// only allow http(s) links typed by users, so a javascript: link can never end up in an href
const safeUrl = (url) => (/^https?:\/\//i.test(url ?? '') ? url : null);

// -------------------------------------------------------------------------
// small building blocks

// section heading with the underline that draws itself once scrolled into view
function SectionHeader({ children }) {
  const [ref, inView] = useInView({ threshold: 1, triggerOnce: true });
  return (
    <h2 ref={ref} className={`netplat-header ${inView ? 'header-underline-appear' : ''}`}>
      {children}
    </h2>
  );
}

// inline confirmation or error message; replaces alert() popups
function Notice({ tone, children }) {
  if (!children) return null;
  return <p className={`netplat-notice netplat-notice-${tone}`} role="status">{children}</p>;
}

// one question: plain-language label, grey hint, then the input itself
function Question({ label, hint, htmlFor, children }) {
  return (
    <div className="netplat-question">
      {htmlFor
        ? <label className="netplat-question-label" htmlFor={htmlFor}>{label}</label>
        : <span className="netplat-question-label">{label}</span>}
      {hint && <p className="netplat-question-hint">{hint}</p>}
      {children}
    </div>
  );
}

// big clickable card used instead of small checkboxes and radio buttons
function ChoiceCard({ picked, onClick, children }) {
  return (
    <button
      type="button"
      aria-pressed={picked}
      className={`netplat-choice ${picked ? 'is-picked' : ''}`}
      onClick={onClick}
    >
      <span className="netplat-choice-mark" aria-hidden="true">{picked ? '✓' : ''}</span>
      {children}
    </button>
  );
}

function ConsentCheck({ checked, onChange, label }) {
  return (
    <label className="netplat-consent">
      <input type="checkbox" required checked={checked} onChange={e => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

// shared state and save logic for both sign-up sheets
function useSignupForm({ role, profile, initial, validate, prepare, onSaved }) {

  const { t } = useTranslation();

  const [form, setForm] = useState(() => ({ ...initial, ...profile }));
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);

  const setField = (key, value) => setForm(prev => ({ ...prev, [key]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setNotice(null);

    const problem = validate(form);
    if (problem) {
      setNotice({ tone: 'error', text: t(problem) });
      return;
    }

    setSaving(true);
    try {
      const path = `/api/network/${role}s`;
      const body = JSON.stringify(prepare(form));
      const saved = profile
        ? await requestJson(`${path}/${profile.id}`, { method: 'PUT', body })
        : await requestJson(path, { method: 'POST', body });
      if (profile) setNotice({ tone: 'good', text: t('networkingPage.signup.saved') });
      onSaved(saved);
    } catch (error) {
      console.error(`${role} sign-up failed:`, error);
      setNotice({ tone: 'error', text: t('networkingPage.saveError') });
    } finally {
      setSaving(false);
    }
  };

  return { form, setField, saving, notice, submit };
}

// -------------------------------------------------------------------------
// step 0: who are you

function RolePicker({ onPick }) {

  const { t } = useTranslation();

  return (
    <div id="netplat-roles">
      <SectionHeader>{t('networkingPage.role.heading')}</SectionHeader>
      <p className="netplat-lead">{t('networkingPage.role.lead')}</p>

      <div className="netplat-role-grid">
        {['supervisor', 'student'].map(role => (
          <button key={role} type="button" className="netplat-role-card" onClick={() => onPick(role)}>
            <span className="netplat-role-title">{t(`networkingPage.role.${role}.title`)}</span>
            <span className="netplat-role-text">{t(`networkingPage.role.${role}.text`)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// step 1a: sheet 1, supervisors

function SupervisorSignup({ profile, onSaved }) {

  const { t } = useTranslation();

  const { form, setField, saving, notice, submit } = useSignupForm({
    role: 'supervisor',
    profile,
    onSaved,
    initial: {
      name: '',
      email: '',
      affiliation: '',
      profileUrl: '',
      country: availableCountries[0],
      studentCount: 1,
      placements: 1,
      projectTypes: [],
      description: '',
      consent: false,
    },
    validate: (values) => (values.projectTypes.length === 0 ? 'networkingPage.supervisor.pickProjectTypes' : null),
    prepare: (values) => ({ ...values, studentCount: Number(values.studentCount), placements: Number(values.placements) }),
  });

  const toggleProjectType = (type) => setField('projectTypes',
    form.projectTypes.includes(type)
      ? form.projectTypes.filter(item => item !== type)
      : [...form.projectTypes, type]);

  const isLinkedIn = /linkedin\.com/i.test(form.profileUrl ?? '');
  const description = form.description ?? '';

  return (
    <form id="netplat-form" onSubmit={submit}>

      <SectionHeader>{t('networkingPage.supervisor.heading')}</SectionHeader>
      <p className="netplat-lead">{t('networkingPage.supervisor.lead')}</p>

      <Question label={t('networkingPage.supervisor.name')} htmlFor="netplat-name">
        <input id="netplat-name" required autoComplete="name" value={form.name} onChange={e => setField('name', e.target.value)} />
      </Question>

      <Question label={t('networkingPage.supervisor.email')} hint={t('networkingPage.supervisor.emailHint')} htmlFor="netplat-email">
        <input id="netplat-email" required type="email" autoComplete="email" value={form.email} onChange={e => setField('email', e.target.value)} />
      </Question>

      <Question label={t('networkingPage.supervisor.affiliation')} hint={t('networkingPage.supervisor.affiliationHint')} htmlFor="netplat-affiliation">
        <input id="netplat-affiliation" required autoComplete="organization" value={form.affiliation} onChange={e => setField('affiliation', e.target.value)} />
      </Question>

      <Question label={t('networkingPage.supervisor.profileUrl')} hint={t('networkingPage.supervisor.profileUrlHint')} htmlFor="netplat-profile">
        <input
          id="netplat-profile"
          required
          type="url"
          placeholder="https://"
          value={form.profileUrl}
          onChange={e => setField('profileUrl', e.target.value)}
        />
        {isLinkedIn && <Notice tone="info">{t('networkingPage.supervisor.linkedinNudge')}</Notice>}
      </Question>

      <Question label={t('networkingPage.supervisor.country')} htmlFor="netplat-country">
        <select id="netplat-country" value={form.country} onChange={e => setField('country', e.target.value)}>
          {availableCountries.map(country => (
            <option key={country} value={country}>{t(`networkingPage.countries.${country}`)}</option>
          ))}
        </select>
      </Question>

      <Question label={t('networkingPage.supervisor.studentCount')} hint={t('networkingPage.supervisor.studentCountHint')} htmlFor="netplat-student-count">
        <input
          id="netplat-student-count"
          required
          type="number"
          min="1"
          className="netplat-input-small"
          value={form.studentCount}
          onChange={e => setField('studentCount', e.target.value)}
        />
      </Question>

      <Question label={t('networkingPage.supervisor.placements')} hint={t('networkingPage.supervisor.placementsHint')} htmlFor="netplat-placements">
        <input
          id="netplat-placements"
          required
          type="number"
          min="1"
          max="50"
          className="netplat-input-small"
          value={form.placements}
          onChange={e => setField('placements', e.target.value)}
        />
      </Question>

      <Question label={t('networkingPage.supervisor.projectTypes')} hint={t('networkingPage.supervisor.projectTypesHint')}>
        <div className="netplat-choice-grid">
          {projectTypes.map(type => (
            <ChoiceCard key={type} picked={form.projectTypes.includes(type)} onClick={() => toggleProjectType(type)}>
              {t(`networkingPage.projectTypes.${type}`)}
            </ChoiceCard>
          ))}
        </div>
      </Question>

      <Question label={t('networkingPage.supervisor.description')} hint={t('networkingPage.supervisor.descriptionHint')} htmlFor="netplat-description">
        <textarea
          id="netplat-description"
          required
          rows="6"
          maxLength={DESCRIPTION_MAX}
          value={description}
          onChange={e => setField('description', e.target.value)}
        />
        <span className="netplat-counter">
          {t('networkingPage.supervisor.characters', { count: description.length, max: DESCRIPTION_MAX })}
        </span>
      </Question>

      <ConsentCheck
        checked={form.consent}
        onChange={value => setField('consent', value)}
        label={t('networkingPage.supervisor.consent')}
      />

      <Notice tone={notice?.tone}>{notice?.text}</Notice>

      <button type="submit" className="netplat-button-primary" disabled={saving}>
        {saving
          ? t('networkingPage.signup.saving')
          : profile ? t('networkingPage.signup.update') : t('networkingPage.supervisor.submit')}
      </button>
    </form>
  );
}

// -------------------------------------------------------------------------
// step 1b: sheet 2, students

function StudentSignup({ profile, onSaved }) {

  const { t } = useTranslation();

  const { form, setField, saving, notice, submit } = useSignupForm({
    role: 'student',
    profile,
    onSaved,
    initial: {
      name: '',
      email: '',
      university: '',
      studyProgram: '',
      projectType: '',
      projectTypeOther: '',
      consent: false,
    },
    validate: (values) => {
      if (!values.projectType) return 'networkingPage.student.pickProjectType';
      if (values.projectType === 'somethingElse' && !(values.projectTypeOther ?? '').trim()) {
        return 'networkingPage.student.describeOther';
      }
      return null;
    },
    // the free-text detail only belongs with "something else"
    prepare: (values) => ({
      ...values,
      projectTypeOther: values.projectType === 'somethingElse' ? (values.projectTypeOther ?? '').trim() : '',
    }),
  });

  return (
    <form id="netplat-form" onSubmit={submit}>

      <SectionHeader>{t('networkingPage.student.heading')}</SectionHeader>
      <p className="netplat-lead">{t('networkingPage.student.lead')}</p>

      <Question label={t('networkingPage.student.name')} htmlFor="netplat-name">
        <input id="netplat-name" required autoComplete="name" value={form.name} onChange={e => setField('name', e.target.value)} />
      </Question>

      <Question label={t('networkingPage.student.email')} hint={t('networkingPage.student.emailHint')} htmlFor="netplat-email">
        <input id="netplat-email" required type="email" autoComplete="email" value={form.email} onChange={e => setField('email', e.target.value)} />
      </Question>

      <Question label={t('networkingPage.student.university')} htmlFor="netplat-university">
        <input id="netplat-university" required autoComplete="organization" value={form.university} onChange={e => setField('university', e.target.value)} />
      </Question>

      <Question label={t('networkingPage.student.studyProgram')} hint={t('networkingPage.student.studyProgramHint')} htmlFor="netplat-program">
        <input id="netplat-program" required value={form.studyProgram} onChange={e => setField('studyProgram', e.target.value)} />
      </Question>

      <Question label={t('networkingPage.student.projectType')} hint={t('networkingPage.student.projectTypeHint')}>
        <div className="netplat-choice-grid" role="radiogroup">
          {projectTypes.map(type => (
            <ChoiceCard key={type} picked={form.projectType === type} onClick={() => setField('projectType', type)}>
              {t(`networkingPage.projectTypes.${type}`)}
            </ChoiceCard>
          ))}
        </div>
      </Question>

      {form.projectType === 'somethingElse' && (
        <Question label={t('networkingPage.student.projectTypeOther')} hint={t('networkingPage.student.projectTypeOtherHint')} htmlFor="netplat-other">
          <textarea
            id="netplat-other"
            required
            rows="3"
            value={form.projectTypeOther ?? ''}
            onChange={e => setField('projectTypeOther', e.target.value)}
          />
        </Question>
      )}

      <ConsentCheck
        checked={form.consent}
        onChange={value => setField('consent', value)}
        label={t('networkingPage.student.consent')}
      />

      <Notice tone={notice?.tone}>{notice?.text}</Notice>

      <button type="submit" className="netplat-button-primary" disabled={saving}>
        {saving
          ? t('networkingPage.signup.saving')
          : profile ? t('networkingPage.signup.update') : t('networkingPage.signup.submit')}
      </button>
    </form>
  );
}

// -------------------------------------------------------------------------
// step 2: dates

function AvailabilityCalendar({ role, profile, onDone }) {

  const { t } = useTranslation();

  const today = useMemo(() => new Date(), []);
  const [view, setView] = useState({ year: today.getFullYear(), month: today.getMonth() });
  const [selected, setSelected] = useState(() => new Set());
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState(null);

  const grid = useMemo(() => buildMonthGrid(view.year, view.month), [view]);

  // load the days already stored for this person
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await requestJson(`/api/network/availability?role=${role}&id=${profile.id}`);
        if (!cancelled) setSelected(new Set(data.dates ?? []));
      } catch (error) {
        console.error('Availability load failed:', error);
      }
    })();
    return () => { cancelled = true; };
  }, [role, profile.id]);

  const toggleDay = (date) => {
    const key = dateKey(date);
    setNotice(null);
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
    setNotice(null);
    try {
      await requestJson('/api/network/availability', {
        method: 'PUT',
        body: JSON.stringify({ role, id: profile.id, dates: [...selected].sort() }),
      });
      setNotice({ tone: 'good', text: t('networkingPage.calendar.saved') });
    } catch (error) {
      console.error('Availability save failed:', error);
      setNotice({ tone: 'error', text: t('networkingPage.saveError') });
    } finally {
      setSaving(false);
    }
  };

  const monthLabel = new Date(view.year, view.month, 1)
    .toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

  return (
    <div id="netplat-calendar">

      <SectionHeader>{t(`networkingPage.calendar.${role}.heading`)}</SectionHeader>
      <p className="netplat-lead">{t('networkingPage.calendar.lead')}</p>

      <div className="netplat-calendar-header">
        <button type="button" onClick={() => shiftMonth(-1)} title={t('networkingPage.calendar.previous')} aria-label={t('networkingPage.calendar.previous')}>&lsaquo;</button>
        <h3>{monthLabel}</h3>
        <button type="button" onClick={() => shiftMonth(1)} title={t('networkingPage.calendar.next')} aria-label={t('networkingPage.calendar.next')}>&rsaquo;</button>
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

      <p className="netplat-calendar-count">
        {selected.size === 0
          ? t('networkingPage.calendar.countNone')
          : t('networkingPage.calendar.count', { count: selected.size })}
      </p>

      <Notice tone={notice?.tone}>{notice?.text}</Notice>

      <div className="netplat-calendar-footer">
        <button type="button" className="netplat-button-primary" onClick={save} disabled={saving}>
          {saving ? t('networkingPage.calendar.saving') : t('networkingPage.calendar.save')}
        </button>
        {notice?.tone === 'good' && (
          <button type="button" className="netplat-button-secondary" onClick={onDone}>
            {t('networkingPage.calendar.goToMatches')}
          </button>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// step 3: matches. students see supervisors, supervisors see students; emails never shown

function MatchList({ role, profile }) {

  const { t } = useTranslation();
  const isStudent = role === 'student';

  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await requestJson(`/api/network/matches?role=${role}&id=${profile.id}`);
      setMatches(data.matches ?? []);
    } catch (error) {
      console.error('Match load failed:', error);
      setNotice({ tone: 'error', text: t('networkingPage.matches.loadError') });
    } finally {
      setLoading(false);
    }
  }, [role, profile.id, t]);

  useEffect(() => { load(); }, [load]);

  const sendRequest = async (match) => {
    setPending(match.id);
    setNotice(null);
    try {
      await requestJson('/api/network/requests', {
        method: 'POST',
        body: JSON.stringify({ fromRole: role, fromId: profile.id, toId: match.id }),
      });
      setMatches(prev => prev.map(item => item.id === match.id ? { ...item, requestStatus: 'sent' } : item));
    } catch (error) {
      console.error('Match request failed:', error);
      setNotice({ tone: 'error', text: t('networkingPage.matches.requestError') });
    } finally {
      setPending(null);
    }
  };

  // first letter of the name, shown in the pink circle
  const initial = (name) => (name?.trim()?.[0] ?? '?').toUpperCase();

  return (
    <div className="netplat-matches-wrap">

      <SectionHeader>{t(`networkingPage.matches.${role}.heading`)}</SectionHeader>
      <p className="netplat-lead">{t(`networkingPage.matches.${role}.lead`)}</p>

      <Notice tone={notice?.tone}>{notice?.text}</Notice>

      {loading && <p className="netplat-empty">{t('networkingPage.matches.loading')}</p>}
      {!loading && matches.length === 0 && <p className="netplat-empty">{t('networkingPage.matches.empty')}</p>}

      {!loading && matches.length > 0 && (
        <ul id="netplat-matches">
          {matches.map(match => {
            const profileLink = safeUrl(match.profileUrl);
            const sharedDays = match.sharedDates?.length ?? 0;
            const tags = isStudent ? (match.projectTypes ?? []) : [match.projectType].filter(Boolean);

            return (
              <li key={match.id} className="netplat-match-item">

                <div className="netplat-match-photo" aria-hidden="true">{initial(match.name)}</div>

                <div className="netplat-match-text">
                  <h3>{match.name}</h3>
                  <p className="netplat-match-score">{t('networkingPage.matches.score', { score: match.score })}</p>

                  {isStudent ? (
                    <>
                      <p>
                        {match.affiliation}, {t(`networkingPage.countries.${match.country}`)}<br />
                        {t('networkingPage.matches.places', { count: match.placements })},{' '}
                        {t('networkingPage.matches.sharedDays', { count: sharedDays })}
                      </p>
                      <p>{match.description}</p>
                      {profileLink && (
                        <a href={profileLink} target="_blank" rel="noopener noreferrer">
                          {t('networkingPage.matches.viewProfile')}
                        </a>
                      )}
                    </>
                  ) : (
                    <p>
                      {match.studyProgram}, {match.university}<br />
                      {t('networkingPage.matches.sharedDays', { count: sharedDays })}
                      {match.projectTypeOther && <><br />{match.projectTypeOther}</>}
                    </p>
                  )}

                  <ul className="netplat-tag-row">
                    {tags.map(type => (
                      <li key={type} className="netplat-tag">{t(`networkingPage.projectTypes.${type}`)}</li>
                    ))}
                  </ul>

                  {match.requestStatus === 'sent'
                    ? <p className="netplat-notice netplat-notice-good">{t('networkingPage.matches.requested')}</p>
                    : (
                      <button
                        type="button"
                        className="netplat-button-primary"
                        disabled={pending === match.id}
                        onClick={() => sendRequest(match)}
                      >
                        {pending === match.id
                          ? t('networkingPage.matches.requesting')
                          : t(`networkingPage.matches.${role}.request`)}
                      </button>
                    )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// -------------------------------------------------------------------------

function NetworkingPlatformPage() {

  const { t } = useTranslation();

  // saved sign-up is kept locally so a refresh does not force a new sign-up
  const [session, setSession] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [role, setRole] = useState(() => session?.role ?? null);
  const [step, setStep] = useState(() => (session ? 'matches' : 'role'));

  const pickRole = (picked) => {
    setRole(picked);
    setStep('signup');
  };

  const onSaved = (profile) => {
    const firstTime = !session;
    const next = { role, profile };
    setSession(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch (error) {
      console.error('Could not store sign-up locally:', error);
    }
    if (firstTime) setStep(role === 'student' ? 'calendar' : 'matches');
  };

  return (
    <div className="NetworkingPlatformPage unbounded-weight300">

      <div id="netplat-intro">
        <div id="netplat-title">
          <h1>{t('networkingPage.intro.titleLine1')}<span>{t('networkingPage.intro.kicker')}</span></h1>
          <h1>{t('networkingPage.intro.titleLine2')}</h1>
        </div>
        <p id="netplat-briefing">{t('networkingPage.intro.text')}</p>
      </div>

      {step === 'role' && <RolePicker onPick={pickRole} />}

      {step !== 'role' && (
        <nav id="netplat-steps" aria-label={t('networkingPage.intro.titleLine2')}>
          {steps.filter(key => role === 'student' || key !== 'calendar').map((key, index) => {
            const locked = key !== 'signup' && !session;
            return (
              <button
                key={key}
                type="button"
                disabled={locked}
                title={locked ? t('networkingPage.steps.locked') : undefined}
                className={`netplat-step ${step === key ? 'is-active' : ''}`}
                onClick={() => setStep(key)}
              >
                <span className="netplat-step-number" aria-hidden="true">{index + 1}</span>
                {t(`networkingPage.steps.${key}`)}
              </button>
            );
          })}
        </nav>
      )}

      {/* before signing up, the role can still be changed */}
      {step === 'signup' && !session && (
        <button type="button" className="netplat-link" onClick={() => setStep('role')}>
          &larr; {t('networkingPage.role.back')}
        </button>
      )}

      {step === 'signup' && role === 'supervisor' && <SupervisorSignup profile={session?.profile} onSaved={onSaved} />}
      {step === 'signup' && role === 'student' && <StudentSignup profile={session?.profile} onSaved={onSaved} />}
      {step === 'calendar' && session && <AvailabilityCalendar role={role} profile={session.profile} onDone={() => setStep('matches')} />}
      {step === 'matches' && session && <MatchList role={role} profile={session.profile} />}

    </div>
  );
}

export default NetworkingPlatformPage;