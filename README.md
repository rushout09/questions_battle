Certainly! Here's the content formatted properly as Markdown:

```markdown
# Setup Instructions

## Update and Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.9 python3.9-venv python3.9-distutils python3-pip nginx redis-server -y
```

## Clone the Repository

```bash
git clone git@github.com:rushout09/questions_battle.git
cd questions_battle
```

## Setup Python Environment

```bash
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Create Service File

```bash
sudo nano /etc/systemd/system/questions_battle.service
```

Add the following content to the service file:

```ini
[Unit]
Description=FastAPI WebSocket Application
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/questions_battle
Environment="PATH=/home/ubuntu/questions_battle/venv/bin"
ExecStart=/home/ubuntu/questions_battle/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b unix:/tmp/questions_battle.sock

[Install]
WantedBy=multi-user.target
```

## Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/questions_battle
```

Add the following content to the Nginx config file:

```nginx
server {
    listen 80;
    server_name your_domain.com;  # or your EC2 public IP

    location / {
        proxy_pass http://unix:/tmp/questions_battle.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /home/ubuntu/questions_battle/static;
    }
}
```

## Enable Nginx Configuration

```bash
sudo ln -s /etc/nginx/sites-available/questions_battle /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # remove default config
```

## Test Nginx Configuration

```bash
sudo nginx -t
```

## Start and Enable Services

```bash
sudo systemctl start questions_battle
sudo systemctl enable questions_battle
sudo systemctl restart nginx
```

## Check Service Status

```bash
sudo systemctl status questions_battle
sudo systemctl status nginx
```

## Set Permissions

```bash
sudo chmod -R 755 /home/ubuntu/questions_battle/static
sudo chown -R www-data:www-data /home/ubuntu/questions_battle/static
sudo chown -R www-data:www-data /home/ubuntu/questions_battle
sudo chown -R www-data:www-data /home/ubuntu
```
```

This Markdown format organizes the instructions into sections with code blocks for each command or configuration file.
