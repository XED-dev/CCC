"""ccc.system.self_heal — Self-Heal-Helper für apt/dpkg/Pro-Notice.

Module:
- safe_purge: apt-get purge mit Cascade-Schutz via --simulate + Whitelist
- pro_notice: non-destruktive Ubuntu-Pro-Werbung-Deaktivierung
- dpkg: Composite (snap-purge + dpkg-cfg + apt-fix + autoremove)
"""

from ccc.system.self_heal.dpkg import self_heal_dpkg
from ccc.system.self_heal.pro_notice import disable_pro_notice
from ccc.system.self_heal.safe_purge import safe_purge

__all__ = ["safe_purge", "disable_pro_notice", "self_heal_dpkg"]
