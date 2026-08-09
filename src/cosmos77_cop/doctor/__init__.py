"""Staged opponent-compatibility probe (``cosmos-cop doctor --json``).

Seven independent stages — reach, contract, locks, handshake, uid, forensics, topology — each
with a green|yellow|red verdict, a human finding and, where possible, a ``fix_line`` the user can
paste to the opponent. The report is one canonical-JSON object on stdout; a refusal is data, not
an error, so the exit code is 0 unless the command line itself was unusable.
"""
