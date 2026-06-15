# VPS Hosting Guide

This guide shows how to run the API on an Ubuntu VPS and expose it as a normal HTTP API.

Example public URL:

```text
https://your-domain.com/api/matches
```

## 1. Connect To Your VPS

```bash
ssh root@YOUR_SERVER_IP
```

Update packages:

```bash
apt update && apt upgrade -y
```

Install Python and Nginx:

```bash
apt install -y python3 python3-venv nginx git
```

## 2. Upload Or Clone The Project

Create an app folder:

```bash
mkdir -p /var/www/football-api
```

Upload your project files into:

```text
/var/www/football-api
```

Your folder should contain:

```text
app.py
fubo808_parser.py
test_fubo808_parser.py
README.md
HOSTING.md
```

If you are using Git later, clone your repository into this same folder.

## 3. Test The App Manually

```bash
cd /var/www/football-api
python3 -m unittest -v
python3 app.py
```

In another terminal, test:

```bash
curl http://127.0.0.1:8001/api/health
```

Stop the app with `Ctrl+C`.

## 4. Create A systemd Service

Create a service file:

```bash
nano /etc/systemd/system/football-api.service
```

Paste this:

```ini
[Unit]
Description=Football API
After=network.target

[Service]
Type=simple
WorkingDirectory=/var/www/football-api
ExecStart=/usr/bin/python3 /var/www/football-api/app.py
Restart=always
RestartSec=5
Environment=PUBLIC_API_PREFIX=/api

[Install]
WantedBy=multi-user.target
```

Start the service:

```bash
systemctl daemon-reload
systemctl enable football-api
systemctl start football-api
systemctl status football-api
```

View logs:

```bash
journalctl -u football-api -f
```

## 5. Configure Nginx

Create an Nginx site:

```bash
nano /etc/nginx/sites-available/football-api
```

For a domain, use:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
ln -s /etc/nginx/sites-available/football-api /etc/nginx/sites-enabled/football-api
nginx -t
systemctl reload nginx
```

Now test:

```bash
curl http://your-domain.com/api/health
curl http://your-domain.com/api/matches
```

## 6. Add HTTPS

Install Certbot:

```bash
apt install -y certbot python3-certbot-nginx
```

Issue SSL:

```bash
certbot --nginx -d your-domain.com -d www.your-domain.com
```

Test HTTPS:

```bash
curl https://your-domain.com/api/health
```

## 7. Use The API From JavaScript

```js
const response = await fetch("https://your-domain.com/api/matches");
const data = await response.json();

console.log(data.matches);
```

Search:

```js
const response = await fetch("https://your-domain.com/api/matches?q=mexico");
const data = await response.json();
```

Get details:

```js
const response = await fetch("https://your-domain.com/api/matches/2990785/details");
const data = await response.json();
```

## 8. Useful Commands

Restart API:

```bash
systemctl restart football-api
```

Stop API:

```bash
systemctl stop football-api
```

Check API status:

```bash
systemctl status football-api
```

Check logs:

```bash
journalctl -u football-api -n 100
```

Reload Nginx:

```bash
nginx -t && systemctl reload nginx
```

## 9. Updating The API

After uploading new files:

```bash
cd /var/www/football-api
python3 -m unittest -v
systemctl restart football-api
```

Then verify:

```bash
curl https://your-domain.com/api/health
```
