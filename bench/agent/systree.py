"""Simulated Ubuntu 24.04 system tree around the sandbox home.

Owner's rule (2026-10-28): the agent and the PC are one, so the agent may read anywhere on the
machine. The tree is simulated (never the real host: no leak of the real environment) and
consistent with the simulated machine (simsys.py): processes in /proc, input devices in
/dev/input and /proc/bus/input/devices, apt packages in /usr/bin, kernels in /boot, the wifi
interface in /sys/class/net. As for a desktop user, it is read-only at the OS level except
/tmp; `sudo` lifts that (see env.py). Timestamps are fixed (no real time in `ls -l`).
"""
import os
from contextlib import contextmanager
from pathlib import Path

BOOT_AGE_S = 5 * 3600  # the simulated PC was booted 5 h before the case clock
OS_RELEASE = """PRETTY_NAME="Ubuntu 24.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.1 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
UBUNTU_CODENAME=noble
"""
STATIC = {
    "etc/os-release": OS_RELEASE,
    "etc/lsb-release": 'DISTRIB_ID=Ubuntu\nDISTRIB_RELEASE=24.04\nDISTRIB_CODENAME=noble\nDISTRIB_DESCRIPTION="Ubuntu 24.04.1 LTS"\n',
    "etc/hostname": "pc-maison\n",
    "etc/hosts": "127.0.0.1 localhost\n127.0.1.1 pc-maison\n",
    "etc/passwd": ("root:x:0:0:root:/root:/bin/bash\nlp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin\n"
                   "user:x:1000:1000:User,,,:/home/user:/bin/bash\n"),
    "etc/group": "root:x:0:\nsudo:x:27:user\nlpadmin:x:122:user\nuser:x:1000:\n",
    "etc/fstab": "UUID=3b1f9c2e-7d1a-4c55-9b0e-2f6a8c1d4e90 /         ext4 errors=remount-ro 0 1\n"
                 "UUID=6A1C-2F3B                           /boot/efi vfat umask=0077      0 1\n",
    "etc/default/locale": "LANG=fr_FR.UTF-8\n",
    "etc/timezone": "Europe/Paris\n",
    "proc/version": ("Linux version 6.8.0-48-generic (buildd@lcy02-amd64-040) (x86_64-linux-gnu-gcc-13 "
                     "(Ubuntu 13.2.0-23ubuntu4) 13.2.0) #48-Ubuntu SMP PREEMPT_DYNAMIC Fri Sep 27 14:04:52 UTC 2024\n"),
    "proc/uptime": f"{BOOT_AGE_S}.00 {BOOT_AGE_S * 6}.00\n",
    "proc/cpuinfo": "".join(f"processor\t: {i}\nvendor_id\t: GenuineIntel\nmodel name\t: 11th Gen Intel(R) Core(TM) "
                            f"i5-1135G7 @ 2.40GHz\ncpu cores\t: 4\n\n" for i in range(8)),
    "sys/class/bluetooth/hci0/name": "pc-maison\n",
    # NetworkManager (Ubuntu 24.04 desktop defaults); saved connections are dynamic, see sync()
    "etc/NetworkManager/NetworkManager.conf": ("[main]\nplugins=ifupdown,keyfile\n\n[ifupdown]\nmanaged=false\n\n"
                                               "[device]\nwifi.scan-rand-mac-address=no\n"),
    "etc/NetworkManager/conf.d/default-wifi-powersave-on.conf": "[connection]\nwifi.powersave = 3\n",
    "run/systemd/resolve/stub-resolv.conf": ("# This is /run/systemd/resolve/stub-resolv.conf managed by man:systemd-resolved(8).\n"
                                             "# Do not edit.\n\nnameserver 127.0.0.53\noptions edns0 trust-ad\nsearch .\n"),
    # sockets and runtime files of the running services (shown as plain empty files)
    "run/dbus/system_bus_socket": "", "run/cups/cups.sock": "", "run/systemd/journal/socket": "",
    "run/user/1000/bus": "", "run/user/1000/pipewire-0": "", "run/user/1000/pipewire-0-manager": "",
    "run/user/1000/pulse/native": "", "run/user/1000/wayland-0": "", "run/utmp": "",
}
# Never readable by the user (mode 000), as on a real system.
PRIVATE = {"etc/shadow": "", "etc/sudoers": "", "etc/cups/printers.conf": ""}
# Directories only root can open (mode 700 root:root on Ubuntu); filled by sync().
PRIVATE_DIRS = {"etc/NetworkManager/system-connections"}
EMPTY_DIRS = ["root", "media/user", "mnt", "opt", "srv", "var/log", "var/spool/cups", "usr/sbin", "usr/lib", "tmp",
              "etc/NetworkManager/dispatcher.d", "etc/NetworkManager/system-connections", "run/lock", "run/udev",
              "run/NetworkManager/devices", "run/user/1000/systemd", "run/gdm3"]
USB = [  # same devices as `lsusb` in simsys.py
    ("usb1", "1d6b", "0002", "Linux Foundation", "xHCI Host Controller"),
    ("1-2", "03f0", "7d11", "HP", "DeskJet 2700 series"),
    ("1-10", "8087", "0026", "Intel Corp.", "AX201 Bluetooth"),
    ("1-5", "13d3", "56ff", "IMC Networks", "Integrated Camera"),
    ("usb2", "1d6b", "0003", "Linux Foundation", "xHCI Host Controller"),
]
# Built-in input devices: (event, name, bus:vendor:product, handlers, by-path link)
INPUT = [
    ("event0", "Power Button", "0019:0000:0001", "kbd event0", None),
    ("event1", "Lid Switch", "0019:0000:0005", "event1", None),
    ("event2", "AT Translated Set 2 keyboard", "0011:0001:0001", "sysrq kbd leds event2", "platform-i8042-serio-0-event-kbd"),
    ("event3", "ELAN0712:00 04F3:30FD Touchpad", "0018:04f3:30fd", "mouse0 event3", "pci-0000:00:15.0-platform-i2c_designware.0-event-mouse"),
    ("event4", "Video Bus", "0019:0000:0006", "kbd event4", None),
    ("event5", "Integrated Camera: Integrated C", "0003:13d3:56ff", "kbd event5", "pci-0000:00:14.0-usb-0:5:1.0-event"),
]
# Other programs of a stock Ubuntu desktop, listed in /usr/bin (they cannot be run here).
SYSTEM_BINARIES = {"bash", "sh", "sudo", "systemctl", "journalctl", "reboot", "shutdown", "poweroff", "xrandr",
                   "xinput", "python3", "nautilus", "gnome-control-center", "gnome-text-editor", "evince",
                   "eog", "update-manager", "software-properties-gtk", "dpkg", "apt-cache", "curl", "wget",
                   "ssh", "nano", "less", "sort", "uniq", "cut", "tr", "sed", "awk", "touch", "ln", "chmod"}


@contextmanager
def writable(dirs):
    """Let the harness itself update read-only parts of the tree."""
    dirs = [d for d in dirs if d.exists()]
    for d in dirs:
        os.chmod(d, 0o755)
    try:
        yield
    finally:
        for d in dirs:
            if d.exists():  # a killed process's /proc/<pid> is gone
                os.chmod(d, 0o555)


def _write(p, text, mode=0o444):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        os.chmod(p, 0o644)
    p.write_text(text)
    os.chmod(p, mode)


def build(fsroot, stamp):
    """Create the static part of the tree. The home already exists under fsroot/home/user."""
    fsroot = Path(fsroot)
    for rel, text in STATIC.items():
        _write(fsroot / rel, text)
    for rel in PRIVATE:
        _write(fsroot / rel, "", 0o000)
    for rel in EMPTY_DIRS:
        (fsroot / rel).mkdir(parents=True, exist_ok=True)
    for dev, vid, pid, manuf, product in USB:
        d = fsroot / "sys/bus/usb/devices" / dev
        for name, val in (("idVendor", vid), ("idProduct", pid), ("manufacturer", manuf), ("product", product)):
            _write(d / name, val + "\n")
    for d in ("bin", "sbin"):
        (fsroot / d).symlink_to(f"usr/{d}")
    (fsroot / "etc/resolv.conf").symlink_to("../run/systemd/resolve/stub-resolv.conf")
    for rel in ("dev/input/by-path", "dev/input/by-id", "proc/bus/input", "usr/bin", "boot", "sys/class/net"):
        (fsroot / rel).mkdir(parents=True, exist_ok=True)


def nmconnection(ssid, psk):
    """A saved Wi-Fi profile as NetworkManager's keyfile plugin writes it."""
    import uuid
    return (f"[connection]\nid={ssid}\nuuid={uuid.uuid5(uuid.NAMESPACE_DNS, 'nm.' + ssid)}\ntype=wifi\n"
            f"interface-name=wlp2s0\n\n[wifi]\nmode=infrastructure\nssid={ssid}\n\n[wifi-security]\n"
            f"auth-alg=open\nkey-mgmt=wpa-psk\npsk={psk}\n\n[ipv4]\nmethod=auto\n\n[ipv6]\n"
            f"addr-gen-mode=default\nmethod=auto\n\n[proxy]\n")


def desired(state, commands):
    """The dynamic part of the tree, from the simulated machine's state."""
    procs = (state or {}).get("processes", [])
    bt = [d for d in (state or {}).get("bluetooth", {}).get("devices", []) if d.get("connected")]
    pk = (state or {}).get("packages", {})
    apt = [k for k in pk.get("installed", []) if "." not in k]
    kernels = ["6.8.0-48-generic"] + ([] if "linux-image-6.8.0-49-generic" in pk.get("updates", ["linux-image-6.8.0-49-generic"])
                                      else ["6.8.0-49-generic"])
    net = (state or {}).get("network", {})
    mem = (state or {}).get("memory", {}).get("total_mb", 7800)
    return {"procs": [(p["pid"], p["name"], p.get("cpu", 0), p.get("mem_mb", 0)) for p in procs],
            "bt": [(d["name"], d.get("mac", "")) for d in bt], "bin": sorted(set(commands) | set(apt)),
            "kernels": kernels, "wifi_up": bool(net.get("wifi_radio", True) and net.get("connected")),
            "nm": sorted((net.get("known") or {}).items()),
            "mem": (mem, sum(p.get("mem_mb", 0) for p in procs))}


def sync(fsroot, want, stamp):
    """Rewrite the dynamic part of the tree to match `want` (from desired())."""
    fsroot = Path(fsroot)
    proc, devin, bins, boot = fsroot / "proc", fsroot / "dev/input", fsroot / "usr/bin", fsroot / "boot"
    netd = fsroot / "sys/class/net"
    dyn = [fsroot / "proc", fsroot / "proc/bus/input", devin, devin / "by-path", devin / "by-id", bins, boot, netd]
    dyn += [p for p in proc.iterdir() if p.is_dir() and p.name.isdigit()]
    dyn += [p for p in netd.iterdir() if p.is_dir()]
    with writable(dyn):
        for p in [*proc.iterdir()]:
            if p.is_dir() and p.name.isdigit():
                for f in p.iterdir():
                    f.unlink()
                p.rmdir()
        for pid, name, cpu, mem_mb in want["procs"]:
            d = proc / str(pid)
            d.mkdir()
            _write(d / "comm", name + "\n")
            _write(d / "cmdline", f"/usr/bin/{name}\0")
            _write(d / "status", f"Name:\t{name}\nState:\t{'R (running)' if cpu > 50 else 'S (sleeping)'}\n"
                                 f"Pid:\t{pid}\nUid:\t1000\t1000\t1000\t1000\nVmRSS:\t{mem_mb * 1024} kB\n")
            os.chmod(d, 0o555)
        total, used = want["mem"]
        _write(proc / "meminfo", f"MemTotal:       {total * 1024} kB\nMemFree:        {(total - used) * 1024 // 2} kB\n"
                                 f"MemAvailable:   {(total - used) * 1024} kB\n")
        for p in [*devin.iterdir(), *(devin / "by-path").iterdir(), *(devin / "by-id").iterdir()]:
            if not p.is_dir() or p.is_symlink():
                p.unlink()
        devices = list(INPUT) + [(f"event{6 + i}", name, "0005:046d:b016", f"mouse{1 + i} event{6 + i}", None)
                                 for i, (name, _) in enumerate(want["bt"])]
        blocks = []
        for event, name, ids, handlers, path_link in devices:
            _write(devin / event, "", 0o660)
            for h in handlers.split():
                if h.startswith("mouse"):
                    _write(devin / h, "", 0o660)
            if path_link:
                (devin / "by-path" / path_link).symlink_to(f"../{event}")
            bus, vendor, product = ids.split(":")
            blocks.append(f'I: Bus={bus} Vendor={vendor} Product={product} Version=0001\nN: Name="{name}"\n'
                          f"H: Handlers={handlers}\n")
        _write(devin / "mice", "", 0o660)
        (devin / "by-id" / "usb-IMC_Networks_Integrated_Camera_0001-event-if00").symlink_to("../event5")
        _write(fsroot / "proc/bus/input/devices", "\n".join(blocks))
        for p in [*bins.iterdir()]:
            p.unlink()
        for name in want["bin"]:
            _write(bins / name, "\x7fELF\x02\x01\x01\n", 0o555)
        for p in [*boot.iterdir()]:
            p.unlink()
        for k in want["kernels"]:
            for f in ("vmlinuz", "initrd.img", "config", "System.map"):
                _write(boot / f"{f}-{k}", "")
        nmd = fsroot / "etc/NetworkManager/system-connections"
        os.chmod(nmd, 0o755)
        for f in [*nmd.iterdir()]:
            os.chmod(f, 0o644)
            f.unlink()
        boot = stamp - BOOT_AGE_S  # freeze() cannot enter a mode-000 directory: fix the times here
        for ssid, psk in want.get("nm", []):
            f = nmd / f"{ssid}.nmconnection"
            _write(f, nmconnection(ssid, psk), 0o600)
            os.utime(f, (boot, boot))
        os.utime(nmd, (boot, boot))
        os.chmod(nmd, 0o000)
        runnm = fsroot / "run/NetworkManager"
        os.chmod(runnm, 0o755)
        _write(runnm / "resolv.conf", "# Generated by NetworkManager\n" + ("nameserver 192.168.1.1\n" if want["wifi_up"] else ""))
        os.chmod(runnm, 0o555)
        for name, up in (("lo", True), ("wlp2s0", want["wifi_up"])):
            d = netd / name
            if not d.exists():
                d.mkdir()
            os.chmod(d, 0o755)
            _write(d / "operstate", ("up" if up else "down") + "\n")
            os.chmod(d, 0o555)
    freeze(fsroot, stamp)


def freeze(fsroot, stamp):
    """Fixed timestamps outside the home: boot time, so `ls -l /` never shows the real clock."""
    boot = stamp - BOOT_AGE_S
    home = Path(fsroot) / "home"
    for p in [Path(fsroot), *Path(fsroot).rglob("*")]:
        if p == home or home in p.parents:
            continue
        try:
            os.utime(p, (boot, boot), follow_symlinks=False)
        except PermissionError:
            pass


def seal(fsroot):
    """Read-only for the user, except /tmp and the home; private files stay unreadable."""
    fsroot = Path(fsroot)
    home, tmp = fsroot / "home/user", fsroot / "tmp"
    for p in sorted(fsroot.rglob("*"), reverse=True):
        if p.is_symlink() or p == home or home in p.parents or p == tmp or tmp in p.parents:
            continue
        rel = p.relative_to(fsroot).as_posix()
        if rel in PRIVATE or rel in PRIVATE_DIRS or rel == "root":
            os.chmod(p, 0o000)  # the harness runs as the files' owner: 000 is the only way to deny it
        elif p.is_dir():
            os.chmod(p, 0o555)
    os.chmod(tmp, 0o1777)
    os.chmod(fsroot / "home", 0o555)
    os.chmod(fsroot, 0o555)


def unseal(fsroot):
    """Make the whole tree writable again (sudo for one command, or cleanup)."""
    for rel in PRIVATE_DIRS:  # open them first, so the walk below enters them
        d = Path(fsroot) / rel
        if d.is_dir() or d.exists():
            os.chmod(d, 0o700)
    for p in [Path(fsroot), *Path(fsroot).rglob("*")]:
        if p.is_symlink():
            continue
        try:
            os.chmod(p, (p.stat().st_mode | 0o700) if p.is_dir() else (p.stat().st_mode | 0o600))
        except PermissionError:
            pass
