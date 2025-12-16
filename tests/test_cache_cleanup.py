"""
Unit tests for the cache-cleanup command.

These tests validate the functionality of identifying and removing
recipes without binary packages from the Conan cache.
"""

import json
import unittest
from unittest.mock import patch, MagicMock, call, Mock
import sys
import os

# Mock the conan modules before importing the command module
sys.modules['conan'] = MagicMock()
sys.modules['conan.api'] = MagicMock()
sys.modules['conan.api.output'] = MagicMock()
sys.modules['conan.cli'] = MagicMock()
sys.modules['conan.cli.command'] = MagicMock()
sys.modules['conan.errors'] = MagicMock()

# Add the parent directory to the path to import the command module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from extensions.commands.cmd_cache_cleanup import (
    _identify_recipes_without_binaries,
    _run_conan_command,
    _list_cache_recipes,
    _remove_recipe
)


# Helper class for exception testing
class ConanException(Exception):
    """Test exception class to simulate ConanException."""
    pass


class TestIdentifyRecipesWithoutBinaries(unittest.TestCase):
    """Test the _identify_recipes_without_binaries function."""
    
    def test_empty_cache(self):
        """Test with an empty cache."""
        cache_data = {"Local Cache": {}}
        result = _identify_recipes_without_binaries(cache_data)
        
        self.assertEqual(result["recipes_to_remove"], [])
        self.assertEqual(result["recipes_with_binaries"], [])
        self.assertEqual(result["total_inspected"], 0)
    
    def test_all_recipes_have_binaries(self):
        """Test when all recipes have binary packages."""
        cache_data = {
            "Local Cache": {
                "zlib/1.2.13": {
                    "revisions": {
                        "abc123": {
                            "packages": {
                                "pkg1": {"id": "pkg1"}
                            }
                        }
                    }
                },
                "openssl/3.0.0": {
                    "revisions": {
                        "def456": {
                            "packages": {
                                "pkg2": {"id": "pkg2"}
                            }
                        }
                    }
                }
            }
        }
        result = _identify_recipes_without_binaries(cache_data)
        
        self.assertEqual(len(result["recipes_to_remove"]), 0)
        self.assertEqual(len(result["recipes_with_binaries"]), 2)
        self.assertEqual(result["total_inspected"], 2)
        self.assertIn("zlib/1.2.13#abc123", result["recipes_with_binaries"])
        self.assertIn("openssl/3.0.0#def456", result["recipes_with_binaries"])
    
    def test_all_recipes_without_binaries(self):
        """Test when all recipes lack binary packages."""
        cache_data = {
            "Local Cache": {
                "zlib/1.2.13": {
                    "revisions": {
                        "abc123": {
                            "packages": {}
                        }
                    }
                },
                "openssl/3.0.0": {
                    "revisions": {
                        "def456": {
                            "packages": {}
                        }
                    }
                }
            }
        }
        result = _identify_recipes_without_binaries(cache_data)
        
        self.assertEqual(len(result["recipes_to_remove"]), 2)
        self.assertEqual(len(result["recipes_with_binaries"]), 0)
        self.assertEqual(result["total_inspected"], 2)
        self.assertIn("zlib/1.2.13#abc123", result["recipes_to_remove"])
        self.assertIn("openssl/3.0.0#def456", result["recipes_to_remove"])
    
    def test_mixed_recipes(self):
        """Test when some recipes have binaries and some don't."""
        cache_data = {
            "Local Cache": {
                "zlib/1.2.13": {
                    "revisions": {
                        "abc123": {
                            "packages": {
                                "pkg1": {"id": "pkg1"}
                            }
                        }
                    }
                },
                "openssl/3.0.0": {
                    "revisions": {
                        "def456": {
                            "packages": {}
                        }
                    }
                },
                "boost/1.82.0": {
                    "revisions": {
                        "ghi789": {
                            "packages": {}
                        }
                    }
                }
            }
        }
        result = _identify_recipes_without_binaries(cache_data)
        
        self.assertEqual(len(result["recipes_to_remove"]), 2)
        self.assertEqual(len(result["recipes_with_binaries"]), 1)
        self.assertEqual(result["total_inspected"], 3)
        self.assertIn("openssl/3.0.0#def456", result["recipes_to_remove"])
        self.assertIn("boost/1.82.0#ghi789", result["recipes_to_remove"])
        self.assertIn("zlib/1.2.13#abc123", result["recipes_with_binaries"])
    
    def test_multiple_revisions_per_recipe(self):
        """Test when a recipe has multiple revisions."""
        cache_data = {
            "Local Cache": {
                "zlib/1.2.13": {
                    "revisions": {
                        "abc123": {
                            "packages": {
                                "pkg1": {"id": "pkg1"}
                            }
                        },
                        "xyz789": {
                            "packages": {}
                        }
                    }
                }
            }
        }
        result = _identify_recipes_without_binaries(cache_data)
        
        self.assertEqual(len(result["recipes_to_remove"]), 1)
        self.assertEqual(len(result["recipes_with_binaries"]), 1)
        self.assertEqual(result["total_inspected"], 2)
        self.assertIn("zlib/1.2.13#abc123", result["recipes_with_binaries"])
        self.assertIn("zlib/1.2.13#xyz789", result["recipes_to_remove"])


class TestRunConanCommand(unittest.TestCase):
    """Test the _run_conan_command function."""
    
    @patch('extensions.commands.cmd_cache_cleanup.subprocess.run')
    def test_successful_command(self, mock_run):
        """Test successful command execution."""
        mock_run.return_value = MagicMock(
            stdout="command output",
            stderr="",
            returncode=0
        )
        
        result = _run_conan_command(["conan", "list"])
        
        self.assertEqual(result, "command output")
        mock_run.assert_called_once()
    
    @patch('extensions.commands.cmd_cache_cleanup.subprocess.run')
    def test_failed_command(self, mock_run):
        """Test failed command execution."""
        with patch('extensions.commands.cmd_cache_cleanup.ConanException', ConanException):
            mock_run.side_effect = Exception("Command failed")
            
            with self.assertRaises(Exception):
                _run_conan_command(["conan", "list"])
    
    def test_non_conan_command_rejected(self):
        """Test that non-conan commands are rejected."""
        with patch('extensions.commands.cmd_cache_cleanup.ConanException', ConanException):
            with self.assertRaises(ConanException):
                _run_conan_command(["rm", "-rf", "/"])
            
            with self.assertRaises(ConanException):
                _run_conan_command(["python", "script.py"])
    
    def test_empty_command_rejected(self):
        """Test that empty commands are rejected."""
        with patch('extensions.commands.cmd_cache_cleanup.ConanException', ConanException):
            with self.assertRaises(ConanException):
                _run_conan_command([])


class TestRemoveRecipe(unittest.TestCase):
    """Test the _remove_recipe function."""
    
    @patch('extensions.commands.cmd_cache_cleanup._run_conan_command')
    def test_remove_without_confirmation(self, mock_run):
        """Test removing a recipe without confirmation."""
        result = _remove_recipe("zlib/1.2.13#abc123", confirm=False)
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(["conan", "remove", "zlib/1.2.13#abc123", "-c"])
    
    @patch('extensions.commands.cmd_cache_cleanup._run_conan_command')
    @patch('builtins.input', return_value='y')
    def test_remove_with_confirmation_yes(self, mock_input, mock_run):
        """Test removing a recipe with confirmation (user says yes)."""
        result = _remove_recipe("zlib/1.2.13#abc123", confirm=True)
        
        self.assertTrue(result)
        mock_input.assert_called_once()
        mock_run.assert_called_once_with(["conan", "remove", "zlib/1.2.13#abc123", "-c"])
    
    @patch('extensions.commands.cmd_cache_cleanup._run_conan_command')
    @patch('builtins.input', return_value='n')
    def test_remove_with_confirmation_no(self, mock_input, mock_run):
        """Test removing a recipe with confirmation (user says no)."""
        result = _remove_recipe("zlib/1.2.13#abc123", confirm=True)
        
        self.assertFalse(result)
        mock_input.assert_called_once()
        mock_run.assert_not_called()


class TestListCacheRecipes(unittest.TestCase):
    """Test the _list_cache_recipes function."""
    
    @patch('extensions.commands.cmd_cache_cleanup._run_conan_command')
    def test_list_cache_recipes(self, mock_run):
        """Test listing cache recipes."""
        mock_output = json.dumps({"Local Cache": {}})
        mock_run.return_value = mock_output
        
        result = _list_cache_recipes()
        
        self.assertEqual(result, {"Local Cache": {}})
        mock_run.assert_called_once_with(["conan", "list", "*:*", "-c", "-f", "json"])
    
    @patch('extensions.commands.cmd_cache_cleanup._run_conan_command')
    def test_list_cache_recipes_invalid_json(self, mock_run):
        """Test listing cache recipes with invalid JSON."""
        with patch('extensions.commands.cmd_cache_cleanup.ConanException', ConanException):
            mock_run.return_value = "invalid json"
            
            with self.assertRaises(ConanException):
                _list_cache_recipes()


if __name__ == '__main__':
    unittest.main()
