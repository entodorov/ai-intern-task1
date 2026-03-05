import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

response = supabase.table("meetings").select("id, title, meeting_date").execute()

print("\n--- СПИСЪК СЪС СРЕЩИ В SUPABASE ---")
for meeting in response.data:
    print(f"ID: {meeting['id']} | Заглавие: {meeting['title']} | Дата: {meeting['meeting_date']}")