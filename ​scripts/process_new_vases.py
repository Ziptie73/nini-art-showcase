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

        results = service.files().list(
            q="mimeType contains 'image/'",
            pageSize=1000,
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            print("No images found in Drive.")
            return

        new_downloads = []

        for item in items:
            file_id = item['id']
            file_name = item['name'].replace(" ", "_").strip()
            
            if os.path.exists(file_name):
                continue
                
            print(f"Downloading {file_name}...")
            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(file_name, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            new_downloads.append(file_name)

        # Auto-update HTML with new vase images and flowers specification
        if new_downloads:
            print(f"Updating index.html with {len(new_downloads)} new images...")
            if os.path.exists("index.html"):
                with open("index.html", "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                new_html_blocks = ""
                for img in new_downloads:
                    new_html_blocks += f'\n    <div class="product-card">\n      <img src="{img}" alt="Nini\'s Paint Pour vase with flowers">\n    </div>'
                
                updated_html = html_content.replace("</body>", f"{new_html_blocks}\n</body>")
                
                with open("index.html", "w", encoding="utf-8") as f:
                    f.write(updated_html)
                print("Website HTML updated successfully!")
            else:
                print("Could not find index.html to update.")

        print("Sync complete!")

    finally:
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

if __name__ == '__main__':
    main()
    
