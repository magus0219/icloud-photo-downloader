# Artascope

Artascope is a project to sync iCloud Photos to your own device (e.g. NAS).
It wrapped [picklepete/pyicloud](https://github.com/picklepete/pyicloud) with celery and offer a simple WEB UI.

## Motivation
I used to take photos by iPhone and iCloud complains not enough storage space soon.
After got one NAS(Synology 918+) I started to use Synology Moments/Photo Station to manager my pictures. But they also have shortcomings:
1. Upload occurs only opening Apps
2.


## Features
#### Simple UI to set up account info and running configuration
#### Support filter photos by date/last count
#### Sync photos to remote sftp server
#### Resume broken transfer during downloading photos
#### Simple notification by slack channel or email
#### Support schedule sync tasks using crontab expression

## Installation
### Clone repository
```bash
git clone https://github.com/magus0219/icloud-photo-downloader
```

### Deploy by Docker-compose or Kubernetes
#### Docker-compose
Use the [docker-compose](https://docs.docker.com/compose/) to install artascope.

```bash
env=value... docker-compose -f deployment/docker-compose/docker-compose.yml up -d
```
You can add env
* ARTASCOPE_WEB_PORT is port of web admin
* ARTASCOPE_FLOWER_PORT is port of flower (celery admin)

#### Kubernetes
Use the [Kubernetes](https://kubernetes.io/) to install artascope.

1. Build k8s yaml with custom environment variables
    1. Install [envsubst](https://command-not-found.com/envsubst)
    2. Build using the following script:

    ```bash
    cd deployment/k8s
    env1=value1 env2=value2... sh ./create_k8s_yaml.sh
    ```

    Available Environment Variables:

    | # | Name | default | desc |
    |----|----|----|----|
    | 1 |ARTASCOPE_TIMEZONE| UTC | TIMEZONE used by project |
    | 2 |ARTASCOPE_STORAGE_CLASS| managed-nfs-storage | [Storage Class](https://kubernetes.io/docs/concepts/storage/storage-classes) of PVC used by redis<br>You should *always* overwrite it to adapt for your k8s cluster |
    | 3 |ARTASCOPE_ADMIN_PORT| 31100 | [NodePort](https://kubernetes.io/docs/concepts/services-networking/service/#nodeport) of Web Admin |
    | 4 |ARTASCOPE_FLOWER_PORT| 31101 | [NodePort](https://kubernetes.io/docs/concepts/services-networking/service/#nodeport) of Celery Admin |


2. Modify service.yaml to adapt for your k8s cluster if needed(e.g. ingress)

3. Apply k8s yaml
```bash
kubectl apply -f build/namespace.yaml
kubectl apply -f build/
```

## Uninstallation
### docker-compose
```bash
cd deployment/docker-compose
ARTASCOPE_WEB_PORT={port1} ARTASCOPE_FLOWER_PORT={port2} docker-compose down -v --rmi all
```

### kubernetes
```bash
cd deployment/k8s
kubectl delete -f build/
```

## Usage
### Add User
Open Web admin(http://{admin_host}:{admin:port}/user/) and click 'Add' button.

| # | Name | sample | desc |
|----|----|----|----|
| 1 |Username| name@example.com | iCloud account username |
| 2 |Password| **** | iCloud account password |
| 3 |URL Prefix| http://{admin_host}:{admin:port} | used to generate URL in notification message |
| 4 |SFTP Host| 192.168.1.1 | Target SFTP Host |
| 5 |SFTP Port| 22 | Target SFTP Port |
| 6 |SFTP User| somebody | Target SFTP Username |
| 7 |SFTP Password| **** | Target SFTP Password |
| 8 |Slack Token | **** | Token used by your slack app |
| 9 |Channel Name | channel | Which slack channel message will be send to |
| 10 |SMTP Host| smtp.google.com | SMTP Host |
| 11 |SMTP Port| 465 | SMTP Port |
| 12 |SMTP Username| somebody | SMTP Username |
| 13 |SMTP Password| **** | SMTP Password |
| 14 |Email From| somebody@domain.com | Email sender |
| 15 |Email To| somebody@domain.com;somebody@domain.com | Email Receivers |
| 16 |Trigger Time| 0 1 * * * | Crontab Expression Format: min hour day month weekday |
| 17 |Sync Photos of Recently Days| 3 | Sync photos of last *cnt* days|

### Run task
Open Web admin(http://{admin_host}:{admin:port}/user/) and click 'Run' button.
Select Run type:

| # | Type | desc |
|----|----|----|
| 1 | All | download all photos in iCloud |
| 2 | Last | download last *Cnt* photos |
| 3 | DateRange | download photos filtered by date range |

### Check task status
Open Web admin(http://{admin_host}:{admin:port}/task/) and click specific task.

### Check scheduled task
Open Web admin(http://{admin_host}:{admin:port}/scheduler/) to see next trigger time of tasks.

### Restrictions
1. Live Photos are missing

   Improvement needed in picklepete/pyicloud to support downloading live photos.

2. Security

   Your iCloud Account and Password are stored in redis.
   The web UI is crude and simple. It is better to setup a https reverse-proxy in front of it.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
