import os
import unittest
loader = unittest.TestLoader()
start_dir = os.path.abspath('test_modules')
suite = loader.discover(start_dir)
runner = unittest.TextTestRunner()
runner.run(suite)