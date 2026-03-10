// ── UI Logic (uses i18n.js and api.js) ──

let isLoggedIn = false;

// ── Toast (slide-in/out) ──
function showToast(msg, type) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = 'toast toast-' + type + ' show';
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.classList.remove('show');
    toast.classList.add('hiding');
    setTimeout(() => { toast.className = 'toast'; }, 350);
  }, 2500);
}

// ── Button ripple effect ──
function addRipple(e) {
  const btn = e.currentTarget;
  const circle = document.createElement('span');
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  circle.style.width = circle.style.height = size + 'px';
  circle.style.left = (e.clientX - rect.left - size / 2) + 'px';
  circle.style.top = (e.clientY - rect.top - size / 2) + 'px';
  circle.className = 'ripple';
  btn.appendChild(circle);
  circle.addEventListener('animationend', () => circle.remove());
}

// ── Loading spinner helper ──
function btnLoading(btn, loading) {
  if (loading) {
    btn.disabled = true;
    btn._origText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span>' + btn.textContent;
  } else {
    btn.disabled = false;
    if (btn._origText) btn.innerHTML = btn._origText;
  }
}

// ── Navigation ──
function navigateTo(page) {
  if (page === 'management' && !isLoggedIn) {
    document.getElementById('login-modal').classList.add('show');
    return;
  }
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelector(`.nav-item[data-page="${page}"]`).classList.add('active');
}

// ── Tabs ──
function setupTabs() {
  document.querySelectorAll('.tabs-nav').forEach(nav => {
    nav.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        const parent = nav.parentElement;
        nav.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        parent.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        parent.querySelector('#' + tabId).classList.add('active');
      });
    });
  });
}

// ── Descriptions table builder ──
function descTable(rows) {
  let html = '<table class="desc-table">';
  rows.forEach(([label, value]) => {
    if (value !== undefined) {
      html += `<tr><th>${label}</th><td>${value}</td></tr>`;
    }
  });
  html += '</table>';
  return html;
}

// ── Dashboard: health checks ──
function loadHealthChecks() {
  const container = document.getElementById('health-cards');
  const services = [
    { key: 'weightService', url: '/api/weight/health', port: 5000 },
    { key: 'billingService', url: '/api/billing/health', port: 5001 },
  ];
  container.innerHTML = services.map(svc =>
    `<div class="status-card" id="health-${svc.key}">
      <div><h3>${t(svc.key)}</h3><span class="port">${t('port')} ${svc.port}</span></div>
      <span class="tag tag-default">${t('checking')}</span>
    </div>`
  ).join('');

  services.forEach(svc => {
    checkHealth(svc.url)
      .then(result => {
        const card = document.getElementById('health-' + svc.key);
        const tag = card.querySelector('.tag');
        if (result.ok) {
          tag.className = 'tag tag-success';
          tag.textContent = '✓ ' + t('online');
          card.classList.remove('offline');
          card.classList.add('online');
        } else { throw new Error(); }
      })
      .catch(() => {
        const card = document.getElementById('health-' + svc.key);
        const tag = card.querySelector('.tag');
        tag.className = 'tag tag-error';
        tag.textContent = '✗ ' + t('offline');
        card.classList.remove('online');
        card.classList.add('offline');
      });
  });
}

// ── Weight: Record ──
function setupWeightForm() {
  const form = document.getElementById('weight-form');
  const forceSwitch = document.getElementById('force-switch');
  const forceInput = form.querySelector('[name="force"]');

  forceSwitch.addEventListener('click', () => {
    const isOn = forceSwitch.classList.toggle('on');
    forceInput.value = isOn ? 'true' : 'false';
  });

  form.addEventListener('reset', () => {
    forceSwitch.classList.remove('on');
    forceInput.value = 'false';
    document.getElementById('weight-result').innerHTML = '';
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('[type="submit"]');
    const fd = new FormData(form);
    const params = new URLSearchParams();
    params.append('direction', fd.get('direction'));
    params.append('truck', fd.get('truck') || 'na');
    params.append('containers', fd.get('containers') || '');
    params.append('weight', fd.get('weight'));
    params.append('unit', fd.get('unit'));
    params.append('force', fd.get('force'));
    params.append('produce', fd.get('produce') || 'na');

    btnLoading(submitBtn, true);
    try {
      const data = await recordWeight(params);
      showToast(t('weightRecorded'), 'success');
      const rows = [
        ['ID', data.id],
        [t('truck'), data.truck],
        [t('bruto'), data.bruto + ' kg'],
      ];
      if (data.truckTara !== undefined) rows.push([t('truckTara'), data.truckTara + ' kg']);
      if (data.neto !== undefined) rows.push([t('neto'), data.neto + ' kg']);
      document.getElementById('weight-result').innerHTML = descTable(rows);
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(submitBtn, false); }
  });
}

// ── Weight: Session Lookup ──
function setupSessionLookup() {
  const input = document.getElementById('session-id-input');
  const btn = document.getElementById('session-search-btn');
  const result = document.getElementById('session-result');

  async function lookup() {
    const id = input.value.trim();
    if (!id) return;
    result.innerHTML = '';
    btnLoading(btn, true);
    try {
      const data = await getSession(id);
      if (!data) {
        result.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        const rows = [
          ['ID', data.id],
          [t('truck'), data.truck],
          [t('bruto'), data.bruto + ' kg'],
        ];
        if (data.truckTara !== undefined) rows.push([t('truckTara'), data.truckTara + ' kg']);
        if (data.neto !== undefined) rows.push([t('neto'), data.neto === 'na' ? 'N/A' : data.neto + ' kg']);
        result.innerHTML = descTable(rows);
      }
    } catch { showToast(t('error'), 'error'); }
    finally { btnLoading(btn, false); }
  }

  btn.addEventListener('click', lookup);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') lookup(); });
}

// ── Weight: Unknown Containers ──
function setupUnknownContainers() {
  const btn = document.getElementById('refresh-unknown');
  const list = document.getElementById('unknown-list');

  btn.addEventListener('click', async () => {
    list.innerHTML = '<div class="empty">...</div>';
    try {
      const ids = await getUnknownContainers();
      if (ids.length === 0) {
        list.innerHTML = `<div class="empty">${t('noUnknown')}</div>`;
      } else {
        let html = '<table class="data-table"><thead><tr><th>' + t('containerId') + '</th></tr></thead><tbody>';
        ids.forEach(id => { html += `<tr><td>${id}</td></tr>`; });
        html += '</tbody></table>';
        list.innerHTML = html;
      }
    } catch { showToast(t('error'), 'error'); }
  });
}

// ── Billing: Truck Bill ──
function setupTruckBill() {
  const input = document.getElementById('bill-truck-input');
  const btn = document.getElementById('bill-truck-btn');
  const result = document.getElementById('bill-truck-result');

  async function lookup() {
    const id = input.value.trim();
    if (!id) return;
    result.innerHTML = '';
    btnLoading(btn, true);
    try {
      const data = await getTruck(id);
      if (!data) {
        result.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        const sessionsHtml = data.sessions?.length > 0
          ? data.sessions.map(s => `<span class="tag tag-info">${s}</span> `).join('')
          : '—';
        result.innerHTML = descTable([
          [t('truckId'), data.id],
          [t('tara'), data.tara + ' kg'],
          [t('sessions'), sessionsHtml],
        ]);
      }
    } catch { showToast(t('error'), 'error'); }
    finally { btnLoading(btn, false); }
  }

  btn.addEventListener('click', lookup);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') lookup(); });
}

// ── Management: Providers ──
function setupProviders() {
  document.getElementById('create-provider-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('[type="submit"]');
    const name = e.target.querySelector('[name="name"]').value;
    btnLoading(submitBtn, true);
    try {
      const data = await createProvider(name);
      showToast(t('providerCreated'), 'success');
      document.getElementById('create-provider-result').innerHTML = descTable([[t('providerId'), data.id]]);
      e.target.reset();
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(submitBtn, false); }
  });

  document.getElementById('update-provider-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('[type="submit"]');
    const id = e.target.querySelector('[name="id"]').value;
    const name = e.target.querySelector('[name="name"]').value;
    btnLoading(submitBtn, true);
    try {
      const data = await updateProvider(id, name);
      showToast(t('providerUpdated'), 'success');
      document.getElementById('update-provider-result').innerHTML = descTable([
        [t('providerId'), data.id],
        [t('providerName'), data.name],
      ]);
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(submitBtn, false); }
  });
}

// ── Management: Trucks ──
function setupTrucks() {
  document.getElementById('register-truck-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('[type="submit"]');
    const id = e.target.querySelector('[name="id"]').value;
    const provider = e.target.querySelector('[name="provider"]').value;
    btnLoading(submitBtn, true);
    try {
      await registerTruck(id, provider);
      showToast(t('truckRegistered'), 'success');
      e.target.reset();
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(submitBtn, false); }
  });

  document.getElementById('update-truck-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('[type="submit"]');
    const id = e.target.querySelector('[name="id"]').value;
    const provider = e.target.querySelector('[name="provider"]').value;
    btnLoading(submitBtn, true);
    try {
      await updateTruck(id, provider);
      showToast(t('truckUpdated'), 'success');
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(submitBtn, false); }
  });

  const lookupInput = document.getElementById('lookup-truck-input');
  const lookupBtn = document.getElementById('lookup-truck-btn');
  const lookupResult = document.getElementById('lookup-truck-result');

  async function lookup() {
    const id = lookupInput.value.trim();
    if (!id) return;
    lookupResult.innerHTML = '';
    btnLoading(lookupBtn, true);
    try {
      const data = await lookupTruck(id);
      if (!data) {
        lookupResult.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        const sessionsHtml = data.sessions?.length > 0
          ? data.sessions.map(s => `<span class="tag tag-info">${s}</span> `).join('')
          : '—';
        lookupResult.innerHTML = descTable([
          [t('truckId'), data.id],
          [t('tara'), data.tara + ' kg'],
          [t('sessions'), sessionsHtml],
        ]);
      }
    } catch { showToast(t('error'), 'error'); }
    finally { btnLoading(lookupBtn, false); }
  }

  lookupBtn.addEventListener('click', lookup);
  lookupInput.addEventListener('keydown', e => { if (e.key === 'Enter') lookup(); });
}

// ── Login ──
function setupLogin() {
  const modal = document.getElementById('login-modal');
  const form = document.getElementById('login-form');
  const closeBtn = document.getElementById('login-close');

  closeBtn.addEventListener('click', () => { modal.classList.remove('show'); form.reset(); });
  modal.addEventListener('click', (e) => { if (e.target === modal) { modal.classList.remove('show'); form.reset(); } });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const username = form.querySelector('[name="username"]').value;
    const password = form.querySelector('[name="password"]').value;
    if (username === 'admin' && password === 'admin') {
      isLoggedIn = true;
      modal.classList.remove('show');
      form.reset();
      showToast(t('loginSuccess'), 'success');
      navigateTo('management');
    } else {
      showToast(t('loginFailed'), 'error');
    }
  });
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  // Nav
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => navigateTo(item.dataset.page));
  });

  // Sidebar toggle
  document.getElementById('toggle-sidebar').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
  });

  // Language toggle
  document.getElementById('toggle-lang').addEventListener('click', () => {
    lang = lang === 'he' ? 'en' : 'he';
    setRtl();
    applyTranslations();
    loadHealthChecks();
  });

  // Setup everything
  setupTabs();
  setupWeightForm();
  setupSessionLookup();
  setupUnknownContainers();
  setupTruckBill();
  setupProviders();
  setupTrucks();
  setupLogin();

  // Ripple effect on all buttons
  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', addRipple);
  });

  // Initial state
  setRtl();
  applyTranslations();
  loadHealthChecks();
});
