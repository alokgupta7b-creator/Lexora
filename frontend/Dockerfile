FROM node:20-alpine AS builder

WORKDIR /workspace

# Copy dependencies manifest
COPY package.json package-lock.json* ./
RUN npm install

# Copy application source
COPY . .

# Build Next.js static asset bundles
RUN npm run build

# --- Production runner image ---
FROM node:20-alpine AS runner
WORKDIR /workspace

COPY --from=builder /workspace/package.json ./
COPY --from=builder /workspace/.next ./.next
COPY --from=builder /workspace/public ./public
COPY --from=builder /workspace/node_modules ./node_modules

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["npm", "run", "start"]
