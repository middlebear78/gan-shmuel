// ── i18n ──
const translations = {
  he: {
    dashboard:'לוח בקרה', weightNav:'שקילה', billing:'חיוב', management:'ניהול',
    ganShmuel:'גן שמואל', gs:'ג״ש',
    systemOverview:'סקירת מערכת לפלטפורמת הניהול של גן שמואל',
    weightService:'שירות שקילה', billingService:'שירות חיוב',
    online:'מחובר', offline:'מנותק', checking:'בודק...', port:'פורט',
    recordWeight:'רישום שקילה', direction:'כיוון',
    directionIn:'כניסה', directionOut:'יציאה', directionNone:'ללא',
    truck:'משאית', truckPlaceholder:'מספר רישוי (או na)',
    containers:'מכולות', containersPlaceholder:'מזהי מכולות מופרדים בפסיק',
    weight:'משקל', unit:'יחידה', force:'כפה',
    produce:'תוצרת', producePlaceholder:'סוג תוצרת (או na)',
    submit:'שלח', reset:'נקה', success:'הצלחה', error:'שגיאה',
    weightRecorded:'שקילה נרשמה בהצלחה',
    sessionLookup:'חיפוש שקילה', sessionId:'מזהה שקילה',
    search:'חפש', session:'שקילה', bruto:'ברוטו', neto:'נטו',
    truckTara:'טרה משאית', notFound:'לא נמצא',
    truckBill:'חשבון משאית',
    unknownContainers:'מכולות ללא משקל ידוע', containerId:'מזהה מכולה',
    noUnknown:'כל המכולות עם משקל ידוע', refresh:'רענן',
    providers:'ספקים', trucks:'משאיות', rates:'תעריפים', bills:'חשבונות',
    providerName:'שם ספק', providerNamePlaceholder:'הכנס שם ספק',
    createProvider:'צור ספק', updateProvider:'עדכן ספק',
    providerId:'מזהה ספק', providerCreated:'ספק נוצר בהצלחה',
    providerUpdated:'ספק עודכן בהצלחה', newName:'שם חדש',
    registerTruck:'רשום משאית', updateTruck:'עדכן משאית', lookupTruck:'חפש משאית',
    truckId:'מזהה משאית', truckIdPlaceholder:'מספר רישוי',
    provider:'ספק', providerIdPlaceholder:'מזהה ספק',
    truckRegistered:'משאית נרשמה בהצלחה', truckUpdated:'משאית עודכנה בהצלחה',
    tara:'טרה', sessions:'שקילות',
    uploadRates:'העלה תעריפים', downloadRates:'הורד תעריפים',
    viewBill:'הצג חשבון', comingSoon:'בקרוב',
    loginRequired:'נדרשת התחברות', username:'שם משתמש', password:'סיסמה',
    login:'התחבר', loginSuccess:'התחברת בהצלחה', loginFailed:'שם משתמש או סיסמה שגויים',
  },
  en: {
    dashboard:'Dashboard', weightNav:'Weight', billing:'Billing', management:'Management',
    ganShmuel:'Gan Shmuel', gs:'GS',
    systemOverview:'System overview for Gan Shmuel management platform',
    weightService:'Weight Service', billingService:'Billing Service',
    online:'Online', offline:'Offline', checking:'Checking...', port:'Port',
    recordWeight:'Record Weight', direction:'Direction',
    directionIn:'In', directionOut:'Out', directionNone:'None',
    truck:'Truck', truckPlaceholder:'License plate (or na)',
    containers:'Containers', containersPlaceholder:'Comma-separated container IDs',
    weight:'Weight', unit:'Unit', force:'Force',
    produce:'Produce', producePlaceholder:'Produce type (or na)',
    submit:'Submit', reset:'Reset', success:'Success', error:'Error',
    weightRecorded:'Weight recorded successfully',
    sessionLookup:'Session Lookup', sessionId:'Session ID',
    search:'Search', session:'Session', bruto:'Bruto', neto:'Neto',
    truckTara:'Truck Tara', notFound:'Not found',
    truckBill:'Truck Bill',
    unknownContainers:'Unknown Containers', containerId:'Container ID',
    noUnknown:'All containers have known weight', refresh:'Refresh',
    providers:'Providers', trucks:'Trucks', rates:'Rates', bills:'Bills',
    providerName:'Provider Name', providerNamePlaceholder:'Enter provider name',
    createProvider:'Create Provider', updateProvider:'Update Provider',
    providerId:'Provider ID', providerCreated:'Provider created successfully',
    providerUpdated:'Provider updated successfully', newName:'New Name',
    registerTruck:'Register Truck', updateTruck:'Update Truck', lookupTruck:'Lookup Truck',
    truckId:'Truck ID', truckIdPlaceholder:'License plate',
    provider:'Provider', providerIdPlaceholder:'Provider ID',
    truckRegistered:'Truck registered successfully', truckUpdated:'Truck updated successfully',
    tara:'Tara', sessions:'Sessions',
    uploadRates:'Upload Rates', downloadRates:'Download Rates',
    viewBill:'View Bill', comingSoon:'Coming Soon',
    loginRequired:'Login Required', username:'Username', password:'Password',
    login:'Log In', loginSuccess:'Logged in successfully', loginFailed:'Invalid username or password',
  },
};

let lang = 'he';
let isLoggedIn = false;

function t(key) { return translations[lang]?.[key] || key; }

function applyTranslations() {
  document.querySelectorAll('[data-t]').forEach(el => {
    el.textContent = t(el.dataset.t);
  });
  document.querySelectorAll('[data-t-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.tPlaceholder);
  });
  // Update select options
  document.querySelectorAll('select[name="direction"] option').forEach(opt => {
    if (opt.dataset.t) opt.textContent = t(opt.dataset.t);
  });
  document.getElementById('sidebar-title').textContent = t('ganShmuel');
  const langBtn = document.getElementById('toggle-lang');
  langBtn.textContent = lang === 'he' ? '🌐 English' : '🌐 עברית';
}

function setRtl() {
  const app = document.getElementById('app');
  const html = document.documentElement;
  if (lang === 'he') {
    app.classList.add('rtl');
    html.dir = 'rtl';
    html.lang = 'he';
  } else {
    app.classList.remove('rtl');
    html.dir = 'ltr';
    html.lang = 'en';
  }
}

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
    fetch(svc.url)
      .then(res => {
        const card = document.getElementById('health-' + svc.key);
        const tag = card.querySelector('.tag');
        if (res.ok) {
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
      const res = await fetch('/api/weight/weight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || t('error'), 'error');
      } else {
        showToast(t('weightRecorded'), 'success');
        const rows = [
          ['ID', data.id],
          [t('truck'), data.truck],
          [t('bruto'), data.bruto + ' kg'],
        ];
        if (data.truckTara !== undefined) rows.push([t('truckTara'), data.truckTara + ' kg']);
        if (data.neto !== undefined) rows.push([t('neto'), data.neto + ' kg']);
        document.getElementById('weight-result').innerHTML = descTable(rows);
      }
    } catch { showToast(t('error'), 'error'); }
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
      const res = await fetch('/api/weight/session/' + id);
      if (res.status === 404) {
        result.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        const data = await res.json();
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
      const res = await fetch('/api/weight/unknown');
      const ids = await res.json();
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
      const res = await fetch('/api/billing/truck/' + id);
      if (res.status === 404) {
        result.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        const data = await res.json();
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
      const res = await fetch('/api/billing/provider', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'name=' + encodeURIComponent(name),
      });
      const data = await res.json();
      if (!res.ok) { showToast(data.error || t('error'), 'error'); }
      else {
        showToast(t('providerCreated'), 'success');
        document.getElementById('create-provider-result').innerHTML = descTable([[t('providerId'), data.id]]);
        e.target.reset();
      }
    } catch { showToast(t('error'), 'error'); }
    finally { btnLoading(submitBtn, false); }
  });

  document.getElementById('update-provider-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('[type="submit"]');
    const id = e.target.querySelector('[name="id"]').value;
    const name = e.target.querySelector('[name="name"]').value;
    btnLoading(submitBtn, true);
    try {
      const res = await fetch('/api/billing/provider/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'name=' + encodeURIComponent(name),
      });
      const data = await res.json();
      if (!res.ok) { showToast(data.error || t('error'), 'error'); }
      else {
        showToast(t('providerUpdated'), 'success');
        document.getElementById('update-provider-result').innerHTML = descTable([
          [t('providerId'), data.id],
          [t('providerName'), data.name],
        ]);
      }
    } catch { showToast(t('error'), 'error'); }
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
      const params = new URLSearchParams({ id, provider });
      const res = await fetch('/api/billing/truck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params.toString(),
      });
      const data = await res.json();
      if (!res.ok) { showToast(data.error || t('error'), 'error'); }
      else { showToast(t('truckRegistered'), 'success'); e.target.reset(); }
    } catch { showToast(t('error'), 'error'); }
    finally { btnLoading(submitBtn, false); }
  });

  document.getElementById('update-truck-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = e.target.querySelector('[type="submit"]');
    const id = e.target.querySelector('[name="id"]').value;
    const provider = e.target.querySelector('[name="provider"]').value;
    btnLoading(submitBtn, true);
    try {
      const res = await fetch('/api/billing/truck/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'provider=' + encodeURIComponent(provider),
      });
      const data = await res.json();
      if (!res.ok) { showToast(data.error || t('error'), 'error'); }
      else { showToast(t('truckUpdated'), 'success'); }
    } catch { showToast(t('error'), 'error'); }
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
      const res = await fetch('/api/billing/truck/' + id);
      if (res.status === 404) {
        lookupResult.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        const data = await res.json();
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
