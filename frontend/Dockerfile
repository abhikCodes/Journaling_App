FROM node:18-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies with package-lock
RUN npm ci

# Copy the rest of the code
COPY . .

# Expose port 3000
EXPOSE 3000

# Start Vite dev server with hot reloading
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3001"]