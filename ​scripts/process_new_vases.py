import os
import io
import json
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import google.generativeai as genai
import PIL.Image

def main():
    print("Starting Nini's Paint Pour Creations sync with AI Vision...")
    
    # 1. Authenticate Google Drive
    sa_key_json = os.environ.get("GCP_SA_KEY")
    if not sa_key_json:
        raise ValueError("GCP_SA_KEY environment variable not found!")

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_key:
        temp_key.write(sa_key_json)
        temp_key_path = temp_key.name

    # 2. Authenticate Gemini AI
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        genai.configure(api_key=gemini_key)
        # Using Flash for fast, cost-free vision processing
        ai_model = genai.GenerativeModel('gemini-1.5-flash')
        print("Gemini AI Vision initialized successfully!")
    else:
        ai_model = None
        print("WARNING: GEMINI_API_KEY not found. Falling back to generic text.")

    try:
        creds = service_account.Credentials.from_service_account_file(
            temp_key_path, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=creds)

        results = service.files().list(
            q="mimeType contains 'image/' or mimeType contains 'video/'",
            pageSize=1000,
            fields="files(id, name, mimeType)"
        ).execute()
        
        items = results.get('files', [])
        if not items:
            print("No media found in Drive.")
            return

        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            
            new_html_blocks = ""
            for item in items:
                file_id = item['id']
                file_name = item['name'].replace(" ", "_").strip()
                mime_type = item.get('mimeType', '')
                
                # Check if it needs to be processed
                if file_name not in html_content:
                    # Download the file first
                    if not os.path.exists(file_name):
                        print(f"Downloading {file_name}...")
                        request = service.files().get_media(fileId=file_id)
                        fh = io.FileIO(file_name, 'wb')
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while done is False:
                            status, done = downloader.next_chunk()

                    # Default fallback text
                    card_title = "New Showcase Vase"
                    card_desc = "Beautiful fluid art piece featuring flowers."
                    is_video = 'video' in mime_type or file_name.lower().endswith(('.mp4', '.mov', '.webm'))

                    # Run AI Vision Analysis if it's a photo
                    if ai_model and not is_video:
                        try:
                            print(f"Analyzing {file_name} with Gemini AI...")
                            img = PIL.Image.open(file_name)
                            prompt = """
                            Analyze this Nini's Paint Pour Creations fluid art vase. 
                            Return ONLY a valid JSON object with two keys: 
                            'title' (a short, descriptive title like 'Midnight Blue Swirl Vase') 
                            'description' (a poetic, single-sentence description of the colors, fluid motion, and style matching a country-luxe art gallery). 
                            Do not include markdown formatting or backticks.
                            """
                            response = ai_model.generate_content([prompt, img])
                            # Clean and parse the JSON response
                            clean_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                            data = json.loads(clean_json)
                            card_title = data.get('title', card_title)
                            card_desc = data.get('description', card_desc)
                        except Exception as e:
                            print(f"AI Analysis failed for {file_name}: {e}")

                    # Generate HTML element
                    if is_video:
                        media_element = f'<video src="{file_name}" autoplay loop muted playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>'
                    else:
                        media_element = f'<img src="{file_name}" alt="Nini\'s Paint Pour vase with flowers">'
                    
                    new_html_blocks += f"""
            <div class="product-card">
                <div class="image-wrapper">
                    {media_element}
                </div>
                <div class="product-info">
                    <h3>{card_title}</h3>
                    <p>{card_desc}</p>
                    <button class="modal-btn" onclick="alert('360-Degree Video View Coming Soon')">View 360° Experience</button>
                </div>
            </div>"""
            
            if new_html_blocks:
                print("Injecting AI-curated HTML into index.html...")
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
    
