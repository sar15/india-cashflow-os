import { createHmac, pbkdf2Sync, randomBytes, randomUUID } from "node:crypto";

function toBase64Url(value) {
  return Buffer.from(value)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function createPasswordHash(password) {
  const iterations = 600000;
  const salt = randomBytes(16);
  const hash = pbkdf2Sync(password, salt, iterations, 32, "sha256");
  return `pbkdf2$sha256$${iterations}$${toBase64Url(salt)}$${toBase64Url(hash)}`;
}

function parseArg(name, fallback = "") {
  const index = process.argv.indexOf(`--${name}`);
  if (index === -1) {
    return fallback;
  }
  return process.argv[index + 1] ?? fallback;
}

const email = parseArg("email");
const name = parseArg("name");
const orgId = parseArg("org", "demo-org");
const role = parseArg("role", "owner");
const password = parseArg("password");

if (!email || !name || !password) {
  console.error("Usage: node scripts/generate_auth_bundle.mjs --email owner@company.com --name \"Owner\" --password \"strong-password\" [--org demo-org] [--role owner]");
  process.exit(1);
}

const apiToken = `cashflow-${randomUUID()}`;
const passwordHash = createPasswordHash(password);
const sessionSecret = createHmac("sha256", randomBytes(32)).update(randomUUID()).digest("hex");

const webUser = {
  email: email.toLowerCase(),
  name,
  orgId,
  role,
  apiToken,
  passwordHash
};

const apiTokenRegistry = {
  [apiToken]: {
    org_id: orgId,
    role,
    token_name: name
  }
};

console.log("CASHFLOW_SESSION_SECRET=");
console.log(sessionSecret);
console.log("");
console.log("CASHFLOW_WEB_USERS_JSON=");
console.log(JSON.stringify([webUser]));
console.log("");
console.log("CASHFLOW_AUTH_TOKENS_JSON=");
console.log(JSON.stringify(apiTokenRegistry));
