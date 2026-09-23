/// <reference types="vite/client" />

interface Window {
  __ACH_CONFIG__?: {
    apiBaseUrl: string;
    launchToken?: string;
    demoMode?: boolean;
    startupError?: string | null;
  };
  __ACH_RUNTIME_ERROR__?: string;
}
