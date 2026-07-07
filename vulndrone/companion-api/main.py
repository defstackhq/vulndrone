import base64
import ipaddress
import json
import os
import pickle
import threading
import time
from urllib.parse import urlsplit

import jwt
import requests
from fastapi import FastAPI, HTTPException, Header, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymavlink import mavutil

SITL_HOST = os.environ.get("SITL_HOST", "sitl")
SITL_PORT = int(os.environ.get("SITL_PORT", 14550))

app = FastAPI(title="Companion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DroneLink:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.master = None
        self.lock = threading.Lock()
        self.telemetry = {
            "lat": 0.0,
            "lon": 0.0,
            "alt": 0.0,
            "armed": False,
            "connected": False,
        }

    def connect(self):
        conn_str = f"udpin:0.0.0.0:{self.port}"
        self.master = mavutil.mavlink_connection(conn_str)
        self.master.wait_heartbeat(timeout=30)
        with self.lock:
            self.telemetry["connected"] = True

    def run(self):
        while True:
            try:
                if self.master is None:
                    self.connect()

                msg = self.master.recv_match(blocking=True, timeout=5)
                if msg is None:
                    continue

                msg_type = msg.get_type()

                if msg_type == "GLOBAL_POSITION_INT":
                    with self.lock:
                        self.telemetry["lat"] = msg.lat / 1e7
                        self.telemetry["lon"] = msg.lon / 1e7
                        self.telemetry["alt"] = msg.relative_alt / 1000.0

                elif msg_type == "HEARTBEAT":
                    with self.lock:
                        self.telemetry["armed"] = bool(
                            msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                        )

            except Exception:
                with self.lock:
                    self.telemetry["connected"] = False
                self.master = None
                time.sleep(3)

    def get_telemetry(self):
        with self.lock:
            return dict(self.telemetry)

    def send_arm(self, value):
        if self.master is None:
            raise RuntimeError("not connected to sitl")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1 if value else 0,
            0, 0, 0, 0, 0, 0,
        )

    def send_takeoff(self, altitude):
        if self.master is None:
            raise RuntimeError("not connected to sitl")
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, 0, 0, 0,
            altitude,
        )


link = DroneLink(SITL_HOST, SITL_PORT)
threading.Thread(target=link.run, daemon=True).start()

JWT_SECRET = "dronekey"

USERS = {
    "pilot_amy": {"password": "amy2025", "role": "pilot"},
    "pilot_ravi": {"password": "ravi2025", "role": "pilot"},
}


def require_auth(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="invalid token")
    return payload


def require_superadmin(payload: dict = Depends(require_auth)):
    if payload.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="insufficient privileges")
    return payload


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
def login(req: LoginRequest):
    user = USERS.get(req.username)
    if user is None or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = jwt.encode({"sub": req.username, "role": user["role"]}, JWT_SECRET, algorithm="HS256")
    return {"token": token, "role": user["role"]}


@app.get("/public/notice")
def public_notice():
    return {
        "posted": "2026-06-30",
        "message": (
            "Reminder to pilot_amy and pilot_ravi to file post flight reports before the "
            "Friday sync. Contact ops if your access needs a reset. Also, integrations team, "
            "please stop joking that the webhook sync feature has a mind of its own, it is "
            "starting to spook the new hires."
        ),
    }


@app.get("/status")
def status(payload: dict = Depends(require_auth)):
    t = link.get_telemetry()
    return {
        "service": "companion-api",
        "sitl_host": SITL_HOST,
        "sitl_port": SITL_PORT,
        "connected": t["connected"],
    }


@app.get("/telemetry")
def telemetry(payload: dict = Depends(require_auth)):
    return link.get_telemetry()


class ArmRequest(BaseModel):
    value: bool


@app.post("/command/arm")
def command_arm(req: ArmRequest):
    try:
        link.send_arm(req.value)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"result": "sent", "armed": req.value}


class TakeoffRequest(BaseModel):
    altitude: float


@app.post("/command/takeoff")
def command_takeoff(req: TakeoffRequest):
    try:
        link.send_takeoff(req.altitude)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"result": "sent", "altitude": req.altitude}


MISSIONS = {
    1: {
        "owner": "pilot_amy",
        "name": "Warehouse perimeter check",
        "waypoints": [[12.9716, 77.5946], [12.9720, 77.5950]],
    },
    2: {
        "owner": "pilot_ravi",
        "name": "Rooftop solar inspection",
        "waypoints": [[12.9352, 77.6146], [12.9360, 77.6150]],
    },
    3: {
        "owner": "pilot_sara",
        "name": "Restricted site survey, internal use only",
        "waypoints": [[12.9611, 77.6387], [12.9615, 77.6390]],
    },
}


@app.get("/missions")
def list_missions(payload: dict = Depends(require_auth)):
    owner = payload.get("sub")
    return {mid: m for mid, m in MISSIONS.items() if m["owner"] == owner}


@app.get("/missions/{mission_id}")
def get_mission(mission_id: int, payload: dict = Depends(require_auth)):
    mission = MISSIONS.get(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="mission not found")
    return mission


LOG_DIR = "/app/flight_logs"
os.makedirs(LOG_DIR, exist_ok=True)

SAMPLE_LOGS = {
    "flight_2026_06_01.log": "takeoff at 09:14, landed at 09:26, no anomalies",
    "flight_2026_06_02.log": "takeoff at 14:02, gps drift logged at 14:07",
}

for name, content in SAMPLE_LOGS.items():
    path = os.path.join(LOG_DIR, name)
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(content)

SECRET_PATH = "/app/internal_notes.txt"
if not os.path.exists(SECRET_PATH):
    with open(SECRET_PATH, "w") as f:
        f.write("internal note, admin override code is 4471, do not expose this file over http")


@app.get("/logs/{filename:path}")
def get_log(filename: str, payload: dict = Depends(require_superadmin)):
    path = os.path.join(LOG_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="log not found")
    with open(path, "r") as f:
        content = f.read()
    return {"filename": filename, "content": content}


BLOCKED_HOSTS = {"localhost", "127.0.0.1", "169.254.169.254", "0.0.0.0"}

INTERNAL_SERVICE_TREE = {
    "/": {"paths": ["/metadata", "/internal"]},
    "/metadata": {},
    "/internal": {"paths": ["/internal/config", "/internal/routes"]},
    "/internal/config": {
        "region": "ap-south-1",
        "sync_protocol": "v2",
        "identity_scope": "superadmin",
        "token_bootstrap": "true",
        "archive_manifest": "internal_notes.txt",
    },
    "/internal/routes": {
        "routes": [
            {"path": "/v2/health"},
            {"path": "/v2/metrics"},
            {"path": "/v2/config", "headers": ["x-user-id", "x-generate-token"]},
        ]
    },
}


def alternate_ip_forms(host):
    forms = []
    try:
        if host.lower().startswith("0x"):
            forms.append(str(ipaddress.IPv4Address(int(host, 16))))
    except (ValueError, ipaddress.AddressValueError):
        pass
    try:
        forms.append(str(ipaddress.IPv4Address(int(host))))
    except (ValueError, ipaddress.AddressValueError):
        pass
    try:
        octets = host.split(".")
        if len(octets) == 4 and all(o.startswith("0") and len(o) > 1 for o in octets):
            forms.append(".".join(str(int(o, 8)) for o in octets))
    except ValueError:
        pass
    return forms


def internal_service_lookup(path):
    normalized = path if path else "/"
    if normalized != "/" and normalized.endswith("/"):
        normalized = normalized[:-1]
    return INTERNAL_SERVICE_TREE.get(normalized, {"error": "not found"})


class ExportRequest(BaseModel):
    webhook_url: str


@app.post("/integrations/export-telemetry")
def export_telemetry(req: ExportRequest, payload: dict = Depends(require_auth)):
    parsed = urlsplit(req.webhook_url)
    host = parsed.hostname or ""

    if host.lower() in BLOCKED_HOSTS:
        raise HTTPException(status_code=400, detail="requests to internal or loopback hosts are blocked")

    if "169.254.169.254" in alternate_ip_forms(host):
        body = internal_service_lookup(parsed.path)
        return {
            "sent_to": req.webhook_url,
            "remote_status": 200,
            "remote_body_preview": json.dumps(body),
        }

    data = link.get_telemetry()
    try:
        resp = requests.post(req.webhook_url, json=data, timeout=5)
        status_code = resp.status_code
        if resp.headers.get("x-sync-format") == "pickle":
            try:
                result = pickle.loads(base64.b64decode(resp.content))
                sync_ack = f"you successfully hacked a drone fleet. ground station replied: {result}"
            except Exception as e:
                sync_ack = f"sync parse error: {e}"
            body_preview = sync_ack
        else:
            body_preview = resp.text[:500]
    except Exception as e:
        body_preview = str(e)
        status_code = None

    return {
        "sent_to": req.webhook_url,
        "remote_status": status_code,
        "remote_body_preview": body_preview,
    }


STREAM_API_KEY = "sk_live_51J7f9aKcNhx8rQ2mZpLk3vDdT6yUxWnA"



@app.get("/video/stream-url")
def video_stream_url(payload: dict = Depends(require_auth)):
    return {
        "stream_url": f"rtsp://stream.dronefeed.local/live?key={STREAM_API_KEY}",
        "provider": "dronefeed",
    }


FIRMWARE_DIR = "/app/firmware"
os.makedirs(FIRMWARE_DIR, exist_ok=True)


@app.post("/firmware/upload")
async def firmware_upload(file: UploadFile = File(...), payload: dict = Depends(require_superadmin)):
    dest = os.path.join(FIRMWARE_DIR, file.filename)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"result": "firmware staged", "filename": file.filename, "size": len(content)}


@app.get("/firmware/list")
def firmware_list(payload: dict = Depends(require_superadmin)):
    return {"files": os.listdir(FIRMWARE_DIR)}


@app.post("/admin/reset-fleet")
def admin_reset_fleet(payload: dict = Depends(require_superadmin)):
    return {"result": "fleet reset queued", "by": payload.get("sub")}


@app.get("/v2/config")
def v2_config(
    payload: dict = Depends(require_auth),
    x_user_id: str = Header(None),
    x_generate_token: str = Header(None),
):
    if x_user_id == "superadmin" and x_generate_token == "true":
        token = jwt.encode({"sub": "superadmin", "role": "superadmin"}, JWT_SECRET, algorithm="HS256")
        return {"token": token, "role": "superadmin"}
    return {"build": "2.4.1", "region": "ap-south-1", "telemetry_rate_hz": 5}
