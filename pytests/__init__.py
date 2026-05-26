import pytest, allure, re, time, os, logging

from api.unified_id_api import Unified_ID_API
from config import (    
    UID_USER_NAME,
    UID_PWD,
    UID_ACCOUNT_ID,    
    ORG_OWNER_EMAIL,
    ORG_OWNER_ACCOUNT_ID,
    CERT_COMPANY_ID,
    CERT_COMPANY_NAME,
    NON_CERT_COMPANY_ID,    
    NON_CERT_COMPANY_NAME,
    ORG_ADMIN_EMAIL,
    ORG_ADMIN_EMAIL_2,
    ORG_MEMBER_EMAIL,
    ORG_MEMBER_ACCOUNT_ID,    
)

from utilities.helpers import Helpers
from datetime import datetime
from faker import Faker
from pathlib import Path

from utilities.log_util import Logger
log = Logger(__name__, logging.INFO)