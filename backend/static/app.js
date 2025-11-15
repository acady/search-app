async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  const resBox = document.getElementById("uploadResult");

  if (!fileInput.files.length) {
    resBox.innerText = "Bitte zuerst eine Datei auswählen.";
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const res = await fetch("/api/upload", {
    method: "POST",
    body: formData,
  });

  const data = await res.json();
  resBox.innerText = JSON.stringify(data, null, 2);
}

async function runSearch() {
  const q = document.getElementById("searchInput").value;
  const out = document.getElementById("resultsContainer");

  const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
  const data = await res.json();

  out.innerHTML = "";
  data.results.forEach(doc => {
    const div = document.createElement("div");
    div.className = "result-card";
    div.innerHTML = `
      <div class="header">
        <b>${doc.filename}</b> <span class="doctype">${doc.doctype}</span>
      </div>
      <div class="snippet">${(doc.snippet || "")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")}</div>
      <div class="keywords">Keywords: ${
        (doc.keywords || []).join(", ") || "-"
      }</div>
    `;
    out.appendChild(div);
  });
}

async function runKW() {
  const kw = document.getElementById("kwInput").value;
  const out = document.getElementById("kwResult");

  const res = await fetch(`/api/related?keyword=${encodeURIComponent(kw)}`);
  const data = await res.json();

  out.innerHTML = "";
  if (!data.documents.length) {
    out.innerText = "Keine verknüpften Dokumente gefunden.";
    return;
  }

  data.documents.forEach(doc => {
    const div = document.createElement("div");
    div.className = "related-card";
    div.innerHTML = `
      <b>${doc.filename}</b><br/>
      ID: ${doc.id}<br/>
      Keywords: ${(doc.keywords || []).join(", ")}
    `;
    out.appendChild(div);
  });
}

async function sendChat() {
  const inputEl = document.getElementById("chatInput");
  const chatLog = document.getElementById("chatLog");
  const userMsg = inputEl.value.trim();
  if (!userMsg) return;

  const userDiv = document.createElement("div");
  userDiv.className = "chatline-user";
  userDiv.innerText = userMsg;
  chatLog.appendChild(userDiv);

  const res = await fetch(`/api/chat?q=${encodeURIComponent(userMsg)}`);
  const data = await res.json();

  const botDiv = document.createElement("div");
  botDiv.className = "chatline-bot";

  let answerText = data.answer || "(keine Antwort)";
  answerText += "\n\nTreffer:\n";
  (data.results || []).forEach(hit => {
    answerText += `• ${hit.filename} [${(hit.score || 0).toFixed(2)}]\n`;
  });

  botDiv.innerText = answerText;
  chatLog.appendChild(botDiv);

  chatLog.scrollTop = chatLog.scrollHeight;
  inputEl.value = "";
}

document.getElementById("uploadBtn").addEventListener("click", uploadFile);
document.getElementById("searchBtn").addEventListener("click", runSearch);
document.getElementById("kwBtn").addEventListener("click", runKW);
document.getElementById("chatSend").addEventListener("click", sendChat);
document.getElementById("chatInput").addEventListener("keypress", e => {
  if (e.key === "Enter") {
    sendChat();
  }
});
