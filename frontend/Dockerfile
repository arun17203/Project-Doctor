# ==============================================================================
# Project Doctor - Frontend Multi-Stage Containerfile
# Stage 1: Build static assets with Node.js 20
# Stage 2: Serve high-performance static SPA with Nginx Alpine
# ==============================================================================

# -----------------
# Stage 1: Builder
# -----------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies using package-lock.json for reproducible builds
COPY package*.json ./
RUN npm ci

# Copy source code and build production bundle
COPY . .
RUN npm run build

# -----------------
# Stage 2: Production Web Server
# -----------------
FROM nginx:1.27-alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy production build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
