(function (global) {
  function normalizeOrigin(value) {
    if (!value) {
      return "";
    }

    try {
      return new URL(value).origin;
    } catch (error) {
      return value;
    }
  }

  function buildPluginUrl(baseUrl, options) {
    const url = new URL(baseUrl);
    url.searchParams.set("plugin", "1");

    if (options && options.launchToken) {
      url.searchParams.set("token", options.launchToken);
    }

    return url.toString();
  }

  function buildPopupFeatures(options) {
    const opts = options || {};
    const width = opts.width || 920;
    const height = opts.height || 760;

    const left = Math.max(0, Math.round((window.screen.width - width) / 2));
    const top = Math.max(0, Math.round((window.screen.height - height) / 2));

    return [
      "popup=yes",
      "noopener=no",
      "noreferrer=no",
      "menubar=no",
      "toolbar=no",
      "location=no",
      "status=no",
      "resizable=yes",
      "scrollbars=yes",
      `width=${width}`,
      `height=${height}`,
      `left=${left}`,
      `top=${top}`
    ].join(",");
  }

  function buildPopupName(options) {
    const opts = options || {};
    return opts.windowName || `FaceAuthPluginWindow_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
  }

  function preopenFaceAuthPopup(options) {
    const opts = options || {};
    const popupName = buildPopupName(opts);
    const features = buildPopupFeatures(opts);
    const preopenedPopup = window.open("about:blank", popupName, features);

    if (!preopenedPopup) {
      throw new Error("No se pudo abrir popup. Verifica bloqueador de ventanas emergentes.");
    }

    return preopenedPopup;
  }

  async function requestLaunchToken(options) {
    const opts = options || {};

    if (!opts.tokenEndpoint) {
      throw new Error("Falta tokenEndpoint para obtener token de lanzamiento.");
    }

    if (!opts.clientId) {
      throw new Error("Falta clientId para solicitar token de plugin.");
    }

    if (!opts.apiKey) {
      throw new Error("Falta apiKey para solicitar token de plugin.");
    }

    const response = await fetch(opts.tokenEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Plugin-Api-Key": opts.apiKey
      },
      body: JSON.stringify({
        client_id: opts.clientId,
        origin: opts.origin || window.location.origin
      })
    });

    const body = await response.json();

    if (!response.ok || !body.ok || !body.data?.token) {
      throw new Error(body.error || "No se pudo obtener token de plugin.");
    }

    return body.data.token;
  }

  function resolveOnClose(opts, resolve, reject) {
    const shouldReject = opts && opts.rejectOnClose === true;

    if (shouldReject) {
      const error = new Error("La ventana del plugin fue cerrada antes de completar la autenticacion.");
      error.code = "FACE_PLUGIN_WINDOW_CLOSED";
      reject(error);
      return;
    }

    resolve({
      cancelled: true,
      reason: "window_closed"
    });
  }

  function closePopupIfPossible(popup) {
    if (!popup) {
      return;
    }

    try {
      popup.close();
    } catch (error) {
      // Ignore close errors. The auth result is already available.
    }
  }

  function openEmbeddedFaceAuthPlugin(pluginUrl, opts) {
    const expectedOrigin = normalizeOrigin(opts.expectedOrigin || pluginUrl);
    const container = typeof opts.container === "string"
      ? document.querySelector(opts.container)
      : opts.container;

    if (!container || !(container instanceof Element)) {
      return Promise.reject(new Error("Debes enviar container valido para usar modo embebido."));
    }

    return new Promise((resolve, reject) => {
      let finished = false;

      const shell = document.createElement("div");
      shell.style.position = "relative";
      shell.style.width = "100%";
      shell.style.minHeight = `${opts.height || 760}px`;

      const closeButton = document.createElement("button");
      closeButton.type = "button";
      closeButton.textContent = "Cerrar";
      closeButton.style.position = "absolute";
      closeButton.style.top = "10px";
      closeButton.style.right = "10px";
      closeButton.style.zIndex = "2";
      closeButton.style.padding = "8px 12px";
      closeButton.style.border = "0";
      closeButton.style.borderRadius = "8px";
      closeButton.style.cursor = "pointer";

      const frame = document.createElement("iframe");
      frame.src = pluginUrl;
      frame.allow = "camera";
      frame.style.width = "100%";
      frame.style.height = `${opts.height || 760}px`;
      frame.style.border = "0";
      frame.style.borderRadius = "12px";
      frame.style.background = "#fff";

      function cleanup() {
        window.removeEventListener("message", onMessage);

        if (shell.parentNode) {
          shell.parentNode.removeChild(shell);
        }
      }

      function finishWithResolve(payload) {
        if (finished) {
          return;
        }

        finished = true;
        cleanup();
        resolve(payload);
      }

      function finishWithReject(error) {
        if (finished) {
          return;
        }

        finished = true;
        cleanup();
        reject(error);
      }

      function onMessage(event) {
        const data = event.data || {};
        const isFromEmbeddedFrame = event.source === frame.contentWindow;

        if (data.source !== "face-auth-plugin") {
          return;
        }

        if (!isFromEmbeddedFrame) {
          return;
        }

        if (expectedOrigin && event.origin !== expectedOrigin) {
          if (opts && opts.debug === true) {
            console.warn("FaceAuthPlugin(embed): origin inesperado", {
              expectedOrigin,
              receivedOrigin: event.origin
            });
          }
        }

        if (data.event === "auth:success") {
          finishWithResolve(data.payload);
          return;
        }

        if (data.event === "register:success" && opts.resolveOnRegister) {
          finishWithResolve(data.payload);
        }
      }

      closeButton.addEventListener("click", () => {
        if (opts.rejectOnClose === true) {
          finishWithReject(new Error("El flujo embebido fue cerrado manualmente."));
          return;
        }

        finishWithResolve({
          cancelled: true,
          reason: "window_closed"
        });
      });

      shell.appendChild(closeButton);
      shell.appendChild(frame);
      container.appendChild(shell);
      window.addEventListener("message", onMessage);
    });
  }

  function openFaceAuthPlugin(options) {
    const opts = options || {};

    if (!opts.launchToken) {
      return Promise.reject(
        new Error("Debes enviar launchToken. Solicitalo desde tu backend antes de abrir el plugin.")
      );
    }

    const pluginUrl = buildPluginUrl(
      opts.pluginUrl || "http://127.0.0.1:5000/",
      {
        launchToken: opts.launchToken
      }
    );

    if (opts.mode === "embed" || opts.container) {
      return openEmbeddedFaceAuthPlugin(pluginUrl, opts);
    }

    const expectedOrigin = normalizeOrigin(opts.expectedOrigin || pluginUrl);

    const popup = opts.preopenedPopup || null;

    if (popup && !popup.closed) {
      try {
        popup.location.replace(pluginUrl);
      } catch (error) {
        return Promise.reject(new Error("No se pudo navegar el popup preabierto al plugin."));
      }
    }

    const features = buildPopupFeatures(opts);
    const popupName = buildPopupName(opts);
    const openedPopup = popup && !popup.closed ? popup : window.open(pluginUrl, popupName, features);

    if (!openedPopup) {
      return Promise.reject(new Error("No se pudo abrir la ventana del plugin."));
    }

    return new Promise((resolve, reject) => {
      let pollTimer = null;
      let closeGraceTimer = null;
      let finished = false;
      let closeDetected = false;

      function finishWithResolve(payload) {
        if (finished) {
          return;
        }

        finished = true;
        cleanup();
        resolve(payload);
      }

      function finishWithReject(error) {
        if (finished) {
          return;
        }

        finished = true;
        cleanup();
        reject(error);
      }

      function cleanup() {
        window.removeEventListener("message", onMessage);

        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }

        if (closeGraceTimer) {
          clearTimeout(closeGraceTimer);
          closeGraceTimer = null;
        }
      }

      function onMessage(event) {
        const data = event.data || {};
        const isFromPopup = event.source === openedPopup;

        if (data.source !== "face-auth-plugin") {
          return;
        }

        if (!isFromPopup) {
          return;
        }

        if (expectedOrigin && event.origin !== expectedOrigin) {
          if (opts && opts.debug === true) {
            console.warn("FaceAuthPlugin(popup): origin inesperado", {
              expectedOrigin,
              receivedOrigin: event.origin
            });
          }
        }

        if (data.event === "auth:success") {
          closePopupIfPossible(openedPopup);
          finishWithResolve(data.payload);
        }

        if (data.event === "register:success" && opts.resolveOnRegister) {
          closePopupIfPossible(openedPopup);
          finishWithResolve(data.payload);
        }
      }

      window.addEventListener("message", onMessage);

      pollTimer = setInterval(() => {
        if (openedPopup.closed && !closeDetected) {
          closeDetected = true;
          closeGraceTimer = setTimeout(() => {
            if (finished) {
              return;
            }

            const shouldReject = opts && opts.rejectOnClose === true;
            if (shouldReject) {
              const error = new Error("La ventana del plugin fue cerrada antes de completar la autenticacion.");
              error.code = "FACE_PLUGIN_WINDOW_CLOSED";
              finishWithReject(error);
              return;
            }

            finishWithResolve({
              cancelled: true,
              reason: "window_closed"
            });
          }, opts.closeGraceMs || 1200);
        }
      }, 400);
    });
  }

  global.FaceAuthPlugin = {
    open: openFaceAuthPlugin,
    preopenPopup: preopenFaceAuthPopup,
    requestLaunchToken
  };
})(window);
