import { getToken } from "./auth";

export type ApiUser = { id: number; email: string };

export type PromptSet = { id: number; name: string; created_at: string };
export type PromptVersionMeta = {
  id: number;
  version: number;
  notes: string | null;
  created_at: string;
};

export type RunRow = {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  project_id: string;
  yaml_filename: string;
  prompt_version_id: number | null;
  container_id: string | null;
  exit_code: number | null;
};

export type DbTaskRow = {
  id: string;
  name: string | null;
  stage: string | null;
  status: string;
  content: string | null;
  result_path: string | null;
  error_info: string | null;
  created_at: string;
  updated_at: string;
};

export type Artifact = {
  kind: string;
  path: string;
  stage?: string;
  task_id?: string;
};

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8080";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = String(data.detail);
    } catch {}
    throw new Error(detail);
  }

  return (await res.json()) as T;
}

export async function register(email: string, password: string): Promise<{ access_token: string; user: ApiUser }> {
  return request("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) });
}

export async function login(email: string, password: string): Promise<{ access_token: string; user: ApiUser }> {
  return request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export async function me(): Promise<ApiUser> {
  return request("/me");
}

export async function baselinePromptfiles(): Promise<{ baseline: Record<string, string> }> {
  return request("/promptfiles");
}

export async function listPromptSets(): Promise<PromptSet[]> {
  return request("/promptsets");
}

export async function createPromptSet(name: string): Promise<PromptSet> {
  return request("/promptsets", { method: "POST", body: JSON.stringify({ name }) });
}

export async function listPromptVersions(promptSetId: number): Promise<PromptVersionMeta[]> {
  return request(`/promptsets/${promptSetId}/versions`);
}

export async function createPromptVersion(
  promptSetId: number,
  notes: string,
  payload: Record<string, string>,
): Promise<{ id: number; prompt_set_id: number; version: number; notes: string | null; created_at: string }> {
  return request(`/promptsets/${promptSetId}/versions`, {
    method: "POST",
    body: JSON.stringify({ notes, payload }),
  });
}

export async function listRuns(): Promise<RunRow[]> {
  return request("/runs");
}

export async function createRun(
  yaml_text: string,
  yaml_filename: string,
  project_id: string,
  prompt_version_id: number | null,
): Promise<RunRow> {
  return request("/runs", { method: "POST", body: JSON.stringify({ yaml_text, yaml_filename, project_id, prompt_version_id }) });
}

export async function getRun(runId: string): Promise<RunRow> {
  return request(`/runs/${runId}`);
}

export async function cancelRun(runId: string): Promise<{ id: string; status: string }> {
  return request(`/runs/${runId}/cancel`, { method: "POST" });
}

export async function getStages(runId: string): Promise<{ db_path: string | null; tasks: DbTaskRow[] }> {
  return request(`/runs/${runId}/stages`);
}

export async function getArtifacts(runId: string): Promise<Artifact[]> {
  return request(`/runs/${runId}/artifacts`);
}

export function downloadUrl(runId: string, path: string): string {
  const base = apiBase();
  return `${base}/runs/${runId}/download?path=${encodeURIComponent(path)}`;
}

export async function downloadBlob(runId: string, path: string): Promise<Blob> {
  const token = getToken();
  const res = await fetch(downloadUrl(runId, path), {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = String(data.detail);
    } catch {}
    throw new Error(detail);
  }
  return await res.blob();
}
