"""ccc.commands.phases — Phase-Funktionen fuer bootstrap_system Verb.

Migriert aus firstboot.sh v0.8.4 Phasen 2-6:
- locale: apply_timezone + apply_locales (SS3.4a)
- apt: apply_packages + apply_dist_upgrade (SS3.4b geplant)
- editor: apply_editor (SS3.4c Reserve-Split)
"""
