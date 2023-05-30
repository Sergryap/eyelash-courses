## Сайт с ботами ВК и TG, с базой данных и интерфейсом admin Django для организации записи на обучающие курсы.

#### На данный момент реализованы следующие возможности

Для ботов:

1. Просмотр предстоящих курсов для ознакомления.
2. Просмотр информации о конкретном курсе с возможностью записаться на курс либо отменить запись.
3. Возможность просмотра своих курсов прошедших и предстоящих.
4. Возможность просмотра информации о расположении места проведения курса.
5. Возможность связаться с администрацией.

Для администратора реализованы следующие возможности через интерфейс admin Django:

1. Создание программ для курсов.
2. Создание лекторов.
2. Создание курсов с выбором программы, лектора, времени, стоимости и длительности с одновременным созданием одноименного альбома в группе ВК с загрузкой фотографий и с описанием.
3. Возможность выбора фотографий для загрузки в альбом ВК.
4. Возможность установки главной фотографии альбома. Главной устанавливается первая фотография в отображаемом списке фотографий курса. Поменять её можно простым перетаскиванием мышью.

#### В будущем планируется реализовать:
1. Создание постов через admin Django и управление ими.
2. Анализ аудитории.

## Как запустить prod-версию сайта

#### Арендуйте удаленный сервер и установите на нем последнюю версию OS Ubuntu

Установите Postgresql, git, pip, venv, nginx:
```sh
sudo apt update
sudo apt -y install git
sudo apt -y install postgresql
sudo apt -y install python3-pip
sudo apt -y install python3-venv
sudo apt -y install nginx
```

#### Создайте базу данных Postgres и пользователя для работы с ней:
```sh
sudo su - postgres
psql
CREATE DATABASE <имя базы данных>;
CREATE USER <пользователь postgres> WITH PASSWORD '<пароль для пользователя>';
ALTER ROLE <имя пользователя> SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE <имя базы данных> TO <имя пользователя>;
```

#### Скачайте код проекта в каталог `/opt` корневого каталога сервера:
```sh
cd /opt
git clone https://github.com/Sergryap/eyelash-courses.git
```

#### В каталоге проекта создайте виртуальное окружение:
```sh
cd opt/eyelash-courses
python3 -m venv venv
source venv/bin/activate
```

#### Установите зависимости в виртуальное окружение:
```sh
pip install -r requirements.txt
pip install gunicorn

```

#### Перед запуском необходимо создать файл для переменных окружения `.env`:

```sh
SECRET_KEY=<django secret key>
ADMIN_URL=<url админ-панели сайта>

# Данные ВК
VK_TOKEN=<токен сообщества ВК>
VK_USER_TOKEN=<токен пользователя ВК>
VK_GROUP=<id группы ВК, к которой привязывается бот>
ADMIN_IDS=<id администраторов группы>
OFFICE_PHOTO=<ID фото офиса>

# Данные TG
TG_ADMIN_IDS=<ID администраторов>
TG_TOKEN=<Токен TG бота для бота>
TG_LOGGER_BOT=<Токен TG бота для отправки сообщений логера>
TG_LOGGER_CHAT=<Chat TG ID для сообщений логера>
TG_BOT_NAME=<Имя бота>

# Данные YouTube
YOUTUBE_CHANEL_ID=<ID YouTube канала>

# Данные для админ-панели
SITE_HEADER=<>
INDEX_TITLE=<>
SITE_TITLE=<>

# Данные для Redis
REDIS_URL=<>
REDIS_PASSWORD=<Пароль для Redis>
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Данные для Postgresql
DB_URL=<url для подлючения к Postgresql>

# Карта Яндекс
SRC_MAP=<код для встраивания яндекс-карты>

# Данные для отправки Email
PASSWORD_EMAIL=<>
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=2525
EMAIL_HOST_USER=<>
RECIPIENTS_EMAIL=<>

# Данные для контента сайта
PHONE_NUMBER=<Номер тедефона для сайта в формате 71234567894>
PHONE_NUMBER_READABLE=<Номер телефона для сатй в формате +7(xxx)xxx-xx-xx>
```

#### Выполните миграцию базы данных:

```sh
python3 manage.py migrate
```
#### Создайте суперпользователя:
```sh
python3 manage.py createsuperuser
```
#### Соберите статику для prod-версии:
```sh
python3 manage.py collectstatic
```

#### Настройте Systemd:

##### eyelash-courses.service:

```sh
[Unit]
Description=eyelash-courses start
After=network.target
After=nginx.service
After=redis.service
After=postgres.service

[Service]
User=root
Group=root
WorkingDirectory=/opt/eyelash-courses/
Environment="DEBUG=False"
Environment="ALLOWED_HOSTS=<разрешенные хосты>"
ExecStart=/opt/eyelash-courses/venv/bin/gunicorn -b 127.0.0.1:8000 --workers 3 eyelash_courses.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
```

##### bots-start.service:

```sh
[Unit]
Description=bots start
After=eyelash-courses.service

[Service]
User=root
Group=root
WorkingDirectory=/opt/eyelash-courses/
ExecStart=/opt/eyelash-courses/venv/bin/python3 manage.py start_all_bot
Restart=always 

[Install]
WantedBy=multi-user.target
```

##### Настройте регулярную очистку сессий:

eyelash-courses-clearsession.service:

```sh
[Unit]
Description=eyelash-courses clearsessions
Requires=eyelash-courses.service

[Service]
User=root
Group=root
WorkingDirectory=/opt/eyelash-courses/
ExecStart=/opt/eyelash-courses/venv/bin/python3 manage.py clearsessions
```

eyelash-courses-clearsession.timer:

```sh
[Unit]
Description=Timer for Django clearsessions

[Timer]
OnBootSec=300
OnUnitActiveSec=1w

[Install]
WantedBy=multi-user.target
```

```sh
server {
     server_name oksa-studio-school.ru 95.163.233.229;     
     listen 80;

     location /media/ {
         alias /opt/eyelash-courses/media/;
     }
     location /static/ {
         alias /opt/eyelash-courses/static/;
     }
     location / {
         include '/etc/nginx/proxy_params';
         proxy_pass http://127.0.0.1:8005/;
     }
}
```
