// ── UI Logic (uses i18n.js and api.js) ──

// ── Convert datetime-local value to API format (yyyymmddhhmmss) ──
function datetimeLocalToApi(value) {
  if (!value) return '';
  return value.replace(/[-T:]/g, '') + '00';
}

// ── Wire up "Today" buttons ──
function setupTodayButtons() {
  document.querySelectorAll('.btn-today').forEach(btn => {
    btn.addEventListener('click', () => {
      const [fromId, toId] = btn.dataset.today.split(',');
      const now = new Date();
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, '0');
      const d = String(now.getDate()).padStart(2, '0');
      const h = String(now.getHours()).padStart(2, '0');
      const min = String(now.getMinutes()).padStart(2, '0');
      document.getElementById(fromId).value = `${y}-${m}-${d}T00:00`;
      document.getElementById(toId).value = `${y}-${m}-${d}T${h}:${min}`;
    });
  });
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
    { key: 'weightService', url: '/api/weight/health' },
    { key: 'billingService', url: '/api/billing/health' },
  ];
  container.innerHTML = services.map(svc =>
    `<div class="status-card" id="health-${svc.key}">
      <h3>${t(svc.key)}</h3>
      <div class="health-rows">
        <div class="health-row"><span>${t('service')}</span><span class="tag tag-default">${t('checking')}</span></div>
        <div class="health-row"><span>${t('database')}</span><span class="tag tag-default">${t('checking')}</span></div>
      </div>
    </div>`
  ).join('');

  services.forEach(svc => {
    checkHealth(svc.url)
      .then(result => {
        const card = document.getElementById('health-' + svc.key);
        const tags = card.querySelectorAll('.tag');
        // Service status
        tags[0].className = 'tag tag-success';
        tags[0].textContent = '✓ ' + t('online');
        // DB status
        if (result.db === true) {
          tags[1].className = 'tag tag-success';
          tags[1].textContent = '✓ ' + t('online');
        } else if (result.db === false) {
          tags[1].className = 'tag tag-error';
          tags[1].textContent = '✗ ' + t('offline');
        } else {
          tags[1].className = 'tag tag-default';
          tags[1].textContent = t('na');
        }
        card.classList.add('online');
      })
      .catch(() => {
        const card = document.getElementById('health-' + svc.key);
        const tags = card.querySelectorAll('.tag');
        tags[0].className = 'tag tag-error';
        tags[0].textContent = '✗ ' + t('offline');
        tags[1].className = 'tag tag-error';
        tags[1].textContent = '✗ ' + t('offline');
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

// ── Weight: List Transactions ──
function setupWeightList() {
  const btn = document.getElementById('wl-load-btn');
  const result = document.getElementById('wl-result');

  btn.addEventListener('click', async () => {
    const from = datetimeLocalToApi(document.getElementById('wl-from').value);
    const to = datetimeLocalToApi(document.getElementById('wl-to').value);
    const filter = document.getElementById('wl-filter').value;
    result.innerHTML = '';
    btnLoading(btn, true);
    try {
      const data = await getWeightList(from, to, filter);
      if (!data || data.length === 0) {
        result.innerHTML = `<div class="empty">${t('noResults')}</div>`;
      } else {
        let html = '<table class="data-table"><thead><tr>';
        html += `<th>${t('id')}</th><th>${t('direction')}</th><th>${t('truck')}</th>`;
        html += `<th>${t('bruto')}</th><th>${t('neto')}</th><th>${t('produce')}</th><th>${t('containers')}</th>`;
        html += '</tr></thead><tbody>';
        data.forEach(row => {
          const neto = row.neto === 'na' ? 'N/A' : row.neto;
          const containers = Array.isArray(row.containers) ? row.containers.join(', ') : (row.containers || '');
          html += `<tr><td>${row.id}</td><td>${row.direction}</td><td>${row.truck}</td>`;
          html += `<td>${row.bruto}</td><td>${neto}</td><td>${row.produce}</td><td>${containers}</td></tr>`;
        });
        html += '</tbody></table>';
        result.innerHTML = html;
      }
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(btn, false); }
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

// ── Weight: Item Lookup ──
function setupItemLookup() {
  const btn = document.getElementById('item-search-btn');
  const result = document.getElementById('item-result');

  btn.addEventListener('click', async () => {
    const id = document.getElementById('item-id-input').value.trim();
    if (!id) return;
    const from = datetimeLocalToApi(document.getElementById('item-from').value);
    const to = datetimeLocalToApi(document.getElementById('item-to').value);
    result.innerHTML = '';
    btnLoading(btn, true);
    try {
      const data = await getItem(id, from, to);
      if (!data) {
        result.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        const sessionsHtml = data.sessions?.length > 0
          ? data.sessions.map(s => `<span class="tag tag-info">${s}</span> `).join('')
          : '—';
        result.innerHTML = descTable([
          [t('id'), data.id],
          [t('tara'), data.tara === 'na' ? 'N/A' : data.tara + ' kg'],
          [t('sessions'), sessionsHtml],
        ]);
      }
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(btn, false); }
  });
}

// ── Weight: Batch Weight ──
function setupBatchWeight() {
  const btn = document.getElementById('batch-upload-btn');
  const result = document.getElementById('batch-result');

  btn.addEventListener('click', async () => {
    const filename = document.getElementById('batch-file-input').value.trim();
    if (!filename) return;
    result.innerHTML = '';
    btnLoading(btn, true);
    try {
      const data = await batchWeight(filename);
      showToast(t('batchSuccess'), 'success');
      result.innerHTML = descTable([[t('processed'), data.message || JSON.stringify(data)]]);
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(btn, false); }
  });
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

// ── Billing: Rates ──
function setupRates() {
  // Upload
  const uploadBtn = document.getElementById('rates-upload-btn');
  const uploadResult = document.getElementById('rates-upload-result');

  uploadBtn.addEventListener('click', async () => {
    const filename = document.getElementById('rates-file-input').value.trim();
    if (!filename) return;
    uploadResult.innerHTML = '';
    btnLoading(uploadBtn, true);
    try {
      const data = await uploadRates(filename);
      showToast(t('ratesUploaded'), 'success');
      uploadResult.innerHTML = descTable([
        [t('rows'), data.rows],
        [t('inserted'), data.inserted],
        [t('updated'), data.updated],
      ]);
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(uploadBtn, false); }
  });

  // Download
  const downloadBtn = document.getElementById('rates-download-btn');
  const downloadResult = document.getElementById('rates-download-result');

  downloadBtn.addEventListener('click', async () => {
    downloadResult.innerHTML = '';
    btnLoading(downloadBtn, true);
    try {
      const blob = await downloadRates();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'rates.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(downloadBtn, false); }
  });
}

// ── Billing: Provider Bill ──
function setupBill() {
  const btn = document.getElementById('bill-generate-btn');
  const result = document.getElementById('bill-result');

  btn.addEventListener('click', async () => {
    const providerId = document.getElementById('bill-provider-input').value.trim();
    if (!providerId) return;
    const from = datetimeLocalToApi(document.getElementById('bill-from').value);
    const to = datetimeLocalToApi(document.getElementById('bill-to').value);
    result.innerHTML = '';
    btnLoading(btn, true);
    try {
      const data = await getBill(providerId, from, to);
      if (!data) {
        result.innerHTML = `<div class="empty">${t('notFound')}</div>`;
      } else {
        let html = descTable([
          [t('providerId'), data.id],
          [t('providerName'), data.name],
          [t('from'), data.from],
          [t('to'), data.to],
          [t('truckCount'), data.truckCount],
          [t('sessionCount'), data.sessionCount],
        ]);
        if (data.products && data.products.length > 0) {
          html += '<table class="data-table" style="margin-top:12px"><thead><tr>';
          html += `<th>${t('product')}</th><th>${t('count')}</th><th>${t('amount')}</th><th>${t('rate')}</th><th>${t('pay')}</th>`;
          html += '</tr></thead><tbody>';
          data.products.forEach(p => {
            html += `<tr><td>${p.product}</td><td>${p.count}</td><td>${p.amount}</td><td>${p.rate}</td><td>${p.pay}</td></tr>`;
          });
          html += '</tbody></table>';
        } else {
          html += `<div class="empty" style="margin-top:12px">${t('noData')}</div>`;
        }
        html += descTable([[t('total'), data.total]]);
        result.innerHTML = html;
      }
    } catch (err) { showToast(err.message || t('error'), 'error'); }
    finally { btnLoading(btn, false); }
  });
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
      const data = await getTruck(id);
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
  setupTodayButtons();
  setupWeightForm();
  setupWeightList();
  setupSessionLookup();
  setupItemLookup();
  setupBatchWeight();
  setupUnknownContainers();
  setupTruckBill();
  setupRates();
  setupBill();
  setupProviders();
  setupTrucks();

  // Ripple effect on all buttons
  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', addRipple);
  });

  // Initial state
  setRtl();
  applyTranslations();
  loadHealthChecks();
});
