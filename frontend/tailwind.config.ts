import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        aarav: { bg: "#1a1a2e", mid: "#16213e", deep: "#0f3460", accent: "#e94560" },
        aarohi: { bg: "#f5e6ca", mid: "#e8c99a", deep: "#c9a96e", accent: "#8B6914" },
      },
    },
  },
  plugins: [],
};
export default config;
