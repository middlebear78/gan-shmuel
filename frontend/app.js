// ── Service Configuration ──
var BASE = window.location.hostname;
var SERVICES = {
  weight: { port: 5000, label: "תחנת שקילה" },
  billing: { port: 5001, label: "חיובים" },
  devops: { port: 5002, label: "DevOps" },
};

function serviceUrl(port, path) {
  return "http://" + BASE + ":" + port + path;
}

// ── Navigation ──
document.querySelectorAll(".nav-links li").forEach(function (item) {
  item.addEventListener("click", function () {
    document.querySelectorAll(".nav-links li").forEach(function (el) {
      el.classList.remove("active");
    });
    document.querySelectorAll(".section").forEach(function (el) {
      el.classList.remove("active");
    });
    item.classList.add("active");
    var section = item.getAttribute("data-section");
    document.getElementById(section).classList.add("active");
    loadSectionData(section);
  });
});

// ── Health Checks ──
function checkHealth() {
  Object.entries(SERVICES).forEach(function (entry) {
    var name = entry[0];
    var svc = entry[1];
    fetch(serviceUrl(svc.port, "/health"), { mode: "cors" })
      .then(function (res) {
        if (res.ok) {
          setStatus(name, "פעיל", true);
        } else {
          setStatus(name, "לא פעיל", false);
        }
      })
      .catch(function () {
        setStatus(name, "לא פעיל", false);
      });
  });
  document.getElementById("last-updated").textContent =
    "עודכן: " + new Date().toLocaleTimeString("he-IL");
}

function setStatus(name, text, online) {
  var statusText = document.getElementById(name + "-status-text");
  var indicator = document.getElementById(name + "-indicator");
  if (statusText) {
    statusText.textContent = text;
    statusText.style.color = online ? "#22c55e" : "#ef4444";
  }
  if (indicator) {
    indicator.className = "stat-indicator " + (online ? "online" : "offline");
  }

  var pill = document.getElementById(name + "-pill");
  if (pill) {
    pill.textContent = text;
    pill.className = "status-pill " + (online ? "online" : "offline");
  }

  var healthCell = document.getElementById("health-" + name);
  if (healthCell) {
    healthCell.textContent = text;
    healthCell.className = online ? "online" : "offline";
  }
}

// ── Load Section Data ──
function loadSectionData(section) {
  if (section === "weight") {
    loadWeightData();
  }
  if (section === "billing") {
    loadBillingData();
  }
}

function loadWeightData() {
  fetch(serviceUrl(5000, "/weight"), { mode: "cors" })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      var el = document.getElementById("weight-data");
      if (Array.isArray(data) && data.length > 0) {
        var html =
          '<table class="data-table"><thead><tr><th>מזהה</th><th>כיוון</th><th>משאית</th><th>ברוטו</th><th>תאריך</th></tr></thead><tbody>';
        data.slice(0, 20).forEach(function (w) {
          html +=
            "<tr><td>" +
            w.id +
            "</td><td>" +
            w.direction +
            "</td><td>" +
            (w.truck || "-") +
            "</td><td>" +
            (w.bruto || "-") +
            "</td><td>" +
            (w.datetime || "-") +
            "</td></tr>";
        });
        html += "</tbody></table>";
        el.innerHTML = html;
      }
    })
    .catch(function () {
      document.getElementById("weight-data").innerHTML =
        '<p class="placeholder">שירות שקילה לא זמין</p>';
    });

  fetch(serviceUrl(5000, "/unknown"), { mode: "cors" })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      var el = document.getElementById("unknown-containers");
      if (Array.isArray(data) && data.length > 0) {
        el.innerHTML = data
          .map(function (c) {
            return '<span class="status-pill">' + c + "</span> ";
          })
          .join("");
      } else {
        el.innerHTML = '<p class="placeholder">אין מכולות לא מזוהות</p>';
      }
    })
    .catch(function () {
      document.getElementById("unknown-containers").innerHTML =
        '<p class="placeholder">שירות שקילה לא זמין</p>';
    });
}

function loadBillingData() {
  fetch(serviceUrl(5001, "/rates"), { mode: "cors" })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      var el = document.getElementById("rates-data");
      if (Array.isArray(data) && data.length > 0) {
        var html =
          '<table class="data-table"><thead><tr><th>מוצר</th><th>תעריף</th><th>היקף</th></tr></thead><tbody>';
        data.forEach(function (r) {
          html +=
            "<tr><td>" +
            (r.product || "-") +
            "</td><td>" +
            (r.rate || "-") +
            "</td><td>" +
            (r.scope || "-") +
            "</td></tr>";
        });
        html += "</tbody></table>";
        el.innerHTML = html;
      }
    })
    .catch(function () {
      document.getElementById("rates-data").innerHTML =
        '<p class="placeholder">שירות חיובים לא זמין</p>';
    });
}

function loadDashboard() {
  fetch(serviceUrl(5000, "/weight"), { mode: "cors" })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      var el = document.getElementById("recent-weighings");
      if (Array.isArray(data) && data.length > 0) {
        var html =
          '<table class="data-table"><thead><tr><th>משאית</th><th>כיוון</th><th>ברוטו</th></tr></thead><tbody>';
        data.slice(0, 5).forEach(function (w) {
          html +=
            "<tr><td>" +
            (w.truck || "-") +
            "</td><td>" +
            (w.direction || "-") +
            "</td><td>" +
            (w.bruto || "-") +
            "</td></tr>";
        });
        html += "</tbody></table>";
        el.innerHTML = html;
      }
    })
    .catch(function () {});
}

// ── Init ──
checkHealth();
loadDashboard();
setInterval(checkHealth, 30000);
