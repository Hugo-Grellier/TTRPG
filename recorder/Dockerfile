FROM node:22.23.4-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY bot.mjs decode.mjs session.mjs ./
ENV RECORDER_OUTPUT_DIR=/recordings
USER node
CMD ["node", "bot.mjs"]
