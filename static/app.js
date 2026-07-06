const camera = document.getElementById("camera");
const canvas = document.getElementById("buffer");
const resultBox = document.getElementById("result");
const streamStatus = document.getElementById("streamStatus");

const registerForm = document.getElementById("registerForm");
const authCard = document.getElementById("authCard");
const tabRegister = document.getElementById("tabRegister");
const tabAuth = document.getElementById("tabAuth");

const btnStartAuth = document.getElementById("btnStartAuth");
const btnStartRegister = document.getElementById("btnStartRegister");

let stream = null;
let activeMode = "register";
let loopTimer = null;
let requestInFlight = false;

function setResult(message, kind = "") {
  resultBox.textContent = message;
  resultBox.className = `result ${kind}`.trim();
}

function setMode(mode) {
  activeMode = mode;
  const register = mode === "register";

  tabRegister.classList.toggle("active", register);
  tabAuth.classList.toggle("active", !register);

  registerForm.classList.toggle("hidden", !register);
  authCard.classList.toggle("hidden", register);

  stopLoop();
  requestInFlight = false;
  btnStartRegister.disabled = false;
  btnStartAuth.disabled = false;

  setResult("Listo para comenzar.");
}

async function startCamera() {
  streamStatus.textContent = "Solicitando permisos de cámara...";

  stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: "user",
      width: { ideal: 1280 },
      height: { ideal: 720 }
    },
    audio: false
  });

  camera.srcObject = stream;

  await camera.play();
  streamStatus.textContent = "Streaming activo";
}

function captureFrameDataURL() {
  const width = camera.videoWidth || 640;
  const height = camera.videoHeight || 480;

  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(camera, 0, 0, width, height);

  return canvas.toDataURL("image/jpeg", 0.82);
}

async function sendFrame(endpoint, payloadBuilder, onSuccess) {
  if (requestInFlight) {
    return;
  }

  requestInFlight = true;

  try {
    const frame = captureFrameDataURL();
    const payload = payloadBuilder(frame);

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const body = await response.json();

    if (response.ok && body.ok) {
      onSuccess(body.data);
      stopLoop();
      return;
    }

    const err = body.error || body.data?.message || "No se pudo procesar el rostro.";
    setResult(err, "bad");
  } catch (error) {
    setResult(`Error de conexión: ${error.message}`, "bad");
  } finally {
    requestInFlight = false;
  }
}

function startLoop(endpoint, payloadBuilder, onSuccess) {
  stopLoop();

  setResult("Procesando stream en vivo... mantente frente a la cámara.");

  loopTimer = setInterval(() => {
    sendFrame(endpoint, payloadBuilder, onSuccess);
  }, 850);
}

function stopLoop() {
  if (loopTimer) {
    clearInterval(loopTimer);
    loopTimer = null;
  }
}

registerForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const nombre = document.getElementById("nombre").value.trim();
  const documento = document.getElementById("documento").value.trim();

  if (!nombre || !documento) {
    setResult("Completa nombre y documento.", "bad");
    return;
  }

  btnStartRegister.disabled = true;

  startLoop(
    "/api/stream/register",
    (frame) => ({ nombre, documento, frame }),
    (data) => {
      setResult(
        `Registro exitoso\nNombre: ${data.nombre}\nDocumento: ${data.documento}\nHash: ${data.face_hash}`,
        "ok"
      );
      btnStartRegister.disabled = false;
    }
  );
});

btnStartAuth.addEventListener("click", () => {
  btnStartAuth.disabled = true;

  startLoop(
    "/api/stream/authenticate",
    (frame) => ({ frame }),
    (data) => {
      const user = data.user;
      setResult(
        `Autenticación correcta\nNombre: ${user.nombre}\nDocumento: ${user.documento}\nHash: ${user.face_hash}\nScore: ${data.score} (umbral ${data.threshold})`,
        "ok"
      );
      btnStartAuth.disabled = false;
    }
  );
});

tabRegister.addEventListener("click", () => setMode("register"));
tabAuth.addEventListener("click", () => setMode("auth"));

(async function init() {
  try {
    await startCamera();
    setMode("register");
  } catch (error) {
    streamStatus.textContent = "No se pudo abrir la cámara";
    setResult(`Permiso de cámara denegado o no disponible: ${error.message}`, "bad");
  }
})();
