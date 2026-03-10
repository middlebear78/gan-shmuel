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
