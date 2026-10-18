/**
 * CodeGraph AI - Frontend API Client
 * Connects directly to the FastAPI backend endpoints.
 */

const API_BASE = '';

export async function checkDbHealth() {
  const res = await fetch(`${API_BASE}/api/db-health`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error_message || `HTTP ${res.status}: Database unavailable`);
  }
  return res.json();
}

export async function getGraphData(graphName = '', limit = 150) {
  const params = new URLSearchParams();
  if (graphName) params.append('graph_name', graphName);
  params.append('limit', limit.toString());

  const res = await fetch(`${API_BASE}/api/graph?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to load graph data (HTTP ${res.status})`);
  }
  return res.json();
}

export async function analyzeRepository(payload) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Analysis failed (HTTP ${res.status})`);
  }
  return res.json();
}

export async function runInvestigation(payload) {
  const res = await fetch(`${API_BASE}/api/investigate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Investigation failed (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getDemoRepoMetadata() {
  const res = await fetch(`${API_BASE}/api/demo-repo`);
  if (!res.ok) return null;
  return res.json();
}
