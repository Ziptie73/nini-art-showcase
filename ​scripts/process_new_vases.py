import os
import io
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def main():
    print("Starting Nini's Paint Pour Creations download sync...")
    
    sa_key_json = os.environ.get("GCP_SA_KEY")
    if not sa_key_json:
        raise ValueError("GCP_SA_KEY environment variable not found!")

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_key:
        temp_key.write(sa_key_json)
        temp_key_path = temp_key.name

    try:
        creds = service_account.Credentials.from_service_account_file(
            temp_key_path, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)
        print("Successfully authenticated with Google Cloud and Drive API!")

        # Retrieve only image files
        results = service.files().list(
            q="mimeType contains 'image/'",
            pageSize=1000,
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print("No images found in Drive.")
            return

        print(f"Found {len(items)} images visible to the service account. Starting download...")

        for item in items:
            file_id = item['id']
            # Clean up potential tablet naming glitches
            file_name = item['name'].replace(" ", "_").strip()
            
            # Skip if we already have it in the repository
            if os.path.exists(file_name):
                print(f"Skipping {file_name}, already exists in repository.")
                continue
                
            print(f"Downloading {file_name}...")
            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_name, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

        print("Sync complete!")

    finally:
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

if __name__ == '__main__':
    main()
    
