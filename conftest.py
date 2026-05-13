import pytest
import sys
import os
from unittest.mock import MagicMock

# --- 1. ISOLATION LAYER ---
# Mock problematic libraries BEFORE importing app
mock_groq = MagicMock()
mock_pinecone = MagicMock()
sys.modules['langchain_groq'] = mock_groq
sys.modules['langchain_pinecone'] = mock_pinecone
sys.modules['pinecone'] = MagicMock()
sys.modules['langchain_community.cross_encoders'] = MagicMock()
sys.modules['langchain_community.retrievers'] = MagicMock()
sys.modules['langchain.retrievers'] = MagicMock()
sys.modules['langchain.retrievers.document_compressors'] = MagicMock()

# Ensure we can find the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app

@pytest.fixture
def client():
    app.app.config['TESTING'] = True
    app.app.config['SECRET_KEY'] = 'test-secret'
    with app.app.test_client() as client:
        yield client
