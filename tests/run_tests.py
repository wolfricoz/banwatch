import os
import unittest
loader = unittest.TestLoader()
start_dir = os.path.join(os.path.dirname(__file__), 'test_modules')
suite = loader.discover(start_dir)
runner = unittest.TextTestRunner()
runner.run(suite)