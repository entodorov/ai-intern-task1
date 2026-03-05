import os
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import docx

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def chunk_text(text, chunk_size=1500):
    """
    Transcript Chunking:
    Разделя дълъг текст на по-малки парчета по думи (напр. по 1500 символа), 
    за да може AI да го чете, без да препълва лимита си (context window).
    """
    words = text.split(' ')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1 
        if current_length > chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word) + 1
        else:
            current_chunk.append(word)
            
    if current_chunk:
        chunks.append(' '.join(current_chunk))
        
    return chunks

def read_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())
    return '\n'.join(full_text)

def main():
    data_dir = 'data'
    if not os.path.exists(data_dir):
        print(f"Папката {data_dir} не беше намерена.")
        return

    for project_folder in os.listdir(data_dir):
        project_path = os.path.join(data_dir, project_folder)
        
        if os.path.isdir(project_path):
            print(f"\nПроверявам проект: {project_folder}...")
            
            for filename in os.listdir(project_path):
                if filename.endswith('.docx'):
                    file_path = os.path.join(project_path, filename)
                    title = filename.replace('.docx', '')
                    
                    existing = supabase.table("meetings").select("id").eq("title", title).execute()
                    if len(existing.data) > 0:
                        print(f"ПРОПУСКАНЕ: '{title}' вече съществува в базата.")
                        continue
                    
                    raw_transcript = read_docx(file_path)
                    
                    chunks = chunk_text(raw_transcript, chunk_size=1500)
                    print(f"Текстът е нарязан на {len(chunks)} AI парчета (chunks).")
                    
                    transcript_json = json.dumps(chunks, ensure_ascii=False)
                    
                    timestamp = os.path.getmtime(file_path)
                    meeting_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                    
                    meeting_data = {
                        "title": title,
                        "meeting_date": meeting_date,
                        "source": project_folder, 
                        "raw_transcript": transcript_json
                    }
                    
                    try:
                        supabase.table("meetings").insert(meeting_data).execute()
                        print(f"Успешно добавена нова среща: {title}")
                    except Exception as e:
                        print(f"Проблем със записването на {title}: {e}")

if __name__ == "__main__":
    main()