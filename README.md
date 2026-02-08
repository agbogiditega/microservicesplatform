# AWS Microservices Platform

Auth • User • Billing • Notification

This repository contains a production-style repo for deploying a distributed microservices platform on AWS ECS Fargate, fronted by an Application Load Balancer (HTTPS) and backed by RDS, SQS, Secrets Manager, Parameter Store, CloudWatch, and Auto Scaling.

The platform is designed to be deployed using CloudFormation and container images stored in Amazon ECR.

## Architecture Summary

![Diagram](./architecture.png)

* **Compute:** Amazon ECS (Fargate)
* **Ingress:** Application Load Balancer (HTTPS, TLS via ACM)
* **Networking:** VPC with 2 public + 4 private subnets, NAT Gateways
* **Services:** auth-service, user-service, billing-service, notification-service
* **Data:** Amazon RDS (PostgreSQL)
* **Messaging:** Amazon SQS with DLQ
* **Config & Secrets:** SSM Parameter Store, AWS Secrets Manager
* **Observability:** CloudWatch Logs (KMS encrypted), Metrics, Alarms
* **Scaling:** ECS Service Auto Scaling (CPU target tracking)

## Repository Structure
```
microservices-platform/
├── cloudformation/
│   └── microserviceplatform.yaml
├── services/
│   ├── auth-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/main.py
│   ├── user-service/
│   ├── billing-service/
│   └── notification-service/
├── README.md
└── .gitignore
```

## Prerequisites

Ensure the following are installed and configured:
* AWS CLI v2 (aws --version)
* Docker (with Buildx enabled)
* Git
* An AWS account with permissions for:
  * CloudFormation
  * ECS, ECR
  * EC2/VPC
  * RDS
  * SQS
  * IAM
  * CloudWatch
  * Secrets Manager
  * SSM Parameter Store
  * An ACM certificate issued in the target region (for HTTPS)

## Environment Setup
```
export AWS_REGION="us-east-1"
export ENV="dev"               
export STACK_NAME="$ENV-microservices-platform"
export ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
```

## Step 1: Deploy CloudFormation Infrastructure
Validate template
```
aws cloudformation validate-template \
  --template-body file://cloudformation/microserviceplatform.yaml
```

Deploy stack
```
aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --template-file cloudformation/microserviceplatform.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvironmentName="$ENV" \
    AcmCertificateArn="arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/XXXXXXXX"
```    

## Wait for completion
```
aws cloudformation wait stack-create-complete \
  --stack-name "$STACK_NAME"
```


This step provisions:
* VPC, subnets, NAT Gateways
* ALB (HTTP → HTTPS redirect)
* ECS Cluster
* ECR repositories (4)
* RDS PostgreSQL
* SQS + DLQ
* IAM roles (least privilege)
* CloudWatch log groups, alarms
* ECS services & auto scaling

## Step 2: Build & Push Container Images to ECR

Important: ECS Fargate expects linux/amd64.
If building on Apple Silicon (M1/M2/M3), you must use multi-arch builds.

Enable Docker Buildx (one-time)
```
docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch
docker buildx inspect --bootstrap
```

Authenticate Docker to ECR
```
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
  "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

Build & push all services (multi-arch)
```
export TAG="latest"
ECR="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker buildx build --platform linux/amd64,linux/arm64 \
  -t "$ECR/$ENV/auth-service:$TAG" \
  --push ./services/auth-service

docker buildx build --platform linux/amd64,linux/arm64 \
  -t "$ECR/$ENV/user-service:$TAG" \
  --push ./services/user-service

docker buildx build --platform linux/amd64,linux/arm64 \
  -t "$ECR/$ENV/billing-service:$TAG" \
  --push ./services/billing-service

docker buildx build --platform linux/amd64,linux/arm64 \
  -t "$ECR/$ENV/notification-service:$TAG" \
  --push ./services/notification-service
```

Verify image manifests include amd64
```
aws ecr describe-images \
  --region "$AWS_REGION" \
  --repository-name "$ENV/auth-service"
```

## Step 3: Update ECS Services (if images were pushed after stack creation)

If the stack was created before images existed, update it to force ECS to pull images:

```
aws cloudformation update-stack \
  --stack-name "$STACK_NAME" \
  --use-previous-template \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=AuthImageTag,ParameterValue="$TAG" \
    ParameterKey=UserImageTag,ParameterValue="$TAG" \
    ParameterKey=BillingImageTag,ParameterValue="$TAG" \
    ParameterKey=NotificationImageTag,ParameterValue="$TAG"
```

Or simply force a new deployment:

```
aws ecs update-service \
  --cluster "$ENV-ecs-cluster" \
  --service "$ENV-auth-service" \
  --force-new-deployment
```

(Repeat for other services if needed.)

## Step 4: Verify Deployment
Get ALB endpoint
```
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='AlbDnsName'].OutputValue" \
  --output text
```

Health checks
```
curl -k https://<ALB_DNS>/auth/health
curl -k https://<ALB_DNS>/users/health
curl -k https://<ALB_DNS>/billing/health
curl -k https://<ALB_DNS>/notify/health
```


Expected response:
```
{
  "status": "ok",
  "checks": {
    "db_tcp": true,
    "sqs_access": true
  }
}
```

Step 5: Observability & Operations
* Logs: CloudWatch → `/ecs/<env>/<service-name>`
* Metrics: ECS CPU/Memory, ALB request counts

Alarms:
* ALB 5XX errors
* ECS service CPU high
* Scaling: Automatic ECS task scaling based on CPU utilization

Security Notes
* No hard-coded credentials
* Secrets stored in Secrets Manager (KMS-encrypted)
* Config in SSM Parameter Store
* ECS Task Roles use least-privilege IAM
* Private subnets with NAT egress only
*TLS enforced at ALB

Common Errors & Fixes
* CannotPullContainerError: platform linux/amd64
  Fix: Rebuild images using docker buildx --platform linux/amd64,linux/arm64.

* Tasks stuck in PENDING
  Check NAT Gateway routes

* Verify subnets and security groups
  Confirm image exists in ECR

* Health checks failing
  Ensure /health endpoint exists
  Confirm container port matches target group port

