docker build -t ziutek_bot .
docker run -d -p 3969:3969 --name ziutek ziutek_bot