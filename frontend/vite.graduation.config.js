// Extend the current branch's config so its agent middleware remains available.
import { defineConfig, mergeConfig } from "vite";
import baseConfig from "./vite.config.js";

export default defineConfig(async (environment) => {
  const base = await (typeof baseConfig === "function"
    ? baseConfig(environment)
    : baseConfig);
  return mergeConfig(base, {
    server: { proxy: { "/api/v1": "http://127.0.0.1:5000" } },
  });
});
