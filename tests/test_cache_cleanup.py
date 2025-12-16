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
    _list_cache_recipes,
    _remove_recipe,
)


# Helper class for exception testing
class ConanException(Exception):
    """Test exception class to simulate ConanException."""
    pass


# Helper classes to simulate Conan API objects
class MockPackage:
    """Mock package object."""
    def __init__(self, package_id):
        self.id = package_id


class MockRecipeRevisionBundle:
    """Mock recipe revision bundle."""
    def __init__(self, packages=None):
        self.packages = packages or {}


class MockRecipeBundle:
    """Mock recipe bundle."""
    def __init__(self, revisions=None):
        self.revisions = revisions or {}


class MockListResult:
    """Mock ListResult object."""
    def __init__(self, recipe_bundles=None):
        self.recipe_bundles = recipe_bundles or {}


class TestIdentifyRecipesWithoutBinaries(unittest.TestCase):
    """Test the _identify_recipes_without_binaries function."""
    
    def test_empty_cache(self):
        """Test with an empty cache."""
        list_result = MockListResult(recipe_bundles={})
        result = _identify_recipes_without_binaries(list_result)
        
        self.assertEqual(result["recipes_to_remove"], [])
        self.assertEqual(result["recipes_with_binaries"], [])
        self.assertEqual(result["total_inspected"], 0)
    
    def test_all_recipes_have_binaries(self):
        """Test when all recipes have binary packages."""
        # Create mock structure
        recipe_bundles = {
            "zlib/1.2.13": MockRecipeBundle(revisions={
                "abc123": MockRecipeRevisionBundle(packages={
                    "pkg1": MockPackage("pkg1")
                })
            }),
            "openssl/3.0.0": MockRecipeBundle(revisions={
                "def456": MockRecipeRevisionBundle(packages={
                    "pkg2": MockPackage("pkg2")
                })
            })
        }
        list_result = MockListResult(recipe_bundles=recipe_bundles)
        result = _identify_recipes_without_binaries(list_result)
        
        self.assertEqual(len(result["recipes_to_remove"]), 0)
        self.assertEqual(len(result["recipes_with_binaries"]), 2)
        self.assertEqual(result["total_inspected"], 2)
        self.assertIn("zlib/1.2.13#abc123", result["recipes_with_binaries"])
        self.assertIn("openssl/3.0.0#def456", result["recipes_with_binaries"])
    
    def test_all_recipes_without_binaries(self):
        """Test when all recipes lack binary packages."""
        # Create mock structure with empty packages
        recipe_bundles = {
            "zlib/1.2.13": MockRecipeBundle(revisions={
                "abc123": MockRecipeRevisionBundle(packages={})
            }),
            "openssl/3.0.0": MockRecipeBundle(revisions={
                "def456": MockRecipeRevisionBundle(packages={})
            })
        }
        list_result = MockListResult(recipe_bundles=recipe_bundles)
        result = _identify_recipes_without_binaries(list_result)
        
        self.assertEqual(len(result["recipes_to_remove"]), 2)
        self.assertEqual(len(result["recipes_with_binaries"]), 0)
        self.assertEqual(result["total_inspected"], 2)
        self.assertIn("zlib/1.2.13#abc123", result["recipes_to_remove"])
        self.assertIn("openssl/3.0.0#def456", result["recipes_to_remove"])
    
    def test_mixed_recipes(self):
        """Test when some recipes have binaries and some don't."""
        recipe_bundles = {
            "zlib/1.2.13": MockRecipeBundle(revisions={
                "abc123": MockRecipeRevisionBundle(packages={
                    "pkg1": MockPackage("pkg1")
                })
            }),
            "openssl/3.0.0": MockRecipeBundle(revisions={
                "def456": MockRecipeRevisionBundle(packages={})
            }),
            "boost/1.82.0": MockRecipeBundle(revisions={
                "ghi789": MockRecipeRevisionBundle(packages={})
            })
        }
        list_result = MockListResult(recipe_bundles=recipe_bundles)
        result = _identify_recipes_without_binaries(list_result)
        
        self.assertEqual(len(result["recipes_to_remove"]), 2)
        self.assertEqual(len(result["recipes_with_binaries"]), 1)
        self.assertEqual(result["total_inspected"], 3)
        self.assertIn("openssl/3.0.0#def456", result["recipes_to_remove"])
        self.assertIn("boost/1.82.0#ghi789", result["recipes_to_remove"])
        self.assertIn("zlib/1.2.13#abc123", result["recipes_with_binaries"])
    
    def test_multiple_revisions_per_recipe(self):
        """Test when a recipe has multiple revisions."""
        recipe_bundles = {
            "zlib/1.2.13": MockRecipeBundle(revisions={
                "abc123": MockRecipeRevisionBundle(packages={
                    "pkg1": MockPackage("pkg1")
                }),
                "xyz789": MockRecipeRevisionBundle(packages={})
            })
        }
        list_result = MockListResult(recipe_bundles=recipe_bundles)
        result = _identify_recipes_without_binaries(list_result)
        
        self.assertEqual(len(result["recipes_to_remove"]), 1)
        self.assertEqual(len(result["recipes_with_binaries"]), 1)
        self.assertEqual(result["total_inspected"], 2)
        self.assertIn("zlib/1.2.13#abc123", result["recipes_with_binaries"])
        self.assertIn("zlib/1.2.13#xyz789", result["recipes_to_remove"])


class TestRemoveRecipe(unittest.TestCase):
    """Test the _remove_recipe function."""
    
    def test_remove_without_confirmation(self):
        """Test removing a recipe without confirmation."""
        mock_api = MagicMock()
        mock_api.remove.recipe = MagicMock()
        
        result = _remove_recipe(mock_api, "zlib/1.2.13#abc123", confirm=False)
        
        self.assertTrue(result)
        mock_api.remove.recipe.assert_called_once_with(
            pattern="zlib/1.2.13#abc123", confirm=True, remote=None
        )
    
    @patch('builtins.input', return_value='y')
    def test_remove_with_confirmation_yes(self, mock_input):
        """Test removing a recipe with confirmation (user says yes)."""
        mock_api = MagicMock()
        mock_api.remove.recipe = MagicMock()
        
        result = _remove_recipe(mock_api, "zlib/1.2.13#abc123", confirm=True)
        
        self.assertTrue(result)
        mock_input.assert_called_once()
        mock_api.remove.recipe.assert_called_once_with(
            pattern="zlib/1.2.13#abc123", confirm=True, remote=None
        )
    
    @patch('builtins.input', return_value='n')
    def test_remove_with_confirmation_no(self, mock_input):
        """Test removing a recipe with confirmation (user says no)."""
        mock_api = MagicMock()
        
        result = _remove_recipe(mock_api, "zlib/1.2.13#abc123", confirm=True)
        
        self.assertFalse(result)
        mock_input.assert_called_once()
        mock_api.remove.recipe.assert_not_called()


class TestListCacheRecipes(unittest.TestCase):
    """Test the _list_cache_recipes function."""
    
    def test_list_cache_recipes(self):
        """Test listing cache recipes."""
        mock_api = MagicMock()
        mock_list_result = MockListResult(recipe_bundles={})
        mock_api.list.select = MagicMock(return_value=mock_list_result)
        
        result = _list_cache_recipes(mock_api)
        
        self.assertEqual(result, mock_list_result)
        mock_api.list.select.assert_called_once_with(
            pattern="*:*", package_query=None, remote=None, lru=None
        )
    
    def test_list_cache_recipes_error(self):
        """Test listing cache recipes with error."""
        with patch('extensions.commands.cmd_cache_cleanup.ConanException', ConanException):
            mock_api = MagicMock()
            mock_api.list.select = MagicMock(side_effect=Exception("Connection error"))
            
            with self.assertRaises(ConanException):
                _list_cache_recipes(mock_api)


if __name__ == '__main__':
    unittest.main()
