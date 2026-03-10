// ── i18n ──
const translations = {
  he: {
    dashboard:'לוח בקרה', weightNav:'שקילה', billing:'חיוב', management:'ניהול',
    ganShmuel:'גן שמואל', gs:'ג״ש',
    systemOverview:'סקירת מערכת לפלטפורמת הניהול של גן שמואל',
    weightService:'שירות שקילה', billingService:'שירות חיוב',
    online:'מחובר', offline:'מנותק', checking:'בודק...', service:'שירות', database:'מסד נתונים', na:'לא נבדק',
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
    // new features
    weightList:'רשימת שקילות', from:'מתאריך', to:'עד תאריך', filter:'סינון',
    load:'טען', noResults:'אין תוצאות', id:'מזהה',
    batchWeight:'טעינת משקלים', fileName:'שם קובץ', fileNamePlaceholder:'שם קובץ (למשל containers1.csv)', selectFile:'בחר קובץ...',
    upload:'העלה', batchSuccess:'הקובץ עובד בהצלחה', processed:'רשומות עובדו',
    itemLookup:'חיפוש פריט', itemId:'מזהה פריט', itemIdPlaceholder:'מזהה מכולה או משאית',
    ratesFileName:'שם קובץ אקסל', ratesFilePlaceholder:'שם קובץ (למשל rates.xlsx)',
    ratesUploaded:'תעריפים הועלו בהצלחה', rows:'שורות', inserted:'נוספו', updated:'עודכנו',
    download:'הורד',
    providerBill:'חשבון ספק', fromDate:'מתאריך', toDate:'עד תאריך',
    generate:'הפק', today:'היום',
    truckCount:'מספר משאיות', sessionCount:'מספר שקילות',
    product:'מוצר', count:'כמות', amount:'משקל (ק"ג)', rate:'תעריף', pay:'תשלום',
    total:'סה"כ', noData:'אין נתונים',
  },
  en: {
    dashboard:'Dashboard', weightNav:'Weight', billing:'Billing', management:'Management',
    ganShmuel:'Gan Shmuel', gs:'GS',
    systemOverview:'System overview for Gan Shmuel management platform',
    weightService:'Weight Service', billingService:'Billing Service',
    online:'Online', offline:'Offline', checking:'Checking...', service:'Service', database:'Database', na:'N/A',
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
    // new features
    weightList:'Weight List', from:'From', to:'To', filter:'Filter',
    load:'Load', noResults:'No results', id:'ID',
    batchWeight:'Batch Weight', fileName:'File Name', fileNamePlaceholder:'Filename (e.g. containers1.csv)', selectFile:'Select file...',
    upload:'Upload', batchSuccess:'File processed successfully', processed:'records processed',
    itemLookup:'Item Lookup', itemId:'Item ID', itemIdPlaceholder:'Container or truck ID',
    ratesFileName:'Excel File Name', ratesFilePlaceholder:'Filename (e.g. rates.xlsx)',
    ratesUploaded:'Rates uploaded successfully', rows:'Rows', inserted:'Inserted', updated:'Updated',
    download:'Download',
    providerBill:'Provider Bill', fromDate:'From', toDate:'To',
    generate:'Generate', today:'Today',
    truckCount:'Trucks', sessionCount:'Sessions',
    product:'Product', count:'Count', amount:'Amount (kg)', rate:'Rate', pay:'Pay',
    total:'Total', noData:'No data',
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
