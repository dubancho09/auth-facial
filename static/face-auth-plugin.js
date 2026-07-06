(function (global) {
  function buildPluginUrl(baseUrl, options) {
    const url = new URL(baseUrl);
    url.searchParams.set("plugin", "1");

    if (options && options.launchToken) {
      url.searchParams.set("token", options.launchToken);
    }

    return url.toString();
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

    const width = opts.width || 920;
    const height = opts.height || 760;

    const left = Math.max(0, Math.round((window.screen.width - width) / 2));
    const top = Math.max(0, Math.round((window.screen.height - height) / 2));

    const features = [
      "popup=yes",
      `width=${width}`,
      `height=${height}`,
      `left=${left}`,
      `top=${top}`
    ].join(",");

    const popup = window.open(pluginUrl, "FaceAuthPluginWindow", features);

    if (!popup) {
      return Promise.reject(new Error("No se pudo abrir la ventana del plugin."));
    }

    return new Promise((resolve, reject) => {
      let pollTimer = null;

      function cleanup() {
        window.removeEventListener("message", onMessage);

        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      }

      function onMessage(event) {
        const data = event.data || {};

        if (data.source !== "face-auth-plugin") {
          return;
        }

        if (!opts.expectedOrigin || event.origin !== opts.expectedOrigin) {
          return;
        }

        if (data.event === "auth:success") {
          cleanup();
          resolve(data.payload);
        }

        if (data.event === "register:success" && opts.resolveOnRegister) {
          cleanup();
          resolve(data.payload);
        }
      }

      window.addEventListener("message", onMessage);

      pollTimer = setInterval(() => {
        if (popup.closed) {
          cleanup();
          reject(new Error("La ventana del plugin fue cerrada antes de completar la autenticacion."));
        }
      }, 400);
    });
  }

  global.FaceAuthPlugin = {
    open: openFaceAuthPlugin,
    requestLaunchToken
  };
})(window);
