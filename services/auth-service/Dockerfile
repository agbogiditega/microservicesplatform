FROM public.ecr.aws/amazonlinux/amazonlinux:2

# Install Node.js 20 (NodeSource) + minimal tools
RUN yum -y update \
    && yum -y install curl ca-certificates \
    && curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - \
    && yum -y install nodejs \
    && yum -y clean all \
    && rm -rf /var/cache/yum

WORKDIR /app

# Create non-root user
RUN useradd -m appuser

COPY package.json package-lock.json* ./
RUN npm ci --omit=dev || npm install --omit=dev

COPY src ./src

USER appuser
EXPOSE 8080

CMD ["npm", "start"]
