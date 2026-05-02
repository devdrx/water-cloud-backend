# ─────────────────────────────────────────────────────────────
# Mosquitto with runtime password generation
# ─────────────────────────────────────────────────────────────

FROM eclipse-mosquitto:latest

COPY mosquitto.conf /mosquitto/config/mosquitto.conf
COPY entrypoint.sh  /entrypoint.sh

# Fix Windows CRLF → LF and make executable
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
