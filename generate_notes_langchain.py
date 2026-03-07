import os
import json
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from tqdm import tqdm

load_dotenv()
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

class ActionItem(BaseModel):
    text: str = Field(description="Task description")
    owner: Optional[str] = Field(description="Person name or null", default=None)
    due_date: Optional[str] = Field(description="Date or null", default=None)

class NextStep(BaseModel):
    text: str = Field(description="Next step description")
    owner: Optional[str] = Field(description="Person name or null", default=None)

class MeetingNotes(BaseModel):
    summary: str = Field(description="Overview of the meeting")
    action_items: List[ActionItem] = Field(default_factory=list)
    decisions: List[str] = Field(default_factory=list)
    key_takeaways: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    next_steps: List[NextStep] = Field(default_factory=list)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, api_key=os.environ.get("GEMINI_API_KEY"))

structured_llm = llm.with_structured_output(MeetingNotes)

def generate_with_langchain(transcript_text):
    """Генерира бележки, използвайки LangChain и Pydantic за структуриран изход."""
    
    if len(transcript_text.split()) < 10:
        print("Текстът е твърде къс за анализ.")
        return None, "Твърде къс текст"

    prompt = f"Read the following meeting transcript and generate structured meeting notes.\n\nTranscript:\n{transcript_text}"
    
    try:
        result = structured_llm.invoke(prompt)
        
        notes_dict = result.model_dump()
        
        unique_actions = []
        seen_texts = set()
        for item in notes_dict["action_items"]:
            task_text = item.get("text", "").strip().lower()
            if task_text and task_text not in seen_texts:
                seen_texts.add(task_text)
                unique_actions.append(item)
        notes_dict["action_items"] = unique_actions

        return notes_dict, json.dumps(notes_dict, ensure_ascii=False)
        
    except Exception as e:
        print(f"ГРЕШКА при обработката с LangChain: {e}")
        return None, str(e)

def process_meeting(meeting):
    meeting_id = meeting['id']
    title = meeting['title']
    #print(f"\nОбработвам среща с LangChain: {title} (ID: {meeting_id})")
    
    try:
        chunks = json.loads(meeting['raw_transcript'])
        full_transcript = " ".join(chunks)
    except:
        full_transcript = meeting['raw_transcript']

    notes_dict, raw_response = generate_with_langchain(full_transcript)
    
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
        tqdm.write(f"Успешно генерирани и записани бележки чрез LangChain!")
    else:
        tqdm.write(f"Пропускане на запис поради грешка.")

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
    for meeting in tqdm(meetings_to_process, desc="LangChain AI", unit="среща"):
        process_meeting(meeting)

if __name__ == "__main__":
    main()