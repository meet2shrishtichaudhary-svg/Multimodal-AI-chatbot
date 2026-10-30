import urllib.request
import urllib.error
import json
import uuid
import os

BASE_URL = "http://localhost:8000"

def upload_multipart(filename, content_bytes, content_type):
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.extend(content_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{BASE_URL}/api/uploads",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    return req

def test_upload_image():
    # 1x1 valid transparent PNG
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    req = upload_multipart("test_diagram.png", png_bytes, "image/png")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["attachment_type"] == "image"
        assert data["file_name"] == "test_diagram.png"
        assert "id" in data
        return data

def test_upload_document():
    doc_text = "Aura AI Architecture Specification\n1. Overview\nThis document describes system capabilities."
    req = upload_multipart("test_specs.txt", doc_text.encode("utf-8"), "text/plain")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["attachment_type"] == "document"
        assert data["file_name"] == "test_specs.txt"
        assert "id" in data
        return data

def test_upload_unsupported_rejection():
    # Attempt to upload .exe or .zip
    bad_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    req = upload_multipart("malware.exe", bad_bytes, "application/octet-stream")
    try:
        urllib.request.urlopen(req)
        assert False, "Should have rejected unsupported file extension"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        err_msg = json.loads(e.read().decode())
        assert "not supported" in err_msg["detail"]
        return err_msg["detail"]

def test_upload_oversized_rejection():
    # Exceed 25 MB limit
    # We will simulate a 26 MB chunked payload
    oversized_bytes = b"0" * (26 * 1024 * 1024)
    req = upload_multipart("huge_dataset.txt", oversized_bytes, "text/plain")
    try:
        urllib.request.urlopen(req)
        assert False, "Should have rejected oversized file"
    except urllib.error.HTTPError as e:
        assert e.code == 413
        err_msg = json.loads(e.read().decode())
        assert "exceeds maximum allowed size" in err_msg["detail"]
        return err_msg["detail"]

def test_chat_with_attachments(img_id, doc_id):
    # Send message with image and doc attachment IDs
    chat_payload = {
        "message": "Please analyze this diagram and specs document.",
        "attachment_ids": [img_id, doc_id],
        "enable_web_search": False,
        "persona": "general"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=json.dumps(chat_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert "assistant_message" in data
        assert "conversation_id" in data
        assert len(data["assistant_message"]["content"]) > 0
        return f"Conversation {data['conversation_id']} created with response: '{data['assistant_message']['content'][:60]}...'"

def test_chat_text_alone():
    chat_payload = {
        "message": "Hello Aura, what are your core capabilities?",
        "attachment_ids": [],
        "enable_web_search": False,
        "persona": "general"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=json.dumps(chat_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert "assistant_message" in data
        return f"Response received: '{data['assistant_message']['content'][:60]}...'"

if __name__ == "__main__":
    print("--- STARTING '+' ATTACHMENTS VERIFICATION SUITE ---")
    
    # 1. Test image upload
    img_data = test_upload_image()
    print(f"[PASS] Image Upload: ID {img_data['id']} (type={img_data['attachment_type']})")

    # 2. Test document upload
    doc_data = test_upload_document()
    print(f"[PASS] Document Upload: ID {doc_data['id']} (type={doc_data['attachment_type']})")

    # 3. Test unsupported file rejection
    unsupported_res = test_upload_unsupported_rejection()
    print(f"[PASS] Unsupported File Rejection: {unsupported_res}")

    # 4. Test oversized file rejection
    oversized_res = test_upload_oversized_rejection()
    print(f"[PASS] Oversized (>25MB) Rejection: {oversized_res}")

    # 5. Test chat with attachments
    chat_att_res = test_chat_with_attachments(img_data["id"], doc_data["id"])
    print(f"[PASS] Chat with Attachments: {chat_att_res}")

    # 6. Test chat text alone
    chat_text_res = test_chat_text_alone()
    print(f"[PASS] Chat Text Alone: {chat_text_res}")

    print("\n[ALL 6 VERIFICATIONS PASSED 100%]")
