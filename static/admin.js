const usersBody = document.getElementById("usersBody");
const usersResult = document.getElementById("usersResult");
const camera = document.getElementById("camera");
const canvas = document.getElementById("buffer");
const streamStatus = document.getElementById("streamStatus");
const createUserForm = document.getElementById("createUserForm");
const btnCreate = document.getElementById("btnCreate");
const btnToggleCamera = document.getElementById("btnToggleCamera");
const btnAuthenticate = document.getElementById("btnAuthenticate");
const authResult = document.getElementById("authResult");

let stream = null;

function setResult(message, kind = "") {
  usersResult.textContent = message;
  usersResult.className = `result ${kind}`.trim();
}

function escapeHtml(value) {
  return (value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function startCamera() {
  if (stream) {
    return;
  }

  streamStatus.textContent = "Solicitando permisos de camara...";

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
  updateCameraUi(true);
}

function stopCamera() {
  if (!stream) {
    updateCameraUi(false);
    return;
  }

  stream.getTracks().forEach((track) => track.stop());
  stream = null;
  camera.srcObject = null;
  updateCameraUi(false);
}

function updateCameraUi(isOn) {
  streamStatus.textContent = isOn ? "Camara activa" : "Camara apagada";
  btnToggleCamera.textContent = isOn ? "Apagar camara" : "Encender camara";
  btnCreate.disabled = !isOn;
  btnAuthenticate.disabled = !isOn;
  camera.classList.toggle("camera-off", !isOn);
}

function captureFrameDataURL() {
  if (!stream || !camera.srcObject) {
    throw new Error("La camara esta apagada. Enciendela para continuar.");
  }

  const width = camera.videoWidth || 640;
  const height = camera.videoHeight || 480;

  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(camera, 0, 0, width, height);

  return canvas.toDataURL("image/jpeg", 0.85);
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function renderUsers(users) {
  if (!Array.isArray(users) || users.length === 0) {
    usersBody.innerHTML = '<tr><td colspan="6">No hay usuarios registrados.</td></tr>';
    return;
  }

  usersBody.innerHTML = users
    .map((user) => {
      const shortHash = (user.face_hash || "").slice(0, 16);
      return `
      <tr>
        <td>${user.id}</td>
        <td>${escapeHtml(user.nombre)}</td>
        <td>${escapeHtml(user.documento)}</td>
        <td title="${escapeHtml(user.face_hash || "")}">${escapeHtml(shortHash)}...</td>
        <td>${escapeHtml(formatDate(user.fecha_creacion))}</td>
        <td>
          <div class="actions">
            <button type="button" class="btn" data-edit="${user.id}">Editar</button>
            <button type="button" class="btn danger" data-delete="${user.id}">Eliminar</button>
          </div>
        </td>
      </tr>`;
    })
    .join("");
}

async function loadUsers() {
  try {
    const response = await fetch("/admin/api/users");
    const body = await response.json();

    if (!response.ok || !body.ok) {
      throw new Error(body.error || "No se pudieron cargar los usuarios.");
    }

    renderUsers(body.data || []);
    setResult(`Usuarios cargados: ${(body.data || []).length}`, "ok");
  } catch (error) {
    setResult(error.message, "bad");
  }
}

async function createUser(nombre, documento) {
  const frame = captureFrameDataURL();

  const response = await fetch("/admin/api/users", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ nombre, documento, frame })
  });

  const body = await response.json();

  if (!response.ok || !body.ok) {
    throw new Error(body.error || "No se pudo crear el usuario.");
  }

  return body.data;
}

function setAuthResult(message, kind = "") {
  authResult.textContent = message;
  authResult.className = `result auth-result ${kind}`.trim();
}

async function authenticateCurrentFrame() {
  const frame = captureFrameDataURL();

  const response = await fetch("/api/stream/authenticate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ frame })
  });

  const body = await response.json();
  if (!response.ok || !body.data) {
    throw new Error(body.error || "No se pudo autenticar en este momento.");
  }

  return body.data;
}

async function updateUser(id, nombre, documento) {
  const response = await fetch(`/admin/api/users/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ nombre, documento })
  });

  const body = await response.json();

  if (!response.ok || !body.ok) {
    throw new Error(body.error || "No se pudo actualizar el usuario.");
  }
}

async function deleteUser(id) {
  const response = await fetch(`/admin/api/users/${id}`, {
    method: "DELETE"
  });

  const body = await response.json();

  if (!response.ok || !body.ok) {
    throw new Error(body.error || "No se pudo eliminar el usuario.");
  }
}

createUserForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const nombre = document.getElementById("nombre").value.trim();
  const documento = document.getElementById("documento").value.trim();

  if (!nombre || !documento) {
    setResult("Nombre y documento son obligatorios.", "bad");
    return;
  }

  btnCreate.disabled = true;
  setResult("Creando usuario biometrico...", "");

  try {
    const created = await createUser(nombre, documento);
    setResult(`Usuario creado: ${created.nombre} (${created.documento})`, "ok");
    createUserForm.reset();
    await loadUsers();
  } catch (error) {
    setResult(error.message, "bad");
  } finally {
    btnCreate.disabled = false;
  }
});

btnToggleCamera.addEventListener("click", async () => {
  if (stream) {
    stopCamera();
    setResult("Camara apagada manualmente.", "");
    return;
  }

  try {
    await startCamera();
    setResult("Camara encendida.", "ok");
  } catch (error) {
    updateCameraUi(false);
    setResult(`No se pudo encender la camara: ${error.message}`, "bad");
  }
});

btnAuthenticate.addEventListener("click", async () => {
  if (!stream) {
    setAuthResult("La camara esta apagada. Enciendela para autenticar.", "bad");
    return;
  }

  btnAuthenticate.disabled = true;
  setAuthResult("Autenticando rostro...", "");

  try {
    const result = await authenticateCurrentFrame();
    if (!result.authenticated) {
      setAuthResult(
        `${result.message || "Rostro no reconocido."} (score: ${result.score ?? 0}, umbral: ${result.threshold ?? "n/a"})`,
        "bad"
      );
      return;
    }

    setAuthResult(
      `Autenticado: ${result.user?.nombre || "Usuario"} (${result.user?.documento || "-"}) | score: ${result.score}`,
      "ok"
    );
  } catch (error) {
    setAuthResult(error.message, "bad");
  } finally {
    btnAuthenticate.disabled = !stream;
  }
});

usersBody.addEventListener("click", async (event) => {
  const editId = event.target.getAttribute("data-edit");
  const deleteId = event.target.getAttribute("data-delete");

  if (editId) {
    const currentRow = event.target.closest("tr");
    const currentNombre = currentRow.children[1].textContent.trim();
    const currentDocumento = currentRow.children[2].textContent.trim();

    const nombre = window.prompt("Nuevo nombre:", currentNombre);
    if (nombre === null) {
      return;
    }

    const documento = window.prompt("Nuevo documento:", currentDocumento);
    if (documento === null) {
      return;
    }

    try {
      await updateUser(editId, nombre.trim(), documento.trim());
      setResult("Usuario actualizado correctamente.", "ok");
      await loadUsers();
    } catch (error) {
      setResult(error.message, "bad");
    }

    return;
  }

  if (deleteId) {
    const confirmed = window.confirm("Esta accion eliminara el usuario. ¿Deseas continuar?");
    if (!confirmed) {
      return;
    }

    try {
      await deleteUser(deleteId);
      setResult("Usuario eliminado correctamente.", "ok");
      await loadUsers();
    } catch (error) {
      setResult(error.message, "bad");
    }
  }
});

(async function init() {
  try {
    await startCamera();
  } catch (error) {
    updateCameraUi(false);
    streamStatus.textContent = "No se pudo abrir la camara";
    setResult(`Permiso de camara denegado o no disponible: ${error.message}`, "bad");
  }

  await loadUsers();
})();

window.addEventListener("beforeunload", () => {
  stopCamera();
});
