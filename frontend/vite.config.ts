import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    watch: {
      // Windows + Docker 볼륨 마운트에서는 파일시스템 이벤트가 컨테이너로 전달되지 않는 경우가 많아 폴링 사용
      usePolling: true,
    },
  },
});
