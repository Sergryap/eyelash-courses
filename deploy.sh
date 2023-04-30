# #!/bin/bash
set -Eeuo pipefail
cd /opt/eyelash-courses/
git pull
if ! [ -e venv ]
then
python3 -m venv venv
fi
source venv/bin/activate
python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
sudo systemctl daemon-reload
sudo systemctl restart django-bot-example.service
sudo systemctl restart django-bot-start.service
echo "Deploy completed successfully!"
