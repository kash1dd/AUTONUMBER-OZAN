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

class ScrollableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        self._height = kwargs.pop("height", None)
        kwargs.update({"scrollbar_button_color": None, "scrollbar_button_hover_color": "#555555"})
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

class PhoneEntry(ctk.CTkFrame):
    def __init__(self, master, phone, code=None, service=None, id=None, app=None):
        bg_color = "#1A2A1A" if code else "#1A1A1A"
        super().__init__(master, corner_radius=15, fg_color=bg_color, border_width=2, border_color="#00AA00" if code else "#333333")
        self.phone, self.code, self.service, self.id, self.app = phone, code, service, id, app
        self.timeout_seconds = app.config["sms_wait_timeout"] if app else 90
        self.start_time = time.time()
        self.timer_running = not code
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        if service:
            sf = ctk.CTkFrame(self, fg_color="#252525", corner_radius=10)
            sf.grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="nw")
            ctk.CTkLabel(sf, text="💬", font=("Segoe UI", 14)).pack(side="left", padx=(8, 4), pady=6)
            ctk.CTkLabel(sf, text=service, font=("Segoe UI", 13, "bold"), text_color="#AAAAAA").pack(side="left", padx=(0, 8), pady=6)
        pf = ctk.CTkFrame(self, fg_color="#252525", corner_radius=10)
        pf.grid(row=1, column=0, padx=12, pady=(6, 12), sticky="ew")
        ctk.CTkLabel(pf, text="📱", font=("Segoe UI", 18)).pack(side="left", padx=(10, 5), pady=10)
        pif = ctk.CTkFrame(pf, fg_color="transparent")
        pif.pack(side="left", fill="x", expand=True, padx=0, pady=10)
        ctk.CTkLabel(pif, text="Номер:", font=("Segoe UI", 12), text_color="#888888").pack(side="top", anchor="w", padx=5, pady=(0, 3))
        pv = ctk.CTkLabel(pif, text=phone, font=("Segoe UI", 16, "bold"), cursor="hand2")
        pv.pack(side="top", anchor="w", padx=5)
        pv.bind("<Button-1>", lambda e: self.copy_to_clipboard(phone[2:] if len(phone) > 2 else phone, "Номер скопирован (без префикса)"))
        sf = ctk.CTkFrame(pf, fg_color="#00BB00" if code else "#FFAA00", corner_radius=8)
        sf.pack(side="right", padx=10, pady=10)
        ctk.CTkLabel(sf, text="Получен" if code else "Ожидание", font=("Segoe UI", 12, "bold"), text_color="#FFFFFF").pack(padx=8, pady=(3, 0 if code else 0))
        if not code:
            self.timer_label = ctk.CTkLabel(sf, text=f"{self.timeout_seconds}с", font=("Segoe UI", 10, "bold"), text_color="#FFFFFF")
            self.timer_label.pack(padx=8, pady=(0, 3))
            self.update_timer()
        if code:
            cf = ctk.CTkFrame(self, fg_color="#252525", corner_radius=10)
            cf.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
            ctk.CTkLabel(cf, text="🔑", font=("Segoe UI", 18)).pack(side="left", padx=(10, 5), pady=10)
            cif = ctk.CTkFrame(cf, fg_color="transparent")
            cif.pack(side="left", fill="x", expand=True, padx=0, pady=10)
            ctk.CTkLabel(cif, text="Код:", font=("Segoe UI", 12), text_color="#888888").pack(side="top", anchor="w", padx=5, pady=(0, 3))
            cv = ctk.CTkLabel(cif, text=code, font=("Segoe UI", 18, "bold"), cursor="hand2")
            cv.pack(side="top", anchor="w", padx=5)
            cv.bind("<Button-1>", lambda e: self.copy_to_clipboard(code, "Код скопирован"))
            copy_code_btn = ctk.CTkButton(cf, text="Копировать код", width=110, height=30, corner_radius=8, 
                                  font=("Segoe UI", 12, "bold"), fg_color="#3a7ebf", hover_color="#1f538d",
                                  command=lambda: self.copy_to_clipboard(code, "Код скопирован"))
            copy_code_btn.pack(side="right", padx=10, pady=10)
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.grid(row=1, column=1, rowspan=2 if code else 1, padx=(0, 12), pady=12, sticky="e")
        ctk.CTkButton(bf, text="Копировать", width=110, height=36, corner_radius=10, font=("Segoe UI", 13, "bold"), fg_color="#3a7ebf", hover_color="#1f538d",
                      command=lambda: self.copy_to_clipboard(phone[2:] if len(phone) > 2 else phone if not code else f"Номер: {phone[2:] if len(phone) > 2 else phone}\nКод: {code}", "Данные скопированы")).pack(side="top", pady=(0, 5))
        if not code and id and app:
            ctk.CTkButton(bf, text="Отмена", width=110, height=36, corner_radius=10, font=("Segoe UI", 13, "bold"), fg_color="#AA3333", hover_color="#CC4444",
                          command=self.cancel_activation).pack(side="top", pady=(5, 0))

    def update_timer(self):
        if not self.timer_running:
            return
        elapsed = time.time() - self.start_time
        remaining = max(0, int(self.timeout_seconds - elapsed))
        try:
            self.timer_label.configure(text=f"{remaining}с")
            if remaining <= 10:
                self.timer_label.configure(text_color="#FFCCCC")
            if remaining > 0:
                self.after(100, self.update_timer)
            else:
                self.timer_running = False
        except:
            self.timer_running = False

    def copy_to_clipboard(self, text, message):
        pyperclip.copy(text)
        CTkMessagebox(title="Успешно", message=message, icon="check", corner_radius=10)

    def update_code(self, code):
        self.code = code
        self.timer_running = False
        self.configure(fg_color="#1A2A1A", border_color="#00AA00")
        self.timer_label.master.configure(fg_color="#00BB00")
        self.timer_label.configure(text="Получен")
        cf = ctk.CTkFrame(self, fg_color="#252525", corner_radius=10)
        cf.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
        ctk.CTkLabel(cf, text="🔑", font=("Segoe UI", 18)).pack(side="left", padx=(10, 5), pady=10)
        cif = ctk.CTkFrame(cf, fg_color="transparent")
        cif.pack(side="left", fill="x", expand=True, padx=0, pady=10)
        ctk.CTkLabel(cif, text="Код:", font=("Segoe UI", 12), text_color="#888888").pack(side="top", anchor="w", padx=5, pady=(0, 3))
        cv = ctk.CTkLabel(cif, text=code, font=("Segoe UI", 18, "bold"), cursor="hand2")
        cv.pack(side="top", anchor="w", padx=5)
        cv.bind("<Button-1>", lambda e: self.copy_to_clipboard(code, "Код скопирован"))
        copy_code_btn = ctk.CTkButton(cf, text="Копировать код", width=110, height=30, corner_radius=8, 
                              font=("Segoe UI", 12, "bold"), fg_color="#3a7ebf", hover_color="#1f538d",
                              command=lambda: self.copy_to_clipboard(code, "Код скопирован"))
        copy_code_btn.pack(side="right", padx=10, pady=10)
        self.app.after(1000, lambda: self.configure(border_color="#00AA00"))

    def cancel_activation(self):
        if self.app and self.id and self.service:
            self.timer_running = False
            self.app.cancel_id(self.id, self.phone, self.service)

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Настройки")
        self.geometry("600x500")
        self.resizable(False, False)
        self.grab_set()
        tv = ctk.CTkTabview(self)
        tv.pack(fill="both", expand=True, padx=10, pady=10)
        gt = tv.add("Общие")
        gt.grid_columnconfigure((0, 1), weight=1)
        timeout_var = ctk.IntVar(value=master.config["sms_wait_timeout"])
        ctk.CTkLabel(gt, text="Таймаут ожидания SMS (сек):", font=("Segoe UI", 12)).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        ctk.CTkEntry(gt, textvariable=timeout_var, width=100).grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        service_id_var = ctk.StringVar(value=master.config["service_id"])
        ctk.CTkLabel(gt, text="ID сервиса:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkEntry(gt, textvariable=service_id_var, width=100).grid(row=1, column=1, padx=20, pady=5, sticky="w")
        country_id_var = ctk.StringVar(value=master.config["country_id"])
        ctk.CTkLabel(gt, text="ID страны:", font=("Segoe UI", 12)).grid(row=2, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkEntry(gt, textvariable=country_id_var, width=100).grid(row=2, column=1, padx=20, pady=5, sticky="w")
        low_balance_var = ctk.DoubleVar(value=master.config.get("low_balance_warning", 10.0))
        ctk.CTkLabel(gt, text="Порог низкого баланса (руб):", font=("Segoe UI", 12)).grid(row=3, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkEntry(gt, textvariable=low_balance_var, width=100).grid(row=3, column=1, padx=20, pady=5, sticky="w")
        ct = tv.add("Копирование")
        ct.grid_columnconfigure(0, weight=1)
        phone_copy_var = ctk.BooleanVar(value=master.config["auto_copy"]["phone"])
        ctk.CTkCheckBox(ct, text="Автоматически копировать номер телефона", variable=phone_copy_var, font=("Segoe UI", 12)).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        code_copy_var = ctk.BooleanVar(value=master.config["auto_copy"]["code"])
        ctk.CTkCheckBox(ct, text="Автоматически копировать код из SMS", variable=code_copy_var, font=("Segoe UI", 12)).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        st = tv.add("Звук")
        st.grid_columnconfigure((0, 1), weight=1)
        sound_enabled_var = ctk.BooleanVar(value=master.config["sound_notifications"]["enabled"])
        ctk.CTkCheckBox(st, text="Включить звуковые уведомления", variable=sound_enabled_var, font=("Segoe UI", 12)).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        volume_var = ctk.IntVar(value=master.config["sound_notifications"]["volume"])
        ctk.CTkLabel(st, text="Громкость:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkSlider(st, from_=0, to=100, variable=volume_var).grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(st, textvariable=volume_var, font=("Segoe UI", 12)).grid(row=1, column=2, padx=(0, 20), pady=10, sticky="w")
        ctk.CTkButton(st, text="Тест звука", width=120, height=30, font=("Segoe UI", 12), corner_radius=8, command=lambda: master.play_sound("notification")).grid(row=2, column=0, columnspan=2, padx=20, pady=20)
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(bf, text="Сохранить", width=150, height=40, font=("Segoe UI", 14, "bold"), corner_radius=8, fg_color="#3a7ebf", hover_color="#1f538d",
                      command=lambda: self._save_settings(timeout_var.get(), service_id_var.get(), country_id_var.get(), phone_copy_var.get(), code_copy_var.get(), sound_enabled_var.get(), volume_var.get(), low_balance_var.get(), master)).pack(side="right", padx=10, pady=10)
        ctk.CTkButton(bf, text="Отмена", width=150, height=40, font=("Segoe UI", 14, "bold"), corner_radius=8, fg_color="#555555", hover_color="#777777", command=self.destroy).pack(side="right", padx=10, pady=10)

    def _save_settings(self, timeout, service_id, country_id, phone_copy, code_copy, sound_enabled, volume, low_balance, master):
        master.config.update({"sms_wait_timeout": timeout, "service_id": service_id, "country_id": country_id, "auto_copy": {"phone": phone_copy, "code": code_copy}, "sound_notifications": {"enabled": sound_enabled, "volume": volume}, "low_balance_warning": low_balance})
        save_config(master.config)
        master.add_log("Настройки успешно сохранены", "SUCCESS")
        self.destroy()

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("История операций")
        self.geometry("800x600")
        self.minsize(800, 600)
        self.grab_set()
        history = sorted(load_history(), key=lambda x: x.get("timestamp", ""), reverse=True)
        tv = ctk.CTkTabview(self)
        tv.pack(fill="both", expand=True, padx=10, pady=10)
        ht = tv.add("История")
        hf = ScrollableFrame(ht, width=760, height=480)
        hf.pack(fill="both", expand=True, padx=10, pady=10)
        hdf = ctk.CTkFrame(hf, fg_color="transparent")
        hdf.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        for i, (header, width) in enumerate(zip(["Время", "Действие", "Сервис", "Номер", "Код/ID"], [150, 100, 120, 150, 150])): 
            ctk.CTkLabel(hdf, text=header, font=("Segoe UI", 12, "bold"), width=width).grid(row=0, column=i, padx=5, pady=5)
        ctk.CTkFrame(hf, height=2, fg_color="#555555").grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        if history:
            for i, entry in enumerate(history):
                rf = ctk.CTkFrame(hf, fg_color="#292929" if i % 2 else "transparent")
                rf.grid(row=i+2, column=0, sticky="ew", padx=10, pady=2)
                ctk.CTkLabel(rf, text=entry.get("timestamp", ""), font=("Segoe UI", 11), width=150).grid(row=0, column=0, padx=5, pady=5)
                action = {"purchase": "Покупка", "sms_received": "Получен код"}.get(entry.get("action", ""), entry.get("action", ""))
                ctk.CTkLabel(rf, text=action, font=("Segoe UI", 11), width=100).grid(row=0, column=1, padx=5, pady=5)
                ctk.CTkLabel(rf, text=entry.get("service", ""), font=("Segoe UI", 11), width=120).grid(row=0, column=2, padx=5, pady=5)
                ctk.CTkLabel(rf, text=entry.get("phone", ""), font=("Segoe UI", 11), width=150).grid(row=0, column=3, padx=5, pady=5)
                ctk.CTkLabel(rf, text=entry.get("code", entry.get("id", "")), font=("Segoe UI", 11), width=150).grid(row=0, column=4, padx=5, pady=5)
        else:
            ctk.CTkLabel(hf, text="История пуста", font=("Segoe UI", 14)).grid(row=2, column=0, padx=10, pady=20)
        st = tv.add("Статистика")
        stats = load_statistics()
        sf = ctk.CTkFrame(st, fg_color="transparent")
        sf.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(sf, text="Общая статистика", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 20), sticky="w")
        total_purchases = sum(stats["purchases"].values())
        total_codes = sum(stats["codes"].values())
        ctk.CTkLabel(sf, text="Всего номеров куплено:", font=("Segoe UI", 13)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(sf, text=str(total_purchases), font=("Segoe UI", 13, "bold")).grid(row=1, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(sf, text="Всего получено кодов:", font=("Segoe UI", 13)).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(sf, text=str(total_codes), font=("Segoe UI", 13, "bold")).grid(row=2, column=1, padx=10, pady=5, sticky="w")
        success_rate = round((total_codes / total_purchases * 100) if total_purchases > 0 else 0, 2)
        ctk.CTkLabel(sf, text="Успешность получения кодов:", font=("Segoe UI", 13)).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(sf, text=f"{success_rate}%", font=("Segoe UI", 13, "bold")).grid(row=3, column=1, padx=10, pady=5, sticky="w")
        avg_wait_time = round(stats["waiting_times"]["total_seconds"] / stats["waiting_times"]["count"], 2) if stats["waiting_times"]["count"] > 0 else 0
        ctk.CTkLabel(sf, text="Среднее время ожидания SMS:", font=("Segoe UI", 13)).grid(row=4, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(sf, text=f"{avg_wait_time} сек.", font=("Segoe UI", 13, "bold")).grid(row=4, column=1, padx=10, pady=5, sticky="w")
        total_spent = round(sum(stats["total_spent"].values()), 2)
        ctk.CTkLabel(sf, text="Всего потрачено:", font=("Segoe UI", 13)).grid(row=5, column=0, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(sf, text=f"{total_spent} руб.", font=("Segoe UI", 13, "bold")).grid(row=5, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkFrame(sf, height=2, fg_color="#555555", width=500).grid(row=6, column=0, columnspan=2, padx=10, pady=15, sticky="ew")
        ctk.CTkLabel(sf, text="Статистика по сервисам", font=("Segoe UI", 16, "bold")).grid(row=7, column=0, columnspan=2, padx=10, pady=(15, 20), sticky="w")
        for i, header in enumerate(["Сервис", "Номера", "Коды", "Успешность", "Расходы"]):
            ctk.CTkLabel(sf, text=header, font=("Segoe UI", 12, "bold")).grid(row=8, column=i, padx=10, pady=5, sticky="w")
        services = {"tiger": "Tiger SMS", "reg": "Reg-SMS", "smslive": "SMSLive"}
        for i, (s, name) in enumerate(services.items()):
            purchases = stats["purchases"].get(s, 0)
            codes = stats["codes"].get(s, 0)
            ctk.CTkLabel(sf, text=name, font=("Segoe UI", 11)).grid(row=9+i, column=0, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(sf, text=str(purchases), font=("Segoe UI", 11)).grid(row=9+i, column=1, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(sf, text=str(codes), font=("Segoe UI", 11)).grid(row=9+i, column=2, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(sf, text=f"{round((codes / purchases * 100) if purchases > 0 else 0, 2)}%", font=("Segoe UI", 11)).grid(row=9+i, column=3, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(sf, text=f"{round(stats['total_spent'].get(s, 0), 2)} руб.", font=("Segoe UI", 11)).grid(row=9+i, column=4, padx=10, pady=5, sticky="w")
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(bf, text="Экспорт истории", width=150, height=40, font=("Segoe UI", 14), corner_radius=8, fg_color="#3a7ebf", hover_color="#1f538d", command=master.export_history).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(bf, text="Очистить историю", width=150, height=40, font=("Segoe UI", 14), corner_radius=8, fg_color="#AA3333", hover_color="#CC4444", command=lambda: master.clear_history(self)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(bf, text="Закрыть", width=150, height=40, font=("Segoe UI", 14, "bold"), corner_radius=8, fg_color="#555555", hover_color="#777777", command=self.destroy).pack(side="right", padx=10, pady=10)