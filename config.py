#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
from dotenv import load_dotenv
from secret_manager import secret_manager

load_dotenv()


class DefaultConfig:
    """ Bot Configuration """

    API_BASE_URL = os.environ.get(
        "API_BASE_URL")
    PORT = 3969
    PROJECT_ID = 'ziutek'
    APP_ID = secret_manager(PROJECT_ID, 'ziutek-ms-app-id')
    APP_PASSWORD = secret_manager(PROJECT_ID, 'ziutek-ms-password')
    CLIENT_ID = secret_manager(PROJECT_ID, 'ziutek-client-id')
    TENANT_ID = secret_manager(PROJECT_ID, 'ziutek-tenant-id')
    API_BASE_URL = secret_manager(PROJECT_ID, 'ziutek-api-base-url')
    API_USERNAME = secret_manager(PROJECT_ID, 'ziutek-api-username')
    API_PASSWORD = secret_manager(PROJECT_ID, 'ziutek-api-password')
    CARD_SCHEMA = secret_manager(PROJECT_ID, "ziutek-card-schema")
    CARD_VERSION = secret_manager(PROJECT_ID, "ziutek-card-version")

    # APP_ID = os.environ.get(
    #     "MicrosoftAppId")
    # APP_PASSWORD = os.environ.get(
    #     "MicrosoftAppPassword")
    # CLIENT_ID = os.environ.get(
    #     "CLIENT_ID")
    # CLIENT_SECRET = os.environ.get(
    #     "CLIENT_SECRET")
    # TENANT_ID = os.environ.get(
    #     "TENANT_ID")
    # API_USERNAME = os.environ.get(
    #     "API_USERNAME")
    # API_PASSWORD = os.environ.get(
    #     "API_PASSWORD")
    # CARD_SCHEMA = os.environ.get(
    #     "CARD_SCHEMA")
    # CARD_VERSION = os.environ.get(
    #     "CARD_VERSION")
