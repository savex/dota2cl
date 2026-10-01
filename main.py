# Alex Savatieiev, a.savex@gmail.com

import sys

from dotclient import runner


def entrypoint():
    # Run module
    # Do not include any external logic, just bare module run for compatibility
    # with <python -m ...>
    runner.run()
    sys.exit(0)

    # TODO: Cleanups maybe?

    return


if __name__ == "__main__":
    entrypoint()
    sys.exit(0)
