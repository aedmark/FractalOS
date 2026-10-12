#!/usr/bin/env bash
# provision_x64.sh - Turns a minimal Debian (12/13) or Ubuntu install on any x86_64 machine that can run a modern
# browser into a FractalOS mesh node, signal server or kiosk. Old laptops and desktops welcome.
# (The Raspberry Pi / ARM path is extras/provision_appliance.sh.)
#
# Roles:
#   signal  Serves FractalOS over HTTP and relays mesh signaling. No browser, no screen needed.
#   node    signal + a browser running FractalOS full-time, so the box is itself a mesh peer.
#   kiosk   A browser on this machine's own screen, FractalOS served to localhost only.
#
# Usage: sudo ./provision_x64.sh [--role signal|node|kiosk] [--headless] [--http-port N] [--signal-port N]
#                                [--signal-url ws://host:port] [--no-start] [--uninstall]
#   --headless    node only: run the browser without a display. The first-run account setup needs a screen, so
#                 do that once without this flag, or flip FRACTAL_HEADLESS in /etc/default/fractalos afterwards.
#   --signal-url  kiosk only: join the mesh through an existing signal server.

set -euo pipefail

ROLE="signal"
HEADLESS=0
HTTP_PORT=8000
SIGNAL_PORT=8080
SIGNAL_URL=""
START=1
UNINSTALL=0

while [ $# -gt 0 ]; do
    case "$1" in
        --role) ROLE="${2:-}"; shift 2 ;;
        --headless) HEADLESS=1; shift ;;
        --http-port) HTTP_PORT="${2:-}"; shift 2 ;;
        --signal-port) SIGNAL_PORT="${2:-}"; shift 2 ;;
        --signal-url) SIGNAL_URL="${2:-}"; shift 2 ;;
        --no-start) START=0; shift ;;
        --uninstall) UNINSTALL=1; shift ;;
        -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1 (try --help)"; exit 2 ;;
    esac
done

case "$ROLE" in signal|node|kiosk) ;; *) echo "Unknown role '$ROLE': use signal, node or kiosk."; exit 2 ;; esac
if [ "$HEADLESS" = 1 ] && [ "$ROLE" != "node" ]; then echo "--headless only applies to --role node."; exit 2; fi
if [ -n "$SIGNAL_URL" ] && [ "$ROLE" != "kiosk" ]; then echo "--signal-url only applies to --role kiosk."; exit 2; fi
for n in "$HTTP_PORT" "$SIGNAL_PORT"; do
    case "$n" in ''|*[!0-9]*) echo "Ports must be numbers."; exit 2 ;; esac
done

if [ "$EUID" -ne 0 ]; then echo "Please run as root (use sudo)."; exit 1; fi

INSTALL_DIR="/opt/fractalos"
STATE_DIR="/var/lib/fractalos"
SYSTEMD=0
[ -d /run/systemd/system ] && SYSTEMD=1

UNITS="fractalos-web fractalos-signal fractalos-browser"

if [ "$UNINSTALL" = 1 ]; then
    echo "Removing FractalOS services and files (the 'fractal' user and $STATE_DIR are kept)..."
    for u in $UNITS; do
        if [ "$SYSTEMD" = 1 ]; then systemctl disable --now "$u.service" 2>/dev/null || true; fi
        rm -f "/etc/systemd/system/$u.service"
    done
    [ "$SYSTEMD" = 1 ] && systemctl daemon-reload
    rm -rf "$INSTALL_DIR" /usr/local/bin/fractalos-browser /etc/default/fractalos
    echo "Done. Delete the profile and the user yourself if you want them gone: $STATE_DIR, userdel fractal."
    exit 0
fi

echo "=== FractalOS x64 provisioning: role '$ROLE' ==="

# 1. Architecture
ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo "This script is for x86_64 (found: $ARCH). On a Raspberry Pi use extras/provision_appliance.sh."
    exit 1
fi
if ! command -v apt-get >/dev/null 2>&1; then
    echo "This script needs a Debian-family system (apt-get). On anything else, serve resources/ with"
    echo "'python3 -m http.server' and run extras/signaling_server.py yourself."
    exit 1
fi

# 2. Dependencies
export DEBIAN_FRONTEND=noninteractive
PKGS="python3 ca-certificates"
[ "$ROLE" != "kiosk" ] && PKGS="$PKGS python3-websockets"
if [ "$ROLE" != "signal" ]; then
    PKGS="$PKGS xserver-xorg-core xserver-xorg-input-libinput x11-xserver-utils xinit openbox"
fi
echo "Installing: $PKGS"
apt-get update
# shellcheck disable=SC2086
apt-get install -y --no-install-recommends $PKGS

BROWSER=""
if [ "$ROLE" != "signal" ]; then
    for candidate in "${FRACTAL_BROWSER:-}" chromium chromium-browser google-chrome-stable; do
        [ -n "$candidate" ] && command -v "$candidate" >/dev/null 2>&1 && { BROWSER=$(command -v "$candidate"); break; }
    done
    if [ -z "$BROWSER" ]; then
        apt-get install -y --no-install-recommends chromium || apt-get install -y --no-install-recommends chromium-browser || true
        for candidate in chromium chromium-browser; do
            command -v "$candidate" >/dev/null 2>&1 && { BROWSER=$(command -v "$candidate"); break; }
        done
    fi
    if [ -z "$BROWSER" ]; then
        echo "No Chromium-based browser found. Install one (Ubuntu's chromium is a snap and does not suit a"
        echo "system service) and re-run with FRACTAL_BROWSER=/path/to/it."
        exit 1
    fi
    echo "Browser: $BROWSER"
fi

# 3. Service user
if ! id -u fractal >/dev/null 2>&1; then
    echo "Creating 'fractal' user..."
    useradd -m -s /bin/bash -G video,audio,render fractal 2>/dev/null || useradd -m -s /bin/bash -G video,audio fractal
fi
mkdir -p "$STATE_DIR/profile"
chown -R fractal:fractal "$STATE_DIR"

# 4. Install the files: from this checkout or bundle if we are in one, otherwise from GitHub
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$INSTALL_DIR"
if [ -f "$SRC/resources/index.html" ]; then
    echo "Installing from $SRC ..."
    rm -rf "$INSTALL_DIR/resources" "$INSTALL_DIR/extras"
    cp -a "$SRC/resources" "$INSTALL_DIR/resources"
    cp -a "$SRC/extras" "$INSTALL_DIR/extras"
    rm -f "$INSTALL_DIR/resources/deploy.json"
else
    command -v git >/dev/null 2>&1 || apt-get install -y --no-install-recommends git
    echo "Cloning FractalOS..."
    rm -rf "$INSTALL_DIR.src"
    git clone --depth 1 https://github.com/aedmark/FractalOS.git "$INSTALL_DIR.src"
    rm -rf "$INSTALL_DIR/resources" "$INSTALL_DIR/extras"
    mv "$INSTALL_DIR.src/resources" "$INSTALL_DIR/resources"
    mv "$INSTALL_DIR.src/extras" "$INSTALL_DIR/extras"
    rm -rf "$INSTALL_DIR.src"
fi

# 5. deploy.json: the runtime switch that turns the mesh on (D-046)
if [ "$ROLE" = "kiosk" ]; then
    BIND="127.0.0.1"
    if [ -n "$SIGNAL_URL" ]; then
        printf '{"networking": true, "signalingUrl": "%s"}\n' "$SIGNAL_URL" > "$INSTALL_DIR/resources/deploy.json"
    else
        printf '{"networking": false}\n' > "$INSTALL_DIR/resources/deploy.json"
    fi
else
    BIND="0.0.0.0"
    printf '{"networking": true, "signalingUrl": "auto", "signalingPort": %s}\n' "$SIGNAL_PORT" > "$INSTALL_DIR/resources/deploy.json"
fi
chown -R root:root "$INSTALL_DIR"
chmod -R a+rX "$INSTALL_DIR"

# 6. Services
cat > /etc/default/fractalos <<EOF
# Read by fractalos-browser. Edit and run: systemctl restart fractalos-browser
FRACTAL_HEADLESS=$HEADLESS
FRACTAL_URL=http://127.0.0.1:$HTTP_PORT/
FRACTAL_BROWSER=$BROWSER
# Extra browser flags, e.g. --disable-gpu on stubborn old graphics hardware
FRACTAL_BROWSER_ARGS=""
EOF

cat > /etc/systemd/system/fractalos-web.service <<EOF
[Unit]
Description=FractalOS web server
After=network.target

[Service]
User=fractal
Group=fractal
ExecStart=/usr/bin/python3 -m http.server $HTTP_PORT --bind $BIND --directory $INSTALL_DIR/resources
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
ENABLE="fractalos-web"

if [ "$ROLE" != "kiosk" ]; then
    cat > /etc/systemd/system/fractalos-signal.service <<EOF
[Unit]
Description=FractalOS mesh signaling relay
After=network.target

[Service]
User=fractal
Group=fractal
ExecStart=/usr/bin/python3 $INSTALL_DIR/extras/signaling_server.py --bind $BIND --port $SIGNAL_PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    ENABLE="$ENABLE fractalos-signal"
fi

if [ "$ROLE" != "signal" ]; then
    cat > /usr/local/bin/fractalos-browser <<'EOF'
#!/bin/bash
# Runs the browser that hosts FractalOS: on a display (kiosk) or headless. Settings: /etc/default/fractalos
. /etc/default/fractalos
PROFILE=/var/lib/fractalos/profile
FLAGS=(--user-data-dir="$PROFILE" --no-first-run --no-default-browser-check --noerrdialogs --disable-infobars
       --password-store=basic --autoplay-policy=no-user-gesture-required --disable-features=Translate)
if [ "$FRACTAL_HEADLESS" = "1" ]; then
    exec "$FRACTAL_BROWSER" --headless=new --disable-gpu "${FLAGS[@]}" $FRACTAL_BROWSER_ARGS "$FRACTAL_URL"
fi
cat > /var/lib/fractalos/session.sh <<SESSION
#!/bin/bash
xset s off; xset s noblank; xset -dpms
openbox &
exec "$FRACTAL_BROWSER" --kiosk "${FLAGS[@]}" $FRACTAL_BROWSER_ARGS "$FRACTAL_URL"
SESSION
chmod +x /var/lib/fractalos/session.sh
exec /usr/bin/xinit /var/lib/fractalos/session.sh -- /usr/bin/X :0 -nolisten tcp vt7
EOF
    chmod 755 /usr/local/bin/fractalos-browser

    AFTER="fractalos-web.service"
    [ "$ROLE" = "node" ] && AFTER="fractalos-web.service fractalos-signal.service"
    cat > /etc/systemd/system/fractalos-browser.service <<EOF
[Unit]
Description=FractalOS browser (kiosk / node)
After=systemd-user-sessions.service $AFTER
Wants=$AFTER

[Service]
User=fractal
Group=fractal
PAMName=login
TTYPath=/dev/tty7
StandardInput=tty
ExecStart=/usr/local/bin/fractalos-browser
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    ENABLE="$ENABLE fractalos-browser"
fi

if [ "$SYSTEMD" = 1 ]; then
    systemctl daemon-reload
    for u in $ENABLE; do systemctl enable "$u.service"; done
    if [ "$START" = 1 ]; then
        for u in $ENABLE; do systemctl restart "$u.service"; done
    fi
else
    echo "systemd is not running here: units were written to /etc/systemd/system but not enabled."
fi

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo ""
echo "=== Provisioning complete: role '$ROLE' ==="
if [ "$ROLE" != "kiosk" ]; then
    echo "FractalOS:  http://${IP:-<this machine>}:$HTTP_PORT/   (any browser on the LAN joins the mesh from here)"
    echo "Signaling:  ws://${IP:-<this machine>}:$SIGNAL_PORT"
    echo "There is no authentication. Keep ports $HTTP_PORT and $SIGNAL_PORT on a trusted network."
fi
if [ "$ROLE" != "signal" ]; then
    echo "First run needs a screen to create the first account. Headless afterwards: set FRACTAL_HEADLESS=1 in /etc/default/fractalos."
fi
