from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

from otoc.config import get_client


class ClientConfigTests(unittest.TestCase):
    def test_import_is_inert_and_client_uses_token_without_logging_it(self) -> None:
        token = "test-token-not-a-real-credential"
        expected_client = object()
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda **kwargs: None
        bluequbit = types.ModuleType("bluequbit")
        bluequbit.init = lambda: expected_client
        with patch.dict(sys.modules, {"dotenv": dotenv, "bluequbit": bluequbit}):
            with patch.dict(os.environ, {"BLUEQUBIT_API_TOKEN": token}, clear=True):
                self.assertIs(get_client(), expected_client)
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "BLUEQUBIT_API_TOKEN"):
                    get_client()


if __name__ == "__main__":
    unittest.main()
