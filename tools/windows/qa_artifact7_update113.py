"""Approved schema7 artifact transition98 -> 113; no arbitrary manifest inputs."""
import sys
from qa_artifact7_update import main, TRANSITION113

if __name__ == '__main__':
    sys.exit(main(default_transition=TRANSITION113))
