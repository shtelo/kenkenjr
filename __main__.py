import sys

sys.path.append('.')

from kenkenjr.modules import Kenken
from kenkenjr.utils import Log

if __name__ == '__main__':
    Log.auto('running codes...')
    kenken = Kenken()
