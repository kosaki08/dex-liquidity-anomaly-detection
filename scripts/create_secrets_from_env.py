import sys

from dotenv import dotenv_values
from google.cloud import secretmanager


def to_secret_name(key: str) -> str:
    return key.lower().replace("_", "-")


def main(env_path: str, project_id: str):
    env = dotenv_values(env_path)
    client = secretmanager.SecretManagerServiceClient()

    for key, value in env.items():
        if value is None:
            continue
        secret_id = to_secret_name(key)
        parent = f"projects/{project_id}"
        secret_path = f"{parent}/secrets/{secret_id}"

        try:
            client.get_secret(request={"name": secret_path})
            exist = True
        except Exception:
            exist = False

        if not exist:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            print(f"{secret_id} を作成しました")

        client.add_secret_version(
            request={
                "parent": secret_path,
                "payload": {"data": value.encode()},
            }
        )
        print(f"{secret_id} を更新しました")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("使用方法: python create_secrets_from_env.py path/to/.env PROJECT_ID")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
