const form = document.getElementById("cleanForm");
const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");
const fileTitle = document.getElementById("fileTitle");
const fileSub = document.getElementById("fileSub");
const cleanButton = document.getElementById("cleanButton");
const errorMessage = document.getElementById("errorMessage");
const results = document.getElementById("results");
let currentFileId = null;

function showFile(file) {
  if (!file) return;
  fileTitle.textContent = file.name;
  fileSub.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB · Ready to clean`;
  errorMessage.hidden = true;
}
fileInput.addEventListener("change", () => showFile(fileInput.files[0]));

["dragenter", "dragover"].forEach(eventName => {
  dropZone.addEventListener(eventName, event => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
});
["dragleave", "drop"].forEach(eventName => {
  dropZone.addEventListener(eventName, event => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
});
dropZone.addEventListener("drop", event => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  showFile(file);
});

form.addEventListener("submit", async event => {
  event.preventDefault();
  errorMessage.hidden = true;
  const file = fileInput.files[0];
  if (!file) {
    errorMessage.textContent = "Please select a CSV or Excel file first.";
    errorMessage.hidden = false;
    return;
  }
  const extension = file.name.split(".").pop().toLowerCase();
  if (!["csv", "xlsx", "xls"].includes(extension)) {
    errorMessage.textContent = "Unsupported file type. Please choose CSV, XLSX, or XLS.";
    errorMessage.hidden = false;
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  ["remove_duplicates", "normalize_columns", "trim_cells", "restructure"].forEach(name => {
    const checkbox = form.querySelector(`[name="${name}"]`);
    formData.append(name, checkbox.checked ? "true" : "false");
  });
  formData.append("missing_action", document.getElementById("missingAction").value);

  cleanButton.disabled = true;
  cleanButton.innerHTML = "Cleaning your data…";
  try {
    const response = await fetch("/api/clean", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to clean this file.");
    currentFileId = data.file_id;
    renderResults(data);
    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    errorMessage.textContent = error.message || "Something went wrong. Please try again.";
    errorMessage.hidden = false;
  } finally {
    cleanButton.disabled = false;
    cleanButton.innerHTML = '<span>✦</span> Clean my data <span class="button-arrow">→</span>';
  }
});

function renderResults(data) {
  document.getElementById("originalRows").textContent = data.original.rows.toLocaleString();
  document.getElementById("cleanedRows").textContent = data.cleaned.rows.toLocaleString();
  document.getElementById("duplicateCount").textContent = data.original.duplicates.toLocaleString();
  document.getElementById("duplicatesRemoved").textContent = `Removed: ${data.removed_duplicates.toLocaleString()}`;
  document.getElementById("missingCount").textContent = data.original.missing.toLocaleString();
  document.getElementById("missingAfter").textContent = `Remaining: ${data.cleaned.missing.toLocaleString()}`;
  document.getElementById("downloadName").textContent = data.download_name;

  const table = document.getElementById("previewTable");
  table.replaceChildren();
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  data.preview.columns.forEach(column => {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  data.preview.rows.forEach(row => {
    const tr = document.createElement("tr");
    row.forEach(value => {
      const td = document.createElement("td");
      td.textContent = value === null || value === undefined ? "" : String(value);
      td.title = td.textContent;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
}

document.getElementById("downloadButton").addEventListener("click", () => {
  if (currentFileId) window.location.href = `/api/download/${currentFileId}`;
});
