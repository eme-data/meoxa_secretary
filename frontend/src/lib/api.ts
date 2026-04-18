const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit & { token?: string; rawBody?: BodyInit } = {},
): Promise<T> {
  const { token, headers, rawBody, body, ...rest } = init;
  const isRaw = rawBody !== undefined;
  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    body: isRaw ? rawBody : body,
    headers: {
      ...(isRaw ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, detail.detail ?? "Erreur inconnue");
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

// ---------------- Types ---------------- //

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginResponse extends Partial<TokenPair> {
  mfa_required?: boolean;
  challenge_token?: string;
}

export interface MfaEnrollStart {
  secret: string;
  provisioning_uri: string;
  qr_code_png_b64: string;
}

export interface Setting {
  key: string;
  label: string;
  description: string;
  kind: "string" | "int" | "bool" | "select" | "secret" | "text";
  options: string[];
  is_secret: boolean;
  value: string;
  masked: string;
  has_value: boolean;
}

export interface BrandingOut {
  logo_url: string | null;
  primary_color: string | null;
  accent_color: string | null;
}

export interface SubscriptionOut {
  status:
    | "trialing"
    | "active"
    | "past_due"
    | "canceled"
    | "unpaid"
    | "incomplete"
    | "incomplete_expired"
    | "none";
  plan: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface OnboardingStatus {
  completed: boolean;
  completed_at: string | null;
  steps: {
    logo_uploaded: boolean;
    microsoft_connected: boolean;
    teams_recording_confirmed: boolean;
    reply_tone_configured: boolean;
    signature_configured: boolean;
    mfa_enabled: boolean;
    billing_active: boolean;
  };
}

// ---------------- Auth ---------------- //

export const authApi = {
  signup: (body: {
    email: string;
    full_name: string;
    password: string;
    organization_name: string;
  }) =>
    apiFetch<TokenPair>("/api/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    apiFetch<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  mfaLogin: (body: { challenge_token: string; code: string }) =>
    apiFetch<TokenPair>("/api/v1/auth/mfa/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  mfaEnrollStart: (token: string) =>
    apiFetch<MfaEnrollStart>("/api/v1/auth/mfa/enroll/start", { method: "POST", token }),
  mfaEnrollConfirm: (token: string, body: { secret: string; code: string }) =>
    apiFetch<{ backup_codes: string[] }>("/api/v1/auth/mfa/enroll/confirm", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
  mfaDisable: (token: string) =>
    apiFetch<void>("/api/v1/auth/mfa/disable", { method: "POST", token }),
  me: (token: string) =>
    apiFetch<{
      id: string;
      email: string;
      full_name: string;
      tenant_id: string;
      role: string;
      is_superadmin: boolean;
      totp_enabled: boolean;
    }>("/api/v1/auth/me", { token }),
};

// ---------------- Admin ---------------- //

export const adminApi = {
  listPlatform: (token: string) =>
    apiFetch<Setting[]>("/api/v1/admin/platform-settings", { token }),
  updatePlatform: (token: string, key: string, value: string) =>
    apiFetch<Setting>(`/api/v1/admin/platform-settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      token,
      body: JSON.stringify({ value }),
    }),
  listTenant: (token: string) => apiFetch<Setting[]>("/api/v1/admin/tenant-settings", { token }),
  updateTenant: (token: string, key: string, value: string) =>
    apiFetch<Setting>(`/api/v1/admin/tenant-settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      token,
      body: JSON.stringify({ value }),
    }),
};

// ---------------- Billing ---------------- //

export const billingApi = {
  get: (token: string) => apiFetch<SubscriptionOut>("/api/v1/billing/subscription", { token }),
  checkout: (token: string) =>
    apiFetch<{ url: string }>("/api/v1/billing/checkout", { method: "POST", token }),
  portal: (token: string) =>
    apiFetch<{ url: string }>("/api/v1/billing/portal", { method: "POST", token }),
};

// ---------------- Tenant (branding + RGPD) ---------------- //

export const tenantApi = {
  getBranding: (token: string) =>
    apiFetch<BrandingOut>("/api/v1/tenant/branding", { token }),
  updateBranding: (
    token: string,
    body: Partial<Pick<BrandingOut, "primary_color" | "accent_color" | "logo_url">>,
  ) =>
    apiFetch<BrandingOut>("/api/v1/tenant/branding", {
      method: "PUT",
      token,
      body: JSON.stringify(body),
    }),
  uploadLogo: (token: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch<BrandingOut>("/api/v1/tenant/branding/logo", {
      method: "POST",
      token,
      rawBody: fd,
    });
  },
  requestExport: (token: string) =>
    apiFetch<{ status: string; task_id: string | null }>("/api/v1/tenant/export", {
      method: "POST",
      token,
    }),
  deletionStatus: (token: string) =>
    apiFetch<{ scheduled_at: string | null; grace_period_days?: number }>(
      "/api/v1/tenant/deletion",
      { token },
    ),
  requestDeletion: (token: string) =>
    apiFetch<{ scheduled_at: string | null }>("/api/v1/tenant/deletion", {
      method: "POST",
      token,
    }),
  cancelDeletion: (token: string) =>
    apiFetch<{ scheduled_at: string | null }>("/api/v1/tenant/deletion", {
      method: "DELETE",
      token,
    }),
  onboardingStatus: (token: string) =>
    apiFetch<OnboardingStatus>("/api/v1/tenant/onboarding", { token }),
  confirmTeamsRecording: (token: string) =>
    apiFetch<OnboardingStatus>("/api/v1/tenant/onboarding/teams-confirmed", {
      method: "POST",
      token,
    }),
  importHistory: (token: string) =>
    apiFetch<{ status: string; task_id: string }>(
      "/api/v1/tenant/onboarding/import-history",
      { method: "POST", token },
    ),
  completeOnboarding: (token: string) =>
    apiFetch<OnboardingStatus>("/api/v1/tenant/onboarding/complete", {
      method: "POST",
      token,
    }),
};

// ---------------- Integrations ---------------- //

export interface MsIntegrationStatus {
  connected: boolean;
  healthy: boolean;
  expired?: boolean;
  ms_upn?: string;
  last_error?: string | null;
  last_error_at?: string | null;
  expires_at?: string;
}

export const integrationsApi = {
  microsoftAuthorize: (token: string) =>
    apiFetch<{ authorize_url: string }>("/api/v1/integrations/microsoft/authorize", { token }),
  microsoftStatus: (token: string) =>
    apiFetch<MsIntegrationStatus>("/api/v1/integrations/microsoft/status", { token }),
};

// ---------------- Dashboard tenant ---------------- //

export interface DashboardStats {
  emails_to_review: number;
  meetings_upcoming: number;
  crs_ready: number;
  llm_cost_usd_mtd: number;
}

export interface RecentEmail {
  id: string;
  subject: string;
  from_address: string;
  received_at: string | null;
  status: "pending" | "drafted" | "sent" | "ignored";
}

export interface RecentMeeting {
  id: string;
  title: string;
  starts_at: string;
  status: string;
  has_summary: boolean;
}

export const dashboardApi = {
  get: (token: string) =>
    apiFetch<{
      stats: DashboardStats;
      recent_emails: RecentEmail[];
      recent_meetings: RecentMeeting[];
    }>("/api/v1/tenant/dashboard", { token }),
};

// ---------------- Emails ---------------- //

export interface EmailThreadListItem {
  id: string;
  subject: string;
  from_address: string;
  snippet: string;
  received_at: string | null;
  status: "pending" | "drafted" | "sent" | "ignored";
}

export interface EmailThreadDetail extends EmailThreadListItem {
  body_text: string | null;
  suggested_reply: string | null;
  outlook_draft_id: string | null;
}

export const emailsApi = {
  list: (token: string) => apiFetch<EmailThreadListItem[]>("/api/v1/emails", { token }),
  get: (token: string, id: string) =>
    apiFetch<EmailThreadDetail>(`/api/v1/emails/${id}`, { token }),
  updateSuggestion: (token: string, id: string, suggested_reply: string) =>
    apiFetch<EmailThreadDetail>(`/api/v1/emails/${id}/suggestion`, {
      method: "PUT",
      token,
      body: JSON.stringify({ suggested_reply }),
    }),
  regenerate: (token: string, id: string) =>
    apiFetch<EmailThreadDetail>(`/api/v1/emails/${id}/regenerate`, {
      method: "POST",
      token,
    }),
  pushToOutlook: (token: string, id: string) =>
    apiFetch<EmailThreadDetail>(`/api/v1/emails/${id}/push-to-outlook`, {
      method: "POST",
      token,
    }),
  ignore: (token: string, id: string) =>
    apiFetch<EmailThreadDetail>(`/api/v1/emails/${id}/ignore`, {
      method: "POST",
      token,
    }),
};

// ---------------- Meetings ---------------- //

export interface MeetingListItem {
  id: string;
  title: string;
  starts_at: string;
  status: string;
}

export interface MeetingDetail {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  status: string;
  organizer_email: string;
  join_url: string | null;
  summary_markdown: string | null;
  action_items: Array<{ title: string; owner_email?: string; due_date?: string }> | null;
  planner_task_ids: string[] | null;
  raw_text_length: number;
}

export const meetingsApi = {
  list: (token: string) => apiFetch<MeetingListItem[]>("/api/v1/meetings", { token }),
  detail: (token: string, id: string) =>
    apiFetch<MeetingDetail>(`/api/v1/meetings/${id}/detail`, { token }),
  resendEmail: (token: string, id: string) =>
    apiFetch<{ status: string; to: string }>(`/api/v1/meetings/${id}/resend-email`, {
      method: "POST",
      token,
    }),
};

// ---------------- Agenda / scheduling ---------------- //

export interface Slot {
  start: string;
  end: string;
}

export const agendaApi = {
  suggestSlots: (
    token: string,
    body: { duration_min: number; from_date?: string; to_date?: string; max_slots?: number },
  ) =>
    apiFetch<Slot[]>("/api/v1/agenda/suggest-slots", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
  createMeeting: (
    token: string,
    body: { subject: string; start: string; end: string },
  ) =>
    apiFetch<{ id: string; join_url: string; subject: string }>("/api/v1/agenda/meetings", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
};

// ---------------- DPA ---------------- //

export const dpaApi = {
  generate: async (
    token: string,
    body: {
      legal_name: string;
      address: string;
      signatory_name: string;
      signatory_title: string;
      dpo_email?: string;
    },
  ): Promise<string> => {
    const response = await fetch(`${API_URL}/api/v1/tenant/dpa`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(response.status, detail.detail ?? "Erreur");
    }
    return response.text();
  },
};

// ---------------- Super-admin dashboard ---------------- //

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  onboarded_at: string | null;
  deletion_scheduled_at: string | null;
  members_count: number;
  subscription_status: string;
  last_activity_at: string | null;
  llm_cost_usd_mtd: number;
  llm_calls_mtd: number;
}

export const adminDashboardApi = {
  tenants: (token: string) =>
    apiFetch<{
      generated_at: string;
      totals: Record<string, number>;
      tenants: TenantSummary[];
    }>("/api/v1/admin/dashboard/tenants", { token }),
};

// ---------------- Team ---------------- //

export interface Member {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  totp_enabled: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: string;
  status: "pending" | "accepted" | "revoked" | "expired";
  expires_at: string;
  accept_url: string;
}

export const teamApi = {
  listMembers: (token: string) =>
    apiFetch<Member[]>("/api/v1/tenant/team/members", { token }),
  changeRole: (token: string, userId: string, role: string) =>
    apiFetch<Member>(`/api/v1/tenant/team/members/${userId}/role`, {
      method: "PUT",
      token,
      body: JSON.stringify({ role }),
    }),
  removeMember: (token: string, userId: string) =>
    apiFetch<void>(`/api/v1/tenant/team/members/${userId}`, {
      method: "DELETE",
      token,
    }),
  listInvitations: (token: string) =>
    apiFetch<Invitation[]>("/api/v1/tenant/team/invitations", { token }),
  createInvitation: (token: string, body: { email: string; role: string }) =>
    apiFetch<Invitation>("/api/v1/tenant/team/invitations", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
  revokeInvitation: (token: string, id: string) =>
    apiFetch<void>(`/api/v1/tenant/team/invitations/${id}`, {
      method: "DELETE",
      token,
    }),
};

export const invitationsApi = {
  preview: (token: string) =>
    apiFetch<{
      email: string;
      organization_name: string;
      role: string;
      expires_at: string;
    }>(`/api/v1/auth/invitations/${token}`),
  accept: (body: { token: string; password: string; full_name: string }) =>
    apiFetch<TokenPair>("/api/v1/auth/invitations/accept", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ---------------- Utils ---------------- //

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/access_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}
