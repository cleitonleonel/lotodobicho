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
        self.token = None
        self.filename = None
        self.is_connected = None
        self.email = email
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
        code = input("ACESSE SEU EMAIL, VERIFIQUE A EXISTÊNCIA DE UM CÓDIGO E O INSIRA AQUI: ").upper()
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
                self.is_connected = True
                self.filename = "lotodobicho_token"
                self.save_json()
            return result_data
        return self.response

    def save_json(self, data=None):
        with open(f"{self.filename}.json", "w") as file:
            if not data:
                file.write(json.dumps({"token": self.token}))
            else:
                file.write(json.dumps(data, indent=4))

    def check_token(self):
        self.filename = "lotodobicho_token"
        if not os.path.exists(f"{self.filename}.json"):
            print("Gerando novo token...")
            login = self.auth()
            if login["error"]:
                print(f"Erro, usuário {self.email} é inválido!!!")
                exit()
            return self.authorize()
        with open(f"{self.filename}.json", "r") as file:
            json_data = file.read()
            if json_data == "":
                print("Token não encontrado!!!")
                print("Reconectando...")
                os.remove(f"{self.filename}.json")
                file.close()
                return self.check_token()
            token = json.loads(json_data)
            self.token = token["token"]
            if self.token and self.get_profile().get("result"):
                self.is_connected = True
                print("Token is valid!!!")
            else:
                self.is_connected = False
                print("Token not is valid!!!")
                os.remove(f"{self.filename}.json")
                file.close()
                return self.check_token()

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
                self.is_connected = True
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
        return {"result": False, "message": "Token inválido!!!"}

    def get_raffles(self, raffle_type=0):
        data = {
            "schedule": raffle_type,
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
            ldba.save_json(json.loads(self.response.text))
            return json.loads(self.response.text)
        return self.response


if __name__ == '__main__':
    ldba = LotoDoBichoAPI("email@gmail.com")
    ldba.check_token()
    if not ldba.is_connected:
        ldba.refresh_token()
    else:
        # print(json.dumps(ldba.get_profile(), indent=4))
        # raffle_type = 0 Sul Americano Padrão
        # raffle_type = 1 Europeu
        # raffle_type = 2 Asiático
        # raffle_type = 3 Rio
        ldba.days_to_stamp = 1  # Dias a buscar dados
        ldba.filename = "lotodobicho_results"
        print(json.dumps(ldba.get_raffles(raffle_type=0), indent=4))
