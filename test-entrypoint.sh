#!/bin/sh

set -e

wget -O mkcert -nc https://github.com/FiloSottile/mkcert/releases/download/v1.4.1/mkcert-v1.4.1-linux-amd64
chmod +x mkcert
./mkcert -install
./mkcert -cert-file server-cert.pem -key-file server-key.pem localhost ::1

exec nats-server --port 4224 --tls --tlscert server-cert.pem --tlskey server-key.pem
