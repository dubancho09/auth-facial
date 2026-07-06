from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer


class PluginSecurityService:

    def __init__(self, secret_key, salt="face-auth-plugin"):
        self.serializer = URLSafeTimedSerializer(secret_key=secret_key, salt=salt)

    @staticmethod
    def parse_clients(raw_clients):
        clients = {}

        if not raw_clients:
            return clients

        for item in raw_clients.split(","):
            item = item.strip()
            if not item or ":" not in item:
                continue

            client_id, api_key = item.split(":", 1)
            client_id = client_id.strip()
            api_key = api_key.strip()

            if client_id and api_key:
                clients[client_id] = api_key

        return clients

    def issue_launch_token(self, client_id, origin):
        payload = {
            "client_id": client_id,
            "origin": origin
        }
        return self.serializer.dumps(payload)

    def verify_launch_token(self, token, max_age_seconds):
        try:
            payload = self.serializer.loads(token, max_age=max_age_seconds)
        except (BadSignature, BadTimeSignature) as error:
            raise ValueError("Token de lanzamiento invalido o expirado.") from error

        origin = payload.get("origin")
        client_id = payload.get("client_id")

        if not origin or not client_id:
            raise ValueError("Token de lanzamiento incompleto.")

        return payload
