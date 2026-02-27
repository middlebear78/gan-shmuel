FROM nginx:alpine                                                                                                                                                 │
     │ COPY index.html /usr/share/nginx/html/                                                                                                                            │
     │ COPY style.css /usr/share/nginx/html/                                                                                                                             │
     │ COPY app.js /usr/share/nginx/html/                                                                                                                                │
     │                                                                                                                                                                   │
     │ frontend/docker-compose.yml:                                                                                                                                      │
     │ services:                                                                                                                                                         │
     │   frontend:                                                                                                                                                       │
     │     build: .                                                                                                                                                      │
     │     ports:                                                                                                                                                        │
     │       - "8080:80"                                                                                                                                                 │
     │                   