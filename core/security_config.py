import os
import secrets

# Production deployments should provide CASPER_JWT_SECRET. A process-local
# development key avoids committing a reusable credential to source control.
JWT_SECRET = os.getenv("CASPER_JWT_SECRET") or secrets.token_urlsafe(32)
