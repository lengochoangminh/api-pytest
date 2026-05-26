from random import choice, randint
from string import ascii_letters, digits
from faker import Faker
# from PIL import Image
# from io import BytesIO

import uuid, random, pyotp, secrets


class Helpers:
    emoji_smileys = "😜😂"
    long_string = (
        "Lorem Ipsum is simply dummy text of the printing and typesettings industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. "
        "\nIt has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum"
    )

    def __init__(self):
        self.fake = Faker()

    def random_number(self, digits: int):
        if digits < 1:
            raise ValueError("Number of digits must be at least 1")
        start = 10 ** (digits - 1)
        end = 10**digits - 1
        return random.randint(start, end)

    def generate_session_code():
        return secrets.token_hex(16).upper()  # 16 bytes = 32 hex characters

    def generate_UUID():
        return str(uuid.uuid4())

    def get_totp_code(self, secrect: str):
        totp = pyotp.TOTP(secrect)
        return totp.now()
