import requests
import os

BASE_URL = "http://localhost:8000"

# 1. Register User
email = "test@example.com"
password = "password123"

def run_test():
    print("Running Docsign Test Flow...")
    
    # Register
    print(f"\n1. Registering user {email}...")
    resp = requests.post(f"{BASE_URL}/register", json={"email": email, "password": password})
    if resp.status_code == 200:
        print("User registered.")
    elif resp.status_code == 400 and "already registered" in resp.text:
        print("User already registered.")
    else:
        print(f"Error registering: {resp.text}")
        return

    # Login
    print(f"\n2. Logging in...")
    resp = requests.post(f"{BASE_URL}/token", data={"username": email, "password": password})
    if resp.status_code != 200:
        print(f"Error logging in: {resp.text}")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in.")

    # Upload Document
    print(f"\n3. Uploading document...")
    # Create a dummy PDF if it doesn't exist
    if not os.path.exists("test.pdf"):
        from reportlab.pdfgen import canvas
        c = canvas.Canvas("test.pdf")
        c.drawString(100, 750, "Hello World - Contract")
        c.save()
    
    with open("test.pdf", "rb") as f:
        files = {"file": ("test.pdf", f, "application/pdf")}
        resp = requests.post(f"{BASE_URL}/documents/upload", headers=headers, files=files)
    
    if resp.status_code != 200:
        print(f"Error uploading: {resp.text}")
        return
    doc_id = resp.json()["id"]
    print(f"Document uploaded. ID: {doc_id}")

    # Add Signer
    print(f"\n4. Adding signer...")
    signer_email = "signer@example.com"
    resp = requests.post(f"{BASE_URL}/documents/{doc_id}/signers", headers=headers, json={
        "email": signer_email,
        "name": "John Doe"
    })
    if resp.status_code != 200:
        print(f"Error adding signer: {resp.text}")
        return
    print("Signer added.")

    # Add Field
    print(f"\n5. Adding signature field...")
    resp = requests.post(f"{BASE_URL}/documents/{doc_id}/fields", headers=headers, json={
        "signer_email": signer_email,
        "page_number": 1,
        "x_coordinate": 100,
        "y_coordinate": 100, 
        "type": "SIGNATURE"
    })
    if resp.status_code != 200:
        print(f"Error adding field: {resp.text}")
        return
    print("Field added.")

    # Send Document
    print(f"\n6. Sending document...")
    resp = requests.post(f"{BASE_URL}/documents/{doc_id}/send", headers=headers)
    if resp.status_code != 200:
        print(f"Error sending document: {resp.text}")
        return
    
    json_resp = resp.json()
    print("Document sent.")
    print("Links:", json_resp["links"])
    
    # Extract signing link/token
    link = json_resp["links"][0]["link"]
    token = link.split("/")[-1]
    
    # Mock Signing
    print(f"\n7. Signing document as {signer_email} with token {token}...")
    resp = requests.post(f"{BASE_URL}/signing/sign/{token}?signature_text=JohnDoeParsed", json={})
    if resp.status_code != 200:
        print(f"Error signing: {resp.text}")
        return
    print("Document signed successfully.")
    
    print("\nSUCCESS! Flow completed. Check server logs for PDF generation output.")

if __name__ == "__main__":
    run_test()
