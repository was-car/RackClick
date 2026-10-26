"""Approved schema7 artifact transition61 -> 62; no arbitrary manifest inputs."""
import sys
from qa_artifact7_update import main, TRANSITION62


if __name__ == '__main__':
    sys.exit(main(default_transition=TRANSITION62))
