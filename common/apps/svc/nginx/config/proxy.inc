proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-for $proxy_add_x_forwarded_for;
#proxy_set_header Host $http_host;
auth_basic "Edge Services";
auth_basic_user_file /etc/nginx/conf.d/operators.pass;
