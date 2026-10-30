import os
import io
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def main():
    print("Starting Nini's Paint Pour Creations sync for photos and videos...")
    
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

        # 1. Look for BOTH images and videos
        results = service.files().list(
            q="mimeType contains 'image/' or mimeType contains 'video/'",
            pageSize=1000,
            fields="files(id, name, mimeType)"
        ).execute()
        
        items = results.get('files', [])
        if not items:
            print("No media found in Drive.")
            return

        # 2. Download missing media
        for item in items:
            file_id = item['id']
            file_name = item['name'].replace(" ", "_").strip()
            
            if not os.path.exists(file_name):
                print(f"Downloading {file_name}...")
                request = service.files().get_media(fileId=file_id)
                fh = io.FileIO(file_name, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

        # 3. Update HTML with strict image-wrapper formatting
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            
            new_html_blocks = ""
            for item in items:
                file_name = item['name'].replace(" ", "_").strip()
                mime_type = item.get('mimeType', '')
                
                if file_name not in html_content:
                    # Choose video player or image tag
                    if 'video' in mime_type or file_name.lower().endswith(('.mp4', '.mov', '.webm')):
                        media_element = f'<video src="{file_name}" autoplay loop muted playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>'
                    else:
                        media_element = f'<img src="{file_name}" alt="Nini\'s Paint Pour vase with flowers">'
                    
                    # Wrap in the exact CSS classes Trisha uses for vases 1-16
                    new_html_blocks += f"""
            <div class="product-card">
                <div class="image-wrapper">
                    {media_element}
                </div>
                <div class="product-info">
                    <h3>New Showcase Vase</h3>
                    <p>Beautiful fluid art piece featuring flowers.</p>
                    <button class="modal-btn" onclick="alert('360-Degree Video View Coming Soon')">View 360° Experience</button>
                </div>
            </div>"""
            
            if new_html_blocks:
                print("Adding new formatted media to index.html...")
                updated_html = html_content.replace(
                    "<!-- NEW_VASES_HERE -->", 
                    f"{new_html_blocks}\n            <!-- NEW_VASES_HERE -->"
                )
                with open("index.html", "w", encoding="utf-8") as f:
                    f.write(updated_html)
                print("Website HTML updated successfully!")
            else:
                print("All media is already in the HTML. Nothing to update.")
        else:
            print("Could not find index.html to update.")

        print("Sync complete!")

    finally:
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

if __name__ == '__main__':
    main()
    
