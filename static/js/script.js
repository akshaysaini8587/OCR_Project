const fileInput = document.getElementById("fileInput");
const previewArea = document.getElementById("previewArea");
const dropZone = document.querySelector(".upload-box label");
const extractBtn = document.getElementById("extractBtn");
const outputText = document.getElementById("outputText");
const loading = document.getElementById("loading");
const copyBtn = document.getElementById("copyBtn");
const txtBtn = document.getElementById("txtBtn");
const pdfBtn = document.getElementById("pdfBtn");
const wordBtn = document.getElementById("wordBtn");
const themeToggle = document.getElementById("themeToggle");
const removeFileBtn = document.getElementById("removeFileBtn");

let selectedFile = null;

function applyTheme(theme) {
  document.body.classList.toggle("light", theme === "light");
  themeToggle.textContent = theme === "light" ? "🌞 Light" : "🌙 Dark";
}

const savedTheme = localStorage.getItem("theme") || "dark";
applyTheme(savedTheme);

themeToggle.addEventListener("click", () => {
  const newTheme = document.body.classList.contains("light") ? "dark" : "light";
  localStorage.setItem("theme", newTheme);
  applyTheme(newTheme);
});

function resetFile() {
  selectedFile = null;
  fileInput.value = "";
  previewArea.innerHTML = "<p>No file selected</p>";
}

function showPreview(file) {
  previewArea.innerHTML = "";
  if (!file) {
    previewArea.innerHTML = "<p>No file selected</p>";
    return;
  }

  const url = URL.createObjectURL(file);

  if (file.type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = url;
    previewArea.appendChild(img);
  } else if (file.type === "application/pdf") {
    const embed = document.createElement("embed");
    embed.src = url;
    embed.type = "application/pdf";
    previewArea.appendChild(embed);
  } else {
    previewArea.innerHTML = "<p>Preview not available</p>";
  }
}

fileInput.addEventListener("change", (e) => {
  selectedFile = e.target.files[0];
  showPreview(selectedFile);
});

["dragenter", "dragover"].forEach(eventName => {
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach(eventName => {
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
  });
});

dropZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    fileInput.files = e.dataTransfer.files;
    selectedFile = file;
    showPreview(selectedFile);
  }
});

removeFileBtn.addEventListener("click", () => {
  resetFile();
});

extractBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    alert("Please select a file first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile);

  loading.style.display = "inline-block";
  extractBtn.disabled = true;

  try {
    const response = await fetch("/upload", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (data.success) {
      outputText.value = data.text || "";
      if (data.filename) {
        previewArea.setAttribute("data-filename", data.filename);
      }
    } else {
      alert(data.error || "OCR failed");
    }
  } catch (error) {
    alert("Error: " + error.message);
  } finally {
    loading.style.display = "none";
    extractBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(outputText.value);
  alert("Text copied!");
});

txtBtn.addEventListener("click", () => {
  const blob = new Blob([outputText.value], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "extracted_text.txt";
  link.click();
});

pdfBtn.addEventListener("click", () => {
  alert("PDF download backend step add karna hoga.");
});

wordBtn.addEventListener("click", () => {
  alert("Word download backend step add karna hoga.");
});