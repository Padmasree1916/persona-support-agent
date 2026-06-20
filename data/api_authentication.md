# API authentication and 401 errors

Adsparkx API requests use `Authorization: Bearer <token>`. Tokens are created in Settings > Developer > API keys. Never send a key in a query string. A 401 response means the token is absent, expired, revoked, or copied with whitespace. A 403 means the token is valid but lacks the required workspace role.

## Diagnostic steps

Confirm the production base URL is `https://api.adsparkx.example/v1`, inspect the `request-id` response header, and compare the key's workspace with the requested resource. Rotate a suspected exposed key immediately. Key changes can take up to 60 seconds to propagate.

