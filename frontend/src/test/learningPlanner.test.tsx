import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LearningPlanner } from '../pages/LearningPlanner';
import { endpoints } from '../services/api';
import type { LearningPlanDetail, LearningPlanSummary, LearningSchedule } from '../services/api';

vi.mock('../services/api', () => {
  const createMock = vi.fn();
  const discoverMock = vi.fn();
  const generateMock = vi.fn();
  const listMock = vi.fn();
  const getMock = vi.fn();
  const toggleMock = vi.fn();
  const removeMock = vi.fn();
  const sessionStatusMock = vi.fn();
  const sessionLoginMock = vi.fn();
  const sessionLogoutMock = vi.fn();
  const reverifyMock = vi.fn();
  const domainsMock = vi.fn();
  const scheduleGetMock = vi.fn();
  const scheduleCreateMock = vi.fn();
  const scheduleRemoveMock = vi.fn();
  const planSessionStateMock = vi.fn();
  const planSessionStartMock = vi.fn();
  const planSessionCompleteMock = vi.fn();
  return {
    endpoints: {
      kb: {
        learningPlans: {
          create: createMock,
          discover: discoverMock,
          generate: generateMock,
          list: listMock,
          get: getMock,
          toggleTask: toggleMock,
          remove: removeMock,
          session: {
            status: sessionStatusMock,
            login: sessionLoginMock,
            logout: sessionLogoutMock,
          },
          reverify: reverifyMock,
          planSession: {
            state: planSessionStateMock,
            start: planSessionStartMock,
            complete: planSessionCompleteMock,
          },
          schedule: {
            get: scheduleGetMock,
            create: scheduleCreateMock,
            remove: scheduleRemoveMock,
          },
        },
        gaps: { domains: domainsMock },
      },
    },
  };
});

const unconfiguredSession = {
  session: {
    configured: false,
    authenticated: false,
    email: null,
    expires_at: null,
    last_login_at: null,
    has_cookies: false,
  },
};

const task = (id: number, phase = 1, overrides: Partial<LearningPlanDetail['tasks'][number]> = {}): LearningPlanDetail['tasks'][number] => ({
  id,
  phase,
  phase_title: 'Phase 1 — Foundations',
  sort_order: 0,
  title: `Complete: What is SSRF? ${id}`,
  description: null,
  resource_title: 'What is SSRF?',
  resource_url: null,
  resource_type: 'reading',
  difficulty: 'beginner',
  est_time: null,
  topics: ['SSRF'],
  skills: [],
  prerequisites: [],
  resource_id: 1,
  path_id: 1,
  source_crawled: false,
  done: false,
  ...overrides,
});

const source = {
  report: {
    platform: 'PortSwigger Web Security Academy',
    source_url: 'https://portswigger.net/web-security/learning-paths',
    paths_discovered: 2,
    paths_crawled: 2,
    paths_failed: 0,
    resources_extracted: 4,
    resources_with_url: 1,
    resources_verified: 0,
    resources_failed: 1,
    statuses: { discovered: 3, auth_required: 1 },
  },
  paths: [
    {
      id: 1,
      platform: 'PortSwigger Web Security Academy',
      title: 'Server-side request forgery (SSRF) attacks',
      description: 'This learning path covers SSRF vulnerabilities.',
      difficulty: 'PRACTITIONER',
      source_url: 'https://portswigger.net/web-security/learning-paths/ssrf-attacks',
      first_resource_url: 'https://portswigger.net/web-security/learning-paths/ssrf-attacks/ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf',
      resource_total: 23,
      section_count: 2,
      resource_count: 3,
      crawl_status: 'crawled',
      status_code: 200,
      error: null,
      resources: [
        { id: 1, title: 'What is SSRF?', url: 'https://portswigger.net/web-security/learning-paths/ssrf-attacks/ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf', resource_type: 'reading', difficulty: 'APPRENTICE', section: 'What is SSRF?', sort_order: 1, crawl_status: 'auth_required', status_code: 200, error: 'Page requires authentication (redirected to sign-in)' },
        { id: 2, title: 'Common SSRF attacks', url: null, resource_type: 'reading', difficulty: 'APPRENTICE', section: 'Common SSRF attacks', sort_order: 2, crawl_status: 'discovered', status_code: null, error: null },
        { id: 3, title: 'Lab: Basic SSRF against the local server', url: null, resource_type: 'lab', difficulty: 'APPRENTICE', section: 'Common SSRF attacks', sort_order: 3, crawl_status: 'discovered', status_code: null, error: null },
      ],
    },
  ],
};

const discoveredPlan: LearningPlanDetail = {
  id: 1,
  goal: 'Become proficient in Web Security',
  goal_key: null,
  description: null,
  status: 'discovered',
  engine: 'deterministic',
  created_at: '2026-08-11T10:00:00Z',
  generated_at: null,
  resources: [],
  topics: [],
  dependencies: [],
  overview: '',
  phases: [],
  tasks: [],
  stats: { total_tasks: 0, done_tasks: 0, progress_percent: 0 },
  next_task: null,
  source,
  path_progress: [],
};

const reverifiedPlan: LearningPlanDetail = {
  ...discoveredPlan,
  source: {
    ...source,
    paths: [
      {
        ...source.paths[0],
        resources: source.paths[0].resources.map((r) =>
          r.id === 1
            ? { ...r, crawl_status: 'crawled', status_code: 200, error: null }
            : r.id === 2
              ? {
                  ...r,
                  url: 'https://portswigger.net/web-security/learning-paths/ssrf-attacks/ssrf-attacks-common-ssrf-attacks/ssrf/common-ssrf-attacks',
                  crawl_status: 'crawled',
                  status_code: 200,
                  error: null,
                }
              : {
                  ...r,
                  url: 'https://portswigger.net/web-security/learning-paths/ssrf-attacks/ssrf-attacks-basic-ssrf-against-the-local-server/lab/basic-ssrf-against-the-local-server',
                  crawl_status: 'crawled',
                  status_code: 200,
                  error: null,
                },
        ),
      },
    ],
  },
};

const generatedPlan: LearningPlanDetail = {
  ...discoveredPlan,
  status: 'generated',
  generated_at: '2026-08-11T10:00:00Z',
  resources: [
    { title: 'What is SSRF?', platform: 'PortSwigger Web Security Academy', url: null, type: 'reading', topics: ['SSRF'], skills: [], difficulty: 'beginner', prerequisites: [], estimated_time: '', learning_objectives: [], completion_requirement: '' },
  ],
  topics: [{ name: 'SSRF', status: 'unknown', resources: [], difficulty: 'intermediate', est_time: '' }],
  dependencies: [{ from: 'What is SSRF?', to: 'Common SSRF attacks', source: 'ai', note: 'Recommended prerequisite (AI-inferred)' }],
  overview: 'Built from 3 resources discovered on the source platform.',
  phases: [
    { phase: 1, title: 'Phase 1 — Foundations', tasks: [{ title: 'Complete: What is SSRF?', resource_index: 1, topics: ['SSRF'] }] },
    { phase: 4, title: 'Phase 4 — Practical Labs & Application', tasks: [{ title: 'Complete: Lab: Basic SSRF against the local server', resource_index: 1, topics: ['Lab'] }] },
  ],
  tasks: [task(11), task(12, 4, { title: 'Complete: Lab: Basic SSRF against the local server', resource_id: 3, resource_type: 'lab' })],
  path_progress: [{ path_id: 1, title: 'Server-side request forgery (SSRF) attacks', done_tasks: 0, total_tasks: 2, progress_percent: 0 }],
  next_task: task(11),
};

const scheduleFixture: LearningSchedule = {
  plan_id: 1,
  goal: 'Become proficient in Web Security',
  mode: 'daily_hours',
  params: { daily_hours: 1, modules_per_day: 5, budget_minutes: 60, time_slots: [], instruction: null },
  generated_at: '2026-08-11T12:00:00Z',
  engine: 'deterministic',
  stale: false,
  note: null,
  stats: {
    days: 2,
    total_minutes: 120,
    total_hours: 2,
    tasks_scheduled: 2,
    done_tasks: 0,
    remaining_tasks: 2,
    estimated_end_date: '2026-08-12',
  },
  days: [
    {
      day: 1,
      date: '2026-08-11',
      label: 'Mon, Aug 11',
      total_minutes: 60,
      slots: [],
      tasks: [
        { task_id: 11, phase: 1, phase_title: 'Phase 1 — Foundations', title: 'Complete: What is SSRF? 11', est_time: '1h', minutes: 60, resource_title: 'What is SSRF?', resource_url: null, resource_type: 'reading', done: false },
      ],
    },
    {
      day: 2,
      date: '2026-08-12',
      label: 'Tue, Aug 12',
      total_minutes: 60,
      slots: [],
      tasks: [
        { task_id: 12, phase: 4, phase_title: 'Phase 4 — Practical Labs & Application', title: 'Complete: Lab: Basic SSRF against the local server', est_time: '1h', minutes: 60, resource_title: 'Lab: Basic SSRF', resource_url: null, resource_type: 'lab', done: false },
      ],
    },
  ],
};

const planSessionStateFixture = {
  plan_id: 1,
  live_session: {
    id: 99,
    learning_plan_id: 1,
    learning_task_id: 11,
    practice_task: 'Complete: What is SSRF? 11',
    duration_mins: 25,
    status: 'active',
    created_at: '2026-08-11T12:30:00Z',
    completed_at: null,
  },
  last_session: null,
  next_task: task(12),
  progress: { total_tasks: 2, done_tasks: 0, progress_percent: 0 },
  completed: false,
};

const summary: LearningPlanSummary = {
  id: 1,
  goal: 'Become proficient in Web Security',
  goal_key: null,
  status: 'generated',
  engine: 'deterministic',
  created_at: '2026-08-11T10:00:00Z',
  generated_at: null,
  source: { platform: 'PortSwigger Web Security Academy', paths_discovered: 2, paths_crawled: 2, paths_failed: 0, resources_extracted: 4, resources_verified: 0, resources_failed: 1 },
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <LearningPlanner />
    </MemoryRouter>,
  );

const fillForm = async (goal = 'Become proficient in Web Security') => {
  fireEvent.change(screen.getByPlaceholderText(/Complete all PortSwigger/), { target: { value: goal } });
  fireEvent.change(screen.getByPlaceholderText(/PortSwigger Academy/), { target: { value: 'PortSwigger Academy | https://portswigger.net/web-security/learning-paths' } });
  fireEvent.change(screen.getByPlaceholderText(/HTTP basics, Burp Suite/), { target: { value: 'XSS, CSRF' } });
};

describe('LearningPlanner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(endpoints.kb.learningPlans.list).mockResolvedValue({ items: [summary] });
    vi.mocked(endpoints.kb.gaps.domains).mockResolvedValue({ goals: [] });
    vi.mocked(endpoints.kb.learningPlans.session.status).mockResolvedValue(unconfiguredSession);
    vi.mocked(endpoints.kb.learningPlans.schedule.get).mockResolvedValue({ schedule: null });
    vi.mocked(endpoints.kb.learningPlans.planSession.state).mockResolvedValue({
      session: { plan_id: 1, live_session: null, last_session: null, next_task: null, progress: { total_tasks: 0, done_tasks: 0, progress_percent: 0 }, completed: false },
    });
  });

  it('renders the goal + source form with the two-step buttons', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    expect(screen.getByPlaceholderText(/Complete all PortSwigger/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/PortSwigger Academy/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Discover paths/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Discover \+ roadmap/ })).toBeInTheDocument();
  });

  it('discovers the source structure first (Layer 1), then builds the roadmap (Layer 2)', async () => {
    vi.mocked(endpoints.kb.learningPlans.discover).mockResolvedValue({ plan: discoveredPlan });
    vi.mocked(endpoints.kb.learningPlans.generate).mockResolvedValue({ plan: generatedPlan });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();

    fireEvent.click(screen.getByRole('button', { name: /Discover paths/ }));
    await waitFor(() => expect(endpoints.kb.learningPlans.discover).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByRole('heading', { name: /Source Structure/ })).toBeInTheDocument());

    // Honest crawl report: 2 paths discovered, 4 resources extracted.
    expect(screen.getAllByText((_, el) => el?.textContent?.includes('2 path(s) discovered') ?? false).length).toBeGreaterThan(0);
    expect(screen.getAllByText((_, el) => el?.textContent?.includes('4 resource(s) extracted') ?? false).length).toBeGreaterThan(0);
    // The real learning path with its exact source URL.
    expect(screen.getByText('Server-side request forgery (SSRF) attacks')).toBeInTheDocument();
    expect(screen.getByText(/PRACTITIONER/)).toBeInTheDocument();
    // The 23-resource count from the site itself.
    expect(screen.getByText(/3\/23 resources/)).toBeInTheDocument();
    // Honest status chips: the exposed URL bounced to sign-in; others stay discovered.
    expect(screen.getAllByText('DISCOVERED').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('SIGN-IN REQUIRED')).toBeInTheDocument();
    // No roadmap yet at this stage.
    expect(screen.queryByText(/Personalized Roadmap/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Build personalized roadmap/ }));
    await waitFor(() => expect(endpoints.kb.learningPlans.generate).toHaveBeenCalledWith(1, expect.anything()));
    await waitFor(() => expect(screen.getByText(/Personalized Roadmap/)).toBeInTheDocument());
    // Layer 2 phases reference real resources; labs land in the practical phase.
    expect(screen.getByText('Phase 1 — Foundations')).toBeInTheDocument();
    expect(screen.getByText('Phase 4 — Practical Labs & Application')).toBeInTheDocument();
    // Dependency is labeled "recommended" (AI-inferred), never official.
    expect(screen.getByText('recommended')).toBeInTheDocument();
    // Per-path progress appears under the (expanded) source path.
    fireEvent.click(screen.getByRole('button', { name: /Server-side request forgery \(SSRF\) attacks/ }));
    expect(screen.getByText(/Path progress/)).toBeInTheDocument();
  });

  it('runs discovery + roadmap in one step via the primary button', async () => {
    vi.mocked(endpoints.kb.learningPlans.create).mockResolvedValue({ plan: generatedPlan });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();

    fireEvent.click(screen.getByRole('button', { name: /Discover \+ roadmap/ }));
    await waitFor(() => expect(endpoints.kb.learningPlans.create).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByRole('heading', { name: /Source Structure/ })).toBeInTheDocument());
    expect(screen.getByText(/Personalized Roadmap/)).toBeInTheDocument();
    expect(screen.getByText(/Next:/)).toBeInTheDocument();
  });

  it('shows SOURCE labels (not fake CRAWLED) for unverified resources', async () => {
    vi.mocked(endpoints.kb.learningPlans.create).mockResolvedValue({ plan: generatedPlan });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover \+ roadmap/ }));
    await waitFor(() => expect(screen.getByText(/Personalized Roadmap/)).toBeInTheDocument());
    // Tasks reference real source resources — never labeled crawled.
    expect(screen.getAllByText('SOURCE').length).toBeGreaterThanOrEqual(1);
    // No task chip claims "Resource fetched and verified".
    expect(screen.queryByTitle('Resource fetched and verified')).not.toBeInTheDocument();
  });

  it('renders a generated plan whose resources lack topics/prerequisites (no blank page)', async () => {
    // Simulate a stored payload generated before the backend always sent
    // `topics`/`prerequisites` on resources — the page must still render.
    const legacy = JSON.parse(JSON.stringify(generatedPlan)) as LearningPlanDetail;
    for (const r of legacy.resources) {
      // Simulate a stored payload generated before the backend always sent
      // `topics`/`prerequisites` — a deliberate type lie for the regression.
      delete (r as unknown as Record<string, unknown>).topics;
      delete (r as unknown as Record<string, unknown>).prerequisites;
    }
    vi.mocked(endpoints.kb.learningPlans.create).mockResolvedValue({ plan: legacy });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover \+ roadmap/ }));
    await waitFor(() => expect(screen.getByRole('heading', { name: /Source Structure/ })).toBeInTheDocument());
    // The roadmap and the resource row render without crashing.
    expect(screen.getByText(/Personalized Roadmap/)).toBeInTheDocument();
    expect(screen.getByText(/Resources \(1\)/)).toBeInTheDocument();
  });

  it('toggles a task and recomputes progress + per-path progress', async () => {
    vi.mocked(endpoints.kb.learningPlans.create).mockResolvedValue({ plan: generatedPlan });
    const toggled = { ...task(11), done: true };
    vi.mocked(endpoints.kb.learningPlans.toggleTask).mockResolvedValue({ ok: true, task: toggled });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover \+ roadmap/ }));
    await waitFor(() => expect(screen.getByLabelText(/Mark Complete: What is SSRF/)).toBeInTheDocument());

    fireEvent.click(screen.getByLabelText(/Mark Complete: What is SSRF/));
    await waitFor(() => expect(endpoints.kb.learningPlans.toggleTask).toHaveBeenCalledWith(1, 11, true));
    await waitFor(() => expect(screen.getByText(/1 \/ 2 tasks/)).toBeInTheDocument());
  });

  it('connects a PortSwigger account and re-verifies gated resources', async () => {
    vi.mocked(endpoints.kb.learningPlans.discover).mockResolvedValue({ plan: discoveredPlan });
    vi.mocked(endpoints.kb.learningPlans.session.login).mockResolvedValue({
      session: {
        configured: true,
        authenticated: true,
        email: 'me@example.com',
        expires_at: null,
        last_login_at: '2026-08-11T10:00:00Z',
        has_cookies: true,
      },
    });
    vi.mocked(endpoints.kb.learningPlans.reverify).mockResolvedValue({
      plan: reverifiedPlan,
      reverify: {
        paths_rechecked: 2,
        resources_unlocked: 2,
        resources_verified: 3,
        resources_failed: 0,
        statuses: { crawled: 3 },
      },
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover paths/ }));
    await waitFor(() => expect(screen.getByRole('heading', { name: /Source Structure/ })).toBeInTheDocument());

    // Not connected → the strip offers to connect.
    expect(screen.getByRole('button', { name: /Connect PortSwigger account/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Connect PortSwigger account/ }));
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), { target: { value: 'me@example.com' } });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), { target: { value: 'hunter2' } });
    fireEvent.click(screen.getByRole('button', { name: /Sign in/ }));
    await waitFor(() => expect(endpoints.kb.learningPlans.session.login).toHaveBeenCalledWith({
      email: 'me@example.com',
      password: 'hunter2',
      remember: true,
    }));

    // Connected → the gated resources can now be re-verified.
    await waitFor(() => expect(screen.getByText('me@example.com')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Re-verify gated resources/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Re-verify gated resources/ }));
    await waitFor(() => expect(endpoints.kb.learningPlans.reverify).toHaveBeenCalledWith(1));
    // Expand the path to see the resource rows.
    fireEvent.click(screen.getByRole('button', { name: /Server-side request forgery \(SSRF\) attacks/ }));
    await waitFor(() => expect(screen.getAllByText('CRAWLED').length).toBeGreaterThanOrEqual(3));
    // The previously URL-less lab now links to its real URL.
    const lab = screen.getByText('Lab: Basic SSRF against the local server');
    expect(lab.closest('a')).toHaveAttribute('href', expect.stringContaining('/lab/'));
  });

  it('builds a day-by-day study schedule on explicit user action', async () => {
    vi.mocked(endpoints.kb.learningPlans.create).mockResolvedValue({ plan: generatedPlan });
    vi.mocked(endpoints.kb.learningPlans.schedule.create).mockResolvedValue({ schedule: scheduleFixture });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover \+ roadmap/ }));
    await waitFor(() => expect(screen.getByText(/Personalized Roadmap/)).toBeInTheDocument());

    // Study Schedule section: no schedule yet → the create form (mode chips).
    expect(screen.getByText('📅 Study Schedule')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create study plan/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Create study plan/ }));

    await waitFor(() =>
      expect(endpoints.kb.learningPlans.schedule.create).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ mode: 'daily_hours', daily_hours: 1, modules_per_day: null, time_slots: [], instruction: null }),
      ),
    );
    // Day-by-day view with real roadmap task titles and honest stats.
    // (The task title also appears in the roadmap card → multiple matches.)
    await waitFor(() => expect(screen.getByText('Day 1 · Mon, Aug 11')).toBeInTheDocument());
    expect(screen.getByText('Day 2 · Tue, Aug 12')).toBeInTheDocument();
    expect(screen.getAllByText('Complete: What is SSRF? 11').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/2 days/)).toBeInTheDocument();
    expect(screen.getByText(/2h total/)).toBeInTheDocument();
    // Each day offers a Start button scoped to its first incomplete task.
    expect(screen.getAllByTitle(/Start a session on/).length).toBeGreaterThanOrEqual(2);
  });

  it('shows a stale banner when task progress changed since the schedule was built', async () => {
    vi.mocked(endpoints.kb.learningPlans.create).mockResolvedValue({ plan: generatedPlan });
    vi.mocked(endpoints.kb.learningPlans.schedule.get).mockResolvedValue({ schedule: { ...scheduleFixture, stale: true } });
    const toggled = { ...task(11), done: true };
    vi.mocked(endpoints.kb.learningPlans.toggleTask).mockResolvedValue({ ok: true, task: toggled });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover \+ roadmap/ }));
    await waitFor(() => expect(screen.getByLabelText(/Mark Complete: What is SSRF/)).toBeInTheDocument());

    // Toggling progress re-reads the schedule (read-only, no LLM) → stale flag.
    fireEvent.click(screen.getByLabelText(/Mark Complete: What is SSRF/));
    await waitFor(() => expect(endpoints.kb.learningPlans.schedule.get).toHaveBeenCalled());
    expect(screen.getByText(/Task progress changed since this schedule was built/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Regenerate/ })).toBeInTheDocument();
  });

  it('starts a study session on a specific scheduled-day task', async () => {
    vi.mocked(endpoints.kb.learningPlans.create).mockResolvedValue({ plan: generatedPlan });
    vi.mocked(endpoints.kb.learningPlans.schedule.create).mockResolvedValue({ schedule: scheduleFixture });
    vi.mocked(endpoints.kb.learningPlans.planSession.start).mockResolvedValue({
      ok: true,
      session: planSessionStateFixture.live_session,
      state: planSessionStateFixture,
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover \+ roadmap/ }));
    await waitFor(() => expect(screen.getByText(/Personalized Roadmap/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Create study plan/ }));
    await waitFor(() => expect(screen.getByText('Day 1 · Mon, Aug 11')).toBeInTheDocument());

    // Day 1's Start button targets the day's first incomplete task by id.
    // (Scoped by title — the Study Session card has its own global Start.)
    fireEvent.click(screen.getAllByTitle(/Start a session on/)[0]);
    await waitFor(() =>
      expect(endpoints.kb.learningPlans.planSession.start).toHaveBeenCalledWith(1, { task_id: 11 }),
    );
    await waitFor(() => expect(screen.getByText(/Study session started on:/)).toBeInTheDocument());
    // The live session card shows the practice task.
    expect(screen.getAllByText('Complete: What is SSRF? 11').length).toBeGreaterThanOrEqual(2);
  });

  it('shows an error when discovery fails', async () => {
    vi.mocked(endpoints.kb.learningPlans.discover).mockRejectedValue(new Error('API 500: boom'));
    renderPage();
    await waitFor(() => expect(screen.getByText(/New learning plan/)).toBeInTheDocument());
    await fillForm();
    fireEvent.click(screen.getByRole('button', { name: /Discover paths/ }));
    await waitFor(() => expect(screen.getByText(/API 500: boom/)).toBeInTheDocument());
  });
});
