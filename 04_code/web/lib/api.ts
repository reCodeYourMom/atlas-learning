// Client API minimal. Le token Bearer est stocké en localStorage (démo MVP).
// Toutes les requêtes passent par /api/* (proxy Next → FastAPI), donc same-origin.

import type {
  ArCoverage,
  ClassDigest,
  ClassGap,
  CurriculumSettings,
  LinguistItem,
  LinguistQueue,
  Me,
  NextItem,
  RemediationPreview,
  ProofSurfaces,
  SchoolOverview,
  TutorExplanation,
  StudentProfile,
  StudentRow,
  Trajectory,
} from "./types";

const TOKEN_KEY = "atlas.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  // Un Authorization explicite prime sur le token de session.
  if (token && !headers["Authorization"]) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface Integration {
  organization: {
    id: string; name: string; domain: string | null;
    seats: number | null; seats_used: number; over_capacity?: boolean;
  };
  integration: {
    provider: string; status: string; admin_email: string | null;
    last_sync_at: string | null; last_error: string | null;
  } | null;
}

export interface RosterRun {
  id: string; status: string; summary: string | null;
  created: number; updated: number; deactivated: number; errors: number;
  pending_deactivations: number;
  started_at: string | null; finished_at: string | null;
}

export interface AuditEntry {
  id: string; action: string; user_id: string | null; school_id: string | null;
  resource_type: string | null; resource_id: string | null; created_at: string | null;
}

export interface SetupState {
  steps: { key: string; done: boolean }[];
  done: number;
  total: number;
}

export interface Guardian {
  user_id: string;
  email: string;
  source: string;
}

export const api = {
  // Providers SSO activés côté serveur (pour afficher les bons boutons).
  authProviders: () =>
    request<{ providers: string[]; demo_login: boolean }>("/auth/providers"),

  // Connexion de démonstration (hors production, cf. /demo/login côté API).
  demoLogin: (email: string, password: string) =>
    request<{ token: string; user_id: string }>("/demo/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  // — Console IT admin : rostering —
  adminIntegration: () => request<Integration>("/admin/integration"),
  rosteringSync: (force = false) =>
    request<RosterRun>(`/admin/rostering/sync${force ? "?force=true" : ""}`, { method: "POST" }),
  rosteringRuns: () => request<{ runs: RosterRun[] }>("/admin/rostering/runs"),

  // — Console curriculum (B3) : framework d'affichage du tenant —
  adminCurriculum: () => request<CurriculumSettings>("/admin/curriculum"),
  adminSetCurriculum: (curriculum_view: string) =>
    request<{ curriculum_view: string }>("/admin/curriculum", {
      method: "POST",
      body: JSON.stringify({ curriculum_view }),
    }),

  // — Conformité PDPL —
  adminAudit: (limit = 8) => request<{ entries: AuditEntry[] }>(`/admin/audit?limit=${limit}`),
  adminExport: () => request<unknown>("/admin/export"),

  // — Onboarding guidé + accès parent —
  adminSetup: () => request<SetupState>("/admin/setup"),
  parentsInvite: () => request<{ invited: number }>("/admin/parents/invite", { method: "POST" }),
  parentRequestLink: (email: string) =>
    request<{ ok: boolean }>("/parent/request-link", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  // Consommation du lien magique (single-use) : POST déclenché par un clic HUMAIN —
  // le GET du lien email ne consomme rien (anti-préchargement des scanners d'emails).
  parentLoginConfirm: (token: string) =>
    request<{ token: string }>("/parent/login/confirm", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  adminLoginConfirm: (token: string) =>
    request<{ token: string }>("/admin/login/confirm", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  // Lien magique du back-office linguiste (même contrat single-use / anti-préchargement).
  linguistRequestLink: (email: string) =>
    request<{ ok: boolean }>("/linguist/request-link", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  linguistLoginConfirm: (token: string) =>
    request<{ token: string }>("/linguist/login/confirm", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  parentChildren: () => request<{ children: { student_id: string; label: string }[] }>("/parent/children"),

  // — Tuteurs gérés par le staff —
  listGuardians: (studentId: string) =>
    request<{ guardians: Guardian[] }>(`/students/${studentId}/guardians`),
  addGuardian: (studentId: string, email: string) =>
    request<unknown>(`/students/${studentId}/guardians`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  removeGuardian: (studentId: string, userId: string) =>
    request<unknown>(`/students/${studentId}/guardians/${userId}`, { method: "DELETE" }),

  me: () => request<Me>("/me"),

  classGaps: (classroomId: string) =>
    request<{ classroom_id: string; gaps: ClassGap[] }>(`/classrooms/${classroomId}/gaps`),

  classStudents: (classroomId: string) =>
    request<{ classroom_id: string; name: string; students: StudentRow[] }>(
      `/classrooms/${classroomId}/students`,
    ),

  classDigest: (classroomId: string) =>
    request<ClassDigest>(`/classrooms/${classroomId}/digest`),

  studentProfile: (studentId: string) =>
    request<StudentProfile>(`/students/${studentId}/profile`),

  studentTrajectory: (studentId: string) =>
    request<Trajectory>(`/students/${studentId}/trajectory`),

  tutorExplain: (studentId: string, competencyCode: string) =>
    request<TutorExplanation>(
      `/students/${studentId}/tutor?competency_code=${encodeURIComponent(competencyCode)}`,
    ),

  remediation: (competency_code: string, lang: string) =>
    request<RemediationPreview>("/remediation/preview", {
      method: "POST",
      body: JSON.stringify({ competency_code, lang }),
    }),

  schoolOverview: (schoolId: string) =>
    request<SchoolOverview>(`/schools/${schoolId}/overview`),

  schoolProof: (schoolId: string) =>
    request<ProofSurfaces>(`/schools/${schoolId}/proof`),

  // — Couverture arabe de la banque (surface de preuve, lecture seule pour un admin) —
  // La proposition/validation AR (gate G3) vit dans le back-office linguiste ci-dessous :
  // c'est un acte de staff Atlas, jamais d'un admin d'établissement.
  arCoverage: () => request<ArCoverage>("/admin/arabic/coverage"),

  // — Back-office linguiste (persona dédié) : file de validation AR —
  linguistQueue: () => request<LinguistQueue>("/linguist/queue"),
  linguistItem: (itemId: string) => request<LinguistItem>(`/linguist/items/${itemId}`),
  linguistEditArabic: (itemId: string, content_ar: Record<string, unknown>) =>
    request<LinguistItem>(`/linguist/items/${itemId}/arabic`, {
      method: "POST",
      body: JSON.stringify({ content_ar }),
    }),
  linguistValidate: (itemId: string) =>
    request<LinguistItem>(`/linguist/items/${itemId}/validate`, { method: "POST" }),
  linguistFlag: (itemId: string, reason: string) =>
    request<LinguistItem>(`/linguist/items/${itemId}/flag`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  // — Session élève —
  startSession: (student_id: string) =>
    request<{ session_id: string; status: string }>("/sessions", {
      method: "POST",
      body: JSON.stringify({ student_id }),
    }),

  nextItem: (sessionId: string) => request<NextItem>(`/sessions/${sessionId}/next-item`),

  submitResponse: (sessionId: string, item_id: string, selected: string, lang: string) =>
    request<NextItem>(`/sessions/${sessionId}/responses`, {
      method: "POST",
      body: JSON.stringify({ item_id, selected, lang }),
    }),
};
