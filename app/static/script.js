// Mismo código JavaScript anterior, pero con ajuste para el overlay de video

const video = document.getElementById('video');
const resultado = document.getElementById('resultado');
const volumeSlider = document.getElementById('volumeSlider');
const volumeValue = document.getElementById('volumeValue');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const videoOverlay = document.getElementById('videoOverlay');

let voiceVolume = 1.0;
let capturing = false;
let availableVoices = [];

// Ajustar tamaño del overlay cuando cambia el video
function resizeOverlay() {
  if (video.videoWidth && video.videoHeight) {
    const videoRatio = video.videoWidth / video.videoHeight;
    const containerRatio = video.clientWidth / video.clientHeight;
    
    if (containerRatio > videoRatio) {
      // Contenedor más ancho que el video
      const scale = video.clientWidth / video.videoWidth;
      videoOverlay.style.transform = `scale(${scale})`;
    } else {
      // Contenedor más alto que el video
      const scale = video.clientHeight / video.videoHeight;
      videoOverlay.style.transform = `scale(${scale})`;
    }
  }
}

// Observar cambios de tamaño del video
const resizeObserver = new ResizeObserver(resizeOverlay);
resizeObserver.observe(video);

speechSynthesis.onvoiceschanged = () => {
  availableVoices = speechSynthesis.getVoices();
};

volumeSlider.addEventListener('input', () => {
  voiceVolume = volumeSlider.value / 100;
  volumeValue.textContent = volumeSlider.value;
});

navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    video.srcObject = stream;
    video.onloadedmetadata = () => {
      resizeOverlay();
    };
  })
  .catch(err => {
    showError("Error al acceder a la cámara: " + err.message);
  });

// Resto del código JavaScript permanece igual...
async function capture() {
  if (!capturing) return;

  const canvas = document.createElement("canvas");
  canvas.width = 224;
  canvas.height = 224;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataURL = canvas.toDataURL("image/jpeg");
  const base64Image = dataURL.split(',')[1];

  try {
    updateResultState("thinking", "🤔 Analizando imagen...");
    
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64Image })
    });

    const result = await response.json();

    if (result.label && result.confidence >= 0.9) {
      const confidencePercent = (result.confidence * 100).toFixed(1);
      updateResultState("success", `${result.label} (${confidencePercent}% confianza)`);
      
      const msg = new SpeechSynthesisUtterance(result.label);
      msg.volume = voiceVolume;
      msg.pitch = 1.1;
      msg.rate = 0.95;
      msg.lang = result.language === "es" ? "es-ES"
        : result.language === "pt" ? "pt-BR"
        : "en-US";

      const preferredVoice = availableVoices.find(v => v.lang === msg.lang);
      if (preferredVoice) msg.voice = preferredVoice;

      msg.onend = () => { 
        if (capturing) setTimeout(capture, 500); 
      };

      speechSynthesis.cancel();
      speechSynthesis.speak(msg);
      
    } else if (result.label) {
      updateResultState("thinking", "🤔 No estoy seguro...");
      setTimeout(capture, 1000);
    } else {
      updateResultState("error", "⚠️ No se pudo reconocer el objeto");
      setTimeout(capture, 1500);
    }
  } catch (err) {
    updateResultState("error", "❌ Error: " + err.message);
    setTimeout(capture, 1500);
  }
}

function updateResultState(state, message) {
  resultado.innerHTML = message;
  resultado.className = "result-card";
  resultado.classList.add(state);
}

function showError(message) {
  updateResultState("error", "❌ " + message);
}

function startCapture() {
  if (!capturing) {
    capturing = true;
    startBtn.style.display = "none";
    stopBtn.style.display = "flex";
    updateResultState("active", "🔍 Iniciando reconocimiento...");
    capture();
  }
}

function stopCapture() {
  capturing = false;
  speechSynthesis.cancel();
  startBtn.style.display = "flex";
  stopBtn.style.display = "none";
  updateResultState("", `
    <div class="result-placeholder">
      <span class="icon">⏸️</span>
      <p>Captura detenida</p>
    </div>
  `);
}