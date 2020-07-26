import sys

sys.path.append('.')

from kenkenjr.utils import Log
from kenkenjr.bot import Kenken


if __name__ == '__main__':
    Log.auto('running codes...')
    kenken = Kenken()
