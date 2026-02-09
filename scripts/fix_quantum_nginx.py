import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('10.10.1.40', username='abathur', password='SargaS91195', timeout=10)

# Get all running quantum containers
stdin, stdout, stderr = client.exec_command('sudo docker ps --filter "name=quantum-" --format "{{.Names}}"')
containers = [c.strip() for c in stdout.read().decode().strip().split('\n') if c.strip()]
print(f"Found containers: {containers}")

# Build nginx config
config = """# Quantum Apps - quantum.sargas.cloud
# Auto-generated from running containers
server {
    listen 80;
    server_name quantum.sargas.cloud;

    # Default - landing page
    location / {
        proxy_pass http://quantum-quantum-landing:8080/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""

# Standard apps with their routes
apps = {
    'quantum-rag': 'rag',
    'quantum-blog': 'blog',
    'quantum-mario': 'mario',
    'quantum-snake': 'snake',
    'quantum-tictactoe': 'tictactoe',
    'quantum-tower': 'tower',
    'quantum-hello': 'hello',
    'quantum-chat': 'chat',
    'quantum-llm-demo': 'llm',
    'quantum-quantum-blog': 'quantum-blog',
    'quantum-quantum-landing': 'quantum-landing',
    'quantum-quantum-debug': 'quantum-debug',
    'quantum-dashboard': 'dashboard',
}

for container in containers:
    if container in apps:
        route = apps[container]
        config += f"""
    # {container}
    location /{route}/ {{
        proxy_pass http://{container}:8080/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /{route};
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }}
"""

config += "}\n"

# Write via SFTP
sftp = client.open_sftp()
with sftp.file('/tmp/quantum_nginx_full.conf', 'w') as f:
    f.write(config)
sftp.close()
print('Config written to /tmp/quantum_nginx_full.conf')

# Copy to NPM
stdin, stdout, stderr = client.exec_command('sudo docker cp /tmp/quantum_nginx_full.conf nginx-proxy-manager:/data/nginx/default_host/quantum.conf')
stdout.channel.recv_exit_status()
print('Copied to NPM container')

# Test nginx
stdin, stdout, stderr = client.exec_command('sudo docker exec nginx-proxy-manager nginx -t')
exit_status = stdout.channel.recv_exit_status()
result = stderr.read().decode()
print(f'Nginx test: {result}')

if exit_status == 0:
    stdin, stdout, stderr = client.exec_command('sudo docker exec nginx-proxy-manager nginx -s reload')
    stdout.channel.recv_exit_status()
    print('Nginx reloaded')
else:
    print('ERROR: nginx test failed')

client.exec_command('rm /tmp/quantum_nginx_full.conf')
client.close()
print('Done!')
