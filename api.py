import os
import json
import requests
from datetime import datetime, timedelta, timezone

BASE_URL = 'https://lotodobicho.com'


def get_timestamp(stamp_day):
    new_day = datetime.now(timezone.utc) - timedelta(days=int(stamp_day))
    now_floored = datetime.combine(new_day.date(), new_day.time().min).replace(tzinfo=timezone.utc)
    return now_floored.timestamp() * 1000


class Browser(object):

    def __init__(self):
        self.response = None
        self.headers = self.get_headers()
        self.session = requests.Session()

    def get_headers(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/87.0.4280.88 Safari/537.36"
        }
        return self.headers

    def send_request(self, method, url, **kwargs):
        self.response = self.session.request(method, url, **kwargs)
        return self.response


class LotoDoBichoAPI(Browser):

    def __init__(self, email):
        super().__init__()
        self.email = email
        self.token = None
        self.days_to_stamp = 5

    def auth(self):
        self.headers["referer"] = f"{BASE_URL}/sign/in"
        self.send_request('GET',
                          f"{BASE_URL}/auth/generateCode/{self.email}",
                          headers=self.headers)
        if self.response.status_code == 200:
            return json.loads(self.response.text)
        return self.response

    def authorize(self):
        code = input("ACESSE SEU EMAIL, VERIFIQUE A EXISTÊNCIA DE UM CÓDIGO E O INSIRA AQUI: ")
        if not code:
            print("CÓDIGO INVÁLIDO, SAINDO...")
            return
        data = {
            "value": self.email,
            "code": code,
            "app": "app",
            "deviceId": "2750bc42-702e-4cbe-bae5-798f171389e1"
        }
        self.headers["referer"] = f"{BASE_URL}/sign/code"
        self.send_request('POST',
                          f"{BASE_URL}/auth/onetimeCode",
                          data=data,
                          headers=self.headers)
        if self.response.status_code == 201:
            result_data = json.loads(self.response.text)
            if result_data.get("result"):
                self.token = result_data["data"]["access_token"]
                self.save_token()
            return result_data
        return self.response

    def save_token(self):
        with open("lotodobicho_token.json", "w") as file:
            file.write(json.dumps({"token": self.token}))

    def check_token(self):
        if not os.path.exists("lotodobicho_token.json"):
            self.auth()
            return self.authorize()
        with open("lotodobicho_token.json", "r") as file:
            token = json.loads(file.read())
            self.token = token["token"]
            if self.get_profile().get("result"):
                print("Token is valid!!!")
                return True
            print("Token not is valid!!!")
        return False

    def refresh_token(self):
        self.headers["Authorization"] = f"Bearer {self.token}"
        self.headers["referer"] = f"{BASE_URL}/app/bets/betting/add"
        self.send_request('GET',
                          f"{BASE_URL}/auth/refresh",
                          headers=self.headers)
        if self.response.status_code == 200:
            result_data = json.loads(self.response.text)
            if result_data.get("result"):
                self.token = result_data["data"]["access_token"]
            return result_data
        return self.response

    def get_profile(self):
        self.headers["Authorization"] = f"Bearer {self.token}"
        self.headers["referer"] = f"{BASE_URL}/app/bets/betting/add"
        self.send_request('GET',
                          f"{BASE_URL}/api/FUP",
                          headers=self.headers)

        if self.response.status_code == 200:
            return json.loads(self.response.text)
        return self.response

    def get_raffles(self):
        data = {
            "schedule": 3,
            "timestamps": [int(get_timestamp(stamp_day))
                           for stamp_day in range(0, self.days_to_stamp + 1)]
        }
        self.headers["Authorization"] = f"Bearer {self.token}"
        self.headers["referer"] = f"{BASE_URL}/app/draws/historical"
        self.send_request('POST',
                          f"{BASE_URL}/api/FDAD",
                          data=data,
                          headers=self.headers)
        if self.response.status_code == 201:
            return json.loads(self.response.text)
        return self.response


if __name__ == '__main__':
    ldba = LotoDoBichoAPI("email@gmail.com")
    # ldba.days_to_stamp = 1
    if not ldba.check_token():
        ldba.refresh_token()
    print(json.dumps(ldba.get_raffles(), indent=4))
