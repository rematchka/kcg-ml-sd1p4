import sys
from typing import List

sys.path.append("./")
from utility.labml.internal.logger.destinations import Destination
from utility.labml.internal.util import is_ipynb, is_ipynb_pycharm


def create_destination() -> List[Destination]:
    from utility.labml.internal.logger.destinations.console import ConsoleDestination

    if is_ipynb():
        from utility.labml.internal.logger.destinations.ipynb import IpynbDestination
        return [IpynbDestination(), ConsoleDestination(False)]
    else:
        return [ConsoleDestination(True)]
