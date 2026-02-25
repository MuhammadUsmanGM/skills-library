# Docusaurus Deployment Reference

## Quick Start

```bash
# Initialize site
python scripts/init_docusaurus.py learnflow-docs --title "LearnFlow Documentation"

# Install and run locally
cd learnflow-docs
npm install
npm start

# Build and deploy
python scripts/build.py learnflow-docs --docker
python scripts/deploy.py learnflow-docs --namespace docs
```

## Documentation Structure

### Organizing Docs

```
docs/
├── intro.md                    # Introduction (sidebar_position: 1)
├── getting-started/
│   ├── installation.md
│   ├── configuration.md
│   └── quickstart.md
├── guides/
│   ├── basic-usage.md
│   ├── advanced-features.md
│   └── best-practices.md
├── api/
│   ├── overview.md
│   ├── endpoints.md
│   └── authentication.md
└── troubleshooting.md
```

### Doc Frontmatter

```markdown
---
sidebar_position: 1
title: Getting Started
description: Learn how to get started with LearnFlow
keywords: [getting started, installation, setup]
---
```

### Sidebar Configuration

```javascript
// sidebars.js
module.exports = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/installation',
        'getting-started/configuration',
        'getting-started/quickstart',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/basic-usage',
        'guides/advanced-features',
        'guides/best-practices',
      ],
    },
  ],
};
```

## Dockerfile Patterns

### Multi-Stage Build

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
    }
}
```

## Kubernetes Deployment

### Basic Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: learnflow-docs
spec:
  replicas: 2
  selector:
    matchLabels:
      app: learnflow-docs
  template:
    metadata:
      labels:
        app: learnflow-docs
    spec:
      containers:
      - name: learnflow-docs
        image: learnflow-docs:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "50m"
            memory: "128Mi"
          limits:
            cpu: "200m"
            memory: "256Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: learnflow-docs
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: learnflow-docs
```

### Ingress with TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: learnflow-docs-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - docs.learnflow.example.com
    secretName: learnflow-docs-tls
  rules:
  - host: docs.learnflow.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: learnflow-docs
            port:
              number: 80
```

## Docusaurus Configuration

### Essential Config

```javascript
// docusaurus.config.js
module.exports = {
  title: 'LearnFlow Documentation',
  tagline: 'AI-Powered Python Tutoring Platform',
  url: 'https://docs.learnflow.example.com',
  baseUrl: '/',
  
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/your-org/learnflow-docs/tree/main/',
          routeBasePath: '/', // Serve docs at root
        },
        blog: {
          showReadingTime: true,
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
  
  themeConfig: {
    navbar: {
      title: 'LearnFlow',
      logo: {
        alt: 'LearnFlow Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'Docs',
        },
        {to: '/blog', label: 'Blog', position: 'left'},
        {
          href: 'https://github.com/your-org/learnflow',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
  },
};
```

### Search Configuration (Algolia)

```javascript
themeConfig: {
  algolia: {
    appId: 'YOUR_APP_ID',
    apiKey: 'YOUR_SEARCH_API_KEY',
    indexName: 'learnflow',
    contextualSearch: true,
  },
}
```

### SEO Configuration

```javascript
module.exports = {
  headTags: [
    {
      tagName: 'meta',
      attributes: {
        name: 'description',
        content: 'LearnFlow - AI-Powered Python Tutoring Platform',
      },
    },
    {
      tagName: 'meta',
      attributes: {
        property: 'og:title',
        content: 'LearnFlow Documentation',
      },
    },
  ],
};
```

## Customization

### Custom CSS

```css
/* src/css/custom.css */
:root {
  --ifm-color-primary: #2e8555;
  --ifm-font-family-base: 'Inter', system-ui, -apple-system, sans-serif;
}

.hero {
  padding: 4rem 0;
  text-align: center;
}

.hero__title {
  font-size: 3rem;
  font-weight: 800;
}
```

### Custom Pages

```javascript
// src/pages/index.js
import React from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';

export default function Home() {
  return (
    <Layout title="Home">
      <main className="container margin-vert--lg">
        <h1>Welcome to LearnFlow</h1>
        <p>AI-powered Python tutoring platform</p>
        <Link to="/docs/intro" className="button button--primary">
          Get Started
        </Link>
      </main>
    </Layout>
  );
}
```

### Custom Theme Components

```bash
# Swizzle a component
npm run swizzle @docusaurus/theme-classic Footer
```

## Content Writing

### Markdown Features

```markdown
# Headings

## Code Blocks

```python
def hello():
    print("Hello, World!")
```

### Admonitions

:::tip Tip
This is a helpful tip!
:::

:::note Note
Important information here.
:::

:::warning Warning
Be careful with this!
:::

### Tabs

<Tabs>
  <TabItem value="npm" label="NPM">
    ```bash
    npm install package
    ```
  </TabItem>
  <TabItem value="yarn" label="Yarn">
    ```bash
    yarn add package
    ```
  </TabItem>
</Tabs>
```

### Images

```markdown
![Alt text](/img/screenshot.png)

<figure>
  <img src="/img/diagram.svg" alt="Architecture diagram" />
  <figcaption>LearnFlow Architecture</figcaption>
</figure>
```

## Deployment Automation

### GitHub Actions

```yaml
name: Deploy Docs

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Build
      run: npm run build
    
    - name: Build Docker image
      run: docker build -t learnflow-docs:${{ github.sha }} .
    
    - name: Push to registry
      run: |
        docker tag learnflow-docs:${{ github.sha }} registry.example.com/learnflow-docs:${{ github.sha }}
        docker push registry.example.com/learnflow-docs:${{ github.sha }}
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/learnflow-docs \
          learnflow-docs=registry.example.com/learnflow-docs:${{ github.sha }} \
          -n docs
```

## Troubleshooting

### Build Fails

```bash
# Clear cache
npm run clear

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Try build again
npm run build
```

### Images Not Loading

```bash
# Check static directory structure
ls -la static/img/

# Verify image paths in markdown
# Use absolute paths: /img/logo.png
```

### Deployment Issues

```bash
# Check pod status
kubectl get pods -n docs -l app=learnflow-docs

# View logs
kubectl logs -n docs -l app=learnflow-docs

# Check service
kubectl describe svc learnflow-docs -n docs
```

## Performance Optimization

### Image Optimization

```bash
# Install sharp for image optimization
npm install sharp

# Docusaurus will automatically optimize images
```

### Lazy Loading

```javascript
// In docusaurus.config.js
themeConfig: {
  image: 'img/social-card.jpg',
  metadata: [
    {name: 'twitter:card', content: 'summary_large_image'},
  ],
}
```

### Bundle Analysis

```bash
# Analyze bundle size
npm install --save-dev webpack-bundle-analyzer

# Add to webpack config
```

## Related Resources

- [Docusaurus Documentation](https://docusaurus.io/docs)
- [Docusaurus API](https://docusaurus.io/docs/api/docusaurus-core)
- [MDX Documentation](https://mdxjs.com/docs/)
