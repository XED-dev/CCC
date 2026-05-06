"""Tests fuer ccc.commands.phases.apt — 5 Cases."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ccc.commands.phases.apt import apply_dist_upgrade, apply_packages


# Case 1: apply_packages install-only (nichts installiert)
@patch("ccc.commands.phases.apt.is_installed", return_value=False)
@patch("ccc.commands.phases.apt.subprocess.run")
def test_apply_packages_install_only(mock_run, mock_installed):
    apply_packages(["htop", "curl"])
    # 1 subprocess-Aufruf: apt-get install
    assert mock_run.call_count == 1
    call_args = mock_run.call_args.args[0]
    assert call_args[:5] == [
        "apt-get", "install", "-y", "-qq", "--no-install-recommends",
    ]
    assert "htop" in call_args
    assert "curl" in call_args


# Case 2: apply_packages no-changes (alle installed, target == installed)
@patch("ccc.commands.phases.apt.is_installed", return_value=True)
@patch("ccc.commands.phases.apt.subprocess.run")
def test_apply_packages_no_changes(mock_run, mock_installed):
    apply_packages(["htop"], menu_list=("htop",))
    # Kein Install (alle installed), kein Remove (htop in target)
    assert mock_run.call_count == 0


# Case 3: apply_packages remove via interactive Whiptail-Yesno=True
@patch("ccc.commands.phases.apt.whiptail.yesno", return_value=True)
@patch("ccc.commands.phases.apt.is_installed")
@patch("ccc.commands.phases.apt.subprocess.run")
def test_apply_packages_remove_with_confirm(mock_run, mock_installed, mock_yesno):
    # pwgen ist installed, aber nicht in target -> to_remove
    # htop ist installed UND in target -> kein remove
    mock_installed.side_effect = lambda name: name in {"htop", "pwgen"}
    apply_packages(
        ["htop"], interactive=True,
        menu_list=("htop", "pwgen"),
    )
    # 1 subprocess-Aufruf: apt-get remove pwgen (kein Install — htop ist installed)
    assert mock_run.call_count == 1
    call_args = mock_run.call_args.args[0]
    assert call_args[:4] == ["apt-get", "remove", "-y", "-qq"]
    assert "pwgen" in call_args
    assert mock_yesno.call_count == 1


# Case 4: apply_dist_upgrade keine Updates -> early return
@patch("ccc.commands.phases.apt.subprocess.run")
def test_apply_dist_upgrade_zero_upgradable(mock_run):
    # _count_upgradable gibt 0 zurueck (apt list --upgradable mit nur Header)
    mock_run.return_value = MagicMock(returncode=0, stdout="Listing...\n")
    apply_dist_upgrade(dist_upgrade=True)
    # Nur EIN subprocess (apt list), kein dist-upgrade/autoremove/autoclean
    assert mock_run.call_count == 1


# Case 5: apply_dist_upgrade mit Updates + dist_upgrade=True -> 3 apt-Schritte
@patch("ccc.commands.phases.apt.subprocess.run")
def test_apply_dist_upgrade_with_dist_upgrade_flag(mock_run):
    # _count_upgradable: 2 Pakete-Zeilen mit "/"
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=(
            "Listing...\n"
            "pkg1/stable 1.0 amd64 [upgradable]\n"
            "pkg2/stable 2.0 amd64 [upgradable]\n"
        )),
        MagicMock(returncode=0),  # dist-upgrade
        MagicMock(returncode=0),  # autoremove
        MagicMock(returncode=0),  # autoclean
    ]
    apply_dist_upgrade(dist_upgrade=True)
    # 4 subprocess: apt list + 3 apt-Schritte
    assert mock_run.call_count == 4
    # dist-upgrade-Args: apt-get + -o APT::...Phased-Updates=true + dist-upgrade
    dist_upgrade_args = mock_run.call_args_list[1].args[0]
    assert dist_upgrade_args[0] == "apt-get"
    assert "dist-upgrade" in dist_upgrade_args
    assert "APT::Get::Always-Include-Phased-Updates=true" in dist_upgrade_args
    assert mock_run.call_args_list[2].args[0][:2] == ["apt-get", "autoremove"]
    assert mock_run.call_args_list[3].args[0][:2] == ["apt-get", "autoclean"]
