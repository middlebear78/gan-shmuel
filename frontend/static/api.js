// ── API calls (no DOM, no toasts) ──

async function checkHealth(url) {
  const res = await fetch(url);
  return { ok: res.ok };
}

async function recordWeight(params) {
  const res = await fetch('/api/weight/weight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params.toString(),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'error');
  return data;
}

async function getSession(id) {
  const res = await fetch('/api/weight/session/' + id);
  if (res.status === 404) return null;
  return await res.json();
}

async function getUnknownContainers() {
  const res = await fetch('/api/weight/unknown');
  return await res.json();
}

async function getTruck(id) {
  const res = await fetch('/api/billing/truck/' + id);
  if (res.status === 404) return null;
  return await res.json();
}

async function createProvider(name) {
  const res = await fetch('/api/billing/provider', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'error');
  return data;
}

async function updateProvider(id, name) {
  const res = await fetch('/api/billing/provider/' + id, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'error');
  return data;
}

async function registerTruck(id, provider) {
  const res = await fetch('/api/billing/truck', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, provider }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'error');
  return data;
}

async function updateTruck(id, provider) {
  const res = await fetch('/api/billing/truck/' + id, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'error');
  return data;
}

async function lookupTruck(id) {
  const res = await fetch('/api/billing/truck/' + id);
  if (res.status === 404) return null;
  return await res.json();
}
