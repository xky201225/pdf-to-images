const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");
const fileName = document.getElementById("fileName");
const fileMeta = document.getElementById("fileMeta");
const outputDir = document.getElementById("outputDir");
const format = document.getElementById("format");
const dpi = document.getElementById("dpi");
const pageRange = document.getElementById("pageRange");
const prefix = document.getElementById("prefix");
const convertBtn = document.getElementById("convertBtn");
const browseBtn = document.getElementById("browseBtn");
const status = document.getElementById("status");
const results = document.getElementById("results");
const resultList = document.getElementById("resultList");
const clearBtn = document.getElementById("clearBtn");

let selectedFile = null;

function setStatus(message, kind = "") {
  status.textContent = message;
  status.className = "status" + (kind ? " " + kind : "");
}

function setFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
    setStatus("请选择 PDF 文件", "error");
    return;
  }
  selectedFile = file;
  fileName.textContent = file.name;
  fileMeta.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
  setStatus("文件已就绪");
}

function toBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("无法读取文件"));
        return;
      }
      resolve(result.split(",", 2)[1] || result);
    };
    reader.onerror = () => reject(new Error("读取文件失败"));
    reader.readAsDataURL(file);
  });
}

dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
  });
});

dropZone.addEventListener("drop", (event) => {
  setFile(event.dataTransfer.files[0]);
});

async function chooseFolder() {
  browseBtn.disabled = true;
  setStatus("正在打开文件夹选择窗口...");
  try {
    const response = await fetch("/api/choose-folder", { method: "POST" });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "未选择文件夹");
    }
    outputDir.value = data.path;
    setStatus("已选择保存目录");
  } catch (error) {
    setStatus(error.message || "无法选择文件夹", "error");
  } finally {
    browseBtn.disabled = false;
  }
}

browseBtn.addEventListener("click", chooseFolder);
outputDir.addEventListener("click", chooseFolder);

convertBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    setStatus("请先选择 PDF 文件", "error");
    return;
  }
  if (!outputDir.value.trim()) {
    setStatus("请填写输出目录", "error");
    outputDir.focus();
    return;
  }

  convertBtn.disabled = true;
  setStatus("正在转换，请稍候...");
  results.hidden = true;
  resultList.innerHTML = "";

  try {
    const pdf = await toBase64(selectedFile);
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pdf,
        outputDir: outputDir.value.trim(),
        format: format.value,
        dpi: dpi.value,
        pageRange: pageRange.value,
        prefix: prefix.value,
      }),
    });

    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "转换失败");
    }

    resultList.innerHTML = "";
    data.files.forEach((file) => {
      const li = document.createElement("li");
      const page = document.createElement("span");
      page.textContent = `第 ${file.page} 页`;
      const path = document.createElement("span");
      path.className = "path";
      path.textContent = file.path;
      path.title = file.path;
      li.appendChild(page);
      li.appendChild(path);
      resultList.appendChild(li);
    });
    results.hidden = false;
    setStatus(`成功转换 ${data.count} 张图片`, "success");
  } catch (error) {
    setStatus(error.message || "转换失败", "error");
  } finally {
    convertBtn.disabled = false;
  }
});

clearBtn.addEventListener("click", () => {
  results.hidden = true;
  resultList.innerHTML = "";
});
