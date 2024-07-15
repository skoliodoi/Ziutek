from google.cloud import secretmanager


def secret_manager(project_id, secret_id, project_version='latest'):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{project_version}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")
