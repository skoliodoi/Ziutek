# Dodatkowe pliki
### [Klucz do Secret Managera](https://console.cloud.google.com/security/secret-manager/secret/ziutek-key/versions?project=kluczbork-vcc) (wymagany do uruchomienia Dockera)
### [Manifest.json](https://console.cloud.google.com/security/secret-manager/secret/ziutek-manifest-json/versions?project=ziutek) (potrzebny na wypadek uruchomienia wersji developerskiej na Teamsach - umieszczamy go w folderze "manifest", następnie kompresujemy WSZYSTKIE pliki znajdujące się w tym folderze i wrzucamy powstały w ten sposób "manifest.zip" do Teamsów) 



# Odpalanie dockera
## Windows:
- w roocie: docker_run.ps1

## Linux:
- w roocie: bash docker_run.sh


## ALBO:
- docker build -t ziutek_bot .
- docker run -p 3969:3969 --name ziutek ziutek_bot
