import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    var apiTarget = env.VITE_API_URL || "http://localhost:8000";
    var wsTarget = apiTarget.replace(/^http/, "ws");
    return {
        plugins: [react()],
        server: {
            port: 5173,
            proxy: {
                "/api/ws": { target: wsTarget, ws: true, changeOrigin: true },
                "/api": { target: apiTarget, changeOrigin: true },
            },
        },
        build: {
            outDir: "dist",
            sourcemap: true,
        },
    };
});
