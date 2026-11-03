"""Approved schema7 artifact transition113 -> 128; no arbitrary manifest inputs."""
import sys
from qa_artifact7_update import main, TRANSITION128

if __name__ == '__main__':
    sys.exit(main(default_transition=TRANSITION128))
