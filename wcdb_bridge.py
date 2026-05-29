# -*- coding: utf-8 -*-
"""
wcdb_bridge.py - Python ctypes direct bridge to WeFlow wcdb_api.dll
Reads WeChat encrypted database, extracts group chat messages, outputs txt.

Key insight from WeFlow source: InitProtection() must be called BEFORE wcdb_init().
This is why CipherTalk failed with WeFlow DLLs.

Usage:
    python wcdb_bridge.py [output.txt]
"""
import ctypes
import os
import sys
import json
from ctypes import c_int32, c_int64, c_char_p, c_void_p, POINTER, byref, cdll

# ═══════════════ Configuration ═══════════════

DLL_DIR = r"E:\weflow\resources\resources\wcdb\win32\x64"
ACCOUNT_DIR = r"C:\Users\rog\xwechat_files\wxid_heowxthl0fpn12_89f3"
DB_STORAGE = os.path.join(ACCOUNT_DIR, "db_storage")
SESSION_DB = os.path.join(DB_STORAGE, "session", "session.db")
HEX_KEY = "cfe197ff9df54793b81f60f8bc6d4117f436d637729f4c0eb3ff36f4e1dc87d2"
WXID = "wxid_heowxthl0fpn12"
TARGET_GROUP = "7736769229@chatroom"

# ═══════════════ DLL Loading ═══════════════

def load_dlls():
    """Load WCDB.dll first (dependency), then wcdb_api.dll."""
    wcdb_path = os.path.join(DLL_DIR, "WCDB.dll")
    api_path = os.path.join(DLL_DIR, "wcdb_api.dll")

    if not os.path.exists(wcdb_path):
        raise FileNotFoundError(f"WCDB.dll not found: {wcdb_path}")
    if not os.path.exists(api_path):
        raise FileNotFoundError(f"wcdb_api.dll not found: {api_path}")

    os.environ["PATH"] = DLL_DIR + ";" + os.environ.get("PATH", "")

    wcdb_lib = cdll.LoadLibrary(wcdb_path)
    print(f"[OK] Loaded WCDB.dll")

    api_lib = cdll.LoadLibrary(api_path)
    print(f"[OK] Loaded wcdb_api.dll")

    return api_lib

# ═══════════════ Function Bindings ═══════════════

def bind_functions(lib):
    """Bind all needed native functions with correct signatures."""

    lib.InitProtection.argtypes = [c_char_p]
    lib.InitProtection.restype = c_int32

    lib.wcdb_init.argtypes = []
    lib.wcdb_init.restype = c_int32

    lib.wcdb_shutdown.argtypes = []
    lib.wcdb_shutdown.restype = c_int32

    lib.wcdb_open_account.argtypes = [c_char_p, c_char_p, POINTER(c_int64)]
    lib.wcdb_open_account.restype = c_int32

    lib.wcdb_close_account.argtypes = [c_int64]
    lib.wcdb_close_account.restype = c_int32

    try:
        lib.wcdb_set_my_wxid.argtypes = [c_int64, c_char_p]
        lib.wcdb_set_my_wxid.restype = c_int32
        print("[OK] wcdb_set_my_wxid bound")
    except AttributeError:
        print("[WARN] wcdb_set_my_wxid not available")

    try:
        lib.wcdb_get_sessions.argtypes = [c_int64, POINTER(c_void_p)]
        lib.wcdb_get_sessions.restype = c_int32
        print("[OK] wcdb_get_sessions bound")
    except AttributeError:
        print("[WARN] wcdb_get_sessions not available")

    lib.wcdb_get_messages.argtypes = [c_int64, c_char_p, c_int32, c_int32, POINTER(c_void_p)]
    lib.wcdb_get_messages.restype = c_int32

    lib.wcdb_free_string.argtypes = [c_void_p]
    lib.wcdb_free_string.restype = None

    try:
        lib.wcdb_get_logs.argtypes = [POINTER(c_void_p)]
        lib.wcdb_get_logs.restype = c_int32
    except AttributeError:
        pass

    return lib

# ═══════════════ Core Operations ═══════════════

def decode_result(lib, out_ptr):
    """Decode a C string from void** output and free it."""
    if not out_ptr or not out_ptr[0]:
        return None
    raw = ctypes.cast(out_ptr[0], c_char_p).value
    result = raw.decode("utf-8", errors="replace") if raw else None
    lib.wcdb_free_string(out_ptr[0])
    out_ptr[0] = None
    return result


def map_error(code):
    """Map WCDB error codes to human-readable strings."""
    errors = {
        0: "Success",
        -1: "Parameter error",
        -2: "Key error",
        -3: "Database open failure",
        -4: "Database open failure",
        -5: "Query execution failure",
        -6: "WCDB not initialized",
        -7: "Message schema mismatch",
        -1005: "Open account init error",
        -1006: "WCDB init error",
        -2201: "Protection: missing resource",
        -2202: "Protection: invalid resource",
        -3001: "db_storage not found",
        -3002: "session.db not found",
        -3003: "Invalid handle",
    }
    return errors.get(code, f"Unknown error ({code})")


def print_logs(lib):
    """Print WCDB internal logs for diagnostics."""
    try:
        out = c_void_p(None)
        lib.wcdb_get_logs(byref(out))
        log_text = decode_result(lib, byref(out))
        if log_text:
            print(f"[WCDB LOGS]\n{log_text}")
    except Exception:
        pass


def run():
    print("=" * 50)
    print("WCDB Bridge - Direct WeChat Database Reader")
    print("=" * 50)

    # Step 1: Load DLLs
    print("\n[1/5] Loading DLLs...")
    lib = load_dlls()
    lib = bind_functions(lib)

    # Step 2: InitProtection
    print("\n[2/5] InitProtection...")
    protect_code = lib.InitProtection(DLL_DIR.encode("utf-8"))
    print(f"  InitProtection({DLL_DIR}): {protect_code} ({map_error(protect_code)})")

    if protect_code != 0:
        alt_paths = [
            os.path.dirname(DLL_DIR),
            r"E:\weflow\resources\resources",
            r"E:\weflow\resources",
            r"E:\weflow",
        ]
        for p in alt_paths:
            code = lib.InitProtection(p.encode("utf-8"))
            print(f"  InitProtection({p}): {code} ({map_error(code)})")
            if code == 0:
                protect_code = 0
                break

    # Step 3: wcdb_init
    print("\n[3/5] wcdb_init...")
    init_code = lib.wcdb_init()
    print(f"  wcdb_init: {init_code} ({map_error(init_code)})")
    if init_code != 0:
        print_logs(lib)
        print("\n[FAIL] Cannot initialize WCDB. Is WeChat running and logged in?")
        return 1

    # Step 4: wcdb_open_account
    print("\n[4/5] wcdb_open_account...")
    print(f"  Session DB: {SESSION_DB}")
    print(f"  Key length: {len(HEX_KEY)}")

    if not os.path.exists(SESSION_DB):
        # Search for session.db
        found = False
        for root, dirs, files in os.walk(DB_STORAGE):
            for f in files:
                if f.lower() == "session.db":
                    SESS = os.path.join(root, f)
                    SESSION_DB = SESS
                    print(f"  Found session.db at: {SESS}")
                    found = True
                    break
            if found:
                break
        if not found:
            print(f"  [FAIL] session.db not found in {DB_STORAGE}")
            return 1

    handle = c_int64(0)
    open_code = lib.wcdb_open_account(
        SESSION_DB.encode("utf-8"),
        HEX_KEY.encode("utf-8"),
        byref(handle)
    )
    print(f"  wcdb_open_account: {open_code} ({map_error(open_code)})")
    print(f"  Handle: {handle.value}")

    if open_code != 0 or handle.value <= 0:
        print_logs(lib)
        print("\n[FAIL] Cannot open database. Check key and WeChat login state.")
        return 1

    # Set wxid
    try:
        lib.wcdb_set_my_wxid(handle, WXID.encode("utf-8"))
        print(f"  wcdb_set_my_wxid: OK")
    except Exception as e:
        print(f"  wcdb_set_my_wxid: {e}")

    # Step 5: Get sessions list
    print("\n[5/5] Getting messages...")

    try:
        out_sessions = c_void_p(None)
        code = lib.wcdb_get_sessions(handle, byref(out_sessions))
        if code == 0:
            sessions_json = decode_result(lib, byref(out_sessions))
            if sessions_json:
                sessions = json.loads(sessions_json)
                if isinstance(sessions, list):
                    print(f"  Total sessions: {len(sessions)}")
                    for s in sessions[:10]:
                        if isinstance(s, dict):
                            sid = s.get("username", s.get("sessionId", ""))
                            name = s.get("displayName", s.get("nickname", ""))
                            marker = " <<< TARGET" if TARGET_GROUP in str(sid) else ""
                            print(f"    [{sid[:30]}] {name[:20]}{marker}")
        else:
            print(f"  get_sessions returned code: {code}")
    except Exception as e:
        print(f"  Sessions listing failed: {e}")

    # Get messages for target group
    print(f"\n  Fetching messages for: {TARGET_GROUP}")
    offset = 0
    all_messages = []
    max_batches = 40  # safety limit

    while max_batches > 0:
        max_batches -= 1
        out_json = c_void_p(None)
        code = lib.wcdb_get_messages(
            handle,
            TARGET_GROUP.encode("utf-8"),
            c_int32(50),
            c_int32(offset),
            byref(out_json)
        )
        msg_text = decode_result(lib, byref(out_json))

        if code != 0:
            print(f"  offset={offset}: code={code} ({map_error(code)})")
            print_logs(lib)
            break

        if not msg_text:
            print(f"  offset={offset}: empty response")
            break

        try:
            batch = json.loads(msg_text)
            if isinstance(batch, list):
                count = len(batch)
                all_messages.extend(batch)
                print(f"  offset={offset}: +{count} (total={len(all_messages)})")
                if count < 50:
                    break
                offset += count
            else:
                print(f"  Unexpected response: {type(batch).__name__}")
                break
        except json.JSONDecodeError as e:
            print(f"  JSON parse error at offset {offset}: {e}")
            break

    # Close account
    lib.wcdb_close_account(handle)
    print(f"\n  Closed. Total: {len(all_messages)} messages")

    # Save to file
    output_file = sys.argv[1] if len(sys.argv) > 1 else "group_chat_output.txt"
    if all_messages:
        with open(output_file, "w", encoding="utf-8") as f:
            for msg in all_messages:
                if isinstance(msg, dict):
                    ts = msg.get("createTime", msg.get("create_time", ""))
                    sender = msg.get("senderUsername", msg.get("sender_username", 
                              msg.get("displayName", msg.get("display_name", "?"))))
                    content = msg.get("parsedContent", msg.get("parsed_content",
                                     msg.get("content", msg.get("str_content", ""))))
                    if ts and sender:
                        f.write(f"[{ts}] {sender}: {content}\n")
                    else:
                        f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        print(f"\n  Saved to: {output_file}")
    else:
        print("\n  [WARN] No messages extracted.")

    return 0

if __name__ == "__main__":
    sys.exit(run())
