## Deployment

- [ ] Front end 
- [ ] API 
- [ ] DB 
- [ ] LLMs
- [ ] uploaded pdfs (max size: 100MB, s3(Free: 5GB), local: uploads)

Changes To be done
--

- [ ] Frontend changes 
  - document upload, S3 direct upload
  - session changes
- [ ] API
  - session management - remove those codes
  - mongodb - remove this
  - vector storage -  changes
  - fastapi on single lambda bottlenecks, segregate to multiple ones


AWS
-----
- Auth - Cognito (MAU 50 - Free - Always)
- FE - Cloudfront (CDN) + S3, 
- File storage: S3 (5GB Free Always)
- API Gateway - 1M requests free always

Fast api (24/7) 
--
- aws lambda - Serverless - Pay as you go - fastapi
- EC2 - $/hr - Costly

api → aws spins container → cold start (1st request will slow, afterward fast)

1000 req → 1s → 
1rs → 15min → terminate

15m timeout

- Prod - 8000
- DEV - 4000

DB
---
- MongoDB - auth/session - Cognito - remove this component
- CromaDB - Vector storage - AWS Document db

LLM
---

Sagemaker/Bedrock

- gemma
- llama

CI/CD
---

- Deployments
  - Container - Build Images -> ECR (dockerhub.io) -> lambda/ECS(Fargate/EC2)/EC2/EKS
  - Plain old - file copy into system, → EC2/lambda/BeanStalk

GitHub push → workflow triggers → 

1. FE → npm run build → dist/ → s3 serves the new code
2. BE -> fastapi -> lambda code update -> code deployed

Logs
--

1. cloudwatch - logs
2. EC2 → not direct logs streams → heartbit service → cloudwatch

Monitoring
----

- Grafana - Dashboard framework
- prometheus
- loki/fluentbit