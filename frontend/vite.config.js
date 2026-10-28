import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { createStudyAgentMiddleware } from "./server/studyAgentMiddleware.js";
import { createStudyMemoryMiddleware } from "./server/studyMemoryMiddleware.js";

const projectRoot = fileURLToPath(new URL("..", import.meta.url));

function studyAgentApiPlugin(options) {
  const middleware = createStudyAgentMiddleware(options);
  return {
    name: "nutn-study-agent-api",
    configureServer(server) {
      server.middlewares.use("/api/study-agent", middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use("/api/study-agent", middleware);
    },
  };
}

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

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, projectRoot, "");
  return {
    envDir: projectRoot,
    plugins: [
      react(),
      studyAgentApiPlugin({
        apiKey: process.env.OPENAI_API_KEY || env.OPENAI_API_KEY,
        model: process.env.OPENAI_MODEL || env.OPENAI_MODEL,
        tracingEnabled:
          (process.env.OPENAI_AGENTS_TRACING || env.OPENAI_AGENTS_TRACING) ===
          "true",
      }),
      studyMemoryApiPlugin(),
    ],
  };
});
