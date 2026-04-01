import argparse
import json
import mimetypes
import os
import platform
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib import error, request
from uuid import uuid4


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class AgentConfig:
    api_base_url: str
    api_token: str
    org_id: str
    machine_name: str
    watch_path: Path
    source_type: str
    source_hint: str
    allowed_extensions: tuple[str, ...]
    poll_seconds: int
    heartbeat_seconds: int
    stable_file_seconds: int
    archive_path: Optional[Path]
    state_path: Path


def build_config() -> AgentConfig:
    script_dir = Path(__file__).resolve().parent
    load_env_file(script_dir / ".env")

    api_base_url = os.getenv("DESKTOP_AGENT_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    api_token = os.getenv("DESKTOP_AGENT_API_TOKEN", "").strip()
    org_id = os.getenv("DESKTOP_AGENT_ORG_ID", "").strip()
    machine_name = os.getenv("DESKTOP_AGENT_MACHINE_NAME", "").strip() or platform.node() or "cashflow-desktop-agent"
    watch_path = Path(os.path.expanduser(os.getenv("DESKTOP_AGENT_WATCH_PATH", "~/Desktop/cashflow-exports"))).resolve()
    source_type = os.getenv("DESKTOP_AGENT_SOURCE_TYPE", "auto").strip().lower() or "auto"
    source_hint = os.getenv("DESKTOP_AGENT_SOURCE_HINT", "auto").strip().lower() or "auto"
    allowed_extensions = tuple(
        ext.strip().lower() for ext in os.getenv("DESKTOP_AGENT_ALLOWED_EXTENSIONS", ".csv,.xlsx,.xls,.xml").split(",") if ext.strip()
    )
    poll_seconds = max(2, int(os.getenv("DESKTOP_AGENT_POLL_SECONDS", "5")))
    heartbeat_seconds = max(15, int(os.getenv("DESKTOP_AGENT_HEARTBEAT_SECONDS", "60")))
    stable_file_seconds = max(1, int(os.getenv("DESKTOP_AGENT_STABLE_FILE_SECONDS", "3")))
    archive_path_value = os.getenv("DESKTOP_AGENT_ARCHIVE_PATH", "").strip()
    archive_path = Path(os.path.expanduser(archive_path_value)).resolve() if archive_path_value else None
    state_path = Path.home() / ".cashflow-desktop-agent" / "state.json"

    if not api_token:
        raise RuntimeError("DESKTOP_AGENT_API_TOKEN is required.")
    if not org_id:
        raise RuntimeError("DESKTOP_AGENT_ORG_ID is required.")

    return AgentConfig(
        api_base_url=api_base_url,
        api_token=api_token,
        org_id=org_id,
        machine_name=machine_name,
        watch_path=watch_path,
        source_type=source_type,
        source_hint=source_hint,
        allowed_extensions=allowed_extensions,
        poll_seconds=poll_seconds,
        heartbeat_seconds=heartbeat_seconds,
        stable_file_seconds=stable_file_seconds,
        archive_path=archive_path,
        state_path=state_path,
    )


def log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def load_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {"files": {}}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"files": {}}


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def json_request(method: str, url: str, token: str, payload: Optional[dict] = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc
    return json.loads(raw.decode("utf-8")) if raw else {}


def multipart_request(url: str, token: str, form_fields: Dict[str, str], file_path: Path) -> dict:
    boundary = f"----CashflowDesktopAgent{uuid4().hex}"
    body = bytearray()
    for key, value in form_fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode("utf-8")
    )
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = request.Request(url, data=bytes(body), headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed with {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"POST {url} failed: {exc.reason}") from exc
    return json.loads(raw.decode("utf-8")) if raw else {}


def heartbeat(config: AgentConfig, agent_id: str, message: str) -> dict:
    payload = {
        "status": "online",
        "watched_path": str(config.watch_path),
        "message": message,
    }
    return json_request(
        "POST",
        f"{config.api_base_url}/v1/desktop-agents/{agent_id}/heartbeat",
        config.api_token,
        payload,
    )


def register_agent(config: AgentConfig, state: dict) -> str:
    existing_agent_id = state.get("agent_id")
    if existing_agent_id:
        try:
            heartbeat(config, existing_agent_id, "Reconnected and watching for files.")
            return existing_agent_id
        except RuntimeError:
            log("Saved desktop agent id is no longer valid. Registering a fresh agent.")

    payload = {"org_id": config.org_id, "machine_name": config.machine_name}
    response = json_request("POST", f"{config.api_base_url}/v1/desktop-agents/register", config.api_token, payload)
    agent_id = response["agent_id"]
    state["agent_id"] = agent_id
    return agent_id


def file_fingerprint(file_path: Path) -> str:
    stat = file_path.stat()
    return f"{stat.st_size}:{stat.st_mtime_ns}"


def infer_source_type(config: AgentConfig, file_path: Path) -> str:
    if config.source_type != "auto":
        return config.source_type
    lower_name = file_path.name.lower()
    if file_path.suffix.lower() == ".xml":
        return "tally"
    tally_tokens = ("tally", "receivable", "payable", "debtor", "creditor", "ledger")
    return "tally" if any(token in lower_name for token in tally_tokens) else "manual"


def infer_source_hint(config: AgentConfig, file_path: Path) -> str:
    if config.source_hint != "auto":
        return config.source_hint
    lower_name = file_path.name.lower()
    payable_tokens = ("payable", "creditor", "vendor")
    return "payables" if any(token in lower_name for token in payable_tokens) else "receivables"


def should_upload(config: AgentConfig, state: dict, file_path: Path) -> bool:
    if not file_path.is_file():
        return False
    if file_path.suffix.lower() not in config.allowed_extensions:
        return False
    if file_path.name.startswith("."):
        return False
    age_seconds = max(0.0, time.time() - file_path.stat().st_mtime)
    if age_seconds < config.stable_file_seconds:
        return False
    fingerprint = file_fingerprint(file_path)
    stored = state.get("files", {}).get(str(file_path))
    return stored is None or stored.get("fingerprint") != fingerprint


def upload_file(config: AgentConfig, state: dict, agent_id: str, file_path: Path) -> None:
    source_type = infer_source_type(config, file_path)
    form_fields = {
        "org_id": config.org_id,
        "source_type": source_type,
        "desktop_agent_id": agent_id,
    }
    if source_type == "tally":
        form_fields["source_hint"] = infer_source_hint(config, file_path)

    response = multipart_request(f"{config.api_base_url}/v1/imports", config.api_token, form_fields, file_path)
    import_batch = response["import_batch"]
    fingerprint = file_fingerprint(file_path)
    state.setdefault("files", {})[str(file_path)] = {
        "fingerprint": fingerprint,
        "import_batch_id": import_batch["import_batch_id"],
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if config.archive_path is not None:
        config.archive_path.mkdir(parents=True, exist_ok=True)
        archived_path = config.archive_path / file_path.name
        shutil.move(str(file_path), str(archived_path))
        state["files"][str(archived_path)] = state["files"].pop(str(file_path))
    log(
        "Uploaded {name} as {source_type} with batch {batch_id}.".format(
            name=file_path.name,
            source_type=source_type,
            batch_id=import_batch["import_batch_id"],
        )
    )


def candidate_files(config: AgentConfig) -> list[Path]:
    config.watch_path.mkdir(parents=True, exist_ok=True)
    return sorted((path for path in config.watch_path.iterdir() if path.is_file()), key=lambda path: path.name.lower())


def run_loop(config: AgentConfig, *, once: bool) -> int:
    state = load_state(config.state_path)
    agent_id = register_agent(config, state)
    save_state(config.state_path, state)
    log(f"Desktop agent {agent_id} is watching {config.watch_path}.")

    next_heartbeat_at = 0.0
    while True:
        current_time = time.time()
        if current_time >= next_heartbeat_at:
            heartbeat(config, agent_id, "Watching for new exports.")
            next_heartbeat_at = current_time + config.heartbeat_seconds

        changed_any = False
        for file_path in candidate_files(config):
            if not should_upload(config, state, file_path):
                continue
            upload_file(config, state, agent_id, file_path)
            changed_any = True
        if changed_any:
            save_state(config.state_path, state)

        if once:
            return 0
        time.sleep(config.poll_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cashflow OS desktop sync agent")
    parser.add_argument("--once", action="store_true", help="Run one scan pass and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = build_config()
        return run_loop(config, once=args.once)
    except KeyboardInterrupt:
        log("Desktop agent stopped.")
        return 0
    except Exception as exc:
        log(f"Desktop agent failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
