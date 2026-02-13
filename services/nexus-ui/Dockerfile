# Stage 1: Build the React app
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json ./
RUN npm install

COPY tsconfig.json vite.config.ts ./
COPY src/ src/

# Gemini API key is optional — build with empty default
ARG GEMINI_API_KEY=""
RUN echo "GEMINI_API_KEY=${GEMINI_API_KEY}" > .env.local && npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
