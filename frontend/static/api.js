// ── API calls (no DOM, no toasts) ──

async function checkHealth(url) {
  const res = await fetch(url);
  const result = { service: true, db: null };
  try {
    const data = await res.clone().json();
    // billing returns {"status": "OK"} or {"status": "Failure"}
    result.db = data.status === 'OK';
  } catch {
    // weight returns plain text "OK" — no DB info
    result.db = null;
  }
  return result;
}

// ── Weight ──

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

async function getWeightList(from, to, filter) {
  const params = new URLSearchParams();
  if (from) params.append('from', from);
  if (to) params.append('to', to);
  if (filter) params.append('filter', filter);
  const res = await fetch('/api/weight/weight?' + params.toString());
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.error || 'error');
  }
  return await res.json();
}

async function batchWeight(filename) {
  const res = await fetch('/api/weight/batch-weight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file: filename }),
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

async function getItem(id, from, to) {
  const params = new URLSearchParams();
  if (from) params.append('from', from);
  if (to) params.append('to', to);
  const qs = params.toString();
  const res = await fetch('/api/weight/item/' + id + (qs ? '?' + qs : ''));
  if (res.status === 404) return null;
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.error || 'error');
  }
  return await res.json();
}

async function getUnknownContainers() {
  const res = await fetch('/api/weight/unknown');
  return await res.json();
}

// ── Billing ──

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

async function uploadRates(filename) {
  const res = await fetch('/api/billing/rates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file: filename }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || data.details || 'error');
  return data;
}

async function downloadRates() {
  const res = await fetch('/api/billing/rates');
  if (res.status === 404) {
    const data = await res.json();
    throw new Error(data.error || 'No rates file');
  }
  if (!res.ok) throw new Error('error');
  return await res.blob();
}

async function getBill(providerId, from, to) {
  const params = new URLSearchParams();
  if (from) params.append('from', from);
  if (to) params.append('to', to);
  const qs = params.toString();
  const res = await fetch('/api/billing/bill/' + providerId + (qs ? '?' + qs : ''));
  if (res.status === 404) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || data.details || 'error');
  return data;
}
