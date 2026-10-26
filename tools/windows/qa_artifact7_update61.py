"""Approved schema7 artifact transition60 -> 61; no arbitrary manifest inputs."""
import sys
from qa_artifact7_update import main, TRANSITION61


if __name__ == '__main__':
    sys.exit(main(default_transition=TRANSITION61))
