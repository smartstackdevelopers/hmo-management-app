# Network architecture

Terraform module: `infra/aws/terraform/modules/networking`

## Layout

| Tier | Subnets | Access |
| --- | --- | --- |
| Public | 2× AZ | ALB / NAT (optional) |
| Private app | 2× AZ | ECS tasks |
| Private data | 2× AZ | RDS, ElastiCache |

## Rules

- RDS `publicly_accessible = false`
- Redis in private subnets; security group allows 6379 from app SG only
- S3 via VPC gateway endpoint (recommended add-on post-approval)
- No SSH bastion; prefer SSM Session Manager for break-glass

## Security groups

| SG | Ingress | Egress |
| --- | --- | --- |
| ALB | 443 from internet | To app SG |
| App | From ALB | 443 (Auth0, LLM), to data SG |
| Data | 5432/6379 from app | Minimal |

NAT Gateway: **disabled** by default (`create_nat_gateway = false`) due to cost — **PENDING APPROVAL** for outbound-only private tasks.
