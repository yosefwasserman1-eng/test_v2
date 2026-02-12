
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestRefactoring(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        os.environ["GEMINI_API_KEY"] = "fake_key"
        
    def test01_config_loader(self):
        from utils.config_loader import get_config
        # Test default
        self.assertEqual(get_config("non.existent", "default"), "default")
        # Test loaded config (assuming config.yaml exists or fails gracefully)
        # We can't guarantee config.yaml content, but we can check it doesn't crash

    @patch("google.genai.Client")
    def test02_chat_service_init(self, mock_client):
        from chat_service import ChatService
        
        # Mock cache creation inside init
        with patch.object(ChatService, "_create_cache") as mock_cache:
            service = ChatService()
            self.assertIsNotNone(service)
            self.assertIsNotNone(service.client)

    def test03_wrapper_path(self):
        from tools.wrapper import run_script
        # Test with a non-existent script
        result = run_script("non_existent_script.py")
        self.assertFalse(result["success"])
        self.assertIn("Script not found", result["output"])

    def test04_app_import(self):
        # Mock chainlit to avoid runtime errors during import
        with patch.dict(sys.modules, {"chainlit": MagicMock()}):
            import app
            self.assertIsNotNone(app)

if __name__ == "__main__":
    unittest.main()
