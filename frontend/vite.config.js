import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { createStudyMemoryMiddleware } from "./server/studyMemoryMiddleware.js";

const projectRoot = fileURLToPath(new URL("..", import.meta.url));

function studyMemoryApiPlugin() {
  const middleware = createStudyMemoryMiddleware();
  return {
    name: "nutn-study-memory-api",
    configureServer(server) {
      server.middlewares.use("/api/study-memory", middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use("/api/study-memory", middleware);
    },
  };
}

export default defineConfig({
  envDir: projectRoot,
  plugins: [react(), studyMemoryApiPlugin()],
  server: { proxy: { "/api/v1": "http://127.0.0.1:5050" } },
  preview: { proxy: { "/api/v1": "http://127.0.0.1:5050" } },
});
