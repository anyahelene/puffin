# Puffin v2.0


## Developer setup

### Starting

```
flask --debug -A puffin.app.app run
```

Connect to http://localhost:5000/ 

GitLab login at http://localhost:5000/login/gitlab

### Console commands

#### Set active course

```javascript
await puffin.Course.setActiveCourse(39903); puffin.CourseView.set_course_view()
```

#### Refresh course list

```javascript
await puffin.Course.updateCourses()
```

#### Show course page with sync button (move this!)

```javascript
await puffin.CourseView.display_course(puffin.Course.current)
```
## Dev server
### Nginx configuration

assuming `APP_PREFIX=/puffin`:
```
        location /puffin {
            proxy_pass http://localhost:7777;
            include /etc/nginx/proxy_params;
        }

        location ~ ^/puffin/((js|style|assets|fonts|css|webpack-dev-server)/.*)$ {
            # drop the /puffin/ from the URL path
            rewrite ^/puffin/(.*)$ /$1 break;
            proxy_pass http://localhost:7778;
            include /etc/nginx/proxy_params;
        }
```

## Production deployment

### Nginx configuration
Assuming `APP_PATH=/srv/puffin` and `APP_PREFIX=/puffin`:
```
        location / {
                include /etc/nginx/proxy_params;
                #proxy_pass http://localhost:8080;
                proxy_pass http://unix:/run/puffin/gunicorn.sock:$request_uri;
        }

        location ~ ^/puffin/((js|style|assets|fonts|css)/.*)$ {
            rewrite ^/puffin/(.*)$ /$1 break;
            root /srv/puffin/webroot/;
        }
```

### Docker
Adjust the `Dockerfile` as needed, then build with:

```
docker build -t puffin:latest .
```

and start with:
```
docker run --init \
    -v /srv/puffin:/srv/puffin \
    -v /var/log/puffin:/var/log/puffin \
    -v /run/puffin:/run/puffin \
    puffin
```

### Gunicorn without Docker
```
gunicorn --bind unix:/run/gunicorn.sock --access-logfile /var/log/puffin/access.log --error-logfile /var/log/puffin/error.log puffin.app:app
```

(If using systemd and launching from a systemd socket, drop the `--bind unix:…` part – gunicorn will inherit the socket as a file descriptor.)

