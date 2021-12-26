import os
import sys

BASE_PATH = os.path.dirname(sys.argv[0])
IS_PUB = True if sys.argv[0].endswith(".exe") else False
