const SERVICES = {
  billing: { url: "http://65.2.64.183:5001/health", port: 5001 },
  weight: { url: "http://65.2.64.183:5000/health", port: 5000 },
  devops: { url: "http://65.2.64.183:5002/health", port: 5002 },
};

function checkService(name, config) {
  const el = document.getElementById(name + "-status");
  fetch(config.url, { mode: "cors" })
    .then((res) => {
      if (res.ok) {
        el.textContent = "Online";
        el.className = "service-status online";
      } else {
        el.textContent = "Offline";
        el.className = "service-status offline";
      }
    })
    .catch(() => {
      el.textContent = "Offline";
      el.className = "service-status offline";
    });
}

function navigate(service) {
  const config = SERVICES[service];
  window.open("http://65.2.64.183:" + config.port, "_blank");
}

// Check all services on page load
Object.entries(SERVICES).forEach(([name, config]) =>
  checkService(name, config),
);

// Re-check every 30 seconds
setInterval(() => {
  Object.entries(SERVICES).forEach(([name, config]) =>
    checkService(name, config),
  );
}, 30000);
