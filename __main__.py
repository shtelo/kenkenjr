import sys

sys.path.append('.')

from modules import Kenken
from utils import Log

if __name__ == '__main__':
    Log.auto('sys.argv: ' + str(sys.argv))
    Log.auto('running codes...')
    kenken = Kenken(sys.argv[1:])
