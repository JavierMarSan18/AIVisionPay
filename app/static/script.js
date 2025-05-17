const video = document.getElementById('video');
const resultado = document.getElementById('resultado');
const volumeSlider = document.getElementById('volumeSlider');
const volumeValue = document.getElementById('volumeValue');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');

let voiceVolume = 1.0;
let capturing = false;
let availableVoices = [];

// Configuración inicial
function initApp() {
  // Cargar voces disponibles
  speechSynthesis.onvoiceschanged = () => {
    availableVoices = speechSynthesis.getVoices();
  };

  // Control de volumen
  volumeSlider.addEventListener('input', () => {
    voiceVolume = volumeSlider.value / 100;
    volumeValue.textContent = volumeSlider.value;
  });

  // Iniciar cámara
  navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
      video.srcObject = stream;
    })
    .catch(err => {
      showResult("error", "Error al acceder a la cámara: " + err.message);
    });
}

// Función de captura y reconocimiento
async function capture() {
  if (!capturing) return;

  const canvas = document.createElement("canvas");
  canvas.width = 224;
  canvas.height = 224;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  try {
    showResult("thinking", "Analizando...");
    
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: canvas.toDataURL("image/jpeg").split(',')[1] })
    });

    const result = await response.json();

    if (result.label && result.confidence >= 0.82) {
      showResult("success", `${result.label} (${(result.confidence * 100).toFixed(1)}%)`);
      speakResult(result.label, result.language);
    } else if (result.label) {
      showResult("thinking", "No estoy seguro...");
      setTimeout(capture, 1000);
    } else {
      showResult("error", "No se reconoció el objeto");
      setTimeout(capture, 1500);
    }
  } catch (err) {
    showResult("error", "Error: " + err.message);
    setTimeout(capture, 1500);
  }
}

// Función para hablar el resultado
function speakResult(text, lang) {
  const msg = new SpeechSynthesisUtterance(text);
  msg.volume = voiceVolume;
  msg.lang = lang === "es" ? "es-ES" : lang === "pt" ? "pt-BR" : "en-US";
  
  const voice = availableVoices.find(v => v.lang === msg.lang);
  if (voice) msg.voice = voice;

  msg.onend = () => capturing && setTimeout(capture, 500);
  speechSynthesis.speak(msg);
}

// Mostrar resultado
function showResult(type, message) {
  resultado.innerHTML = message;
  resultado.className = "result-container";
  resultado.classList.add("result-" + type);
}

// Control de captura
function startCapture() {
  if (!capturing) {
    capturing = true;
    startBtn.style.display = "none";
    stopBtn.style.display = "flex";
    showResult("active", "Iniciando...");
    capture();
  }
}

function stopCapture() {
  capturing = false;
  speechSynthesis.cancel();
  startBtn.style.display = "flex";
  stopBtn.style.display = "none";
  resultado.innerHTML = `
    <div class="result-placeholder">
      <span class="icon">⏸️</span>
      <p>Captura detenida</p>
    </div>
  `;
  resultado.className = "result-container";
}

// Iniciar aplicación
document.addEventListener('DOMContentLoaded', initApp);