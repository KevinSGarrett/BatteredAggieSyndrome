from __future__ import annotations
from second_pass_hardening import rebuild_derivatives

def main() -> None:
    rebuild_derivatives(write_manifest=True)
    print('PASS: all Jira derivatives rebuilt from canonical JSON')

if __name__ == '__main__':
    main()
