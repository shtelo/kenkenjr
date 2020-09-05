import sys

sys.path.append('.')

if __name__ == '__main__':
    from modules import Kenken
    from utils import Log
    Log.auto('sys.argv: ' + str(sys.argv))
    Log.auto('running codes...')
    kenken = Kenken(sys.argv[1:])
