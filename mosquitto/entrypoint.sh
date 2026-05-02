#!/bin/sh
set -e

MQTT_USER="${MQTT_USER:-wateriot}"
MQTT_PASSWORD="${MQTT_PASSWORD:-changeme}"

echo "Generating Mosquitto password file for user '${MQTT_USER}'..."
rm -f /mosquitto/config/password_file
mosquitto_passwd -b -c /mosquitto/config/password_file "${MQTT_USER}" "${MQTT_PASSWORD}"
chown mosquitto:mosquitto /mosquitto/config/password_file

exec "$@"
