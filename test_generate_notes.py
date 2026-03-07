import unittest
from unittest.mock import patch, MagicMock
from generate_notes import generate_structured_notes

class TestGenerateNotes(unittest.TestCase):
    def test_transcript_too_short(self):
        """Проверява дали скриптът спира, ако текстът е под 10 думи."""
        short_text = "Здравейте, това е много кратка среща. Довиждане!"
        parsed_json, raw_text = generate_structured_notes(short_text)
        
        self.assertIsNone(parsed_json)
        self.assertEqual(raw_text, "Твърде къс текст")

    @patch('generate_notes.client.models.generate_content')
    def test_generate_structured_notes_success_and_deduplication(self, mock_generate):
        """Проверява дали парсва JSON-а правилно и дали трие дублираните задачи."""
        
        mock_response = MagicMock()
        mock_response.text = '''
        ```json
        {
            "summary": "Тестово резюме",
            "action_items": [
                { "text": "Направи кафе", "owner": "Емо", "due_date": null },
                { "text": "Направи кафе", "owner": "Емо", "due_date": null },
                { "text": "Пиши код", "owner": "Емо", "due_date": "Утре" }
            ],
            "decisions": [],
            "key_takeaways": [],
            "topics": [],
            "next_steps": []
        }
        ```
        '''
        mock_generate.return_value = mock_response

        dummy_transcript = "Това е тестови транскрипт, който е достатъчно дълъг, за да премине първоначалната проверка на скрипта ни без проблем."
        parsed_json, raw_text = generate_structured_notes(dummy_transcript)

        self.assertIsNotNone(parsed_json)
        self.assertEqual(parsed_json["summary"], "Тестово резюме")
        
        self.assertEqual(len(parsed_json["action_items"]), 2)
        self.assertEqual(parsed_json["action_items"][0]["text"], "Направи кафе")
        self.assertEqual(parsed_json["action_items"][1]["text"], "Пиши код")
        
        print("\nВсички тестове за генерацията на бележки минаха успешно!")

if __name__ == '__main__':
    unittest.main()