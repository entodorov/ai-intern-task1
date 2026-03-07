import os
import json
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client
from google import genai
import time

load_dotenv()
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_ID = 'gemini-2.5-flash'

def generate_structured_notes(transcript_text):
    """Праща текста на Gemini и изисква стриктен JSON отговор, с логика за повторни опити (retry/backoff)."""
    
    if len(transcript_text.split()) < 10:
        print("Текстът е твърде къс за анализ.")
        return None, "Твърде къс текст"

    prompt = f"""
    You are an expert AI meeting assistant. Read the following meeting transcript and generate structured notes.
    You MUST respond ONLY with valid JSON. Do not add markdown formatting like ```json or any other text.
    
    The JSON schema MUST exactly match this:
    {{
        "summary": "String (overview of the meeting)",
        "action_items": [
            {{ "text": "Task description", "owner": "Person name or null", "due_date": "Date or null" }}
        ],
        "decisions": ["String", "String"],
        "key_takeaways": ["String", "String"],
        "topics": ["String", "String"],
        "next_steps": [
            {{ "text": "Next step description", "owner": "Person name or null" }}
        ]
    }}
    
    Meeting Transcript:
    {transcript_text}
    """
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
            )
            raw_text = response.text.strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3]
                
            parsed_json = json.loads(raw_text) 
            
            if "action_items" not in parsed_json:
                parsed_json["action_items"] = []
                
            unique_actions = []
            seen_texts = set()
            for item in parsed_json["action_items"]:
                task_text = item.get("text", "").strip().lower()
                if task_text and task_text not in seen_texts:
                    seen_texts.add(task_text)
                    unique_actions.append(item)
            
            parsed_json["action_items"] = unique_actions
                
            return parsed_json, response.text
            
        except json.JSONDecodeError:
            print("ГРЕШКА: Моделът не върна валиден JSON формат.")
            return None, response.text
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt 
                print(f"Мрежова грешка. Опит {attempt + 1} неуспешен. Изчакване {wait_time} сек...")
                time.sleep(wait_time)
            else:
                print(f"ГРЕШКА при връзката с Gemini след {max_retries} опита: {e}")
                return None, str(e)

def process_meeting(meeting):
    meeting_id = meeting['id']
    title = meeting['title']
    print(f"\nОбработвам среща: {title} (ID: {meeting_id})")
    
    try:
        chunks = json.loads(meeting['raw_transcript'])
        full_transcript = " ".join(chunks)
    except:
        full_transcript = meeting['raw_transcript']

    notes_dict, raw_response = generate_structured_notes(full_transcript)
    
    if notes_dict:
        note_data = {
            "meeting_id": meeting_id,
            "summary": notes_dict.get("summary", "Няма резюме"),
            "action_items": notes_dict.get("action_items", []),
            "decisions": notes_dict.get("decisions", []),
            "key_takeaways": notes_dict.get("key_takeaways", []),
            "topics": notes_dict.get("topics", []),
            "next_steps": notes_dict.get("next_steps", []),
            "llm_raw": raw_response
        }
        
        supabase.table("notes").insert(note_data).execute()
        print(f"Успешно генерирани и записани бележки за: {title}!")
    else:
        print(f"Пропускане на запис поради грешка в AI генерирането.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--meeting_id', type=str, help="ID на конкретна среща за обработка.")
    args = parser.parse_args()

    if args.meeting_id:
        response = supabase.table("meetings").select("*").eq("id", args.meeting_id).execute()
        meetings_to_process = response.data
    else:
        notes_response = supabase.table("notes").select("meeting_id").execute()
        processed_ids = [note['meeting_id'] for note in notes_response.data]
        
        meetings_response = supabase.table("meetings").select("*").execute()
        meetings_to_process = [m for m in meetings_response.data if m['id'] not in processed_ids]
        
        if not meetings_to_process:
            print("Всички срещи вече имат генерирани бележки!")
            return

    print(f"Намерени {len(meetings_to_process)} срещи за обработка.")
    for meeting in meetings_to_process:
        process_meeting(meeting)

if __name__ == "__main__":
    main()