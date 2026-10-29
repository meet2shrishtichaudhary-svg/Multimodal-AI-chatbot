import urllib.request
import urllib.error
import json
import time
import uuid

BASE_URL = "http://localhost:8000"

def run_test(name, fn):
    try:
        t0 = time.time()
        detail = fn()
        elapsed = time.time() - t0
        print(f"[PASS] {name} ({elapsed*1000:.1f}ms) -> {detail}")
        return True, detail
    except Exception as e:
        print(f"[FAIL] {name} -> Error: {e}")
        return False, str(e)

results = {}

# 1. Health Liveness
def test_live_health():
    req = urllib.request.Request(f"{BASE_URL}/api/health/live")
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert data["status"] == "alive"
        return "Liveness probe healthy (status=alive)"
results["Health Liveness (/api/health/live)"] = run_test("Health Liveness", test_live_health)

# 2. Health Readiness
def test_ready_health():
    req = urllib.request.Request(f"{BASE_URL}/api/health/ready")
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert data["status"] == "ready"
        return "Readiness probe healthy (database connected)"
results["Health Readiness (/api/health/ready)"] = run_test("Health Readiness", test_ready_health)

# 3. Observability Metrics
def test_metrics():
    req = urllib.request.Request(f"{BASE_URL}/api/health/metrics")
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert "uptime_seconds" in data
        assert "average_latency_ms" in data
        return f"Metrics tracked: uptime={data['uptime_seconds']}s, avg_latency={data['average_latency_ms']}ms"
results["Observability Metrics (/api/health/metrics)"] = run_test("Observability Metrics", test_metrics)

# 4. User Registration & Auth Context
test_email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
token_holder = {}

def test_auth_registration():
    payload = json.dumps({
        "email": test_email,
        "password": "Password123!",
        "full_name": "E2E Live Auditor"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/register",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 201
        data = json.loads(r.read())
        token_holder["token"] = data["access_token"]
        return f"Registered user {test_email} successfully with JWT"
results["User Registration (/api/auth/register)"] = run_test("User Registration", test_auth_registration)

# 5. User Login & Token Verification
def test_auth_login():
    payload = json.dumps({
        "email": test_email,
        "password": "Password123!"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert "access_token" in data
        return "Login successful, issued valid bearer token"
results["User Login (/api/auth/login)"] = run_test("User Login", test_auth_login)

# 6. Protected Profile Verification (/api/auth/me)
def test_auth_me():
    token = token_holder.get("token")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert data["email"] == test_email
        return f"Protected route authenticated: {data['email']}"
results["Protected Profile (/api/auth/me)"] = run_test("Protected Profile", test_auth_me)

# 7. Update User Profile & Persona
def test_update_profile():
    token = token_holder.get("token")
    payload = json.dumps({
        "full_name": "Auditor Principal",
        "bio": "Live QA Validation Specialist",
        "preferred_persona": "analyst",
        "custom_instructions": "Always respond with crisp operational telemetry."
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/profile",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="PATCH"
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert data["preferred_persona"] == "analyst"
        return "Updated profile persona to analyst with custom instructions"
results["User Profile Update (/api/auth/profile)"] = run_test("User Profile Update", test_update_profile)

# 8. Chat Response (Standard JSON)
conv_holder = {}
def test_chat_response():
    token = token_holder.get("token")
    payload = json.dumps({
        "message": "Hello Aura AI, please confirm system readiness.",
        "persona": "analyst"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        conv_holder["conv_id"] = data["conversation_id"]
        conv_holder["asst_msg_id"] = data["assistant_message"]["id"]
        assert len(data["assistant_message"]["content"]) > 0
        return f"Generated chat response in conversation {data['conversation_id']}"
results["Chat Response Standard (/api/chat)"] = run_test("Chat Response Standard", test_chat_response)

# 9. Chat Streaming (Server-Sent Events SSE)
def test_chat_streaming():
    token = token_holder.get("token")
    payload = json.dumps({
        "conversation_id": conv_holder.get("conv_id"),
        "message": "Compute 5 + 5 and explain in 1 sentence.",
        "persona": "analyst"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat/stream",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    tokens_received = 0
    with urllib.request.urlopen(req) as r:
        for line in r:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data: "):
                try:
                    event = json.loads(line_str[6:])
                    if event.get("type") == "token":
                        tokens_received += 1
                except:
                    pass
    assert tokens_received > 0
    return f"Successfully received {tokens_received} streaming SSE token chunks"
results["Chat Streaming SSE (/api/chat/stream)"] = run_test("Chat Streaming SSE", test_chat_streaming)

# 10. AI Image Generation
def test_image_generation():
    token = token_holder.get("token")
    payload = json.dumps({
        "prompt": "a futuristic glowing neon satellite orbiting earth in deep space",
        "conversation_id": conv_holder.get("conv_id")
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/image/generate",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert "image_url" in data
        assert data["format"] in ["image", "svg"]
        return f"Generated visual: {data['image_url']} (format={data['format']})"
results["AI Image Generation (/api/image/generate)"] = run_test("AI Image Generation", test_image_generation)

# 11. Smart Long-Term Memory (Create & Retrieve)
def test_smart_memory():
    token = token_holder.get("token")
    payload = json.dumps({
        "fact": "User is the Principal Quality Automation Lead.",
        "category": "professional"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/memory",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 201
        data = json.loads(r.read())
        mem_id = data["id"]

    # Verify listing
    get_req = urllib.request.Request(
        f"{BASE_URL}/api/memory",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(get_req) as r:
        assert r.status == 200
        list_data = json.loads(r.read())
        assert any(m["id"] == mem_id for m in list_data["memories"])
        return f"Stored and verified persistent memory ID {mem_id}"
results["Smart Long-Term Memory (/api/memory)"] = run_test("Smart Long-Term Memory", test_smart_memory)

# 12. Message Feedback (Thumbs Up / Down)
def test_message_feedback():
    token = token_holder.get("token")
    asst_id = conv_holder.get("asst_msg_id")
    payload = json.dumps({
        "message_id": asst_id,
        "rating": 1,
        "category": "quality",
        "comment": "Accurate and responsive."
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/feedback",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 201

    sum_req = urllib.request.Request(
        f"{BASE_URL}/api/feedback/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(sum_req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert data["total_ratings"] >= 1
        return f"Feedback recorded (total positive={data['positive_ratings']})"
results["Message Feedback (/api/feedback)"] = run_test("Message Feedback", test_message_feedback)

# 13. Background Jobs System
def test_background_jobs():
    token = token_holder.get("token")
    req = urllib.request.Request(
        f"{BASE_URL}/api/jobs/demo?task_name=e2e_live_audit_task",
        headers={"Authorization": f"Bearer {token}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 202
        job_data = json.loads(r.read())
        job_id = job_data["job"]["job_id"]

    # Poll status
    status_req = urllib.request.Request(
        f"{BASE_URL}/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(status_req) as r:
        assert r.status == 200
        assert r.status == 200
        return f"Dispatched and polled async background job {job_id}"
results["Background Jobs (/api/jobs)"] = run_test("Background Jobs", test_background_jobs)

# 14. Document Workspace (Create, Diff, Restore)
def test_document_workspace():
    token = token_holder.get("token")
    # Create
    create_payload = json.dumps({
        "title": "E2E Live Test Document",
        "initial_content": "Line 1: System Baseline Specification."
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/documents/workspace",
        data=create_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        ws_id = json.loads(r.read())["id"]

    # Edit
    edit_payload = json.dumps({
        "instruction": "Add line 2",
        "current_content": "Line 1: System Baseline Specification.\nLine 2: Live QA Verified."
    }).encode("utf-8")
    edit_req = urllib.request.Request(
        f"{BASE_URL}/api/documents/workspace/{ws_id}/edit",
        data=edit_payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(edit_req) as r:
        assert r.status == 200

    # Diff
    diff_req = urllib.request.Request(
        f"{BASE_URL}/api/documents/workspace/{ws_id}/diff?from_version=1&to_version=2",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(diff_req) as r:
        assert r.status == 200
        assert json.loads(r.read())["has_changes"] is True

    # Restore v1
    restore_req = urllib.request.Request(
        f"{BASE_URL}/api/documents/workspace/{ws_id}/restore/1",
        headers={"Authorization": f"Bearer {token}"},
        method="POST"
    )
    with urllib.request.urlopen(restore_req) as r:
        assert r.status == 200
        return f"Workspace {ws_id} created, edited, diffed, and version 1 restored successfully"
results["Document Workspace (/api/documents/workspace)"] = run_test("Document Workspace", test_document_workspace)

# 15. User Account Deletion & Data Purge (Danger Zone)
def test_account_deletion():
    token = token_holder.get("token")
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE"
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert "deleted" in data["message"].lower()
        return f"User account purged: {data['message']}"
results["User Account Deletion (/api/auth/me DELETE)"] = run_test("User Account Deletion", test_account_deletion)

print("\n--- LIVE INTEGRATION SUMMARY ---")
passed = sum(1 for p, _ in results.values() if p)
total = len(results)
print(f"Total Live E2E Endpoints Verified: {passed}/{total} PASSED")
