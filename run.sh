docker stop rickbot && docker rm rickbot
docker run --name rickbot -d --restart="always" --env-file envfile.list --link redis:redis rickbot-bot
docker stop rickbot-web && docker rm rickbot-web
docker run -d --restart="always" --name rickbot-web --link redis:redis --env-file envfile.list rickbot-web
