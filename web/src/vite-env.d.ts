/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API base URL. Defaults to the dev proxy path; set in production to the API origin. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
