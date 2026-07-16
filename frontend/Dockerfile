# ==============================================================
# FRONTEND — Dockerfile multi-stage Next.js
#
# Stage 1 (deps)    : installation des dépendances npm
# Stage 2 (builder) : build de production Next.js
# Stage 3 (runner)  : image finale minimale (~200MB vs ~1GB)
# ==============================================================

# ---- Stage 1 : Dépendances ----------------------------------
FROM node:20-alpine AS deps

RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install


# ---- Stage 2 : Build ----------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Variables disponibles au build-time (injectées dans le bundle JS)
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000

ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build


# ---- Stage 3 : Runner (image minimale) ----------------------
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Utilisateur non-root pour la sécurité
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# Fichiers nécessaires au runtime Next.js standalone
RUN mkdir -p ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone   ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# ------ Healthcheck ------------------------------------------
# Use node + 127.0.0.1 (not wget/localhost): "localhost" can resolve to IPv6
# ::1 first, but the Next server binds IPv4 0.0.0.0, so wget would fail.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/',r=>process.exit(r.statusCode<400?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
