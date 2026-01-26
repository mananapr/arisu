## arisu

Bot for signal group chats.

### Setup

Setup `.env` file
```bash
cp .example.env .env
editor .env
```

Register device (Only required for the first time)
```bash
docker compose --profile init up
# go to http://127.0.0.1:8080/v1/qrcodelink?device_name=local
```

Start JSON-RPC and arisu
```bash
docker compose --profile init down
docker compose up -d
uv run main.py
```
