import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('10.10.1.40', username='abathur', password='SargaS91195', timeout=10)

# Read current config
stdin, stdout, stderr = client.exec_command('sudo docker exec nginx-proxy-manager cat /data/nginx/default_host/quantum.conf')
content = stdout.read().decode()

rag_location = """
    # Quantum App: rag
    location /rag/ {
        proxy_pass http://quantum-rag:8080/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /rag;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
"""

# Insert before final closing brace
new_content = content.rstrip().rstrip('}') + rag_location + '\n}\n'

# Write via SFTP to temp file
sftp = client.open_sftp()
with sftp.file('/tmp/quantum_nginx.conf', 'w') as f:
    f.write(new_content)
sftp.close()
print('Written to /tmp/quantum_nginx.conf')

# Copy into NPM container
stdin, stdout, stderr = client.exec_command('sudo docker cp /tmp/quantum_nginx.conf nginx-proxy-manager:/data/nginx/default_host/quantum.conf')
exit_status = stdout.channel.recv_exit_status()
err = stderr.read().decode()
if err:
    print(f'Copy error: {err}')
else:
    print('Config copied to NPM container')

# Test nginx config
stdin, stdout, stderr = client.exec_command('sudo docker exec nginx-proxy-manager nginx -t')
exit_status = stdout.channel.recv_exit_status()
result = stderr.read().decode()
print(f'Nginx test: {result}')

# Reload nginx
if exit_status == 0:
    stdin, stdout, stderr = client.exec_command('sudo docker exec nginx-proxy-manager nginx -s reload')
    exit_status = stdout.channel.recv_exit_status()
    result = stderr.read().decode()
    print(f'Nginx reload: {result}')
    print('DONE - /rag/ route added to quantum.sargas.cloud')
else:
    print('ERROR - nginx config test failed, not reloading')

# Cleanup
client.exec_command('rm /tmp/quantum_nginx.conf')
client.close()
