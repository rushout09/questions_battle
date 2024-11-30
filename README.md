
sudo apt update && sudo apt upgrade -y

sudo apt install python3-pip python3-venv nginx redis-server -y

git@github.com:rushout09/questions_battle.git

cd questions_battle
python3 -m venv venv

source venv/bin/activate


pip install -r requirements.txt

