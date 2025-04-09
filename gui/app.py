import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import pyperclip
import winsound
from datetime import datetime
import threading
import asyncio
import aiohttp
import time
from api.client import APIClient
from utils.helpers import load_config, save_config, load_api_keys, save_api_keys, load_history, save_history, add_to_history, load_statistics, save_statistics, update_statistics
from gui.widgets import ScrollableFrame, PhoneEntry, SettingsWindow, HistoryWindow

class AutoRegerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AutoReger Ozan")
        self.geometry("900x700")
        self.minsize(900, 700)
        self.maxsize(900, 700)
        self.config = load_config()
        self.api_keys = load_api_keys()
        self.statistics = load_statistics()
        self.active_ids = {}
        self.phone_widgets = {}
        self.max_log_lines = 100
        self.last_log_clean = time.time()
        self.purchase_time = {}
        self.create_widgets()
        self.running = False
        self.background_task = None
        self.api_client = APIClient(self)
        self.after(100, lambda: self.add_log("Программа запущена. Готов к работе.", "INFO"))
        self.schedule_log_cleanup()

    def create_widgets(self):
        self.grid_columnconfigure((0, 1), weight=0)
        self.grid_rowconfigure(0, weight=0)
        lpf = ctk.CTkFrame(self, corner_radius=15, width=350, height=670)
        lpf.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        lpf.grid_propagate(False)
        lp = ctk.CTkFrame(lpf, corner_radius=0, fg_color="transparent", width=330, height=650)
        lp.pack(fill="both", expand=True, padx=5, pady=5)
        lp.pack_propagate(False)
        lp.grid_columnconfigure(0, weight=1)
        tf = ctk.CTkFrame(lp, fg_color="transparent")
        tf.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        tf.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tf, text="AUTOBUY OZAN", font=("Segoe UI", 24, "bold"), anchor="center", width=330).grid(row=0, column=0, sticky="ew")
        ctk.CTkFrame(lp, height=2, fg_color="#555555", corner_radius=1).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        af = ctk.CTkFrame(lp, corner_radius=10, fg_color="#1A1A1A", height=300)
        af.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        af.grid_columnconfigure(0, weight=1)
        af.grid_columnconfigure(1, weight=0)
        af.grid_propagate(False)
        ctk.CTkLabel(af, text="API Ключи", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")
        ctk.CTkLabel(af, text="Tiger SMS API:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=15, pady=(5, 0), sticky="w")
        ctk.CTkButton(af, text="Сменить API Ключ", command=lambda: self.change_api_key("tiger")).grid(row=2, column=0, padx=15, pady=(5, 10), sticky="ew")
        ctk.CTkButton(af, text="Баланс", width=90, height=35, corner_radius=8, font=("Segoe UI", 12, "bold"), fg_color="#2A2A2A", hover_color="#3A3A3A", command=lambda: self.check_balance_ui("Tiger SMS")).grid(row=2, column=1, padx=(0, 15), pady=(5, 10), sticky="e")
        ctk.CTkLabel(af, text="Reg-SMS API:", font=("Segoe UI", 12)).grid(row=3, column=0, padx=15, pady=(5, 0), sticky="w")
        ctk.CTkButton(af, text="Сменить API Ключ", command=lambda: self.change_api_key("reg")).grid(row=4, column=0, padx=15, pady=(5, 10), sticky="ew")
        ctk.CTkButton(af, text="Баланс", width=90, height=35, corner_radius=8, font=("Segoe UI", 12, "bold"), fg_color="#2A2A2A", hover_color="#3A3A3A", command=lambda: self.check_balance_ui("Reg-SMS")).grid(row=4, column=1, padx=(0, 15), pady=(5, 10), sticky="e")
        ctk.CTkLabel(af, text="SMSLive API:", font=("Segoe UI", 12)).grid(row=5, column=0, padx=15, pady=(5, 0), sticky="w")
        ctk.CTkButton(af, text="Сменить API Ключ", command=lambda: self.change_api_key("smslive")).grid(row=6, column=0, padx=15, pady=(5, 15), sticky="ew")
        ctk.CTkButton(af, text="Баланс", width=90, height=35, corner_radius=8, font=("Segoe UI", 12, "bold"), fg_color="#2A2A2A", hover_color="#3A3A3A", command=lambda: self.check_balance_ui("SMSLive")).grid(row=6, column=1, padx=(0, 15), pady=(5, 15), sticky="e")
        actf = ctk.CTkFrame(lp, corner_radius=10, fg_color="#1A1A1A", height=180)
        actf.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        actf.grid_columnconfigure(0, weight=1)
        actf.grid_propagate(False)
        ctk.CTkLabel(actf, text="Действия", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")
        self.service_var = ctk.StringVar(value="all")
        ctk.CTkRadioButton(actf, text="Все сервисы", variable=self.service_var, value="all", font=("Segoe UI", 11)).grid(row=1, column=0, padx=15, pady=(5, 2), sticky="w")
        ctk.CTkRadioButton(actf, text="Tiger SMS", variable=self.service_var, value="tiger", font=("Segoe UI", 11)).grid(row=2, column=0, padx=15, pady=2, sticky="w")
        ctk.CTkRadioButton(actf, text="Reg-SMS", variable=self.service_var, value="reg", font=("Segoe UI", 11)).grid(row=3, column=0, padx=15, pady=2, sticky="w")
        ctk.CTkRadioButton(actf, text="SMSLive", variable=self.service_var, value="smslive", font=("Segoe UI", 11)).grid(row=4, column=0, padx=15, pady=(2, 10), sticky="w")
        bf = ctk.CTkFrame(lp, corner_radius=10, fg_color="#1A1A1A", height=110)
        bf.grid(row=5, column=0, padx=20, pady=0, sticky="ew")
        bf.grid_columnconfigure((0, 1), weight=1)
        bf.grid_propagate(False)
        self.start_button = ctk.CTkButton(bf, text="ЗАПУСТИТЬ", font=("Segoe UI", 15, "bold"), corner_radius=8, height=40, fg_color="#3a7ebf", hover_color="#1f538d", command=self.toggle_service)
        self.start_button.grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="ew")
        ctk.CTkButton(bf, text="Настройки", font=("Segoe UI", 13), corner_radius=8, height=30, fg_color="#2A2A2A", hover_color="#3A3A3A", command=self.show_settings_window).grid(row=1, column=0, padx=(15, 5), pady=(0, 15), sticky="ew")
        ctk.CTkButton(bf, text="История", font=("Segoe UI", 13), corner_radius=8, height=30, fg_color="#2A2A2A", hover_color="#3A3A3A", command=self.show_history_window).grid(row=1, column=1, padx=(5, 15), pady=(0, 15), sticky="ew")
        rpf = ctk.CTkFrame(self, corner_radius=15, width=500, height=670)
        rpf.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        rpf.grid_propagate(False)
        rp = ctk.CTkFrame(rpf, corner_radius=0, fg_color="transparent", width=480, height=650)
        rp.pack(fill="both", expand=True, padx=5, pady=5)
        rp.pack_propagate(False)
        hf = ctk.CTkFrame(rp, fg_color="transparent", height=40)
        hf.pack(fill="x", expand=False, padx=10, pady=(10, 0))
        hf.pack_propagate(False)
        ctk.CTkLabel(hf, text="Результаты", font=("Segoe UI", 20, "bold")).pack(side="left", padx=10)
        ctk.CTkFrame(rp, height=2, fg_color="#555555", corner_radius=1).pack(fill="x", expand=False, padx=10, pady=(5, 10))
        ltf = ctk.CTkFrame(rp, fg_color="transparent", height=30)
        ltf.pack(fill="x", expand=False, padx=10, pady=(0, 5))
        ltf.pack_propagate(False)
        ctk.CTkLabel(ltf, text="Логи:", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(ltf, text="Очистить", width=80, height=25, corner_radius=8, font=("Segoe UI", 11), fg_color="#2A2A2A", hover_color="#3A3A3A", command=self.clear_logs).pack(side="right", padx=10)
        lf = ctk.CTkFrame(rp, corner_radius=10, fg_color="#1A1A1A", height=220)
        lf.pack(fill="x", expand=False, padx=10, pady=(0, 10))
        lf.pack_propagate(False)
        self.logs_text = ctk.CTkTextbox(lf, font=("Consolas", 12), height=200, scrollbar_button_color=None, scrollbar_button_hover_color="#555555")
        self.logs_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.logs_text.configure(state="disabled", wrap="word")
        ntf = ctk.CTkFrame(rp, fg_color="transparent", height=30)
        ntf.pack(fill="x", expand=False, padx=10, pady=(5, 5))
        ntf.pack_propagate(False)
        ctk.CTkLabel(ntf, text="Номера:", font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(ntf, text="Очистить", width=80, height=25, corner_radius=8, font=("Segoe UI", 11), fg_color="#2A2A2A", hover_color="#3A3A3A", command=self.clear_numbers).pack(side="right", padx=10)
        nf = ctk.CTkFrame(rp, corner_radius=10, fg_color="#1A1A1A", height=310)
        nf.pack(fill="x", expand=False, padx=10, pady=(0, 10))
        nf.pack_propagate(False)
        self.results_frame = ScrollableFrame(nf, corner_radius=0, fg_color="transparent", width=440, height=290, scrollbar_fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        sf = ctk.CTkFrame(rp, fg_color="transparent", height=30)
        sf.pack(fill="x", expand=False, padx=10, pady=(0, 10))
        sf.pack_propagate(False)
        self.status_label = ctk.CTkLabel(sf, text="Готов к запуску", font=("Segoe UI", 12))
        self.status_label.pack(side="left", padx=10)
        stats = load_statistics()
        total_purchases = sum(stats["purchases"].values())
        total_codes = sum(stats["codes"].values())
        self.stats_label = ctk.CTkLabel(sf, text=f"Номеров: {total_purchases} | Кодов: {total_codes}", font=("Segoe UI", 12), cursor="hand2")
        self.stats_label.pack(side="right", padx=10)
        self.stats_label.bind("<Button-1>", lambda e: self.show_history_window())

    def toggle_service(self):
        if not self.running:
            self.api_keys.update({"tiger": self.api_keys.get("tiger", ""), "reg": self.api_keys.get("reg", ""), "smslive": self.api_keys.get("smslive", "")})
            save_api_keys(self.api_keys)
            self.running = True
            self.start_button.configure(text="ОСТАНОВИТЬ", fg_color="#AA0000", hover_color="#880000")
            service = self.service_var.get()
            self.add_log(f"Запуск сервиса: {service}", "INFO")
            self.status_label.configure(text=f"Запуск сервиса: {service}")
            self.background_task = threading.Thread(target=self.run_background_service, args=(service,))
            self.background_task.daemon = True
            self.background_task.start()
        else:
            self.running = False
            self.start_button.configure(text="ЗАПУСТИТЬ", fg_color="#3a7ebf", hover_color="#1f538d")
            self.add_log("Остановка сервиса...", "WARNING")
            self.status_label.configure(text="Остановка сервиса...")

    def run_background_service(self, service):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            coro = self.api_client.buy_from_all_services() if service == "all" else self.api_client.run_bot(self.config["api_urls"][service], self.api_keys[service], service.capitalize() + (" SMS" if service != "reg" else "-SMS"))
            loop.run_until_complete(coro)
        except Exception as e:
            self.after(0, lambda: self.add_log(f"Ошибка сервиса: {str(e)}", "ERROR"))
        if self.running:
            self.running = False
            self.after(0, lambda: self.start_button.configure(text="ЗАПУСТИТЬ", fg_color="#3a7ebf", hover_color="#1f538d") or self.add_log("Сервис завершил работу", "INFO") or self.status_label.configure(text="Готов к запуску"))

    def add_phone_entry(self, phone, code=None, service=None, id=None):
        pw = PhoneEntry(self.results_frame, phone, code, service, id, self)
        pw.pack(fill="x", padx=10, pady=5, expand=False)
        self.phone_widgets[phone] = pw
        pw.configure(border_color="#4488FF")
        self.after(1000, lambda: pw.configure(border_color="#333333"))
        self.after(0, lambda: self.add_log(f"Добавлен новый номер: {phone} ({service})", "INFO"))
        return pw

    def update_phone_entry(self, phone, code):
        if phone in self.phone_widgets:
            self.phone_widgets[phone].update_code(code)
            self.after(0, lambda: self.add_log(f"Обновлен номер {phone} с кодом: {code}", "INFO"))

    def update_status(self, message):
        self.after(0, lambda: self.status_label.configure(text=message))

    def add_log(self, message, level="INFO"):
        current_time = datetime.now().strftime("%H:%M:%S")
        tag_color = {"INFO": "#FFFFFF", "SUCCESS": "#00FF00", "WARNING": "#FFFF00", "ERROR": "#FF0000"}.get(level, "#FFFFFF")
        log_message = f"[{current_time}] [{level}] {message}\n"
        self.logs_text.configure(state="normal")
        content = self.logs_text.get("1.0", "end-1c")
        lines = content.count('\n')
        if lines >= self.max_log_lines:
            lines_to_keep = self.max_log_lines // 2
            lines_to_remove = len(content.split('\n')) - lines_to_keep
            if lines_to_remove > 0:
                position = "1.0"
                for _ in range(lines_to_remove):
                    end_of_line = self.logs_text.search('\n', position, stopindex="end")
                    if not end_of_line:
                        break
                    position = f"{end_of_line}+1c"
                self.logs_text.delete("1.0", position)
                self.logs_text.insert("1.0", "[---] [SYSTEM] Автоочистка логов - старые записи удалены [---]\n")
        self.logs_text.insert("end", log_message)
        self.logs_text.see("end")
        self.logs_text.configure(state="disabled")
        self.update_status(message)

    def schedule_log_cleanup(self):
        current_time = time.time()
        if current_time - self.last_log_clean >= 30:
            self.logs_text.configure(state="normal")
            content = self.logs_text.get("1.0", "end-1c")
            lines = content.count('\n')
            if lines > self.max_log_lines // 2:
                lines_to_keep = self.max_log_lines // 2
                lines_to_remove = lines - lines_to_keep
                if lines_to_remove > 0:
                    position = "1.0"
                    for _ in range(lines_to_remove):
                        end_of_line = self.logs_text.search('\n', position, stopindex="end")
                        if not end_of_line:
                            break
                        position = f"{end_of_line}+1c"
                    self.logs_text.delete("1.0", position)
            self.logs_text.configure(state="disabled")
            self.last_log_clean = current_time
        self.after(1000, self.schedule_log_cleanup)

    def cancel_id(self, id, phone, service_name):
        self.add_log(f"Отмена активации номера {phone} (ID: {id}) по запросу пользователя", "WARNING")
        self.update_status(f"Отмена активации номера {phone}...")
        threading.Thread(target=self.api_client._cancel_id_thread, args=(id, phone, service_name), daemon=True).start()

    def check_balance_ui(self, service):
        self.add_log(f"Запрос на проверку баланса {service}...", "INFO")
        threading.Thread(target=self.api_client._check_balance_thread, args=(service,), daemon=True).start()

    def play_sound(self, sound_type):
        try:
            sounds = {"success": (1000, 500), "notification": (1500, 300)}
            if sound_type in sounds:
                freq, duration = sounds[sound_type]
                winsound.Beep(freq, duration)
        except Exception as e:
            self.add_log(f"Ошибка воспроизведения звука: {str(e)}", "ERROR")

    def clear_logs(self):
        self.logs_text.configure(state="normal")
        self.logs_text.delete("1.0", "end")
        self.logs_text.configure(state="disabled")
        self.add_log("Логи очищены", "INFO")

    def clear_numbers(self):
        for widget in self.phone_widgets.values():
            widget.destroy()
        self.phone_widgets.clear()
        self.add_log("Список номеров очищен", "INFO")

    def show_settings_window(self):
        SettingsWindow(self)

    def show_history_window(self):
        HistoryWindow(self)

    def change_api_key(self, service):
        dialog = ctk.CTkInputDialog(text=f"Введите новый API ключ для {service.capitalize()}:", title=f"Сменить API Ключ {service.capitalize()}")
        new_key = dialog.get_input()
        if new_key:
            self.api_keys[service] = new_key
            save_api_keys(self.api_keys)
            self.add_log(f"API ключ для {service.capitalize()} обновлён", "SUCCESS")

if __name__ == "__main__":
    app = AutoRegerApp()
    app.mainloop()