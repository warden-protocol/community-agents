FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install ALL dependencies (need devDeps for build)
RUN npm ci

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build

# Copy knowledge files to dist
RUN mkdir -p dist/knowledge && cp -r src/knowledge/* dist/knowledge/

# Remove devDependencies after build
RUN npm prune --production

# Expose port
EXPOSE 3000

# Run compiled JS
CMD ["npm", "run", "start:prod"]
