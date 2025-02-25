import os
import sys
import unittest

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'main.env'))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
loader = unittest.TestLoader()
start_dir = os.path.join(os.path.dirname(__file__), 'test_modules')
suite = loader.discover(start_dir)
runner = unittest.TextTestRunner()
result = runner.run(suite)
# Exit with a non-zero status code if tests failed
sys.exit(not result.wasSuccessful())