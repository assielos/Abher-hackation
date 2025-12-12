const API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000/api"
    : "https://api.absher.gov.sa/api";

const form = document.getElementById("requestForm");
const statusBox = document.getElementById("status");
const downloadSection = document.getElementById("downloadSection");
const downloadLink = document.getElementById("downloadLink");

let currentRequestId = null;
let pollInterval = null;

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusBox.style.display = "none";
  downloadSection.style.display = "none";

  const data = new FormData(form);

  try {
    const res = await fetch(`${API_BASE}/requests`, {
      method: "POST",
      body: data,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to submit");
    }
    const body = await res.json();
    currentRequestId = body.request_id;
    showStatus(`Request submitted. Request ID: ${currentRequestId}. Upload token for admin: ${body.upload_token}`);
    startPolling();
  } catch (err) {
    showStatus(err.message, true);
  }
});

async function pollStatus() {
  if (!currentRequestId) return;
  try {
    const res = await fetch(`${API_BASE}/requests/${currentRequestId}`);
    const body = await res.json();
    showStatus(`Status: ${body.status}`);
    if (body.status === "READY" && body.download_token) {
      clearInterval(pollInterval);
      const link = `${API_BASE}/requests/${currentRequestId}/download?token=${body.download_token}`;
      downloadLink.href = link;
      downloadSection.style.display = "block";
    }
  } catch (err) {
    showStatus("Failed to fetch status", true);
  }
}

function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(pollStatus, 4000);
}

function showStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
  statusBox.style.display = "block";
}

