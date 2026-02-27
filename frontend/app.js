// ── Service Configuration ──
const BASE = window.location.hostname;
const SERVICES = {
  weight: { url: "/api/weight/health", port: 5000, label: "Weight Station" },
  billing: { url: "/api/billing/health", port: 5001, label: "Billing" },
  devops: { url: "/api/devops/health", port: 5002, label: "DevOps" },
};

// In production, services run on different ports on the same host
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
          setStatus(name, "Online", true);
        } else {
          setStatus(name, "Offline", false);
        }
      })
      .catch(function () {
        setStatus(name, "Offline", false);
      });
  });
  document.getElementById("last-updated").textContent =
    "Updated: " + new Date().toLocaleTimeString();
}

function setStatus(name, text, online) {
  // Dashboard stat cards
  var statusText = document.getElementById(name + "-status-text");
  var indicator = document.getElementById(name + "-indicator");
  if (statusText) {
    statusText.textContent = text;
    statusText.style.color = online ? "#22c55e" : "#ef4444";
  }
  if (indicator) {
    indicator.className = "stat-indicator " + (online ? "online" : "offline");
  }

  // Section pills
  var pill = document.getElementById(name + "-pill");
  if (pill) {
    pill.textContent = text;
    pill.className = "status-pill " + (online ? "online" : "offline");
  }

  // DevOps health table
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
  // Load recent weighings
  fetch(serviceUrl(5000, "/weight"), { mode: "cors" })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      var el = document.getElementById("weight-data");
      if (Array.isArray(data) && data.length > 0) {
        var html =
          '<table class="data-table"><thead><tr><th>ID</th><th>Direction</th><th>Truck</th><th>Bruto</th><th>Date</th></tr></thead><tbody>';
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
        '<p class="placeholder">Weight service unavailable</p>';
    });

  // Load unknown containers
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
        el.innerHTML = '<p class="placeholder">No unknown containers</p>';
      }
    })
    .catch(function () {
      document.getElementById("unknown-containers").innerHTML =
        '<p class="placeholder">Weight service unavailable</p>';
    });
}

function loadBillingData() {
  // Load rates
  fetch(serviceUrl(5001, "/rates"), { mode: "cors" })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      var el = document.getElementById("rates-data");
      if (Array.isArray(data) && data.length > 0) {
        var html =
          '<table class="data-table"><thead><tr><th>Product</th><th>Rate</th><th>Scope</th></tr></thead><tbody>';
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
        '<p class="placeholder">Billing service unavailable</p>';
    });
}

// ── Dashboard Quick Data ──
function loadDashboard() {
  // Recent weighings for dashboard
  fetch(serviceUrl(5000, "/weight"), { mode: "cors" })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      var el = document.getElementById("recent-weighings");
      if (Array.isArray(data) && data.length > 0) {
        var html =
          '<table class="data-table"><thead><tr><th>Truck</th><th>Direction</th><th>Bruto</th></tr></thead><tbody>';
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
