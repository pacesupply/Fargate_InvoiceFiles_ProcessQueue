# Fargate_InvoiceFiles_ProcessQueue

Made to run in a docker contain on a fargate procecs using ECS, it will take one item off the queue and process it, or you can pass in a filename directly to process.

* run for venv
filename=005020.xlsx python run.py

* Build:
```
docker build -t docker-fargate-app .  
```

* RUN:
From Queue:
```
docker run --rm -it -p 80:80 -e 'HOME=/code' -t -v $HOME/.aws:/code/.aws:ro docker-fargate-app
```

* Process filedirectly:
```
docker run --rm -it -p 80:80 -e 'HOME=/code' -e 'filename=37000-00.xlsx' -t -v $HOME/.aws:/code/.aws:ro docker-fargate-app
```


## PUSH IMAGE TO ECR: fargate_invoicefiles_processqueue

* login - make sure docker is running
```
aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 486878523588.dkr.ecr.us-west-1.amazonaws.com
```

* build
```
docker build --platform linux/amd64 -t fargate_invoicefiles_processqueue .
```

* tag
```
docker tag fargate_invoicefiles_processqueue:latest 486878523588.dkr.ecr.us-west-1.amazonaws.com/fargate_invoicefiles_processqueue:latest
```

* push
```
docker push 486878523588.dkr.ecr.us-west-1.amazonaws.com/fargate_invoicefiles_processqueue:latest
```

* Image url
486878523588.dkr.ecr.us-west-1.amazonaws.com/fargate_invoicefiles_processqueue:latest


### Cluster name:
fargate-invoicefiles-processqueue-cluster

### Container
fargate-invoicefiles-processqueue-container

### Task
fargate-invoicefiles-processqueue-task 

### SERVICES
fargate-invoicefiles-processqueue-service

### run task directly from terminal (will process 1st file from queue)
```
aws --region us-west-1 ecs run-task --cluster fargate-invoicefiles-processqueue-cluster --task-definition fargate-invoicefiles-processqueue-task --count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-0e481b9e0173c9528,subnet-019ac445c965c6a22],securityGroups=[sg-00c1682ca200e79ac]}"
```

### run task directly from terminal with filename
```
aws --region us-west-1 ecs run-task --cluster fargate-invoicefiles-processqueue-cluster --task-definition fargate-invoicefiles-processqueue-task --count 1 --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[subnet-0e481b9e0173c9528,subnet-019ac445c965c6a22],securityGroups=[sg-00c1682ca200e79ac]}' --overrides '{ "containerOverrides": [ { "name": "fargate-invoicefiles-processqueue-container", "environment": [ { "name": "filename", "value": "005020.xlsx" } ] } ] }'
```
