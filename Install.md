# Anomaly Detection Installation
This document describes how to set up Anomaly Detection for OpenSDS project.

## Pip Installation
Run command ```which pip``` to check if your environment has pip tool, if not you can refer to the following steps to install it.
```shell
$ wget https://bootstrap.pypa.io/get-pip.py
$ python get-pip.py # Maybe python3 get-pip.py in your environment.
``` 

## Anomaly Detection Installation
Install anomaly detection using pip.
```shell
pip install git+https://github.com/opensds/anomaly-detection.git
```
if you want to install a specified branch, run command like blow:
```shell
$ pip install git+https://github.com/opensds/anomaly-detection.git@0.5.3
```

## Configuration
Anomaly detection will get metrics from Telemetry, before modifying the configuration file, please make sure the telemetry is started up (Note: add telemetry installation guide later).

If your python version is greater than 3.0, run follow command to copy the template configuration file to ```/etc/```,otherwise please skip this step, because the template configuration file has already been copied to the ```/etc/anomaly-detection``` by pip tool automatically.
```
# please note the python version
$ cp /usr/local/lib/python3.5/dist-packages/etc/anomaly_detection /etc
```

## Startup Services
There are three services in anomaly-detection project: api-server, data-generator, data-parser.

### Startup api-server
* Initialize the database.
    ```shell
    $ anomaly-detection-manage db sync --config-file /etc/anomaly_detection/anomaly_detection.conf 
    ```
* Startup
    ```shell
    $ anomaly-detection-api --config-file /etc/anomaly_detection/anomaly_detection.conf
    ```
* Check if server is started successfully
    ```shell
    $ curl http://127.0.0.1:8085
    ```

### Startup the data-parser
* Open the configuration file(```/etc/anomaly_detection/anomaly_detection.conf```) and modify the data_parser relative options in data_parser section. One possible configuration would be like below:
    ```
    [data_parser]
    receiver_name=kafka
    kafka_topic=metrics
    kafka_bootstrap_servers=127.0.0.1:9092
    ```
* Startup
```shell
anomaly-detection-data-parser --config-file /etc/anomaly_detection/anomaly_detection.conf
```

### Startup the data-generator
* Data-generator service will send an API request to the telemetry service periodically, so the credentials are required by data-generator. Open the configuration file(```/etc/anomaly_detection/anomaly_detection.conf```) and modify the keystone relative options in keystone_authtoken section. One possible configuration would be like blow:
    ```shell
    [keystone_authtoken]
    project_domain_name = Default
    project_name = admin
    user_domain_name = Default
    password = opensds@123
    username = admin
    auth_url = http://127.0.0.1/identity
    auth_type = password
    ```
* Open the configuration file(```/etc/anomaly_detection/anomaly_detection.conf```) and modify the data-generator relative options in data_generator section. One possible configuration would be like blow:
    ```shell
    [data_generator]
    opensds_endpoint = http://127.0.0.1:50040
    api_version = v1beta
    auth_strategy = keystone
    http_log_debug = true
    opensds_backend_driver_type = lvm
    ```
* Startup
    ```shell
    anomaly-detection-data-generator --config-file /etc/anomaly_detection/anomaly_detection.conf
    ```