// Client API minimal. Le token Bearer est stocké en localStorage (démo MVP).
// Toutes les requêtes passent par /api/* (proxy Next → FastAPI), donc same-origin.

import type {
  ArCoverage,
  ArItem,
  ClassDigest,
  ClassGap,
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
  // Un Authorization explicite (ex. jeton d'enrôlement MFA) prime sur le token de session.
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

export type LoginResult =
  | { token: string; user_id: string }
  | { mfa_setup_required: true; setup_token: string };

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
  login: (email: string, password: string, mfa_code?: string) =>
    request<LoginResult>("/login", {
      method: "POST",
      body: JSON.stringify({ email, password, mfa_code: mfa_code || null }),
    }),

  // Enrôlement MFA (1er login admin/enseignant) : génère le secret TOTP + URI otpauth.
  mfaEnroll: (setupToken: string) =>
    request<{ secret: string; otpauth_uri: string }>("/mfa/enroll", {
      method: "POST",
      headers: { Authorization: `Bearer ${setupToken}` },
    }),

  mfaConfirm: (setupToken: string, code: string) =>
    request<{ token: string; user_id: string }>("/mfa/enroll/confirm", {
      method: "POST",
      headers: { Authorization: `Bearer ${setupToken}` },
      body: JSON.stringify({ code }),
    }),

  // Providers SSO activés côté serveur (pour afficher les bons boutons).
  authProviders: () => request<{ providers: string[] }>("/auth/providers"),

  // — Console IT admin : rostering —
  adminIntegration: () => request<Integration>("/admin/integration"),
  rosteringSync: (force = false) =>
    request<RosterRun>(`/admin/rostering/sync${force ? "?force=true" : ""}`, { method: "POST" }),
  rosteringRuns: () => request<{ runs: RosterRun[] }>("/admin/rostering/runs"),

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

  // — Console linguiste : descente de l'arabe (Mouvement 02) —
  arCoverage: () => request<ArCoverage>("/admin/arabic/coverage"),
  arPending: () =>
    request<{ items: ArItem[]; coverage: ArCoverage }>("/admin/arabic/pending"),
  arPropose: (itemId: string) =>
    request<ArItem>(`/admin/arabic/${itemId}/propose`, { method: "POST" }),
  arValidate: (itemId: string) =>
    request<ArItem>(`/admin/arabic/${itemId}/validate`, { method: "POST" }),

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
