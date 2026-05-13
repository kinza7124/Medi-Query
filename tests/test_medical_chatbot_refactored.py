import sys
import os
from unittest.mock import MagicMock, patch

# --- 1. ISOLATION LAYER ---
# We mock these libraries BEFORE any other imports to avoid the Pydantic v1 bug
mock_groq = MagicMock()
mock_pinecone = MagicMock()
sys.modules['langchain_groq'] = mock_groq
sys.modules['langchain_pinecone'] = mock_pinecone
sys.modules['pinecone'] = MagicMock()
sys.modules['langchain_community.cross_encoders'] = MagicMock()
sys.modules['langchain_community.retrievers'] = MagicMock()
sys.modules['langchain.retrievers'] = MagicMock()
sys.modules['langchain.retrievers.document_compressors'] = MagicMock()

# Now we can safely import app logic
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
# Mocking heavy singletons to avoid initialization issues
app.get_rag_chain = MagicMock()
app.get_docsearch = MagicMock()
app.get_embeddings = MagicMock()
app.get_llm = MagicMock()

import pytest

class TestMedicalChatbotRefactored:
    """
    Revised test suite using the actual function names found in app.py.
    """

    def test_validate_input_basic(self):
        from app import validate_user_input
        # validate_user_input returns (is_valid, cleaned_query)
        assert validate_user_input("  Hello World  ") == (True, "Hello World")
        assert validate_user_input("<script>alert(1)</script>")[0] is False

    def test_extract_primary_topic(self):
        from app import extract_primary_topic
        # extract_primary_topic returns the topic string
        assert extract_primary_topic("what is flu?") == "flu"
        assert extract_primary_topic("symptoms of diabetes") == "diabetes"

    def test_get_greeting_response(self):
        from app import get_greeting_response
        assert "Medical AI Assistant" in get_greeting_response("who are you")
        assert "Hello" in get_greeting_response("hello")
        assert get_greeting_response("flu symptoms") is None

    def test_needs_clinical_safety_note(self):
        from app import needs_clinical_safety_note
        assert needs_clinical_safety_note("pain in abdomen") is True
        assert needs_clinical_safety_note("how are you?") is False

    def test_append_clinical_safety_note(self):
        from app import append_clinical_safety_note
        answer = "Take aspirin."
        query = "headache"
        result = append_clinical_safety_note(query, answer)
        assert "consult a doctor" in result.lower()

    def test_request_logs_functionality(self):
        from app import request_logs
        request_logs.clear()
        request_logs.info("Test log")
        assert len(request_logs.entries) == 1
        assert request_logs.entries[0]['message'] == "Test log"

    def test_rotating_llm_logic(self):
        from app import RotatingGroqLLM
        with patch('langchain_groq.ChatGroq') as mock_chat_cls:
            mock_llm = MagicMock()
            mock_chat_cls.return_value = mock_llm
            
            # Mock invoke to fail once then succeed
            mock_llm.invoke.side_effect = [
                Exception("429 Rate Limit"),
                MagicMock(content="Success after rotation")
            ]
            
            llm = RotatingGroqLLM(api_keys=["key1", "key2"], model_name="test")
            response = llm.invoke("hello")
            
            assert response.content == "Success after rotation"
            assert llm.current_idx == 1

    @pytest.fixture
    def client(self):
        app.app.config['TESTING'] = True
        with app.app.test_client() as client:
            yield client

    def test_health_endpoint(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}

    def test_clear_session(self, client):
        with client.session_transaction() as sess:
            sess['chat_history'] = ["hi"]
        response = client.post('/clear')
        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get('chat_history') == []

    @patch('app.get_rag_chain')
    def test_chat_endpoint_greeting(self, mock_chain, client):
        response = client.post('/get', data={'msg': 'hello'})
        assert response.status_code == 200
        assert "Hello" in response.get_data(as_text=True)

    @patch('app.get_rag_chain')
    def test_chat_endpoint_medical(self, mock_chain, client):
        mock_chain.return_value.invoke.return_value = "Medical advice here."
        response = client.post('/get', data={'msg': 'stomach pain'})
        assert response.status_code == 200
        answer = response.get_data(as_text=True)
        assert "Medical advice" in answer
        assert "doctor" in answer.lower()
