# Database and warehouse integration

The warehouse connector supports PostgreSQL 14+, MySQL 8+, and Snowflake. Connections require TLS 1.2 or later. Add the documented Adsparkx egress addresses to the database allowlist and use a read-only service account.

For connection failures, test DNS resolution, validate port and certificate chain, then inspect the connector run log. `CONNECTION_TIMEOUT` indicates network reachability; `AUTH_FAILED` indicates credentials or database grants; `SCHEMA_DENIED` indicates missing read permissions.

