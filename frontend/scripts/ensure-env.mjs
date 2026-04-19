import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const envPath = path.join(root, ".env");
const examplePath = path.join(root, ".env.example");

if (fs.existsSync(envPath)) {
  process.exit(0);
}

if (!fs.existsSync(examplePath)) {
  console.warn("No .env or .env.example found; skipping env bootstrap.");
  process.exit(0);
}

fs.copyFileSync(examplePath, envPath);
console.log("Created .env from .env.example");

