import time
import json
import random
import threading
import sys
from locust import HttpUser, task, between, events
import websocket

# Real-world campus boundaries (IIT Bombay coordinates)
LAT_MIN, LAT_MAX = 19.1300, 19.1400
LON_MIN, LON_MAX = 72.9100, 72.9200

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
]

MOCK_CREDENTIAL_ID = "bW9jay1jcmVkZW50aWFsLTEyMzQ"

class StudentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        print("Starting user login...", flush=True)
        response = self.client.post("/api/auth/login", json={
            "email": "deepika.chopra0@scholarlab.edu",
            "password": "student123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            print(f"Login successful for deepika.chopra0, token: {self.token[:10]}...", flush=True)
            
            # Connect to WebSocket
            try:
                host = self.host.replace("http://", "ws://").replace("https://", "wss://")
                ws_url = f"{host}/api/ws/student?token={self.token}"
                print(f"Connecting to WS: {ws_url}", flush=True)
                self.ws = websocket.create_connection(ws_url, timeout=2)
                self.ws_thread = threading.Thread(target=self.receive_ws)
                self.ws_thread.daemon = True
                self.ws_thread.start()
                print("WS Connected!", flush=True)
            except Exception as e:
                print(f"WS error: {e}", flush=True)
        else:
            print(f"Login failed: {response.status_code} {response.text}", flush=True)
            self.token = None

    def receive_ws(self):
        while True:
            try:
                if hasattr(self, 'ws'):
                    self.ws.recv()
                else:
                    break
            except Exception:
                break

    def on_stop(self):
        if hasattr(self, 'ws'):
            try:
                self.ws.close()
            except:
                pass

    @task
    def submit_attendance(self):
        if not self.token:
            return
            
        # 1. Generate Auth Options (Creates Challenge in DB)
        options_resp = self.client.post("/api/auth/webauthn/generate-authentication-options", json={
            "email": "deepika.chopra0@scholarlab.edu"
        }, name="/webauthn/generate-authentication-options")
        
        if options_resp.status_code != 200:
            print(f"Options failed: {options_resp.status_code}", flush=True)
            return

        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/json"
        }
        
        # 2. Submit Mock Signed Payload
        # Note: The signature won't mathematically match the mock public key, 
        # but the endpoint will perform the verification logic before failing with 400/403.
        payload = {
            "session_id": "session-1",
            "geofence_id": "64bcde1234567890abcdef12", 
            "latitude": random.uniform(LAT_MIN, LAT_MAX),
            "longitude": random.uniform(LON_MIN, LON_MAX),
            "bssid": "00:14:22:01:23:45",
            "cryptographic_signature": {
                "id": MOCK_CREDENTIAL_ID,
                "rawId": MOCK_CREDENTIAL_ID,
                "response": {
                    "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MBAAAABQ==",
                    "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiaGFja21lIiwiT3JpZ2luIjoiaHR0cDovL2xvY2FsaG9zdDo1MTczIiwiY3Jvc3NPcmlnaW4iOmZhbHNlfQ==",
                    "signature": "MEYCIQCN2f_J4GZ_VqC...",
                    "userHandle": ""
                },
                "type": "public-key",
                "clientExtensionResults": {}
            }
        }
        
        with self.client.post("/api/attendance/verify", json=payload, headers=headers, catch_response=True, name="/attendance/verify") as response:
            if response.status_code in [200, 403, 400]:
                response.success() 
            else:
                response.failure(f"Unexpected status: {response.status_code}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if environment.stats.total.num_requests > 0:
        p95 = environment.stats.total.get_response_time_percentile(0.95)
        print(f"\n{'='*50}\nIEEE Evaluation Metrics\n{'='*50}", flush=True)
        print(f"Verification Endpoint 95th Percentile Latency (P95): {p95} ms", flush=True)
        print(f"{'='*50}\n", flush=True)
