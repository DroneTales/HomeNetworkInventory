# Deployment guide

This guide walks through deploying **Home Network Inventory** on a Linux
server — a Raspberry Pi, a home server, or a small VPS. The instructions
assume Debian-based distributions (Raspberry Pi OS, Ubuntu, Debian), but
they translate easily to other Linux systems.

After this guide you will have:

- the application running as a systemd service,
- nginx in front of it,
- HTTPS via Let's Encrypt,
- automatic restarts on failure and on boot.

---

## Prerequisites

- A Linux server with sudo access.
- A domain (or subdomain) pointing to the server's public IP, e.g.
  `hni.example.com`.
- Ports 80 and 443 reachable from the internet (for Let's Encrypt).
- Python 3.11 or newer.

## 1. Create a dedicated user (optional but recommended)

Running the application as its own user keeps things tidy and prevents the
service from touching anything outside its directory.

```bash
sudo adduser --system --group --home /opt/hni hni
```

## 2. Install the application

Pick a directory — `/opt/hni` is used throughout this guide.

```bash
sudo mkdir -p /opt/hni
sudo chown hni:hni /opt/hni
cd /opt/hni
sudo -u hni git clone https://github.com/<you>/HomeNetworkInventory.git .
```

Or, if you already have a release archive, unpack it there.

## 3. Create a virtual environment and install dependencies

```bash
cd /opt/hni
sudo -u hni python3 -m venv venv
sudo -u hni ./venv/bin/pip install --upgrade pip
sudo -u hni ./venv/bin/pip install -r requirements.txt
```

## 4. Configure the application

Open `app/config.py` and adjust at least:

```python
class Settings:
    app_name = "Home Network Inventory"
    app_host = "127.0.0.1"
    app_port = 8420
    database_url = "sqlite:///./home_network.db"   # created next to the app
    session_secret = "<paste a random string here>"
    session_timeout_seconds = 2 * 60 * 60          # 2 hours
```

Generate a strong `session_secret`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the output into `session_secret`.

By default the SQLite database lives in the project directory. If you want it
on a different disk (for example, an external drive), change `database_url`
to an absolute path:

```python
database_url = "sqlite:////var/lib/hni/home_network.db"
```

Note the **four** slashes for absolute paths.

## 5. Create the systemd service

Copy the example unit and adjust it:

```bash
sudo cp docs/systemd.service.example /etc/systemd/system/hni.service
sudo nano /etc/systemd/system/hni.service
```

Set `User`, `Group`, `WorkingDirectory`, and `ExecStart` to match your
installation. Example for `/opt/hni` owned by user `hni`:

```ini
[Unit]
Description=Home Network Inventory
After=network.target

[Service]
Type=simple
User=hni
Group=hni
WorkingDirectory=/opt/hni
ExecStart=/opt/hni/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8420 \
    --proxy-headers \
    --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hni.service
sudo systemctl status hni.service
```

Tail logs:

```bash
sudo journalctl -u hni.service -f
```

## 6. Verify the application is listening

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8420/login
```

Should return `200`. The application is now running but only on localhost.

## 7. Install nginx

```bash
sudo apt update
sudo apt install -y nginx
```

## 8. Configure nginx

Copy the example configuration:

```bash
sudo cp docs/nginx.conf.example /etc/nginx/sites-available/hni.example.com
sudo nano /etc/nginx/sites-available/hni.example.com
```

Replace `hni.example.com` with your real domain, then activate:

```bash
sudo ln -s /etc/nginx/sites-available/hni.example.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

At this point the site should respond on plain HTTP.

## 9. Obtain a TLS certificate

Certbot will add the SSL block to the nginx config and set up auto-renewal.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d hni.example.com
```

Answer the prompts. When asked about redirecting HTTP to HTTPS, choose
**Redirect**.

Verify auto-renewal:

```bash
sudo certbot renew --dry-run
```

## 10. First sign-in and initial setup

Open `https://hni.example.com/` in a browser. The default credentials are:

- **Username:** `Admin`
- **Password:** `Admin`

You will be forced to change the password on first sign-in.

Then:

1. You land on the **Choose a home** page. Since no homes exist yet, click
   **Add home** and create your first one — give it a name, optionally an
   address and a photo.
2. Enter the home (click **Enter**).
3. Go to **Reference** and populate locations and networks for the current
   home. If you also need to add global reference data (device types,
   vendors, models, credential types), do it as admin — only administrators
   can manage the global lists. They are shared across all homes.
4. Start adding devices.

If you have more than one home, create them all on the **Choose a home**
page. To switch between homes, use the **Switch home** button in the header.

### Adding more users

1. Go to **Users** → **Add user**.
2. Set username, password, role (`user`).
3. Grant permissions as needed (`Can edit`, `Can view passwords`,
   `Can change passwords`).
4. Save. Open the user again and use the **Homes** block to assign one or
   more homes. Users without assigned homes will not see any devices.

## 11. Backups

The entire application state is the SQLite database file
(`home_network.db`). A simple hourly backup with rotation:

```bash
#!/bin/bash
# /usr/local/bin/hni-backup.sh
DB=/opt/hni/home_network.db
DEST=/var/backups/hni
mkdir -p "$DEST"
cp "$DB" "$DEST/home_network-$(date +%Y%m%d-%H%M%S).db"
# keep only the last 24 backups
ls -1t "$DEST"/*.db | tail -n +25 | xargs -r rm --
```

Make it executable and add a cron job:

```bash
sudo chmod +x /usr/local/bin/hni-backup.sh
sudo crontab -e
```

Add:

```
0 * * * * /usr/local/bin/hni-backup.sh
```

Site photos are stored **inside the database**, so a single file backup is
enough — no separate folder to worry about.

## 12. Updating

```bash
cd /opt/hni
sudo -u hni git pull
sudo -u hni ./venv/bin/pip install -r requirements.txt
sudo systemctl restart hni.service
```

If new database migrations are needed — for now the application creates
missing tables on startup (`Base.metadata.create_all`). Schema changes that
affect existing tables require manual handling; this is a known limitation.

## Troubleshooting

### 502 Bad Gateway from nginx

The application is not running or not listening on `127.0.0.1:8420`.

```bash
sudo systemctl status hni.service
sudo journalctl -u hni.service -n 50 --no-pager
```

### "Safari cannot open the page" after login

This is a Safari + nginx keep-alive quirk. Make sure the nginx config
contains:

```nginx
keepalive_disable safari;
keepalive_timeout 30s;
keepalive_requests 100;
```

The example config includes these lines.

### Permission denied when the service tries to write the database

The user running the service must own the project directory and the directory
where the database lives. Check:

```bash
sudo ls -ld /opt/hni
sudo ls -ld "$(dirname "$(grep database_url /opt/hni/app/config.py)")"
```

### Wrong time in logs

Set the correct timezone:

```bash
sudo timedatectl set-timezone Europe/Berlin
```

### User sees no homes after sign-in

The user has not been assigned to any home. As an admin, go to **Users** →
**Edit** for that user and use the **Homes** block to assign at least one.

## Notes on security

- The application is designed for **private, home use**. Do not expose it to
  the public internet without authentication in front (nginx basic auth,
  VPN, or a firewall rule).
- Device passwords (Wi-Fi, credentials, RTSP URLs) are stored and displayed in
  plain text — by design. Do not put anything truly sensitive in this tool.
- Application user passwords are hashed with bcrypt.
- Session cookies are signed but not encrypted; only `user_id` and
  `last_seen` are stored in them.
- Access to homes is per-user. A user only sees the homes assigned to them.

