export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

interface RuntimeConfig {
  apiBaseUrl: string;
  launchToken: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function runtimeConfig(): RuntimeConfig {
  const injected = window.__ACH_CONFIG__;
  const apiBaseUrl =
    injected?.apiBaseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8765";
  const launchToken = injected?.launchToken ?? import.meta.env.VITE_LAUNCH_TOKEN;

  if (!launchToken) {
    throw new ApiError("Local API launch token is unavailable");
  }
  if (!apiBaseUrl.startsWith("http://127.0.0.1:")) {
    throw new ApiError("Local API must use an explicit 127.0.0.1 address");
  }
  return { apiBaseUrl, launchToken };
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const config = runtimeConfig();
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}/health`, {
      headers: { Authorization: `Bearer ${config.launchToken}` },
      signal,
    });
  } catch {
    throw new ApiError("Local API is unavailable");
  }

  if (!response.ok) {
    throw new ApiError("Local API health check failed", response.status);
  }
  return (await response.json()) as HealthResponse;
}
