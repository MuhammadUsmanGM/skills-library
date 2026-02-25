---
name: docusaurus-deploy
description: Deploy Docusaurus documentation sites to Kubernetes
---

# Docusaurus Documentation Deployment

## When to Use
- Creating documentation for LearnFlow project
- Deploying static documentation sites
- Setting up auto-generated API docs

## Instructions

### Initialize Docusaurus
1. Run init: `python scripts/init_docusaurus.py <site-name> --title "My Docs"`
2. Review generated structure
3. Customize content in `docs/` folder

### Build and Deploy
1. Build: `python scripts/build.py <site-name>`
2. Deploy: `python scripts/deploy.py <site-name> --namespace docs`
3. Verify: `python scripts/verify.py <site-name> --namespace docs`

### Configure Ingress
1. Create ingress: `python scripts/create_ingress.py <site-name> --domain docs.example.com`

## Validation
- [ ] Site builds without errors
- [ ] Pod is Running
- [ ] Site accessible via browser
- [ ] Search working (if configured)

See [REFERENCE.md](./REFERENCE.md) for documentation structure and deployment options.
