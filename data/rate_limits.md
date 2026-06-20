# API rate limits

API limits are 600 requests per minute per workspace and 60 requests per minute per token. Responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`. A 429 response includes `Retry-After` in seconds.

Use exponential backoff with jitter and avoid immediate retries of batch jobs. Requesting a higher workspace limit requires a human capacity review and traffic profile.

