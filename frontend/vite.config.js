import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const projectRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, projectRoot, "BACKEND_");
  const backendTarget = env.BACKEND_PROXY_TARGET || "http://127.0.0.1:5050";
  return {
    envDir: projectRoot,
    plugins: [react()],
    server: { proxy: { "/api/v1": backendTarget } },
    preview: { proxy: { "/api/v1": backendTarget } },
  };
});
