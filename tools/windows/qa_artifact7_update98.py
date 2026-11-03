"""Approved schema7 artifact transition83 -> 98; no arbitrary manifest inputs."""
import sys
from qa_artifact7_update import main, TRANSITION98

if __name__ == '__main__':
    sys.exit(main(default_transition=TRANSITION98))
