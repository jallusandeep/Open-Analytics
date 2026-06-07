# ---------------- base ----------------
FROM node:20-bookworm-slim AS base

# ---------------- deps ----------------
FROM base AS deps
WORKDIR /app

RUN apt-get update && apt-get install -y \
  wget \
  libc6 \
  && rm -rf /var/lib/apt/lists/*

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

ARG VITE_UPSTOX_REDIRECT_URL
ENV VITE_UPSTOX_REDIRECT_URL=$VITE_UPSTOX_REDIRECT_URL

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

# ---------------- builder ----------------
FROM base AS builder
WORKDIR /app

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./

RUN npm run build

# ---------------- runner ----------------
FROM base AS runner
WORKDIR /app

RUN apt-get update && apt-get install -y wget \
  && rm -rf /var/lib/apt/lists/*

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["serve", "-s", "dist", "-l", "3000"]