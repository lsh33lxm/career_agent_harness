/// <reference types="vite/client" />

interface Window {
  __ACH_CONFIG__?: {
    apiBaseUrl: string;
    launchToken?: string;
    demoMode?: boolean;
    /** 仅开发环境：视觉验收 fixture 模式（?demo=visual-review 或注入 true）。生产构建不含此分支。 */
    visualReview?: boolean;
  };
}
