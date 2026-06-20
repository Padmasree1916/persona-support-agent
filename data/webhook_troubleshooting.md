# Webhook delivery troubleshooting

Webhook endpoints must accept HTTPS POST requests and return a 2xx response within 10 seconds. Adsparkx retries failed deliveries after 1, 5, 20, and 60 minutes. Five consecutive failures pause the endpoint.

## Signature verification

Validate the `X-Adsparkx-Signature` HMAC-SHA256 signature against the raw request body. Do not parse or reserialize JSON before validation. Use the delivery log's event ID and request ID when contacting support.

