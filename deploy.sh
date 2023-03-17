# #!/bin/bash
set -Eeuo pipefail
cd /
cd /opt/eyelash-courses
git pull
if ! [ -e venv ]
then
python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
if [ -e static ]
then
sudo rm -rf static
fi
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
sudo systemctl daemon-reload
echo "Deploy completed successfully!"
