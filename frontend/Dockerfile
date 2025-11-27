# ============================================================================
# SARK Frontend - Multi-stage Production Dockerfile
# ============================================================================
# Optimized production build with security hardening and performance tuning
# ============================================================================

# ============================================================================
# Build Arguments
# ============================================================================
ARG NODE_VERSION=18
ARG NGINX_VERSION=1.25-alpine
ARG BUILD_ENV=production

# ============================================================================
# Stage 1: Dependencies
# ============================================================================
# Separate stage for dependencies to improve layer caching
FROM node:${NODE_VERSION}-alpine AS dependencies

WORKDIR /app

# Install security updates
RUN apk upgrade --no-cache

# Copy only package files for better caching
COPY package*.json ./

# Install dependencies with locked versions
# Using npm ci for reproducible builds
RUN npm ci --only=production=false --ignore-scripts

# ============================================================================
# Stage 2: Builder
# ============================================================================
# Build the application
FROM node:${NODE_VERSION}-alpine AS builder

WORKDIR /app

# Copy dependencies from previous stage
COPY --from=dependencies /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build arguments for runtime configuration
ARG VITE_API_URL
ARG VITE_APP_VERSION
ARG VITE_APP_NAME=SARK
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_APP_VERSION=${VITE_APP_VERSION}
ENV VITE_APP_NAME=${VITE_APP_NAME}

# Build application with production optimizations
RUN npm run build

# Verify build output exists
RUN ls -la /app/dist && \
    test -f /app/dist/index.html || (echo "Build failed: index.html not found" && exit 1)

# ============================================================================
# Stage 3: Production
# ============================================================================
# Minimal production image with nginx
FROM nginx:${NGINX_VERSION} AS production

# Install security updates and required tools
RUN apk upgrade --no-cache && \
    apk add --no-cache \
    curl \
    ca-certificates \
    tzdata

# Create non-root user for nginx (security best practice)
# Note: nginx alpine image already has nginx user, we'll use it
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Create directory for DH parameters (for SSL)
RUN mkdir -p /etc/nginx/ssl && \
    chown -R nginx:nginx /etc/nginx/ssl

# Copy nginx configuration files
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/conf.d/security-headers.conf

# Create placeholder for SSL config (optional, enabled via volume mount)
RUN echo "# SSL config placeholder - mount ssl.conf as volume in production" > /etc/nginx/conf.d/ssl.conf.disabled

# Copy built assets from builder stage
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Verify assets were copied correctly
RUN ls -la /usr/share/nginx/html && \
    test -f /usr/share/nginx/html/index.html || (echo "Assets not copied correctly" && exit 1)

# Create cache directory for nginx
RUN mkdir -p /var/cache/nginx && \
    chown -R nginx:nginx /var/cache/nginx

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Add build metadata as labels
LABEL maintainer="SARK Team" \
      description="SARK Frontend - Production Build" \
      version="${VITE_APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/apathy-ca/sark"

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost/health || exit 1

# Switch to non-root user
USER nginx

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]

# ============================================================================
# Build Instructions
# ============================================================================
# Development build:
#   docker build --target production -t sark-frontend:dev .
#
# Production build with args:
#   docker build --target production \
#     --build-arg VITE_API_URL=https://api.example.com \
#     --build-arg VITE_APP_VERSION=$(git describe --tags) \
#     -t sark-frontend:latest .
#
# ============================================================================
