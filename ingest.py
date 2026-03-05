import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import docx

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(url, key)

def read_docx(file_path):
    """Тази функция чете целия текст от даден Word документ."""
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text)
    return '\n'.join(full_text)

def main():
    data_dir = 'data'
    
    if not os.path.exists(data_dir):
        print(f"Папката {data_dir} не беше намерена. Увери се, че си я създал!")
        return

    for project_folder in os.listdir(data_dir):
        project_path = os.path.join(data_dir, project_folder)
        
        if os.path.isdir(project_path):
            print(f"\n📁 Обработвам проект: {project_folder}...")
            
            for filename in os.listdir(project_path):
                if filename.endswith('.docx'):
                    file_path = os.path.join(project_path, filename)
                    
                    title = filename.replace('.docx', '')
                    source = project_folder
                    transcript = read_docx(file_path)

                    timestamp = os.path.getmtime(file_path)
                    meeting_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')

                    meeting_data = {
                        "title": title,
                        "meeting_date": meeting_date,
                        "source": source,
                        "raw_transcript": transcript
                    }

                    try:
                        supabase.table("meetings").insert(meeting_data).execute()
                        print(f"Успешно добавена среща: {title}")
                    except Exception as e:
                        print(f"Проблем със записването на {title}: {e}")

if __name__ == "__main__":
    main()