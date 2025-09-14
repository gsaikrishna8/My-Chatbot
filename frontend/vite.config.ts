import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/ws": {
        target: "http://localhost:8000", // ✅ updated
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
