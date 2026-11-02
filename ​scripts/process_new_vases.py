import os
import io
import json
import tempfile
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google import genai
import PIL.Image

def main():
    sa_key_json = os.environ.get("GCP_SA_KEY")
    if not sa_key_json:
        raise ValueError("GCP_SA_KEY not found!")

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_key:
        temp_key.write(sa_key_json)
        temp_key_path = temp_key.name

    gemini_key = os.environ.get("GEMINI_API_KEY")
    ai_client = genai.Client(api_key=gemini_key) if gemini_key else None

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
            return

        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                html_content = f.read()
            
            new_html_blocks = ""
            item_counter = 1 
            
            for item in items:
                file_id = item['id']
                file_name = item['name'].replace(" ", "_").strip()
                mime_type = item.get('mimeType', '')
                
                if file_name not in html_content:
                    sku = f"#NPC-{item_counter:03}"
                    item_counter += 1
                    
                    if not os.path.exists(file_name):
                        request = service.files().get_media(fileId=file_id)
                        fh = io.FileIO(file_name, 'wb')
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()

                    card_title = "New Showcase Vase"
                    card_desc = "Beautiful fluid art piece."
                    is_video = 'video' in mime_type or file_name.lower().endswith(('.mp4', '.mov', '.webm'))

                    if ai_client and not is_video:
                        try:
                            img = PIL.Image.open(file_name)
                            prompt = """
                            Analyze this Nini's Paint Pour Creations fluid art vase. 
                            Return ONLY a valid JSON object with two keys: 
                            'title' (a short, descriptive title) 
                            'description' (a poetic, single-sentence description of the colors and fluid motion matching a country-luxe art gallery, mentioning the elegant flowers displayed). 
                            Do not include markdown formatting.
                            """
                            max_retries = 3
                            for attempt in range(max_retries):
                                try:
                                    response = ai_client.models.generate_content(
                                        model='gemini-3.8-flash',
                                        contents=[prompt, img]
                                    )
                                    clean_json = response.text.strip().removeprefix('```json').removesuffix('```').strip()
                                    data = json.loads(clean_json)
                                    card_title = data.get('title', card_title)
                                    card_desc = data.get('description', card_desc)
                                    break
                                except Exception:
                                    if attempt < max_retries - 1:
                                        time.sleep(10)
                                    else:
                                        pass
                        except Exception as e:
                            print(f"AI text generation failed for {file_name}: {e}")

                    media_element = f'<video src="{file_name}" autoplay loop muted playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>' if is_video else f'<img src="{file_name}" alt="Nini\'s Paint Pour vase">'
                    
                    new_html_blocks += f"""
            <!-- Item {sku} -->
            <div class="product-card">
                <div class="image-wrapper">
                    <span class="sku-badge">{sku}</span>
                    {media_element}
                </div>
                <div class="product-info">
                    <h3>{card_title}</h3>
                    <p>{card_desc}</p>
                    <button class="modal-btn" onclick="alert('360-Degree Video View Coming Soon')">View 360° Experience</button>
                </div>
            </div>"""
            
            if new_html_blocks:
                updated_html = html_content.replace(
                    "<!-- NEW_VASES_HERE -->", 
                    f"{new_html_blocks}\n            <!-- NEW_VASES_HERE -->"
                )
                with open("index.html", "w", encoding="utf-8") as f:
                    f.write(updated_html)

    finally:
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

if __name__ == '__main__':
    main()
    
