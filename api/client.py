import aiohttp
import time
import asyncio
from datetime import datetime
from utils.helpers import update_statistics, add_to_history
import pyperclip
from CTkMessagebox import CTkMessagebox

class APIClient:
    def __init__(self, app):
        self.app = app

    async def buy_number(self, session, api_url, api_key, service_id, country_id, service_name):
        params = {"api_key": api_key, "action": "getNumber", "service": service_id, "country": country_id}
        try:
            prev_balance = await self.check_balance(session, api_url, api_key, service_name, silent=True)
            async with session.get(api_url, params=params) as response:
                text = await response.text()
                if "ACCESS_NUMBER" in text:
                    _, id, number = text.split(":")
                    sk = service_name.lower().split()[0]
                    update_statistics("purchase", sk)
                    self.app.purchase_time[number] = datetime.now().timestamp()
                    if prev_balance:
                        curr_balance = await self.check_balance(session, api_url, api_key, service_name, silent=True)
                        if curr_balance and prev_balance:
                            try:
                                spent = float(prev_balance) - float(curr_balance)
                                if spent > 0:
                                    update_statistics("spent", sk, spent)
                            except ValueError:
                                pass
                    self.app.add_log(f"Попытка купить номер с {service_name}, результат: Успех (номер {number})", "SUCCESS")
                    self.app.update_status(f"Номер куплен: {number} (ID: {id})")
                    if self.app.config["sound_notifications"]["enabled"]:
                        self.app.play_sound("success")
                    if self.app.config["auto_copy"]["phone"]:
                        pyperclip.copy(number[2:] if len(number) > 2 else number)
                    self.app.after(0, lambda: self.app.add_phone_entry(number, None, service_name, id))
                    add_to_history({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": "purchase", "service": service_name, "phone": number, "id": id})
                    return id, number
                else:
                    error = self.parse_api_error(text)
                    if "NO_BALANCE" in text:
                        self.app.show_low_balance_warning(service_name)
                    self.app.add_log(f"Попытка купить номер с {service_name}, результат: {error}", "ERROR")
                    self.app.update_status(f"Ошибка при покупке через {service_name}: {error}")
                    return None, None
        except Exception as e:
            self.app.add_log(f"Попытка купить номер с {service_name}, результат: Ошибка подключения", "ERROR")
            self.app.update_status(f"Ошибка подключения к {service_name}: {str(e)}")
            return None, None

    async def check_sms(self, session, api_url, api_key, id, number, service_name):
        params = {"api_key": api_key, "action": "getStatus", "id": id}
        try:
            async with session.get(api_url, params=params) as response:
                text = await response.text()
                if "STATUS_OK" in text:
                    _, code = text.split(":")
                    sk = service_name.lower().split()[0]
                    update_statistics("code", sk)
                    if number in self.app.purchase_time:
                        wait_time = datetime.now().timestamp() - self.app.purchase_time.pop(number)
                        update_statistics("waiting_time", sk, wait_time)
                        self.app.add_log(f"Время ожидания SMS: {wait_time:.1f} секунд", "INFO")
                    self.app.add_log(f"SMS получено: {code}", "SUCCESS")
                    self.app.update_status(f"SMS получено: {code}")
                    if self.app.config["sound_notifications"]["enabled"]:
                        self.app.play_sound("notification")
                    if self.app.config["auto_copy"]["code"]:
                        pyperclip.copy(code)
                        self.app.add_log("Код автоматически скопирован в буфер обмена", "INFO")
                    self.app.after(0, lambda: self.app.update_phone_entry(number, code))
                    add_to_history({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": "sms_received", "service": service_name, "phone": number, "code": code})
                    return code
                elif "STATUS_WAIT_CODE" in text:
                    return None
                else:
                    error = self.parse_api_error(text)
                    self.app.add_log(f"Статус: {error}", "WARNING")
                    self.app.update_status(f"Статус: {error}")
                    return None
        except Exception as e:
            self.app.add_log(f"Ошибка проверки SMS: {str(e)}", "ERROR")
            self.app.update_status(f"Ошибка проверки SMS: {str(e)}")
            return None

    async def check_balance(self, session, api_url, api_key, service_name, silent=False):
        params = {"api_key": api_key, "action": "getBalance"}
        try:
            if not silent:
                self.app.add_log(f"Проверка баланса {service_name}...", "INFO")
                self.app.update_status(f"Проверка баланса {service_name}...")
            async with session.get(api_url, params=params) as response:
                text = await response.text()
                if "ACCESS_BALANCE" in text:
                    _, balance = text.split(":")
                    if service_name:
                        sk = service_name.lower().split()[0]
                        update_statistics("balance", sk, float(balance))
                        if not silent and float(balance) <= self.app.config.get("low_balance_warning", 10.0):
                            self.app.show_low_balance_warning(service_name)
                    if not silent:
                        self.app.add_log(f"Баланс {service_name}: {balance}", "SUCCESS")
                        self.app.update_status(f"Баланс {service_name}: {balance}")
                    return balance
                else:
                    error = self.parse_api_error(text)
                    if not silent:
                        self.app.add_log(f"Ошибка при проверке баланса {service_name}: {error}", "ERROR")
                        self.app.update_status(f"Ошибка при проверке баланса {service_name}: {error}")
                    return None
        except Exception as e:
            if not silent:
                self.app.add_log(f"Ошибка подключения к {service_name}: {str(e)}", "ERROR")
                self.app.update_status(f"Ошибка подключения к {service_name}: {str(e)}")
            return None

    async def cancel_activation(self, session, api_url, api_key, id, number, service_name):
        params = {"api_key": api_key, "action": "setStatus", "status": "8", "id": id}
        try:
            self.app.add_log(f"Отмена активации для ID: {id}", "WARNING")
            self.app.update_status(f"Отмена активации для ID: {id}")
            async with session.get(api_url, params=params) as response:
                text = await response.text()
                if "ACCESS_CANCEL" in text:
                    self.app.add_log(f"Активация отменена для ID: {id}", "INFO")
                    self.app.update_status(f"Активация отменена для ID: {id}")
                    if number in self.app.phone_widgets:
                        self.app.after(0, lambda: self.app.phone_widgets[number].destroy() or self.app.phone_widgets.pop(number))
                    return True
                else:
                    self.app.add_log(f"Ошибка при отмене активации: {text}", "ERROR")
                    self.app.update_status(f"Ошибка при отмене активации: {text}")
                    return False
        except Exception as e:
            self.app.add_log(f"Ошибка подключения при отмене: {str(e)}", "ERROR")
            self.app.update_status(f"Ошибка подключения при отмене: {str(e)}")
            return False

    def parse_api_error(self, text):
        errors = {
            "NO_BALANCE": "Недостаточно средств на балансе",
            "NO_NUMBERS": "Нет доступных номеров",
            "BAD_KEY": "Неверный API ключ",
            "ERROR_SQL": "Ошибка сервера",
            "BAD_ACTION": "Неверное действие",
            "BAD_SERVICE": "Неверный сервис",
            "BAD_COUNTRY": "Неверная страна"
        }
        for key, value in errors.items():
            if key in text:
                return value
        return text

    async def run_bot(self, api_url, api_key, service_name):
        async with aiohttp.ClientSession() as session:
            while self.app.running:
                id, number = await self.buy_number(session, api_url, api_key, self.app.config["service_id"], self.app.config["country_id"], service_name)
                if id and number:
                    self.app.update_status(f"Ожидание SMS... (Через {self.app.config['sms_wait_timeout']} секунд покупка отменится)")
                    self.app.add_log(f"Ожидание SMS для номера {number}...", "INFO")
                    start_time = time.time()
                    self.app.active_ids[service_name] = id
                    if number in self.app.phone_widgets:
                        self.app.phone_widgets[number].id = id
                    while self.app.running and time.time() - start_time < self.app.config['sms_wait_timeout']:
                        code = await self.check_sms(session, api_url, api_key, id, number, service_name)
                        if code:
                            self.app.update_status(f"Код получен: {code}")
                            self.app.add_log(f"Код получен: {code} для номера {number}", "SUCCESS")
                            break
                        if time.time() - start_time >= self.app.config['sms_wait_timeout']:
                            self.app.update_status(f"Таймаут ожидания SMS. Отмена активации...")
                            self.app.add_log(f"Таймаут ожидания SMS для номера {number}. Отмена активации...", "WARNING")
                            await self.cancel_activation(session, api_url, api_key, id, number, service_name)
                            break
                    if not self.app.running:
                        self.app.add_log(f"Остановка службы во время ожидания SMS", "WARNING")
                        await self.cancel_activation(session, api_url, api_key, id, number, service_name)
                else:
                    self.app.update_status(f"Не удалось купить номер с {service_name}, повторная попытка...")

    async def buy_from_all_services(self):
        async with aiohttp.ClientSession() as session:
            while self.app.running:
                self.app.add_log("Попытка купить номер со всех сервисов", "INFO")
                tasks = []
                api_services = []
                for s, n in [("tiger", "Tiger SMS"), ("reg", "Reg-SMS"), ("smslive", "SMSLive")]:
                    if self.app.api_keys[s]:
                        tasks.append(self.buy_number(session, self.app.config["api_urls"][s], self.app.api_keys[s], self.app.config["service_id"], self.app.config["country_id"], n))
                        api_services.append((self.app.config["api_urls"][s], self.app.api_keys[s], n))
                if not tasks:
                    self.app.add_log("Нет доступных API ключей. Пожалуйста, добавьте ключи и повторите попытку.", "ERROR")
                    self.app.update_status("Нет доступных API ключей. Пожалуйста, добавьте ключи и повторите попытку.")
                    return
                running_tasks = [asyncio.create_task(t) for t in tasks]
                success_purchases = []
                while running_tasks and not success_purchases:
                    done, running_tasks = await asyncio.wait(running_tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        try:
                            id, number = task.result()
                            if id and number:
                                idx = len(success_purchases)
                                if idx < len(api_services):
                                    success_purchases.append(api_services[idx] + (id, number))
                        except:
                            pass
                for task in running_tasks:
                    task.cancel()
                if success_purchases:
                    api_url, api_key, service_name, id, number = success_purchases[0]
                    self.app.update_status(f"Используем номер с {service_name}: {number}")
                    self.app.add_log(f"Ожидание SMS для номера {number}...", "INFO")
                    self.app.active_ids[service_name] = id
                    if number in self.app.phone_widgets:
                        self.app.phone_widgets[number].id = id
                    start_time = time.time()
                    while self.app.running and time.time() - start_time < self.app.config['sms_wait_timeout']:
                        code = await self.check_sms(session, api_url, api_key, id, number, service_name)
                        if code:
                            self.app.update_status(f"Код получен: {code}")
                            self.app.add_log(f"Код получен: {code} для номера {number}", "SUCCESS")
                            break
                        if time.time() - start_time >= self.app.config['sms_wait_timeout']:
                            self.app.update_status(f"Таймаут ожидания SMS. Отмена активации...")
                            self.app.add_log(f"Таймаут ожидания SMS для номера {number}. Отмена активации...", "WARNING")
                            await self.cancel_activation(session, api_url, api_key, id, number, service_name)
                            break
                    if not self.app.running:
                        self.app.add_log(f"Остановка службы во время ожидания SMS", "WARNING")
                        await self.cancel_activation(session, api_url, api_key, id, number, service_name)
                else:
                    self.app.update_status("Не удалось купить номер ни на одном сервисе, повторная попытка...")
                    self.app.add_log("Попытка купить номер со всех сервисов, результат: Неудача", "WARNING")

    def _cancel_id_thread(self, id, phone, service_name):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        api_url, api_key = self._get_api_info(service_name)
        if api_url and api_key:
            async def _do_cancel():
                async with aiohttp.ClientSession() as session:
                    await self.cancel_activation(session, api_url, api_key, id, phone, service_name)
            loop.run_until_complete(_do_cancel())
        else:
            if phone in self.app.phone_widgets:
                self.app.after(0, lambda: self.app.phone_widgets[phone].destroy() or self.app.phone_widgets.pop(phone))
            self.app.after(0, lambda: self.app.add_log(f"Отмена активации для номера {phone}", "INFO"))

    def _check_balance_thread(self, service):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        api_url, api_key = self._get_api_info(service)
        if api_url and api_key:
            async def _do_check():
                async with aiohttp.ClientSession() as session:
                    balance = await self.check_balance(session, api_url, api_key, service)
                    if balance:
                        self.app.after(0, lambda: CTkMessagebox(title=f"Баланс {service}", message=f"Текущий баланс: {balance}", icon="info", corner_radius=10))
            loop.run_until_complete(_do_check())
        else:
            self.app.after(0, lambda: self.app.add_log(f"Не удалось определить API для {service}", "ERROR"))

    def _get_api_info(self, service_name):
        return {
            "Tiger SMS": (self.app.config["api_urls"]["tiger"], self.app.api_keys["tiger"]),
            "Reg-SMS": (self.app.config["api_urls"]["reg"], self.app.api_keys["reg"]),
            "SMSLive": (self.app.config["api_urls"]["smslive"], self.app.api_keys["smslive"])
        }.get(service_name, (None, None))