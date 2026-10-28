import os
import json
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    print("Starting Nini's Paint Pour Creations pipeline check...")
    
    # Load Google Cloud Service Account credentials from GitHub secret
    sa_key_json = os.environ.get("GCP_SA_KEY")
    if not sa_key_json:
        raise ValueError("GCP_SA_KEY environment variable not found!")
        
    # Write the key to a temporary file so Google client library can read it
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_key:
        temp_key.write(sa_key_json)
        temp_key_path = temp_key.name

    try:
        creds = service_account.Credentials.from_service_account_file(
            temp_key_path, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)
        print("Successfully authenticated with Google Cloud and Drive API!")
        
        # Placeholder for future folder scan and website update logic
        results = service.files().list(
            pageSize=1000, fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])
        
        print(f"Successfully connected to Drive. Found {len(files)} items visible to the service account.")

    finally:
        # Clean up temporary key file
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

if __name__ == '__main__':
    main()
