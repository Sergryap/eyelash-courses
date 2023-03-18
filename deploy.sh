# #!/bin/bash
set -Eeuo pipefail
cd /opt/eyelash-courses/
git pull
sudo systemctl daemon-reload
sudo systemctl restart django-bot-example.service
sudo systemctl restart django-bot-start.service
echo "Deploy completed successfully!"
