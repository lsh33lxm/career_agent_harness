export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  type: string;
  source: { repo: string; ref: string; commit: string; license: string };
  capabilities: string[];
  permissions: {
    network: string[];
    filesystem: string[];
    secrets: string[];
    external_write: boolean;
    scope: string[];
  };
  user_visible_description: string;
}

export interface PluginInstallation {
  status: string;
  enabled: boolean;
  current_version: string;
  last_health_status?: string | null;
}

export interface PluginCatalogItem {
  manifest: PluginManifest;
  installed: boolean;
  installation: PluginInstallation | null;
  release_scan?: {
    overall: string;
    license?: { status?: string; spdx?: string };
    dependencies?: { status?: string };
    security?: { status?: string };
  };
}
