/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Client ID de Google OAuth (público). Se sirve vía config del backend. */
  readonly VITE_GOOGLE_CLIENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// ── Google Identity Services (cargado perezosamente por script) ──
interface GoogleCredentialResponse {
  credential: string;
  select_by?: string;
}

interface GoogleIdConfig {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void;
  auto_select?: boolean;
  cancel_on_tap_outside?: boolean;
}

interface GoogleButtonOptions {
  type?: "standard" | "icon";
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  text?: "signin_with" | "signup_with" | "continue_with" | "signin";
  shape?: "rectangular" | "pill" | "circle" | "square";
  locale?: string;
  width?: number;
}

interface Window {
  google?: {
    accounts: {
      id: {
        initialize: (config: GoogleIdConfig) => void;
        renderButton: (
          parent: HTMLElement,
          options: GoogleButtonOptions,
        ) => void;
        prompt: () => void;
        disableAutoSelect: () => void;
      };
    };
  };
}
