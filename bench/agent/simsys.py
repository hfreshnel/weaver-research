"""Simulated Linux machine for the novice bench: system commands act on a JSON state.

The agent runs the usual CLIs (pactl, nmcli, lp, flatpak, ...) through run_shell. Nothing
real is executed: each handler reads or changes `state`, and appends state-changing actions
to `state["log"]` so checks can test both the final state and the order of actions
(e.g. a snapshot before the updates). Files (scans, conversions, PDFs) are written for real
in the sandbox home.
"""
import copy
import fnmatch
import re

SIM_COMMANDS = {
    "ps", "top", "kill", "pkill", "killall", "df", "du", "free",
    "pactl", "wpctl", "nmcli",
    "lp", "lpr", "lpstat", "lpoptions", "cancel", "cupsenable", "cupsaccept",
    "lpq", "lprm", "lpadmin", "cupsdisable", "which", "uname", "lsb_release", "lsusb",
    "scanimage", "flatpak", "apt", "apt-get", "timeshift", "snapper", "gsettings", "bluetoothctl",
    "libreoffice", "soffice", "pdfunite", "qpdf", "pdfinfo", "magick", "convert", "xdg-open",
    "ping", "ip", "file", "dpkg", "apt-cache",
    "systemctl", "xrandr", "xinput", "reboot", "shutdown", "poweroff",
    "pgrep", "lspci", "lsmod",
}
# systemd units of the simulated desktop: name -> description (aliases below).
UNITS = {"cups": "CUPS Scheduler", "NetworkManager": "Network Manager", "bluetooth": "Bluetooth service",
         "gdm": "GNOME Display Manager", "systemd-udevd": "Rule-based Manager for Device Events and Files",
         "unattended-upgrades": "Unattended Upgrades Shutdown"}
USER_UNITS = {"pipewire": "PipeWire Multimedia Service", "wireplumber": "Multimedia Service Session Manager",
              "pipewire-pulse": "PipeWire PulseAudio"}
UNIT_ALIASES = {"network-manager": "NetworkManager", "gdm3": "gdm", "udev": "systemd-udevd", "cupsd": "cups"}
NO_REBOOT = "Failed to {what}: this session does not allow restarting or stopping the computer."
# Realistic sizes for files the simulated tools create (a marker line + sparse padding).
SIZES = {"scan": 310_000, "convert": 52_000, "image": 420_000}


def write_sized(path, text, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(text.encode())
        f.truncate(max(size, len(text.encode())))


def head_text(path):
    """Marker text at the start of a simulated file, without its sparse padding."""
    with open(path, "rb") as f:
        return f.read(65536).decode(errors="replace").rstrip("\x00")
DESTRUCTIVE = {"kill", "pkill", "killall"}  # a killed program loses its unsaved work


def deep_merge(base, patch):
    out = copy.deepcopy(base)
    for k, v in (patch or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


class SimError(Exception):
    """Command failure: (exit code, message)."""


class SimMachine:
    def __init__(self, state):
        self.s = copy.deepcopy(state)
        self.s.setdefault("log", [])

    def _out(self, path):
        """Every simulated tool that writes a file goes through here: overwriting an existing
        file is destructive (guard + trash), like cp/mv. pdfunite without an output file,
        for instance, silently overwrites its last input."""
        if path.exists():
            self._sb._destructive(self._ev, [path])
            if self._sb.trash:
                self._sb._to_trash(path)
        return path

    def log(self, action, **kw):
        self.s["log"].append({"action": action, **kw})

    # Entry point. `argv` is the raw split command (paths unresolved; handlers resolve them
    # with sb.resolve_in(wd, token)). `sb` also provides the destructive-action guard.
    def run(self, sb, ev, argv, wd):
        cmd = argv[0]
        self._sb, self._ev = sb, ev
        if cmd in DESTRUCTIVE:
            sb._destructive(ev)
        fn = getattr(self, "c_" + cmd.replace("-", "_"))
        try:
            text = fn(sb, argv[1:], wd)
            return f"exit code 0\n{text}".rstrip()
        except SimError as e:
            code, msg = e.args
            return f"exit code {code}\n{msg}"
        except (KeyError, IndexError, ValueError, TypeError):
            # Malformed arguments: answer like a CLI would, never crash the bench.
            return f"exit code 1\n{cmd}: invalid arguments: {' '.join(argv[1:])}"

    # --- processes, disk, memory -------------------------------------------
    def _ps_table(self):
        rows = sorted(self.s["processes"], key=lambda p: -p["cpu"])
        lines = ["USER         PID %CPU %MEM COMMAND"]
        total = self.s["memory"]["total_mb"]
        lines += [f"user      {p['pid']:>6} {p['cpu']:>4.1f} {100 * p['mem_mb'] / total:>4.1f} {p['name']}" for p in rows]
        return "\n".join(lines)

    def c_ps(self, sb, args, wd):
        return self._ps_table()

    def c_top(self, sb, args, wd):
        m = self.s["memory"]
        used = sum(p["mem_mb"] for p in self.s["processes"])
        load = sum(p["cpu"] for p in self.s["processes"]) / 100
        return (f"top - load average: {load:.2f}\nMiB Mem : {m['total_mb']} total, {m['total_mb'] - used} free, {used} used\n\n"
                + self._ps_table())

    def _kill(self, match):
        procs = [p for p in self.s["processes"] if match(p)]
        if not procs:
            raise SimError(1, "no process found")
        for p in procs:
            self.s["processes"].remove(p)
            self.log("kill", name=p["name"], pid=p["pid"])
        return ""

    def c_kill(self, sb, args, wd):
        pids = [int(a) for a in args if a.lstrip("-").isdigit() and not a.startswith("-")]
        if not pids:
            raise SimError(1, "kill: usage: kill [-s sigspec | -n signum | -sigspec] pid")
        return self._kill(lambda p: p["pid"] in pids)

    def c_pkill(self, sb, args, wd):
        names = [a for a in args if not a.startswith("-")]
        return self._kill(lambda p: any(n in p["name"] for n in names))

    def c_killall(self, sb, args, wd):
        names = [a for a in args if not a.startswith("-")]
        return self._kill(lambda p: p["name"] in names)

    def c_df(self, sb, args, wd):
        d = self.s["disk"]
        free = d["total_gb"] - d["used_gb"]
        return (f"Filesystem      Size  Used Avail Use% Mounted on\n/dev/nvme0n1p2  {d['total_gb']}G  {d['used_gb']}G  "
                f"{free}G  {round(100 * d['used_gb'] / d['total_gb'])}% /")

    def c_du(self, sb, args, wd):
        """Apparent sizes (sparse fixture files count at their nominal size)."""
        def size(p):
            return p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

        def fmt(n):
            if "-h" in flags or "-sh" in flags or "-hs" in flags:
                for unit, div in (("G", 1e9), ("M", 1e6), ("K", 1e3)):
                    if n >= div:
                        return f"{n / div:.1f}{unit}"
                return f"{n}B"
            return str(max(1, n // 1024))

        flags = {a for a in args if a.startswith("-")}
        targets = [a for a in args if not a.startswith("-")] or ["."]
        summarize = any("s" in f for f in flags if not f.startswith("--"))
        lines = []
        for t in targets:
            if not sb.resolve_in(wd, t).exists():
                lines.append(f"du: cannot access '{t}': No such file or directory")
                continue
            for p in sorted(sb.resolve_in(wd, x) for x in [t]) if summarize else \
                    [*sorted(d for d in sb.resolve_in(wd, t).rglob("*") if d.is_dir() and not d.is_relative_to(sb.trash_dir)),
                     sb.resolve_in(wd, t)]:
                lines.append(f"{fmt(size(p))}\t{sb.virtual(p)}")
        return "\n".join(lines)

    def c_free(self, sb, args, wd):
        m = self.s["memory"]
        used = sum(p["mem_mb"] for p in self.s["processes"])
        return f"               total        used        free\nMem:          {m['total_mb']}Mi      {used}Mi      {m['total_mb'] - used}Mi"

    # --- audio (PulseAudio / PipeWire) --------------------------------------
    def _sink(self, ref):
        a = self.s["audio"]
        if ref in ("@DEFAULT_SINK@", "@DEFAULT_AUDIO_SINK@"):
            ref = a["default"]
        for i, k in enumerate(a["sinks"]):
            if ref in (k["name"], str(i), str(50 + i)):
                return k
        raise SimError(1, f"Failure: No such entity ({ref})")

    def _set_mute(self, k, v):
        k["muted"] = (not k["muted"]) if v == "toggle" else v in ("1", "true", "yes")
        self.log("audio_mute", sink=k["name"], muted=k["muted"])

    def _set_volume(self, k, v):
        if v.endswith("%"):
            n = float(v.rstrip("%").lstrip("+-"))
            k["volume"] = k["volume"] + n if v.startswith("+") else k["volume"] - n if v.startswith("-") else n
        else:
            k["volume"] = float(v) * 100  # wpctl style: 0.6
        k["volume"] = max(0, min(150, round(k["volume"])))
        self.log("audio_volume", sink=k["name"], volume=k["volume"])

    def c_pactl(self, sb, args, wd):
        a = self.s["audio"]
        if args[:1] == ["list"]:  # pactl list [short] [TYPE], in any order (pactl.c)
            short = any(x in ("short", "s") for x in args[1:])
            kinds = [x for x in args[1:] if x not in ("short", "s")]
            types = ("modules", "sinks", "sources", "sink-inputs", "source-outputs", "clients", "samples", "cards", "message-handlers")
            if len(kinds) > 1 or (kinds and kinds[0] not in types):
                raise SimError(1, "Specify nothing, or one of: " + ", ".join(types))
            args = ["list", *(["short"] if short else []), *kinds]
        sub = " ".join(args[:2])
        if sub == "list short" or args[:3] == ["list", "short", "sinks"] or args[:2] == ["list", "sinks"]:
            if args[:2] == ["list", "sinks"]:
                return "\n\n".join(f"Sink #{i}\n\tName: {k['name']}\n\tDescription: {k['desc']}\n\tMute: {'yes' if k['muted'] else 'no'}\n"
                                   f"\tVolume: {k['volume']}%\n\tActive Port: {'available' if k.get('available', True) else 'not available (unplugged)'}"
                                   for i, k in enumerate(a["sinks"]))
            return "\n".join(f"{i}\t{k['name']}\tmodule-alsa-card.c\ts16le 2ch 48000Hz\t{'RUNNING' if k['name'] == a['default'] else 'SUSPENDED'}"
                             for i, k in enumerate(a["sinks"]))
        if args[:1] == ["list"] and not set(args) & {"sinks"}:
            if "sources" in args:
                return "0\talsa_input.pci-0000_00_1f.3.analog-stereo\tmodule-alsa-card.c\ts16le 2ch 48000Hz\tSUSPENDED"
            return "Sinks:\n" + self.c_pactl(sb, ["list", "sinks"], wd)
        if args[:1] == ["info"]:
            return f"Server Name: PulseAudio (on PipeWire 1.2.7)\nDefault Sink: {a['default']}"
        if args[:1] == ["get-default-sink"]:
            return a["default"]
        if args[:1] == ["set-default-sink"] and len(args) > 1:
            a["default"] = self._sink(args[1])["name"]
            self.log("audio_default", sink=a["default"])
            return ""
        if args[:1] in (["set-source-volume"], ["set-source-mute"], ["set-default-source"], ["set-source-port"],
                        ["set-sink-port"], ["suspend-sink"], ["suspend-source"]) and len(args) > 1:
            if args[0] == "set-sink-port":
                self._sink(args[1])
            elif "source" in args[0] and args[1] not in ("@DEFAULT_SOURCE@", "0", "alsa_input.pci-0000_00_1f.3.analog-stereo"):
                raise SimError(1, "Failure: No such entity")
            return ""  # the microphone is not part of the simulated state
        if args[:1] == ["load-module"] and len(args) > 1:
            return "536870913"
        if args[:1] == ["get-sink-mute"] and len(args) > 1:
            return f"Mute: {'yes' if self._sink(args[1])['muted'] else 'no'}"
        if args[:1] == ["get-sink-volume"] and len(args) > 1:
            return f"Volume: front-left: {self._sink(args[1])['volume']}%"
        if args[:1] == ["set-sink-mute"] and len(args) > 2:
            self._set_mute(self._sink(args[1]), args[2])
            return ""
        if args[:1] == ["set-sink-volume"] and len(args) > 2:
            self._set_volume(self._sink(args[1]), args[2])
            return ""
        known = {"stat", "info", "list", "exit", "upload-sample", "play-sample", "remove-sample", "load-module",
                 "unload-module", "move-sink-input", "move-source-output", "suspend-sink", "suspend-source",
                 "set-card-profile", "get-default-sink", "set-default-sink", "set-sink-port", "get-default-source",
                 "set-default-source", "set-source-port", "get-sink-volume", "set-sink-volume", "get-source-volume",
                 "set-source-volume", "set-sink-input-volume", "set-source-output-volume", "get-sink-mute",
                 "set-sink-mute", "get-source-mute", "set-source-mute", "set-sink-input-mute", "set-source-output-mute",
                 "set-sink-formats", "set-port-latency-offset", "subscribe", "send-message"}
        if not args or args[0] not in known:
            raise SimError(1, "No valid command specified.")
        raise SimError(1, f"pactl: unsupported here: {' '.join(args)}")

    def c_wpctl(self, sb, args, wd):
        a = self.s["audio"]
        if args[:1] in (["status"], []):
            lines = ["Audio", " ├─ Sinks:"]
            for i, k in enumerate(a["sinks"]):
                star = "*" if k["name"] == a["default"] else " "
                lines.append(f" │  {star} {50 + i}. {k['desc']} [vol: {k['volume'] / 100:.2f}{' MUTED' if k['muted'] else ''}]")
            return "\n".join(lines)
        if args[:1] == ["set-default"] and len(args) > 1:
            a["default"] = self._sink(args[1])["name"]
            self.log("audio_default", sink=a["default"])
            return ""
        if args[:1] == ["set-mute"] and len(args) > 2:
            self._set_mute(self._sink(args[1]), args[2])
            return ""
        if args[:1] == ["set-volume"] and len(args) > 2:
            self._set_volume(self._sink(args[1]), args[2])
            return ""
        if args[:1] == ["get-volume"] and len(args) > 1:
            k = self._sink(args[1])
            return f"Volume: {k['volume'] / 100:.2f}{' [MUTED]' if k['muted'] else ''}"
        if args and args[0] not in ("status", "get-volume", "inspect", "set-default", "set-volume", "set-mute",
                                    "set-profile", "set-route", "clear-default", "settings", "set-log-level"):
            raise SimError(1, "Usage:\n  wpctl [OPTION…] COMMAND [COMMAND_OPTIONS] - WirePlumber Control CLI\n\nCommands:\n"
                              "  status\n  get-volume ID\n  inspect ID\n  set-default ID\n  set-volume ID VOL[%][-/+]\n"
                              "  set-mute ID 1|0|toggle\n  set-profile ID INDEX\n  set-route ID INDEX\n  clear-default [ID]\n"
                              "  settings [KEY] [VAL]\n  set-log-level [ID] LEVEL\n\nPass -h after a command to see command-specific options")
        raise SimError(1, f"wpctl: unsupported here: {' '.join(args)}")

    # --- network (NetworkManager) -------------------------------------------
    def _autoconnect(self):
        n = self.s["network"]
        if n["wifi_radio"] and not n["connected"]:
            for ap in n["visible"]:
                if ap["ssid"] in n["known"]:
                    n["connected"] = ap["ssid"]
                    self.log("wifi_connected", ssid=ap["ssid"])
                    break

    def c_nmcli(self, sb, args, wd):
        n = self.s["network"]
        a, skip = [], False
        for x in args:  # drop global options (-t, -p, -g FIELDS, -f FIELDS)
            if skip:
                skip = False
            elif x in ("-g", "-f", "--get-values", "--fields"):
                skip = True
            elif not x.startswith("-"):
                a.append(x)
        head = [x[:3] for x in a[:3]]
        if head[:1] in (["gen"], ["g"]) or a == []:
            state = "connected" if n["connected"] else "disconnected"
            return f"STATE         CONNECTIVITY  WIFI-HW  WIFI\n{state:<13} {'full' if n['connected'] else 'none':<13} enabled  {'enabled' if n['wifi_radio'] else 'disabled'}"
        if head[:1] in (["rad"], ["r"]):
            if len(a) >= 3 and a[2] in ("on", "off"):
                n["wifi_radio"] = a[2] == "on"
                if not n["wifi_radio"]:
                    n["connected"] = None
                self.log("wifi_radio", on=n["wifi_radio"])
                self._autoconnect()
                return ""
            return f"WIFI-HW  WIFI\nenabled  {'enabled' if n['wifi_radio'] else 'disabled'}"
        if head[:2] in (["dev", "wif"], ["d", "wif"], ["d", "w"], ["dev", "w"]):
            if not n["wifi_radio"]:
                raise SimError(10, "Error: Wi-Fi radio is disabled (airplane mode?). Turn it on with: nmcli radio wifi on")
            if len(a) < 3 or a[2] in ("list", "l", "rescan", "r"):
                rows = [f"{'*' if ap['ssid'] == n['connected'] else ' '} {ap['ssid']:<16} {ap['signal']:>3}  {ap.get('security', 'WPA2')}" for ap in n["visible"]]
                return "IN-USE SSID             SIGNAL SECURITY\n" + "\n".join(rows)
            if a[2] not in ("connect", "c") and "show-password".startswith(a[2]):
                if not n["connected"]:
                    raise SimError(10, "Error: no active Wi-Fi connection.")
                return f"SSID: {n['connected']}\nSecurity: WPA\nPassword: {n['known'].get(n['connected'], '')}"
            if not any(w.startswith(a[2]) for w in ("list", "connect", "hotspot", "rescan", "show-password")):
                raise SimError(2, f"Error: argument '{a[2]}' not understood. Try passing --help instead.")
            if a[2] in ("connect", "c"):
                ssid = a[3] if len(a) > 3 else ""
                if ssid not in [ap["ssid"] for ap in n["visible"]]:
                    raise SimError(10, f"Error: No network with SSID '{ssid}' found.")
                pw = a[a.index("password") + 1] if "password" in a and a.index("password") + 1 < len(a) else n["known"].get(ssid)
                if pw != n["passwords"].get(ssid):
                    raise SimError(4, "Error: Connection activation failed: Secrets were required, but not provided (wrong password).")
                n["known"][ssid] = pw
                n["connected"] = ssid
                self.log("wifi_connected", ssid=ssid)
                return f"Device 'wlp2s0' successfully activated with '{ssid}'."
        if head[:1] in (["dev"], ["d"]) and len(a) >= 2 and a[1] == "set":
            if len(a) < 3 or a[2] != "wlp2s0":
                raise SimError(10, f"Error: Device '{a[2] if len(a) > 2 else ''}' not found.")
            props = a[3:]
            if not props:
                raise SimError(2, "Error: no property specified.")
            for k in props[::2]:
                if k not in ("autoconnect", "managed"):
                    raise SimError(2, f"Error: invalid property '{k}', allowed: autoconnect, managed.")
            return ""
        if head[:1] in (["dev"], ["d"]) and len(a) >= 2 and a[1] in ("show", "sh"):
            ip = "192.168.1.34/24" if n["connected"] else "--"
            return (f"GENERAL.DEVICE:  wlp2s0\nGENERAL.TYPE:    wifi\nGENERAL.STATE:   {'100 (connected)' if n['connected'] else '30 (disconnected)'}\n"
                    f"GENERAL.CONNECTION: {n['connected'] or '--'}\nIP4.ADDRESS[1]:  {ip}\nIP4.GATEWAY:     {'192.168.1.1' if n['connected'] else '--'}")
        if head[:1] in (["dev"], ["d"]) and len(a) >= 3 and a[1] in ("connect", "c"):
            if a[2] != "wlp2s0":
                raise SimError(10, f"Error: Device '{a[2]}' not found.")
            if not n["wifi_radio"]:
                raise SimError(4, "Error: Connection activation failed: Wi-Fi radio is disabled.")
            self._autoconnect()
            if not n["connected"]:
                raise SimError(4, "Error: Connection activation failed: no known network in range.")
            return f"Device 'wlp2s0' successfully activated with '{n['connected']}'."
        if head[:1] in (["dev"], ["d"]) and (len(a) < 2 or a[1] in ("status", "s")):
            state = f"connected     {n['connected']}" if n["connected"] else ("disconnected  --" if n["wifi_radio"] else "unavailable   --")
            return f"DEVICE  TYPE  STATE         CONNECTION\nwlp2s0  wifi  {state}"
        if head[:1] in (["con"], ["c"]):
            if len(a) >= 3 and a[1] == "up":
                ssid = a[2]
                if ssid not in n["known"]:
                    raise SimError(10, f"Error: unknown connection '{ssid}'.")
                if not n["wifi_radio"]:
                    raise SimError(4, "Error: Connection activation failed: Wi-Fi radio is disabled.")
                n["connected"] = ssid
                self.log("wifi_connected", ssid=ssid)
                return "Connection successfully activated"
            return "NAME             TYPE  DEVICE\n" + "\n".join(f"{k:<16} wifi  {'wlp2s0' if k == n['connected'] else '--'}" for k in n["known"])
        raise SimError(2, f"nmcli: unsupported here: {' '.join(args)}")

    def c_ping(self, sb, args, wd):
        host = next((a for a in args if not a.startswith("-") and not a.isdigit()), "")
        if not self.s["network"]["connected"]:
            raise SimError(2, f"ping: connect: Network is unreachable")
        return (f"PING {host} 56(84) bytes of data.\n64 bytes from {host}: icmp_seq=1 ttl=117 time=14.2 ms\n"
                f"64 bytes from {host}: icmp_seq=2 ttl=117 time=13.9 ms\n--- {host} ping statistics ---\n2 packets transmitted, 2 received, 0% packet loss")

    def c_ip(self, sb, args, wd):
        """iproute2. Reads for everyone; `ip link set` needs root and fails under RF-kill."""
        n = self.s["network"]
        a = [x for x in args if x not in ("-c", "-color", "--color", "-4", "-6", "-s", "-d", "-details")]
        brief = any(x in ("-br", "-brief") for x in a)
        oneline = any(x in ("-o", "-oneline") for x in a)
        a = [x for x in a if x not in ("-br", "-brief", "-o", "-oneline")]
        if a and a[0].startswith("-"):
            raise SimError(255, f'Option "{a[0]}" is unknown, try "ip -help".')
        obj, rest = (a[0], a[1:]) if a else ("", [])
        conn = n["connected"]
        admin_up = n["wifi_radio"] and (conn or not n.get("link_down"))
        flags = ("BROADCAST,MULTICAST,UP,LOWER_UP" if conn else "NO-CARRIER,BROADCAST,MULTICAST,UP") if admin_up \
            else "BROADCAST,MULTICAST"
        state = "UP" if conn else "DOWN"
        mac = "3c:58:c2:1a:7e:05"
        if not obj or "help".startswith(obj):
            raise SimError(255, "Usage: ip [ OPTIONS ] OBJECT { COMMAND | help }\n"
                                "where  OBJECT := { address | link | neighbor | route | rule | ... }")
        if "link".startswith(obj) and rest[:1] == ["set"]:
            dev = rest[1] if len(rest) > 1 else ""
            if dev in ("dev",):
                dev = rest[2] if len(rest) > 2 else ""
            if dev not in ("lo", "wlp2s0"):
                raise SimError(1, f'Cannot find device "{dev}"')
            if not sb.sudo:
                raise SimError(2, "RTNETLINK answers: Operation not permitted")
            if dev == "wlp2s0" and "up" in rest:
                if not n["wifi_radio"]:
                    raise SimError(2, "RTNETLINK answers: Operation not possible due to RF-kill")
                n["link_down"] = False
                self.log("link_up", dev=dev)
                self._autoconnect()
            elif dev == "wlp2s0" and "down" in rest:
                n["link_down"] = True
                if conn:
                    n["connected"] = False
                self.log("link_down", dev=dev)
            return ""
        if obj in ("a", "ad", "add", "addr", "addre", "addres", "address", "l", "li", "lin", "link"):
            show = lambda w: "show".startswith(w) or "list".startswith(w) or w == "lst"
            if rest and show(rest[0]):
                rest = rest[1:]
            elif rest and rest[0] not in ("dev", "lo", "wlp2s0"):
                if not sb.sudo:
                    raise SimError(2, "RTNETLINK answers: Operation not permitted")
                raise SimError(2, f"ip: unsupported here: {' '.join(args)}")
            names = [x for x in rest if x != "dev"]
            if names and names[0] not in ("lo", "wlp2s0"):
                raise SimError(1, f'Device "{names[0]}" does not exist.')
            want = names[0] if names else None
            link = obj.startswith("l")
            if brief:
                rows = [("lo", "UNKNOWN", "00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>" if link else "127.0.0.1/8 ::1/128"),
                        ("wlp2s0", state, f"{mac} <{flags}>" if link else ("192.168.1.34/24" if conn else ""))]
                return "\n".join(f"{d:<16} {s:<14} {x}".rstrip() for d, s, x in rows if want in (None, d))
            lo = ("1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000\n"
                  "    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00")
            wl = (f"2: wlp2s0: <{flags}> mtu 1500 qdisc noqueue state {state} mode DORMANT group default qlen 1000\n"
                  f"    link/ether {mac} brd ff:ff:ff:ff:ff:ff")
            lo_a = "inet 127.0.0.1/8 scope host lo\n       valid_lft forever preferred_lft forever"
            wl_a = ("inet 192.168.1.34/24 brd 192.168.1.255 scope global dynamic noprefixroute wlp2s0\n"
                    "       valid_lft 86213sec preferred_lft 86213sec")
            if oneline:  # one record per line, continuation lines joined with a backslash
                if link:
                    rows = [("lo", lo.replace("\n", "\\")), ("wlp2s0", wl.replace("\n", "\\"))]
                else:
                    rows = [("lo", "1: lo    " + lo_a.replace("\n", "\\"))]
                    if conn:
                        rows.append(("wlp2s0", "2: wlp2s0    " + wl_a.replace("\n", "\\")))
                return "\n".join(x for d, x in rows if want in (None, d))
            if not link:
                lo = lo.replace(" mode DEFAULT", "") + "\n    " + lo_a
                wl = wl.replace(" mode DORMANT", "")
                if conn:
                    wl += "\n    " + wl_a
            return "\n".join(x for d, x in (("lo", lo), ("wlp2s0", wl)) if want in (None, d))
        if obj in ("r", "ro", "rou", "rout", "route"):
            if rest and not ("show".startswith(rest[0]) or "list".startswith(rest[0]) or rest[0] in ("get", "g")):
                if not sb.sudo:
                    raise SimError(2, "RTNETLINK answers: Operation not permitted")
                raise SimError(2, f"ip: unsupported here: {' '.join(args)}")
            if not conn:
                if rest[:1] in (["get"], ["g"]):
                    raise SimError(2, "RTNETLINK answers: Network is unreachable")
                return ""
            return ("default via 192.168.1.1 dev wlp2s0 proto dhcp src 192.168.1.34 metric 600\n"
                    "192.168.1.0/24 dev wlp2s0 proto kernel scope link src 192.168.1.34 metric 600")
        if obj in ("n", "ne", "nei", "neig", "neigh", "neighbor", "neighbour"):
            return "192.168.1.1 dev wlp2s0 lladdr e4:5d:51:8a:20:11 REACHABLE" if conn else ""
        raise SimError(1, f'Object "{obj}" is unknown, try "ip help".')

    def c_file(self, sb, args, wd):
        out = []
        for a in [x for x in args if not x.startswith("-")]:
            p = sb.resolve_in(wd, a)
            if not p.exists():
                out.append(f"{a}: cannot open (No such file or directory)")
                continue
            kind = {".jpg": "JPEG image data, JFIF standard 1.01", ".jpeg": "JPEG image data", ".png": "PNG image data",
                    ".pdf": "PDF document, version 1.7", ".odt": "OpenDocument Text", ".mkv": "Matroska data",
                    ".mp4": "ISO Media, MP4 v2", ".iso": "ISO 9660 CD-ROM filesystem data"}.get(p.suffix.lower(), "ASCII text")
            if p.is_dir():
                kind = "directory"
            elif "6000x4000" in head_text(p):
                kind += ", 6000x4000"
            out.append(f"{a}: {kind}")
        return "\n".join(out)

    def c_pdfinfo(self, sb, args, wd):
        """poppler-utils 24.02 output. Creator/Producer follow the program that wrote the file
        (scan, LibreOffice export, pdfunite/qpdf merge); dates come from the case clock."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        f = next((a for a in args if not a.startswith("-")), None)
        if f is None:
            raise SimError(99, "pdfinfo version 24.02.0\nCopyright 2005-2024 The Poppler Developers - http://poppler.freedesktop.org\n"
                               "Copyright 1996-2011, 2022 Glyph & Cog, LLC\nUsage: pdfinfo [options] <PDF-file>")
        p = sb.resolve_in(wd, f)
        if not p.is_file():
            raise SimError(1, f"I/O Error: Couldn't open file '{f}': No such file or directory.")
        head = head_text(p)
        if not head.startswith("%SIM-PDF"):
            raise SimError(1, "Syntax Warning: May not be a PDF file (continuing anyway)\nSyntax Error: Couldn't find trailer dictionary\n"
                              "Syntax Error: Couldn't find trailer dictionary\nSyntax Error: Couldn't read xref table")
        first = head.splitlines()[0]
        parts = [ln for ln in head.splitlines() if ln.startswith("%SIM-") and ln != "%SIM-PDF merged"]
        pages = max(1, len(parts))
        when = datetime.fromtimestamp(p.stat().st_mtime, ZoneInfo("Europe/Paris")).strftime("%a %b %d %H:%M:%S %Y %Z")
        info = []
        if "converted from" in first:
            info = [("Creator", "Writer"), ("Producer", "LibreOffice 24.2"), ("CreationDate", when)]
        elif "scan of" in first or first.startswith("%SIM-PDF dossier"):
            info = [("Creator", "scanimage"), ("Producer", "sane-backends 1.2.1"), ("CreationDate", when)]
        rows = info + [("Custom Metadata", "no"), ("Metadata Stream", "no"), ("Tagged", "yes" if "converted from" in first else "no"),
                       ("UserProperties", "no"), ("Suspects", "no"), ("Form", "none"), ("JavaScript", "no"),
                       ("Pages", str(pages)), ("Encrypted", "no"), ("Page size", "595.276 x 841.89 pts (A4)"),
                       ("Page rot", "0"), ("File size", f"{p.stat().st_size} bytes"), ("Optimized", "no"),
                       ("PDF version", "1.7" if "converted from" in first else "1.4")]
        return "\n".join(f"{k + ':':<15} {v}" for k, v in rows)

    # --- printing (CUPS) -----------------------------------------------------
    def _printer(self, name=None):
        p = self.s["printers"]
        name = name or p["default"]
        for x in p["list"]:
            if x["name"] == name:
                return x
        raise SimError(1, f"lp: The printer or class does not exist: {name}")

    def _print(self, sb, args, wd, printer_flag):
        p = self.s["printers"]
        printer, opts, files, copies = None, dict(p.get("defaults", {})), [], 1
        it = iter(range(len(args)))
        for i in it:
            a = args[i]
            if a in (printer_flag, "-d", "-P") and i + 1 < len(args):
                printer = args[i + 1]; next(it)
            elif a == "-o" and i + 1 < len(args):
                k, _, v = args[i + 1].partition("="); opts[k] = v or "true"; next(it)
            elif a in ("-n", "-#") and i + 1 < len(args):
                copies = int(args[i + 1]); next(it)
            elif not a.startswith("-"):
                files.append(a)
        if not files:
            raise SimError(1, "lp: no file given")
        pr = self._printer(printer)
        opts = {**pr.get("defaults", {}), **opts}
        ids = []
        for f in files:
            path = sb.resolve_in(wd, f)
            if not path.is_file():
                raise SimError(1, f"lp: Error - unable to access \"{sb.virtual(path)}\" - No such file or directory")
            p["next_id"] = p.get("next_id", 100) + 1
            job = {"id": p["next_id"], "printer": pr["name"], "file": sb.virtual(path), "options": opts, "copies": copies,
                   "state": "completed" if pr["enabled"] else "pending"}
            p["jobs"].append(job)
            self.log("print", job=job["id"], file=job["file"], options=opts)
            ids.append(f"request id is {pr['name']}-{job['id']} (1 file(s))")
        return "\n".join(ids)

    def c_lp(self, sb, args, wd):
        return self._print(sb, args, wd, "-d")

    def c_lpr(self, sb, args, wd):
        return self._print(sb, args, wd, "-P")

    def c_lpstat(self, sb, args, wd):
        """CUPS 2.4 lpstat: each option prints its own section (-r scheduler, -d default, -v
        devices, -a accepting, -p printers, -o jobs, -t all, -s summary). No option = -o.
        Job lines show id, owner, size and date (file names are lpq's)."""
        from datetime import datetime, timedelta
        p = self.s["printers"]
        now = datetime.fromisoformat(sb.now)
        fmt = lambda d: d.strftime("%a %d %b %Y %H:%M:%S CET")
        boot, yesterday = fmt(now - timedelta(hours=5)), fmt(now - timedelta(hours=19, minutes=47))
        flags = set("".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--")))
        names = [a for a in args if not a.startswith("-")]
        if "t" in flags:
            flags |= set("rdvapo")
        if "s" in flags:
            flags |= set("dv")
        if not flags & set("rdvapo"):
            flags.add("o")
        active = [j for j in p["jobs"] if j["state"] not in ("completed", "cancelled")]
        printers = [x for x in p["list"] if not names or x["name"] in names or "o" in flags]
        out = []
        if "r" in flags:
            out.append("scheduler is running")
        if "d" in flags:
            out.append(f"system default destination: {p['default']}" if p.get("default") else "no system default destination")
        if "v" in flags:
            out += [f"device for {x['name']}: usb://HP/DeskJet%202700%20series?serial=CN2B47F0KJ&interface=1" for x in printers]
        if "a" in flags:
            out += [f"{x['name']} accepting requests since {boot}" for x in printers]
        if "p" in flags:
            for x in printers:
                job = next((j for j in active if j["printer"] == x["name"]), None)
                if not x["enabled"]:
                    out.append(f"printer {x['name']} disabled since {yesterday} -\n\t{x.get('reason', 'Paused')}")
                elif job:
                    out.append(f"printer {x['name']} now printing {x['name']}-{job['id']}.  enabled since {boot}")
                else:
                    out.append(f"printer {x['name']} is idle.  enabled since {boot}")
        if "o" in flags:
            for j in active:
                if names and j["printer"] not in names and f"{j['printer']}-{j['id']}" not in names:
                    continue
                out.append(f"{j['printer'] + '-' + str(j['id']):<24}user            1024   {yesterday if j['state'] == 'stuck' else fmt(now)}")
        bad = [n for n in names if n not in [x["name"] for x in p["list"]] and not any(n == f"{j['printer']}-{j['id']}" for j in p["jobs"])]
        if bad:
            raise SimError(1, f'lpstat: Invalid destination name in list "{bad[0]}".')
        return "\n".join(out)

    def c_lpoptions(self, sb, args, wd):
        p = self.s["printers"]
        for i, a in enumerate(args):
            if a == "-o" and i + 1 < len(args):
                k, _, v = args[i + 1].partition("=")
                p.setdefault("defaults", {})[k] = v
                self.log("print_defaults", option=k, value=v)
        return " ".join(f"{k}={v}" for k, v in p.get("defaults", {}).items()) or "(no default options)"

    def c_cancel(self, sb, args, wd):
        p = self.s["printers"]
        if "-a" in args:
            targets = [j for j in p["jobs"] if j["state"] != "completed"]
        else:
            ids = {a.split("-")[-1] for a in args if not a.startswith("-")}
            targets = [j for j in p["jobs"] if str(j["id"]) in ids]
        if not targets:
            raise SimError(1, "cancel: no such job")
        for j in targets:
            j["state"] = "cancelled"
            self.log("print_cancel", job=j["id"])
        return ""

    def c_cupsenable(self, sb, args, wd):
        for name in [a for a in args if not a.startswith("-")] or [self.s["printers"]["default"]]:
            pr = self._printer(name)
            pr["enabled"] = True
            self.log("printer_enabled", printer=name)
            for j in self.s["printers"]["jobs"]:
                if j["printer"] == name and j["state"] == "pending":
                    j["state"] = "completed"
                elif j["printer"] == name and j["state"] == "stuck":
                    pr["enabled"] = False  # the corrupt job blocks the queue again
                    pr["reason"] = f"Filter failed (job {j['id']})"
                    return f"warning: job {j['id']} failed again, printer {name} paused (Filter failed)"
        return ""

    def c_cupsaccept(self, sb, args, wd):
        return ""

    def c_cupsdisable(self, sb, args, wd):
        for name in [a for a in args if not a.startswith("-")] or [self.s["printers"]["default"]]:
            pr = self._printer(name)
            pr["enabled"], pr["reason"] = False, "Paused"
            self.log("printer_disabled", printer=name)
        return ""

    def c_lpadmin(self, sb, args, wd):
        # The non-destructive forms a desktop user (lpadmin group on Ubuntu) would use:
        # -d NAME (default), -p NAME with -E (after -p: enable and accept jobs), -o NAME-default=VALUE
        # (server default for a job option), -o PPDOPTION=VALUE, -D / -L (description, location).
        # -E before -p / -d means TLS encryption, as in CUPS. Deleting a printer (-x) is not simulated.
        if "-d" in args:
            name = args[args.index("-d") + 1]
            self._printer(name)
            self.s["printers"]["default"] = name
            return ""
        dest, enable, opts, i = None, False, [], 0
        while i < len(args):
            a = args[i]
            if a == "-p" and i + 1 < len(args):
                dest = self._printer(args[i + 1]); i += 1
            elif a == "-E":
                enable = enable or dest is not None
            elif a == "-o" and i + 1 < len(args):
                opts.append(args[i + 1]); i += 1
            elif a in ("-D", "-L") and i + 1 < len(args):
                i += 1
            elif a in ("-x", "-c", "-r", "-i", "-m", "-P", "-v", "-u", "-R", "-U", "-h") or a.startswith(("-m", "-v", "-P")):
                raise SimError(1, f"lpadmin: unsupported here: {' '.join(args)}")
            elif a.startswith("-"):
                raise SimError(1, f'lpadmin: Unknown option "{a[1:]}".')
            else:
                raise SimError(1, f'lpadmin: Unknown argument "{a}".')
            i += 1
        if dest is None:
            if opts:
                raise SimError(1, "lpadmin: Unable to set the printer options:\n         You must specify a printer name first.")
            raise SimError(1, f"lpadmin: unsupported here: {' '.join(args)}")
        duplex = {"DuplexNoTumble": "two-sided-long-edge", "DuplexTumble": "two-sided-short-edge", "None": "one-sided"}
        for o in opts:
            k, _, v = o.partition("=")
            if k.endswith("-default"):
                dest.setdefault("defaults", {})[k[:-len("-default")]] = v
            elif k == "Duplex" and v in duplex:
                dest.setdefault("defaults", {})["sides"] = duplex[v]
            else:
                continue
            self.log("printer_defaults", printer=dest["name"], option=k, value=v)
        if enable:
            return self.c_cupsenable(sb, [dest["name"]], wd)
        return ""

    def c_lpq(self, sb, args, wd):
        p = self.s["printers"]
        name = args[args.index("-P") + 1] if "-P" in args else p["default"]
        pr = self._printer(name)
        jobs = [j for j in p["jobs"] if j["state"] not in ("completed", "cancelled") and ("-a" in args or j["printer"] == name)]
        lines = [f"{name} is {'ready' if pr['enabled'] else 'not ready'}"]
        if not jobs:
            return "\n".join(lines + ["no entries"])
        lines.append("Rank    Owner   Job     File(s)                         Total Size")
        ranks = ["active"] + [f"{i}{'nd' if i == 2 else 'rd' if i == 3 else 'th'}" for i in range(2, 10)]
        for rank, j in zip(ranks if pr["enabled"] else ["1st"] + ranks[1:], jobs):
            lines.append(f"{rank:<8}user    {j['id']:<8}{j['file'].rsplit('/', 1)[-1]:<32}1024 bytes")
        return "\n".join(lines)

    def c_lprm(self, sb, args, wd):
        p = self.s["printers"]
        rest = [a for i, a in enumerate(args) if a != "-P" and (i == 0 or args[i - 1] != "-P")]
        if "-" in rest:
            return self.c_cancel(sb, ["-a"], wd) if any(j["state"] != "completed" for j in p["jobs"]) else ""
        ids = [a for a in rest if not a.startswith("-")]
        if not ids:  # lprm alone removes the current job
            active = [j for j in p["jobs"] if j["state"] not in ("completed", "cancelled")]
            ids = [str(active[0]["id"])] if active else []
        if not ids:
            return ""
        try:
            return self.c_cancel(sb, ids, wd)
        except SimError:
            raise SimError(1, f"lprm: Job #{ids[0]} does not exist.")

    # --- system information (read-only) --------------------------------------
    def c_which(self, sb, args, wd):
        from env import SHELL_ALLOWED  # lazy: env imports this module
        from systree import SYSTEM_BINARIES
        found = [f"/usr/bin/{a}" for a in args
                 if a in SIM_COMMANDS | SHELL_ALLOWED | SYSTEM_BINARIES | set(self._apt_installed())]
        if len(found) < len([a for a in args if not a.startswith("-")]):
            raise SimError(1, "\n".join(found))
        return "\n".join(found)

    def c_uname(self, sb, args, wd):
        parts = {"-s": "Linux", "-n": "pc-maison", "-r": "6.8.0-48-generic",
                 "-v": "#48-Ubuntu SMP PREEMPT_DYNAMIC Fri Sep 27 14:04:52 UTC 2024", "-m": "x86_64"}
        if "-a" in args or "--all" in args:
            return " ".join(parts.values()) + " x86_64 x86_64 GNU/Linux"
        return " ".join(v for k, v in parts.items() if k in args) or "Linux"

    def c_lsb_release(self, sb, args, wd):
        rows = {"-i": ("Distributor ID", "Ubuntu"), "-d": ("Description", "Ubuntu 24.04.1 LTS"),
                "-r": ("Release", "24.04"), "-c": ("Codename", "noble")}
        flags = set()
        for a in args:
            flags |= {f"-{c}" for c in a.lstrip("-")} if not a.startswith("--") else {"-" + a[2]}
        keys = list(rows) if "-a" in flags else [k for k in rows if k in flags]
        if "-s" in flags:
            return "\n".join(rows[k][1] for k in keys)
        return "\n".join(["No LSB modules are available."] + [f"{rows[k][0]}:\t{rows[k][1]}" for k in keys])

    def c_lsusb(self, sb, args, wd):
        return "\n".join([
            "Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub",
            "Bus 001 Device 002: ID 03f0:7d11 HP, Inc DeskJet 2700 series",
            "Bus 001 Device 003: ID 8087:0026 Intel Corp. AX201 Bluetooth",
            "Bus 001 Device 004: ID 13d3:56ff IMC Networks Integrated Camera",
            "Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub"])

    # --- services, display, input (Ubuntu 24.04 GNOME is a Wayland session) ------
    def c_systemctl(self, sb, args, wd):
        from datetime import datetime, timedelta
        user = "--user" in args
        known = {"--user", "--system", "--no-pager", "--all", "--type", "--state", "--failed", "--now", "--quiet", "--full",
                 "--no-legend", "--plain", "--lines", "--output", "--global", "--force", "--no-block", "--value",
                 "--property", "--show-types", "--legend", "--no-ask-password", "--runtime", "--recursive", "--reverse"}
        bad = next((x for x in args if x.startswith("--") and x.split("=")[0] not in known), None)
        if bad:
            raise SimError(1, f"systemctl: unrecognized option '{bad}'")
        a = [x for x in args if not x.startswith("-")]
        units = USER_UNITS if user else UNITS
        since = (datetime.fromisoformat(sb.now) - timedelta(hours=5)).strftime("%a %Y-%m-%d %H:%M:%S CET")

        def unit(name):
            name = name.removesuffix(".service")
            return UNIT_ALIASES.get(name, name)
        if not a or a[0] in ("list-units", "list-unit-files"):
            if not a and not user:
                return (f"● pc-maison\n    State: running\n    Units: 312 loaded (incl. loaded aliases)\n"
                        f"     Jobs: 0 queued\n   Failed: 0 units\n    Since: {since}; 5h ago")
            return "\n".join(f"{u}.service loaded active running {d}" for u, d in units.items())
        cmd, names = a[0], [unit(n) for n in a[1:]]
        if cmd in ("reboot", "poweroff", "halt", "suspend", "hibernate"):
            self.log("power", op=cmd)
            raise SimError(1, NO_REBOOT.format(what=cmd))
        if cmd == "daemon-reload":
            return ""
        if cmd in ("status", "is-active", "is-enabled"):
            out = []
            for n in names:
                if n not in units:
                    if cmd == "status":
                        raise SimError(4, f"Unit {n}.service could not be found.")
                    raise SimError(3, "inactive" if cmd == "is-active" else "not-found")
                if cmd != "status":
                    out.append("active" if cmd == "is-active" else "enabled")
                    continue
                path = "/usr/lib/systemd/user" if user else "/usr/lib/systemd/system"
                out.append(f"● {n}.service - {units[n]}\n     Loaded: loaded ({path}/{n}.service; enabled; preset: enabled)\n"
                           f"     Active: active (running) since {since}; 5h ago")
            return "\n\n".join(out)
        if cmd in ("start", "stop", "restart", "reload", "enable", "disable", "try-restart"):
            for n in names:
                if n not in units:
                    raise SimError(5, f"Failed to {cmd} {n}.service: Unit {n}.service not loaded.")
                self.log("service", op=cmd, unit=n)
                net, bt = self.s["network"], self.s["bluetooth"]
                if n == "NetworkManager" and cmd == "stop":
                    net["connected"] = None
                elif n == "NetworkManager" and cmd in ("start", "restart") and net.get("wifi_radio") and not net.get("connected"):
                    known = [v["ssid"] for v in net.get("visible", []) if v["ssid"] in net.get("known", {})]
                    net["connected"] = known[0] if known else None  # autoconnect to a known visible network
                elif n == "bluetooth" and cmd == "stop":
                    bt["powered"] = False
                    for d in bt.get("devices", []):
                        d["connected"] = False
                elif n == "bluetooth" and cmd in ("start", "restart"):
                    bt["powered"] = True  # BlueZ AutoEnable (default true since 5.65)
            return ""
        raise SimError(1, f"systemctl: unsupported here: {' '.join(args)}")

    def c_reboot(self, sb, args, wd):
        self.log("power", op="reboot")
        raise SimError(1, NO_REBOOT.format(what="reboot"))

    def c_shutdown(self, sb, args, wd):
        self.log("power", op="shutdown")
        raise SimError(1, NO_REBOOT.format(what="shutdown"))

    c_poweroff = c_shutdown

    def c_xrandr(self, sb, args, wd):
        """Wayland: xrandr only sees XWayland; settings have no effect on the GNOME display."""
        sets = [x for x in args if x not in ("-q", "--query", "--current", "--verbose", "--listmonitors")]
        if not sets:
            if "--listmonitors" in args:
                return "Monitors: 1\n 0: +*XWAYLAND0 1920/344x1080/194+0+0  XWAYLAND0"
            return ("Screen 0: minimum 16 x 16, current 1920 x 1080, maximum 32767 x 32767\n"
                    "XWAYLAND0 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 194mm\n"
                    "   1920x1080     59.96*+\n   1680x1050     59.95  \n   1440x900      59.89  \n   1280x800      59.81  ")
        if "--output" in args:
            i = args.index("--output")
            name = args[i + 1] if i + 1 < len(args) else ""
            if name != "XWAYLAND0":
                return f"warning: output {name} not found; ignoring"
        return ""

    def c_xinput(self, sb, args, wd):
        """Wayland: xinput only sees XWayland's virtual devices; settings have no effect."""
        devices = {2: "Virtual core pointer", 3: "Virtual core keyboard", 4: "Virtual core XTEST pointer",
                   5: "Virtual core XTEST keyboard", 6: "xwayland-pointer:17", 7: "xwayland-relative-pointer:17",
                   8: "xwayland-pointer-gestures:17", 9: "xwayland-keyboard:17"}
        cmd = args[0].lstrip("-") if args else "list"
        rest = args[1:]

        def device(tok):
            if tok.isdigit() and int(tok) in devices:
                return int(tok)
            for i, name in devices.items():
                if tok == name:
                    return i
            raise SimError(1, f"unable to find device {tok}")

        if cmd == "list":
            opts = {x for x in rest if x.startswith("-")}
            names = [x for x in rest if not x.startswith("-")]
            if names:
                i = device(names[0])
                return f"{devices[i]}\tid={i}" if "short" not in opts else f"{devices[i]}"
            if "name-only" in {o.lstrip("-") for o in opts}:
                return "\n".join(devices[i] for i in sorted(devices))
            if "id-only" in {o.lstrip("-") for o in opts}:
                return "\n".join(str(i) for i in sorted(devices))
            return ("⎡ Virtual core pointer                    \tid=2\t[master pointer  (3)]\n"
                    "⎜   ↳ Virtual core XTEST pointer              \tid=4\t[slave  pointer  (2)]\n"
                    + "".join(f"⎜   ↳ {devices[i]:<40}\tid={i}\t[slave  pointer  (2)]\n" for i in (6, 7, 8))
                    + "⎣ Virtual core keyboard                   \tid=3\t[master keyboard (2)]\n"
                    "    ↳ Virtual core XTEST keyboard             \tid=5\t[slave  keyboard (3)]\n"
                    f"    ↳ {devices[9]:<40}\tid=9\t[slave  keyboard (3)]")
        if cmd in ("list-props", "watch-props", "query-state", "set-prop", "set-int-prop", "set-float-prop",
                   "set-atom-prop", "delete-prop", "enable", "disable", "set-ptr-feedback", "set-button-map",
                   "get-button-map", "get-feedbacks", "set-mode"):
            if not rest:
                raise SimError(1, f"usage: xinput {cmd} <device> ...")
            i = device(rest[0])
            if cmd == "list-props":
                props = [("Device Enabled", 147, "1")]
                if i in (2, 4, 6, 7, 8):
                    props += [("Coordinate Transformation Matrix", 149, "1.000000, 0.000000, 0.000000, 0.000000, "
                               "1.000000, 0.000000, 0.000000, 0.000000, 1.000000"),
                              ("Device Accel Profile", 284, "0"), ("Device Accel Constant Deceleration", 285, "1.000000"),
                              ("Device Accel Adaptive Deceleration", 286, "1.000000"),
                              ("Device Accel Velocity Scaling", 287, "10.000000")]
                return f"Device '{devices[i]}':\n" + "\n".join(f"\t{k} ({n}):\t{v}" for k, n, v in props)
            if cmd == "query-state":
                return f"1 class :\n{'ButtonClass' if i in (2, 4, 6, 7, 8) else 'KeyClass'}"
            return ""
        raise SimError(1, "usage :\n"
                          "\txinput get-feedbacks <device name>\n\txinput set-ptr-feedback <device name> <threshold> <num> <denom>\n"
                          "\txinput set-integer-feedback <device name> <feedback id> <value>\n\txinput get-button-map <device name>\n"
                          "\txinput set-button-map <device name> <map button 1> [<map button 2> [...]]\n"
                          "\txinput set-pointer <device name> [<x index> <y index>]\n\txinput set-mode <device name> ABSOLUTE|RELATIVE\n"
                          "\txinput list [--short || --long || --name-only || --id-only] [<device name>...]\n"
                          "\txinput query-state <device name>\n\txinput test [-proximity] <device name>\n"
                          "\txinput list-props <device> [<device> ...]\n\txinput set-int-prop <device> <property> <format (8, 16, 32)> <val> [<val> ...]\n"
                          "\txinput set-float-prop <device> <property> <val> [<val> ...]\n\txinput set-atom-prop <device> <property> <val> [<val> ...]\n"
                          "\txinput watch-props <device>\n\txinput delete-prop <device> <property>\n"
                          "\txinput set-prop <device> [--type=atom|float|int] [--format=8|16|32] <property> <val> [<val> ...]\n"
                          "\txinput disable <device>\n\txinput enable <device>")

    # --- hardware and processes (read-only, consistent with lsusb, /proc and /dev/input) ------
    def c_pgrep(self, sb, args, wd):
        letters = set("".join(a[1:] for a in args if a.startswith("-") and not a.startswith("--")))
        letters |= {"a" if a == "--list-full" else "l" if a == "--list-name" else "c" if a == "--count" else ""
                    for a in args if a.startswith("--")}
        pats = [a for a in args if not a.startswith("-")]
        if not pats:
            raise SimError(2, "pgrep: no matching criteria specified\nTry `pgrep --help' for more information.")
        try:
            rx = re.compile(pats[0], re.I if "i" in letters else 0)
        except re.error:
            raise SimError(2, f"pgrep: invalid regular expression: {pats[0]}")
        match = rx.fullmatch if "x" in letters else rx.search
        hits = [p for p in sorted(self.s["processes"], key=lambda p: p["pid"])
                if match(f"/usr/bin/{p['name']}" if "f" in letters else p["name"][:15])]
        if "c" in letters:
            if not hits:
                raise SimError(1, "0")
            return str(len(hits))
        if not hits:
            raise SimError(1, "")
        if "a" in letters:
            return "\n".join(f"{p['pid']} /usr/bin/{p['name']}" for p in hits)
        if "l" in letters:
            return "\n".join(f"{p['pid']} {p['name'][:15]}" for p in hits)
        return "\n".join(str(p["pid"]) for p in hits)

    def c_lspci(self, sb, args, wd):
        return "\n".join([
            "00:00.0 Host bridge: Intel Corporation 11th Gen Core Processor Host Bridge/DRAM Registers (rev 01)",
            "00:02.0 VGA compatible controller: Intel Corporation TigerLake-LP GT2 [Iris Xe Graphics] (rev 01)",
            "00:14.0 USB controller: Intel Corporation Tiger Lake-LP USB 3.2 Gen 2x1 xHCI Host Controller (rev 20)",
            "00:15.0 Serial bus controller: Intel Corporation Tiger Lake-LP Serial IO I2C Controller #0 (rev 20)",
            "00:16.0 Communication controller: Intel Corporation Tiger Lake-LP Management Engine Interface (rev 20)",
            "00:1f.0 ISA bridge: Intel Corporation Tiger Lake-LP LPC Controller (rev 20)",
            "00:1f.3 Audio device: Intel Corporation Tiger Lake-LP Smart Sound Technology Audio Controller (rev 20)",
            "00:1f.4 SMBus: Intel Corporation Tiger Lake-LP SMBus Controller (rev 20)",
            "01:00.0 Non-Volatile memory controller: Samsung Electronics Co Ltd NVMe SSD Controller SM981/PM981/PM983",
            "02:00.0 Network controller: Intel Corporation Wi-Fi 6 AX201 (rev 20)"])

    def c_lsmod(self, sb, args, wd):
        mods = [("snd_sof_pci_intel_tgl", 12288, 0, ""), ("snd_hda_codec_realtek", 200704, 1, ""),
                ("snd_hda_codec_hdmi", 94208, 1, ""), ("snd_hda_intel", 61440, 2, ""),
                ("snd_hda_codec", 204800, 4, "snd_hda_codec_hdmi,snd_hda_intel,snd_hda_codec_realtek"),
                ("snd_pcm", 192512, 6, "snd_hda_codec_hdmi,snd_hda_intel,snd_hda_codec"),
                ("iwlmvm", 790528, 0, ""), ("mac80211", 1720320, 1, "iwlmvm"), ("iwlwifi", 598016, 1, "iwlmvm"),
                ("cfg80211", 1323008, 3, "iwlmvm,iwlwifi,mac80211"), ("btusb", 77824, 0, ""),
                ("btintel", 57344, 1, "btusb"), ("bluetooth", 1028096, 30, "btintel,btusb"),
                ("uvcvideo", 135168, 0, ""), ("i915", 4268032, 30, ""), ("i2c_designware_platform", 16384, 0, ""),
                ("hid_multitouch", 36864, 0, ""), ("usbhid", 77824, 0, ""), ("nvme", 61440, 3, "")]
        return "Module                  Size  Used by\n" + "\n".join(f"{m:<19} {s:>8}  {n} {u}".rstrip() for m, s, n, u in mods)

    # --- scanner -------------------------------------------------------------
    def c_scanimage(self, sb, args, wd):
        sc = self.s["scanner"]
        if "-L" in args or "--list-devices" in args:
            return f"device `{sc['device']}' is a HP DeskJet 2700 all-in-one"
        dest = None
        for i, a in enumerate(args):
            if a in ("-o", "--output-file") and i + 1 < len(args):
                dest = args[i + 1]
            elif a.startswith("--output-file="):
                dest = a.split("=", 1)[1]
        if not dest:
            raise SimError(1, "scanimage: refusing to write binary image data to the terminal; use -o FILE (or --output-file=FILE)")
        path = sb.resolve_in(wd, dest)
        path.parent.mkdir(parents=True, exist_ok=True)
        fmt = next((a.split("=", 1)[1] for a in args if a.startswith("--format=")), path.suffix.lstrip(".") or "pnm")
        write_sized(self._out(path), f"%SIM-{fmt.upper()} scan of: {sc['loaded_doc']}\n", SIZES["scan"])
        self.log("scan", file=sb.virtual(path), format=fmt)
        return ""

    # --- software, updates, snapshots ----------------------------------------
    def c_flatpak(self, sb, args, wd):
        pk = self.s["packages"]
        a = [x for x in args if not x.startswith("-")]
        if a[:1] == ["search"] and len(a) > 1:
            q = " ".join(a[1:]).lower()
            hits = [f"{desc:<34} {app}" for app, desc in pk["available"].items() if any(w in (app + desc).lower() for w in q.split())]
            return "Name / Description                 Application ID\n" + "\n".join(hits) if hits else "No matches found"
        if a[:1] == ["install"]:
            ids = [x for x in a[1:] if x not in ("flathub",)]
            if not ids:
                raise SimError(1, "error: install: missing application id")
            for app in ids:
                match = next((k for k in pk["available"] if app.lower() in k.lower()), None)
                if not match:
                    raise SimError(1, f"error: No remote refs found similar to '{app}'")
                if match not in pk["installed"]:
                    pk["installed"].append(match)
                    self.log("install", app=match)
            return "Installation complete."
        if a[:1] in (["uninstall"], ["remove"]):
            if not a[1:]:
                raise SimError(1, "error: uninstall: missing application id")
            for app in a[1:]:
                match = next((k for k in pk["installed"] if app.lower() in k.lower()), None)
                if not match:
                    raise SimError(1, f"error: {app} not installed")
                pk["installed"].remove(match)
                self.log("uninstall", app=match)
            return "Uninstall complete."
        if a[:1] == ["list"]:
            return "\n".join(pk["installed"])
        if a[:1] == ["info"] and len(a) > 1:
            match = next((k for k in pk["installed"] if k == a[1] and "." in k), None)
            if not match:
                raise SimError(1, f"error: {a[1]}/*unspecified*/*unspecified* not installed")
            return (f"\n{match.split('.')[-1]}\n\n          ID: {match}\n         Ref: app/{match}/x86_64/stable\n"
                    f"        Arch: x86_64\n      Branch: stable\n      Origin: flathub\nInstallation: system\n"
                    f"   Installed: 412.3 MB\n     Runtime: org.freedesktop.Platform/x86_64/23.08")
        if a[:1] in (["update"], ["upgrade"]):
            done = [u for u in pk["updates"] if u.startswith("org.")]
            pk["updates"] = [u for u in pk["updates"] if not u.startswith("org.")]
            self.log("update", scope="flatpak", items=done)
            return "Updating: " + ", ".join(done) if done else "Nothing to do."
        if a[:1] == ["run"]:  # starts the app's window and returns
            if not a[1:]:
                raise SimError(1, "error: APP must be specified")
            match = next((k for k in pk["installed"] if k == a[1] and "." in k), None)
            if not match:
                raise SimError(1, f"error: app/{a[1]}/x86_64/master not installed")
            self.log("open", target=match)
            return ""
        raise SimError(1, f"flatpak: unsupported here: {' '.join(args)}")

    def c_apt(self, sb, args, wd):
        """apt 2.7 (Ubuntu 24.04). Reads work for everyone; changes need root (dpkg lock) and,
        without -y, stop at the [Y/n] prompt: the agent has no terminal, so apt reads EOF and aborts."""
        pk = self.s["packages"]
        a, skip = [], False
        for x in args:  # options with a separate value: -o NAME=VAL, -c FILE, -t RELEASE
            if skip:
                skip = False
            elif x in ("-o", "--option", "-c", "--config-file", "-t", "--target-release"):
                skip = True
            elif not x.startswith("-"):
                a.append(x)
        yes = any(x in ("-y", "--yes", "--assume-yes", "APT::Get::Assume-Yes=true", "APT::Get::Assume-Yes=1") or (x.startswith("-") and not x.startswith("--") and "y" in x[1:]
                                                            and x[1:].isalpha()) for x in args)
        n_up = len([u for u in pk["updates"] if not u.startswith("org.")])
        writes = a[:1] in (["update"], ["upgrade"], ["full-upgrade"], ["dist-upgrade"], ["install"], ["reinstall"],
                           ["remove"], ["purge"], ["autoremove"], ["autopurge"], ["clean"], ["autoclean"])
        if writes and not sb.sudo and not ("--simulate" in args or "--dry-run" in args or "-s" in args):
            if a[0] == "update":
                raise SimError(100, "Reading package lists... Done\nE: Could not open lock file /var/lib/apt/lists/lock - open (13: Permission denied)\n"
                                    "E: Unable to lock directory /var/lib/apt/lists/")
            if a[0] in ("clean", "autoclean"):
                raise SimError(100, "E: Could not open lock file /var/cache/apt/archives/lock - open (13: Permission denied)\n"
                                    "E: Unable to lock directory /var/cache/apt/archives/")
            raise SimError(100, "E: Could not open lock file /var/lib/dpkg/lock-frontend - open (13: Permission denied)\n"
                                "E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), are you root?")
        if ("--simulate" in args or "--dry-run" in args or "-s" in args) and a[:1] in (["upgrade"], ["full-upgrade"], ["dist-upgrade"]):
            ups = [u for u in pk["updates"] if not u.startswith("org.")]
            return ("NOTE: This is only a simulation!\n" + "".join(f"Inst {u} [1.0-1] (1.0-2 Ubuntu:24.04/noble-updates [amd64])\n" for u in ups)
                    + f"{len(ups)} upgraded, 0 newly installed, 0 to remove and 0 not upgraded.")
        if a[:1] == ["check"]:
            return "Reading package lists... Done\nBuilding dependency tree... Done\nReading state information... Done"
        if a[:1] in (["policy"], ["show"]):
            return self.c_apt_cache(sb, args, wd)
        if a[:1] == ["reinstall"]:
            a = ["install", *a[1:]]

        def prompt(summary):
            """The [Y/n] question: aborts without -y (no terminal to answer it)."""
            if yes:
                return summary + "\n"
            raise SimError(1, summary + "\nDo you want to continue? [Y/n] Abort.")
        if a[:1] == ["update"]:
            return "Reading package lists... Done\n" + f"{n_up} packages can be upgraded."
        if a[:1] == ["list"] and "--upgradable" in args:
            return "\n".join(u for u in pk["updates"] if not u.startswith("org."))
        if a[:1] == ["list"] and "--installed" in args:
            names = [n for n in self._apt_installed() if not a[1:] or any(fnmatch.fnmatch(n, q) for q in a[1:])]
            return "Listing... Done\n" + "\n".join(f"{n}/noble,now 1.0-1 amd64 [installed]" for n in names)
        if a[:1] in (["upgrade"], ["full-upgrade"], ["dist-upgrade"]):
            done = [u for u in pk["updates"] if not u.startswith("org.")]
            if not done:
                return "0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."
            head = prompt("The following packages will be upgraded:\n  " + " ".join(done)
                          + f"\n{len(done)} upgraded, 0 newly installed, 0 to remove and 0 not upgraded.")
            pk["updates"] = [u for u in pk["updates"] if u.startswith("org.")]
            self.log("update", scope="system", items=done)
            return head + "".join(f"Setting up {u} (1.0-2) ...\n" for u in done) + "Done"
        if a[:1] in (["autoremove"], ["autopurge"], ["clean"], ["autoclean"]):
            return "0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded." if a[0].startswith("auto") and a[0] != "autoclean" else ""
        if a[:1] == ["search"] and len(a) > 1:
            q = a[1].lower()
            return "\n".join(f"{app.split('.')[-1].lower()}/stable - {desc}" for app, desc in pk["available"].items() if q in (app + desc).lower()) or ""
        if a[:1] == ["install"]:
            if not a[1:]:
                return "0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."
            new_pk = [n for n in a[1:] if n not in pk["installed"]]
            out = [f"{n} is already the newest version (1.0-1)." for n in a[1:] if n in pk["installed"]]
            if new_pk:  # desktop apps pull dependencies, so apt asks before installing
                out.append(prompt("The following NEW packages will be installed:\n  " + " ".join(new_pk)
                                  + f"\n0 upgraded, {len(new_pk)} newly installed, 0 to remove and 0 not upgraded.").rstrip("\n"))
            for name in new_pk:
                pk["installed"].append(name)
                self.log("install", app=name)
                out.append(f"Setting up {name} (1.0-1) ...")
            return "\n".join(out) + "\nDone"
        if a[:1] in (["remove"], ["purge"]):
            # apt only sees apt packages (exact names); a Flatpak app is not one of them.
            in_repo = {k.split(".")[-1].lower() for k in [*pk.get("available", {}), *pk["installed"]]}
            matches, notes = [], []
            for name in a[1:]:
                if name in self._apt_installed():
                    matches.append(name)
                elif name.lower() in in_repo:
                    notes.append(f"Package '{name}' is not installed, so not removed")
                else:
                    raise SimError(100, f"E: Unable to locate package {name}")
            if not matches:
                return "\n".join(notes + ["0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."])
            head = prompt("The following packages will be REMOVED:\n  " + " ".join(matches)
                          + f"\n0 upgraded, 0 newly installed, {len(matches)} to remove and 0 not upgraded.")
            for match in matches:
                pk["installed"].remove(match)
                self.log("uninstall", app=match)
            return head + "".join(f"Removing {m} (1.0-1) ...\n" for m in matches) + "Done"
        raise SimError(100, f"E: unsupported here: {' '.join(args)}")

    c_apt_get = c_apt

    def _apt_installed(self):
        # Packages installed with apt during the case (flatpak ids are reverse-DNS, with dots).
        return [k for k in self.s["packages"]["installed"] if "." not in k]

    def c_dpkg(self, sb, args, wd):
        """Read-only package queries: dpkg -l [PATTERN...], dpkg -s NAME."""
        a = [x for x in args if not x.startswith("-")]
        installed = self._apt_installed()
        if args[:1] in (["--audit"], ["-C"]):
            return ""  # no half-installed package
        if args[:1] in (["-l"], ["--list"]):
            rows = [n for n in installed if not a or any(fnmatch.fnmatch(n, q) for q in a)]
            if a and not rows:
                raise SimError(1, f"dpkg-query: no packages found matching {a[0]}")
            return ("Desired=Unknown/Install/Remove/Purge/Hold\n||/ Name  Version  Architecture  Description\n"
                    + "\n".join(f"ii  {n}  1.0-1  amd64  {n}" for n in rows))
        if args[:1] in (["-s"], ["--status"]) and a:
            if a[0] not in installed:
                raise SimError(1, f"dpkg-query: package '{a[0]}' is not installed and no information is available")
            return f"Package: {a[0]}\nStatus: install ok installed\nVersion: 1.0-1"
        raise SimError(2, f"dpkg: unsupported here: {' '.join(args)}")

    def c_apt_cache(self, sb, args, wd):
        """Read-only: apt-cache policy|show|search NAME."""
        a = [x for x in args if not x.startswith("-")]
        known = {app.split(".")[-1].lower(): desc for app, desc in self.s["packages"]["available"].items()}
        if a[:1] == ["search"] and len(a) > 1:
            return "\n".join(f"{n} - {d}" for n, d in known.items() if a[1].lower() in (n + d).lower())
        if a[:1] == ["policy"] and len(a) == 1:
            return ("Package files:\n 100 /var/lib/dpkg/status\n     release a=now\n"
                    " 500 http://fr.archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages\n"
                    "     release v=24.04,o=Ubuntu,a=noble-updates,n=noble,l=Ubuntu,c=main,b=amd64\n"
                    " 500 http://security.ubuntu.com/ubuntu noble-security/main amd64 Packages\n"
                    "     release v=24.04,o=Ubuntu,a=noble-security,n=noble,l=Ubuntu,c=main,b=amd64\n"
                    " 500 http://fr.archive.ubuntu.com/ubuntu noble/main amd64 Packages\n"
                    "     release v=24.04,o=Ubuntu,a=noble,n=noble,l=Ubuntu,c=main,b=amd64\nPinned packages:")
        if a[:1] == ["madison"] and len(a) > 1:
            ups = self.s["packages"]["updates"] + [i for e in self.s["log"] if e.get("action") == "update"
                                                   and e.get("scope") == "system" for i in e.get("items", [])]
            return "\n".join((f"{n:>20} | 1.0-2 | http://fr.archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages\n" if n in ups else "")
                             + f"{n:>20} | 1.0-1 | http://fr.archive.ubuntu.com/ubuntu noble/main amd64 Packages" for n in a[1:])
        if a[:1] in (["policy"], ["show"]) and len(a) > 1:
            # System packages with a pending update (packages.updates) are installed at 1.0-1 with
            # a 1.0-2 candidate; once upgraded, at 1.0-2.
            ups = [u for u in self.s["packages"]["updates"] if not u.startswith("org.")]
            done = {i for e in self.s["log"] if e.get("action") == "update" and e.get("scope") == "system" for i in e.get("items", [])}
            out = []
            for name in a[1:]:
                if name not in known and name not in self._apt_installed() and name not in ups and name not in done:
                    raise SimError(100, f"E: No packages found" if a[0] == "show" else f"N: Unable to locate package {name}")
                inst = "1.0-2" if name in done else "1.0-1" if (name in self._apt_installed() or name in ups) else "(none)"
                cand = "1.0-2" if (name in ups or name in done) else "1.0-1"
                if a[0] == "show":
                    out.append(f"Package: {name}\nVersion: {cand}\nDescription: {known.get(name, name)}")
                    continue
                rows = ([("1.0-2", "noble-updates")] if cand == "1.0-2" else []) + [("1.0-1", "noble")]
                vt = []
                for v, suite in rows:
                    vt.append(f"{' *** ' if v == inst else '     '}{v} 500\n"
                              f"        500 http://fr.archive.ubuntu.com/ubuntu {suite}/main amd64 Packages")
                    if v == inst:
                        vt.append("        100 /var/lib/dpkg/status")
                out.append(f"{name}:\n  Installed: {inst}\n  Candidate: {cand}\n  Version table:\n" + "\n".join(vt))
            return "\n".join(out)
        raise SimError(100, f"E: unsupported here: {' '.join(args)}")

    def _snapshot(self, tool, comment):
        self.s["snapshots"].append({"tool": tool, "comment": comment})
        self.log("snapshot", tool=tool, comment=comment)
        return f"Snapshot saved successfully ({len(self.s['snapshots'])})."

    def c_timeshift(self, sb, args, wd):
        if "--create" in args:
            c = args[args.index("--comments") + 1] if "--comments" in args and args.index("--comments") + 1 < len(args) else ""
            return self._snapshot("timeshift", c)
        if "--list" in args:
            return "\n".join(f"{i} > {s['comment']}" for i, s in enumerate(self.s["snapshots"])) or "No snapshots found"
        raise SimError(1, "timeshift: use --create [--comments TEXT] or --list")

    def c_snapper(self, sb, args, wd):
        if "create" in args:
            c = args[args.index("-d") + 1] if "-d" in args and args.index("-d") + 1 < len(args) else ""
            return self._snapshot("snapper", c)
        if "list" in args:
            return "\n".join(f"{i} | {s['comment']}" for i, s in enumerate(self.s["snapshots"])) or "(no snapshots)"
        raise SimError(1, "snapper: use create [-d DESC] or list")

    # --- desktop settings, bluetooth -----------------------------------------
    def c_gsettings(self, sb, args, wd):
        d = self.s["display"]
        keys = {("org.gnome.desktop.interface", "text-scaling-factor"): "text_scaling",
                ("org.gnome.desktop.interface", "cursor-size"): "cursor_size"}
        if args[:1] in (["list-keys"], ["list-recursively"]) and len(args) > 1:
            found = [f"{k}" if args[0] == "list-keys" else f"{sch} {k} {d[v]}" for (sch, k), v in keys.items() if sch == args[1]]
            if not found and not args[1].startswith("org.gnome.desktop"):
                raise SimError(1, f"No such schema “{args[1]}”")
            return "\n".join(found)
        if len(args) >= 3 and args[0] in ("get", "set"):
            key = keys.get((args[1], args[2]))
            if not key:
                raise SimError(1, f"No such key “{args[2]}”")
            if args[0] == "get":
                return str(d[key])
            if len(args) < 4:
                raise SimError(1, "gsettings set: missing value")
            d[key] = float(args[3])
            self.log("display", key=key, value=d[key])
            return ""
        raise SimError(1, "gsettings: use get|set SCHEMA KEY [VALUE]")

    def c_bluetoothctl(self, sb, args, wd):
        b = self.s["bluetooth"]
        if args[:1] == ["power"] and len(args) > 1:
            b["powered"] = args[1] == "on"
            self.log("bt_power", on=b["powered"])
            return f"Changing power {args[1]} succeeded"
        if args[:1] == ["devices"]:
            return "\n".join(f"Device {d['mac']} {d['name']}" for d in b["devices"])
        if args[:1] == ["show"] or not args:
            return f"Controller 9C:B6:D0:11:22:33\n\tPowered: {'yes' if b['powered'] else 'no'}"
        if args[:1] in (["info"], ["connect"]) and len(args) > 1:
            d = next((d for d in b["devices"] if d["mac"].lower() == args[1].lower()), None)
            if not d:
                raise SimError(1, f"Device {args[1]} not available")
            if args[0] == "info":
                return f"Device {d['mac']}\n\tName: {d['name']}\n\tPaired: yes\n\tConnected: {'yes' if d['connected'] else 'no'}"
            if not b["powered"]:
                raise SimError(1, "Failed to connect: org.bluez.Error.NotReady (adapter powered off)")
            d["connected"] = True
            self.log("bt_connect", device=d["name"])
            return "Connection successful"
        if args[:1] == ["disconnect"] and len(args) > 1:
            d = next((d for d in b["devices"] if d["mac"].lower() == args[1].lower()), None)
            if not d:
                raise SimError(1, f"Device {args[1]} not available")
            d["connected"] = False
            self.log("bt_disconnect", device=d["name"])
            return "Successful disconnected"
        if args[:1] in (["info"], ["connect"], ["pair"], ["trust"], ["disconnect"]) and len(args) == 1:
            raise SimError(1, "Missing device address argument")
        if args[:2] == ["scan", "on"]:
            if not b["powered"]:
                raise SimError(1, "Failed to start discovery: org.bluez.Error.NotReady")
            return "Discovery started\n" + "\n".join(f"[NEW] Device {d['mac']} {d['name']}" for d in b["devices"])
        if args[:1] in (["agent"], ["default-agent"], ["pair"], ["trust"], ["scan"]):
            if args[0] == "agent":
                return "Agent unregistered" if args[1:2] == ["off"] else "Agent registered"
            return ""
        if args[:1] == ["paired-devices"]:
            return self.c_bluetoothctl(sb, ["devices"], wd)
        if args[:1] in (["exit"], ["quit"]):
            return ""
        main_menu = {"list", "show", "select", "devices", "system-alias", "reset-alias", "power", "pairable", "discoverable",
                     "discoverable-timeout", "agent", "default-agent", "advertise", "set-alias", "scan", "info", "pair",
                     "cancel-pairing", "trust", "untrust", "block", "unblock", "remove", "connect", "disconnect", "menu",
                     "version", "quit", "exit", "help", "export", "paired-devices"}
        if args and args[0] not in main_menu:
            raise SimError(1, f"Invalid command in menu main: {args[0]}\n\nUse \"help\" for a list of available commands in a menu.\n"
                              "Use \"menu <submenu>\" if you want to enter any submenu.\nUse \"back\" if you want to return to menu main.")
        raise SimError(1, f"bluetoothctl: unsupported here: {' '.join(args)}")

    # --- documents and images (real files in the sandbox) --------------------
    def c_libreoffice(self, sb, args, wd):
        if "--convert-to" not in args:
            # No conversion: the GUI opens the files (or the Start Center); headless does nothing.
            if "--headless" not in args:
                files = [sb.virtual(sb.resolve_in(wd, x)) for x in args if not x.startswith("-")]
                self.log("open", target=" ".join(files) or "libreoffice")
            return ""
        i = args.index("--convert-to")
        fmt = args[i + 1].split(":")[0] if i + 1 < len(args) else "pdf"
        outdir = sb.resolve_in(wd, args[args.index("--outdir") + 1]) if "--outdir" in args else wd
        skip = {i + 1, args.index("--outdir") + 1 if "--outdir" in args else -1}
        files = [args[j] for j, a in enumerate(args) if not a.startswith("-") and j not in skip]
        msgs = []
        for f in files:
            src = sb.resolve_in(wd, f)
            if not src.is_file():
                raise SimError(1, f"Error: source file could not be loaded: {sb.virtual(src)}")
            dst = outdir / (src.stem + "." + fmt)
            write_sized(self._out(dst), f"%SIM-{fmt.upper()} converted from {src.name}\n" + head_text(src), SIZES["convert"])
            self.log("convert", src=sb.virtual(src), dst=sb.virtual(dst))
            msgs.append(f"convert {sb.virtual(src)} -> {sb.virtual(dst)} using filter : writer_pdf_Export")
        return "\n".join(msgs)

    c_soffice = c_libreoffice

    def _concat_pdf(self, sb, wd, srcs, dst):
        parts, total = [], 0
        for s in srcs:
            p = sb.resolve_in(wd, s)
            if not p.is_file():
                raise SimError(1, f"I/O Error: Couldn't open file '{sb.virtual(p)}'")
            parts.append(head_text(p))
            total += p.stat().st_size
        d = sb.resolve_in(wd, dst)
        write_sized(self._out(d), "%SIM-PDF merged\n" + "".join(parts), total)
        self.log("pdf_merge", dst=sb.virtual(d), n=len(srcs))
        return ""

    def c_pdfunite(self, sb, args, wd):
        files = [a for a in args if not a.startswith("-")]
        if len(files) < 3:
            raise SimError(1, "Usage: pdfunite <PDF-sourcefile-1>..<PDF-sourcefile-n> <PDF-destfile>")
        return self._concat_pdf(sb, wd, files[:-1], files[-1])

    def c_qpdf(self, sb, args, wd):
        known = {"--empty", "--pages", "--split-pages", "--show-npages", "--check", "--linearize", "--decrypt",
                 "--password", "--rotate", "--collate", "--qdf", "--object-streams", "--compress-streams", "--version",
                 "--help", "--is-encrypted", "--requires-password", "--replace-input", "--warning-exit-0",
                 "--deterministic-id", "--encrypt", "--overlay", "--underlay", "--remove-page-labels", "--"}
        bad = next((x for x in args if x.startswith("--") and x.split("=")[0] not in known), None)
        if bad:
            raise SimError(2, f"qpdf: unrecognized argument {bad}\nFor help:\n  qpdf --help=usage       usage information\n"
                              "  qpdf --help=topic       help on a topic\n  qpdf --help=--option    help on an option\n"
                              "  qpdf --help             general help and a topic list")
        if "--version" in args:
            return "qpdf version 11.9.0\nRun qpdf --copyright to see copyright and license information."
        if "--check" in args:
            f = next((x for x in args if not x.startswith("-")), None)
            info = self.c_pdfinfo(sb, [f] if f else [], wd)
            ver = next(ln.split()[-1] for ln in info.splitlines() if ln.startswith("PDF version:"))
            return (f"checking {f}\nPDF Version: {ver}\nFile is not encrypted\nFile is not linearized\n"
                    "No syntax or stream encoding errors found; the file appears to be valid")
        if "--show-npages" in args:
            f = next((x for x in args if not x.startswith("-")), None)
            info = self.c_pdfinfo(sb, [f] if f else [], wd)
            return next(ln.split()[-1] for ln in info.splitlines() if ln.startswith("Pages:"))
        if "--pages" not in args or "--" not in args:
            raise SimError(2, "qpdf: only `qpdf --empty --pages A.pdf B.pdf -- OUT.pdf` is available here")
        i, j = args.index("--pages"), len(args) - 1 - args[::-1].index("--")
        return self._concat_pdf(sb, wd, args[i + 1:j], args[j + 1])

    def c_magick(self, sb, args, wd):
        files = [a for i, a in enumerate(args) if not a.startswith("-") and not (i > 0 and args[i - 1] in ("-resize", "-quality", "-scale"))]
        if len(files) < 2:
            raise SimError(1, "magick: usage: magick INPUT [-resize 50%] [-quality 80] OUTPUT")
        src, dst = sb.resolve_in(wd, files[0]), sb.resolve_in(wd, files[-1])
        if not src.is_file():
            raise SimError(1, f"magick: unable to open image '{sb.virtual(src)}'")
        ops = " ".join(a for a in args if a.startswith("-") or (args.index(a) > 0 and args[args.index(a) - 1] in ("-resize", "-quality", "-scale")))
        write_sized(self._out(dst), f"%SIM-IMAGE from {src.name} [{ops}] 1600x1067\n", SIZES["image"])
        self.log("image", src=sb.virtual(src), dst=sb.virtual(dst), ops=ops)
        return ""

    c_convert = c_magick

    def c_xdg_open(self, sb, args, wd):
        """xdg-utils 1.1: a URL opens in its app; anything else is a file that must exist
        (`exit_failure_file_missing`, exit 2). It takes exactly one argument."""
        if not args:
            raise SimError(1, "xdg-open: no file or URL specified\nTry 'xdg-open --help' for more information.")
        opt = next((x for x in args if x.startswith("-")), None)
        if opt or len(args) > 1:
            what = f"option '{opt}'" if opt else f"argument '{args[1]}'"
            raise SimError(1, f"xdg-open: unexpected {what}\nTry 'xdg-open --help' for more information.")
        target = args[0]
        if target.startswith("file://") or not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            path = sb.resolve_in(wd, target.removeprefix("file://"))
            if not path.exists():
                raise SimError(2, f"xdg-open: file '{target}' does not exist")
            target = sb.virtual(path)
        self.log("open", target=target)
        return ""

    # --- status for the get_system_status tool --------------------------------
    def status(self, metric):
        if metric == "processes" or metric == "cpu":
            return self._ps_table()
        if metric == "memory":
            return self.c_free(None, [], None)
        if metric == "disk":
            return self.c_df(None, [], None)
        if metric == "battery":
            return "Battery: 64%, discharging"
        raise ValueError(f"unknown metric '{metric}'")


def get_path(state, path):
    cur = state
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def match_rule(value, rule):
    if "equals" in rule:
        return value == rule["equals"]
    if "gte" in rule:
        return value is not None and value >= rule["gte"]
    if "lte" in rule:
        return value is not None and value <= rule["lte"]
    if "contains" in rule:
        return str(rule["contains"]).lower() in str(value).lower()
    if "any_of" in rule:
        return any(str(x).lower() in str(value).lower() for x in rule["any_of"])
    if "glob" in rule:
        return fnmatch.fnmatch(str(value), rule["glob"])
    if "none_of" in rule:
        return not any(str(x).lower() in str(value).lower() for x in rule["none_of"])
    raise ValueError(f"unknown rule {rule}")


def match_item(item, where):
    for k, rule in where.items():
        try:
            v = get_path(item, k)
        except (KeyError, IndexError, TypeError):
            return False
        if not match_rule(v, rule):
            return False
    return True
