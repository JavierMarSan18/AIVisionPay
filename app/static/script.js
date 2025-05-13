const video = document.getElementById('video');
const resultado = document.getElementById('resultado');
const volumeSlider = document.getElementById('volumeSlider');
const volumeValue = document.getElementById('volumeValue');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');

let voiceVolume = 1.0;
let capturing = false;
let availableVoices = [];

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
  })
  .catch(err => {
    resultado.textContent = "❌ Error al acceder a la cámara: " + err.message;
  });

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
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64Image })
    });

    const result = await response.json();

    if (result.label && result.confidence >= 0.9) {
      resultado.textContent = `${result.label} (${(result.confidence * 100).toFixed(1)}%)`;

      const msg = new SpeechSynthesisUtterance(result.label);
      msg.volume = voiceVolume;
      msg.pitch = 1.1;
      msg.rate = 0.95;
      msg.lang = result.language === "es" ? "es-ES"
        : result.language === "pt" ? "pt-BR"
        : "en-US";

      const preferredVoice = availableVoices.find(v => v.lang === msg.lang);
      if (preferredVoice) msg.voice = preferredVoice;

      msg.onend = () => { if (capturing) setTimeout(capture, 500); };

      speechSynthesis.cancel();
      speechSynthesis.speak(msg);
    } else if (result.label) {
      resultado.textContent = `🤔 Pensando...`;
      setTimeout(capture, 1000);
    } else {
      resultado.textContent = "⚠️ Error: " + JSON.stringify(result);
      setTimeout(capture, 1500);
    }
  } catch (err) {
    resultado.textContent = "❌ Error al enviar la imagen: " + err;
    setTimeout(capture, 1500);
  }
}

function startCapture() {
  if (!capturing) {
    capturing = true;
    startBtn.style.display = "none";
    stopBtn.style.display = "inline-block";
    capture();
  }
}

function stopCapture() {
  capturing = false;
  speechSynthesis.cancel();
  startBtn.style.display = "inline-block";
  stopBtn.style.display = "none";
  resultado.textContent = "Captura detenida";
}