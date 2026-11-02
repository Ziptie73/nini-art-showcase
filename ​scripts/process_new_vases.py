import os
import io
import json
import tempfile
import random
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google import genai
import PIL.Image
from PIL import ImageDraw, ImageFont
from rembg import remove

def main():
    print("Starting Nini's Paint Pour sync with Template Compositing and Retry Loop...")
    
    sa_key_json = os.environ.get("GCP_SA_KEY")
    if not sa_key_json:
        raise ValueError("GCP_SA_KEY environment variable not found!")

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_key:
        temp_key.write(sa_key_json)
        temp_key_path = temp_key.name

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        ai_client = genai.Client(api_key=gemini_key)
        print("Gemini AI initialized for text analysis!")
    else:
        ai_client = None

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
                processed_image_name = f"processed_{file_name}"
                mime_type = item.get('mimeType', '')
                
                if file_name not in html_content and processed_image_name not in html_content:
                    sku = f"#NPC-{item_counter:03}"
                    item_counter += 1
                    
                    if not os.path.exists(file_name):
                        request = service.files().get_media(fileId=file_id)
                        fh = io.FileIO(file_name, 'wb')
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while done is False:
                            status, done = downloader.next_chunk()

                    card_title = "New Showcase Vase"
                    card_desc = "Beautiful fluid art piece featuring flowers."
                    is_video = 'video' in mime_type or file_name.lower().endswith(('.mp4', '.mov', '.webm'))

                    if ai_client and not is_video:
                        try:
                            img = PIL.Image.open(file_name)
                            
                            # Text Analysis with Retry Loop
                            prompt = """
                            Analyze this Nini's Paint Pour Creations fluid art vase in the original photo. 
                            First, estimate the approximate height of the vase in inches by comparing it to the standard spray paint can next to it.
                            Then, return ONLY a valid JSON object with two keys: 
                            'title' (a short, descriptive title) 
                            'description' (a poetic, single-sentence description of the colors and fluid motion matching a country-luxe art gallery, seamlessly including its approximate estimated height, such as 'Standing roughly 8 inches tall, this...'). 
                            Do not include markdown formatting or backticks.
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
                                except Exception as api_e:
                                    print(f"Gemini API attempt {attempt + 1} failed: {api_e}")
                                    if attempt < max_retries - 1:
                                        print("Waiting 10 seconds before retrying...")
                                        time.sleep(10)
                                    else:
                                        print("Max retries reached. Aborting AI processing for this item.")
                                        raise api_e

                            # Background Compositing
                            bg_folder = "backgrounds"
                            bg_img = None
                            if os.path.exists(bg_folder):
                                bgs = [f for f in os.listdir(bg_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                                if bgs:
                                    bg_path = os.path.join(bg_folder, random.choice(bgs))
                                    bg_img = PIL.Image.open(bg_path).convert("RGBA")
                            
                            if bg_img is None:
                                bg_img = PIL.Image.new("RGBA", (1080, 1350), (244, 243, 239, 255))
                            
                            bg_img = bg_img.resize((1080, 1350))

                            # Extract and scale vase to exactly 35% of frame
                            vase_only = remove(img).convert("RGBA")
                            target_height = int(bg_img.height * 0.35)
                            aspect_ratio = vase_only.width / vase_only.height
                            target_width = int(target_height * aspect_ratio)
                            vase_resized = vase_only.resize((target_width, target_height), PIL.Image.Resampling.LANCZOS)
                            
                            # Paste vase onto background
                            paste_x = (bg_img.width - target_width) // 2
                            paste_y = bg_img.height - target_height - int(bg_img.height * 0.15)
                            
                            final_img = PIL.Image.new("RGBA", bg_img.size)
                            final_img = PIL.Image.alpha_composite(bg_img, final_img)
                            final_img.paste(vase_resized, (paste_x, paste_y), vase_resized)
                            
                            # Draw SKU ID Card next to vase
                            draw = ImageDraw.Draw(final_img)
                            card_w, card_h = 120, 50
                            card_x, card_y = paste_x + target_width + 10, paste_y + target_height - card_h - 10
                            draw.rectangle([card_x, card_y, card_x + card_w, card_y + card_h], fill=(255, 253, 240, 255), outline=(200, 190, 170, 255), width=2)
                            font = ImageFont.load_default()
                            draw.text((card_x + 15, card_y + 15), sku, fill=(50, 50, 50, 255), font=font)
                            
                            final_img.convert("RGB").save(processed_image_name)

                        except Exception as e:
                            print(f"Extraction or Generation failed for {file_name}: {e}")
                            processed_image_name = file_name 

                    media_element = f'<video src="{file_name}" autoplay loop muted playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>' if is_video else f'<img src="{processed_image_name}" alt="Nini\'s Paint Pour vase">'
                    
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
    
