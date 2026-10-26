"""Approved schema7 artifact transition62 -> 68; no arbitrary manifest inputs."""
import sys
from qa_artifact7_update import main, TRANSITION68


if __name__ == '__main__':
    sys.exit(main(default_transition=TRANSITION68))
