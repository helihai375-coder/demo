// wcdb_bridge.js - Node.js bridge to WeFlow wcdb_api.dll via koffi
// Usage: node wcdb_bridge.js [output.txt]

const path = require("path");
const fs = require("fs");

// ===== Configuration =====
const CONFIG = {
  dllDir: "E:/weflow/resources/resources/wcdb/win32/x64",
  accountDir: "C:/Users/rog/xwechat_files/wxid_heowxthl0fpn12_89f3",
  hexKey: "cfe197ff9df54793b81f60f8bc6d4117f436d637729f4c0eb3ff36f4e1dc87d2",
  wxid: "wxid_heowxthl0fpn12",
  targetGroup: "7736769229@chatroom",
  resourcesPath: "E:/weflow/resources/resources",
  limit: 50,
};

// ===== Setup env (mimic WeFlow exportWorker) =====
process.env.WEFLOW_WORKER = "1";
process.env.WCDB_RESOURCES_PATH = CONFIG.resourcesPath;
process.env.WEFLOW_USER_DATA_PATH = CONFIG.resourcesPath;
process.env.WEFLOW_CONFIG_CWD = CONFIG.resourcesPath;
process.env.WEFLOW_PROJECT_NAME = "WeFlow";

// ===== Load koffi from WeFlow =====
const koffi = require("E:/weflow/resources/app.asar.unpacked/node_modules/koffi");

// ===== Load DLLs =====
const dllDir = CONFIG.dllDir;
const wcdbDll = path.join(dllDir, "WCDB.dll");
const apiDll = path.join(dllDir, "wcdb_api.dll");

console.log("Loading WCDB.dll...");
koffi.load(wcdbDll);
console.log("Loading wcdb_api.dll...");
const lib = koffi.load(apiDll);

// ===== Bind functions =====
console.log("Binding functions...");

const InitProtection = lib.func("int32 InitProtection(const char* resourcePath)");
const wcdb_init = lib.func("int32 wcdb_init()");
const wcdb_shutdown = lib.func("int32 wcdb_shutdown()");
const wcdb_open_account = lib.func("int32 wcdb_open_account(const char* path, const char* key, _Out_ int64* handle)");
const wcdb_close_account = lib.func("int32 wcdb_close_account(int64 handle)");
const wcdb_free_string = lib.func("void wcdb_free_string(void* ptr)");
const wcdb_set_my_wxid = lib.func("int32 wcdb_set_my_wxid(int64 handle, const char* wxid)");
const wcdb_get_sessions = lib.func("int32 wcdb_get_sessions(int64 handle, _Out_ void** outJson)");
const wcdb_get_messages = lib.func("int32 wcdb_get_messages(int64 handle, const char* sessionId, int32 limit, int32 offset, _Out_ void** outJson)");

let wcdb_get_logs = null;
try { wcdb_get_logs = lib.func("int32 wcdb_get_logs(_Out_ void** outJson)"); } catch (e) {}

// ===== Helpers =====
function decodeJson(outPtr) {
  if (!outPtr || !outPtr[0]) return null;
  try {
    const str = koffi.decode(outPtr[0], "char", -1);
    return str || null;
  } finally {
    if (outPtr[0]) wcdb_free_string(outPtr[0]);
    outPtr[0] = null;
  }
}

function mapError(code) {
  const m = {};
  m[0] = "Success";
  m[-1] = "Param error";
  m[-2] = "Key error";
  m[-3] = "DB open fail";
  m[-4] = "DB open fail";
  m[-5] = "Query fail";
  m[-6] = "Not initialized";
  m[-1005] = "Open init error";
  m[-1006] = "WCDB init error";
  m[-2201] = "Protection: missing resource";
  m[-2202] = "Protection: invalid";
  return m[code] || ("Code " + code);
}

function printLogs() {
  if (!wcdb_get_logs) return;
  try {
    const out = [null];
    const r = wcdb_get_logs(out);
    if (r === 0) {
      const txt = decodeJson(out);
      if (txt) console.log("[WCDB LOGS]\n" + txt);
    }
  } catch (e) {}
}

// ===== Find session.db =====
function findSessionDb(accountDir) {
  const dbStorage = path.join(accountDir, "db_storage");
  function search(dir, depth) {
    if (depth > 5) return null;
    try {
      for (const entry of fs.readdirSync(dir)) {
        if (entry.toLowerCase() === "session.db") {
          const p = path.join(dir, entry);
          if (fs.statSync(p).isFile()) return p;
        }
        const full = path.join(dir, entry);
        if (fs.statSync(full).isDirectory()) {
          const found = search(full, depth + 1);
          if (found) return found;
        }
      }
    } catch (e) {}
    return null;
  }
  return search(dbStorage, 0);
}

// ===== Main =====
async function main() {
  console.log("==================================================");
  console.log("WCDB Bridge (Node.js) - Direct WeChat DB Reader");
  console.log("==================================================");

  // Step 1: InitProtection
  console.log("\n[1/4] InitProtection...");
  const protectPaths = [
    CONFIG.resourcesPath,
    dllDir,
    path.dirname(dllDir),
    "E:/weflow/resources",
    "E:/weflow",
  ];
  let protectOk = false;
  for (const p of protectPaths) {
    const code = InitProtection(p);
    console.log("  InitProtection(" + p + "): " + code + " (" + mapError(code) + ")");
    if (code === 0) { protectOk = true; break; }
  }
  if (!protectOk) {
    console.log("[WARN] InitProtection did not return 0, continuing...");
  }

  // Step 2: wcdb_init
  console.log("\n[2/4] wcdb_init...");
  const initCode = wcdb_init();
  console.log("  wcdb_init: " + initCode + " (" + mapError(initCode) + ")");

  if (initCode !== 0) {
    printLogs();
    console.log("\n[FAIL] Cannot initialize WCDB.");
    console.log("The DLL likely requires WeFlow Electron runtime context.");
    console.log("FALLBACK: Use WeFlow GUI to export, then run wechat_accounting.py");
    return 1;
  }
  console.log("  OK");

  // Step 3: wcdb_open_account
  console.log("\n[3/4] wcdb_open_account...");
  const sessionDb = findSessionDb(CONFIG.accountDir);
  console.log("  Account dir: " + CONFIG.accountDir);
  console.log("  Session DB:  " + (sessionDb || "NOT FOUND"));

  if (!sessionDb) {
    console.log("[FAIL] session.db not found");
    return 1;
  }

  const handleOut = [0];
  const openCode = wcdb_open_account(sessionDb, CONFIG.hexKey, handleOut);
  const handle = handleOut[0];
  console.log("  wcdb_open_account: " + openCode + " (" + mapError(openCode) + ")");
  console.log("  Handle: " + handle);

  if (openCode !== 0 || handle <= 0) {
    printLogs();
    console.log("[FAIL] Cannot open database");
    return 1;
  }

  try {
    wcdb_set_my_wxid(handle, CONFIG.wxid);
    console.log("  wcdb_set_my_wxid: OK");
  } catch (e) {
    console.log("  wcdb_set_my_wxid: " + e.message);
  }

  // Step 4: Get messages
  console.log("\n[4/4] Fetching messages for: " + CONFIG.targetGroup);

  // List sessions
  try {
    const sessOut = [null];
    const sessCode = wcdb_get_sessions(handle, sessOut);
    if (sessCode === 0) {
      const sessJson = decodeJson(sessOut);
      if (sessJson) {
        const sessions = JSON.parse(sessJson);
        console.log("  Total sessions: " + sessions.length);
        for (const s of sessions.slice(0, 10)) {
          const sid = s.username || s.sessionId || "";
          const name = s.displayName || s.nickname || "";
          const marker = sid.includes(CONFIG.targetGroup) ? " <<< TARGET" : "";
          console.log("    [" + sid.substring(0, 25) + "] " + name.substring(0, 15) + marker);
        }
      }
    }
  } catch (e) {
    console.log("  Sessions: " + e.message);
  }

  // Fetch messages
  let offset = 0;
  let allMessages = [];
  let maxBatches = 40;

  while (maxBatches-- > 0) {
    const out = [null];
    const code = wcdb_get_messages(handle, CONFIG.targetGroup, CONFIG.limit, offset, out);
    const jsonStr = decodeJson(out);

    if (code !== 0) {
      console.log("  offset=" + offset + ": code=" + code + " (" + mapError(code) + ")");
      printLogs();
      break;
    }
    if (!jsonStr) {
      console.log("  offset=" + offset + ": empty");
      break;
    }

    try {
      const batch = JSON.parse(jsonStr);
      if (Array.isArray(batch)) {
        allMessages.push(...batch);
        console.log("  offset=" + offset + ": +" + batch.length + " (total=" + allMessages.length + ")");
        if (batch.length < CONFIG.limit) break;
        offset += batch.length;
      } else {
        console.log("  Unexpected type: " + typeof batch);
        break;
      }
    } catch (e) {
      console.log("  JSON error at offset " + offset + ": " + e.message);
      break;
    }
  }

  wcdb_close_account(handle);
  console.log("\n  Closed. Total: " + allMessages.length + " messages");

  const outputFile = process.argv[2] || "group_chat_output.txt";
  if (allMessages.length > 0) {
    const lines = allMessages.map(function(msg) {
      if (typeof msg === "object") {
        const ts = msg.createTime || msg.create_time || "";
        const sender = msg.senderUsername || msg.sender_username ||
                       msg.displayName || msg.display_name || "?";
        const content = msg.parsedContent || msg.parsed_content ||
                        msg.content || msg.str_content || "";
        return "[" + ts + "] " + sender + ": " + content;
      }
      return String(msg);
    });
    fs.writeFileSync(outputFile, lines.join("\n"), "utf-8");
    console.log("  Saved to: " + outputFile);
  } else {
    console.log("  [WARN] No messages extracted.");
  }

  wcdb_shutdown();
  return 0;
}

main().then(function(code) { process.exit(code); }).catch(function(e) {
  console.error("Fatal:", e);
  process.exit(1);
});
