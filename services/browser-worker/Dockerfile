FROM mcr.microsoft.com/playwright:v1.41.2-focal

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

CMD ["npm", "start"]
