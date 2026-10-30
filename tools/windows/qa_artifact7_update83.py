"""Approved schema7 artifact transition68 -> 83; no arbitrary manifest inputs."""
import sys
from qa_artifact7_update import main, TRANSITION83


if __name__ == '__main__':
    sys.exit(main(default_transition=TRANSITION83))
