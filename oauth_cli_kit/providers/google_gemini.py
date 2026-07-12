from __future__ import annotations

from oauth_cli_kit.models import OAuthProviderConfig

GOOGLE_GEMINI_PROVIDER = OAuthProviderConfig(
    client_id="YOUR_GOOGLE_OAUTH_CLIENT_ID",  # Desktop app type — không cần secret
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    redirect_uri="http://localhost:1455/auth/callback",
    scope="openid email profile https://www.googleapis.com/auth/generative-language",
    account_id_claim="email",
    token_filename="gemini.json",
)
