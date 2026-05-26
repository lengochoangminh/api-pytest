import os
from dotenv import load_dotenv


def load_env(env_name: str):
    env_file = f".env/.env.{env_name}"

    if os.path.isfile(env_file):
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv(dotenv_path=f".env/.env.beta_use1")


# ====== URL ======
def API_BASE_URL():
    return os.getenv("API_BASE_URL")


# ====== US Region Accounts | Account Status = Not Merge ======
def UID_PWD():
    return os.getenv("UID_PWD")


def UID_ACCOUNT_ID():
    return os.getenv("UID_ACCOUNT_ID")


def UID_USER_NAME():
    return os.getenv("UID_USER_NAME")

# ====== Company ======
def CERT_COMPANY_ID():
    return os.getenv("CERT_COMPANY_ID")


def CERT_COMPANY_NAME():
    return os.getenv("CERT_COMPANY_NAME")


def ORG_OWNER_EMAIL():
    return os.getenv("ORG_OWNER_EMAIL")


def ORG_OWNER_ACCOUNT_ID():
    return os.getenv("ORG_OWNER_ACCOUNT_ID")


def NON_CERT_COMPANY_ID():
    return os.getenv("NON_CERT_COMPANY_ID")


def NON_CERT_COMPANY_NAME():
    return os.getenv("NON_CERT_COMPANY_NAME")


def ORG_MEMBER_EMAIL():
    return os.getenv("ORG_MEMBER_EMAIL")


def ORG_MEMBER_ACCOUNT_ID():
    return os.getenv("ORG_MEMBER_ACCOUNT_ID")


def ORG_MEMBER_EMAIL_2():
    return os.getenv("ORG_MEMBER_EMAIL_2")


def ORG_MEMBER_ACCOUNT_ID_2():
    return os.getenv("ORG_MEMBER_ACCOUNT_ID_2")

def ORG_ADMIN_EMAIL():
    return os.getenv("ORG_ADMIN_EMAIL")


def ORG_ADMIN_EMAIL_2():
    return os.getenv("ORG_ADMIN_EMAIL_2")