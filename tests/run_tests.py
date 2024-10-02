import unittest
loader = unittest.TestLoader()
start_dir = 'test_modules'
suite = loader.discover(start_dir)
runner = unittest.TextTestRunner()
runner.run(suite)