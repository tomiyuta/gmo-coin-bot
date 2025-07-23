import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys

class ConfigEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("GMOコイン 設定エディタ")
        self.root.geometry("600x700")
        
        self.config_file = 'config.json'
        self.config = self.load_config()
        
        self.create_widgets()
        self.load_current_config()
        
    def load_config(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                messagebox.showerror("エラー", f"設定ファイル読み込みエラー: {e}")
                return {}
        return {}
    
    def save_config(self, config):
        """設定ファイルを保存する"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("エラー", f"設定ファイル保存エラー: {e}")
            return False
    
    def create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.geometry("900x700")  # 横幅拡大

        # タイトル
        title_label = ttk.Label(main_frame, text="GMOコイン 設定エディタ", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 左カラムフレーム
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        # 右カラムフレーム
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky="nsew")

        # API設定セクション（左）
        api_frame = ttk.LabelFrame(left_frame, text="API設定", padding="10")
        api_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # API Key
        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky="w", pady=5)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=50, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)

        # API Secret
        ttk.Label(api_frame, text="API Secret:").grid(row=1, column=0, sticky="w", pady=5)
        self.api_secret_var = tk.StringVar()
        self.api_secret_entry = ttk.Entry(api_frame, textvariable=self.api_secret_var, width=50, show="*")
        self.api_secret_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)

        # Discord Webhook URL
        ttk.Label(api_frame, text="Discord Webhook URL:").grid(row=2, column=0, sticky="w", pady=5)
        self.discord_webhook_var = tk.StringVar()
        self.discord_webhook_entry = ttk.Entry(api_frame, textvariable=self.discord_webhook_var, width=50)
        self.discord_webhook_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=5)

        # Discord Botトークン
        ttk.Label(api_frame, text="Discord Botトークン:").grid(row=4, column=0, sticky="w", pady=5)
        self.discord_bot_token_var = tk.StringVar()
        self.discord_bot_token_entry = ttk.Entry(api_frame, textvariable=self.discord_bot_token_var, width=50)
        self.discord_bot_token_entry.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=5)

        # パスワード表示/非表示ボタン
        self.show_password_var = tk.BooleanVar()
        show_password_cb = ttk.Checkbutton(api_frame, text="パスワードを表示", 
                                         variable=self.show_password_var, 
                                         command=self.toggle_password_visibility)
        show_password_cb.grid(row=3, column=0, columnspan=2, pady=10)

        # 取引設定セクション（左）
        trading_frame = ttk.LabelFrame(left_frame, text="取引設定", padding="10")
        trading_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Spread Threshold
        ttk.Label(trading_frame, text="許容スプレッド (pips):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.spread_threshold_var = tk.DoubleVar()
        self.spread_threshold_entry = ttk.Entry(trading_frame, textvariable=self.spread_threshold_var, width=20)
        self.spread_threshold_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Jitter Seconds
        ttk.Label(trading_frame, text="ランダム遅延 (秒):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.jitter_seconds_var = tk.IntVar()
        self.jitter_seconds_entry = ttk.Entry(trading_frame, textvariable=self.jitter_seconds_var, width=20)
        self.jitter_seconds_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Stop Loss Pips
        ttk.Label(trading_frame, text="ストップロス (pips):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.stop_loss_pips_var = tk.IntVar()
        self.stop_loss_pips_entry = ttk.Entry(trading_frame, textvariable=self.stop_loss_pips_var, width=20)
        self.stop_loss_pips_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Take Profit Pips
        ttk.Label(trading_frame, text="テイクプロフィット (pips):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.take_profit_pips_var = tk.IntVar()
        self.take_profit_pips_entry = ttk.Entry(trading_frame, textvariable=self.take_profit_pips_var, width=20)
        self.take_profit_pips_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # レバレッジ設定
        ttk.Label(trading_frame, text="レバレッジ（1～25倍）:").grid(row=4, column=0, sticky="w", pady=5)
        self.leverage_var = tk.IntVar()
        self.leverage_entry = ttk.Entry(trading_frame, textvariable=self.leverage_var, width=20)
        self.leverage_entry.grid(row=4, column=1, sticky="w", padx=(10, 0), pady=5)

        # リスク割合設定
        ttk.Label(trading_frame, text="リスク割合（0.1～1.0）:").grid(row=5, column=0, sticky="w", pady=5)
        self.risk_ratio_var = tk.DoubleVar()
        self.risk_ratio_entry = ttk.Entry(trading_frame, textvariable=self.risk_ratio_var, width=20)
        self.risk_ratio_entry.grid(row=5, column=1, sticky="w", padx=(10, 0), pady=5)

        # 右カラム：注文設定
        order_frame = ttk.LabelFrame(right_frame, text="注文設定", padding="10")
        order_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Entry Order Retry Interval
        ttk.Label(order_frame, text="エントリー注文リトライ間隔 (秒):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_retry_interval_var = tk.IntVar()
        self.entry_retry_interval_entry = ttk.Entry(order_frame, textvariable=self.entry_retry_interval_var, width=20)
        self.entry_retry_interval_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Max Entry Order Attempts
        ttk.Label(order_frame, text="エントリー注文最大リトライ回数:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_entry_attempts_var = tk.IntVar()
        self.max_entry_attempts_entry = ttk.Entry(order_frame, textvariable=self.max_entry_attempts_var, width=20)
        self.max_entry_attempts_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Exit Order Retry Interval
        ttk.Label(order_frame, text="決済注文リトライ間隔 (秒):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.exit_retry_interval_var = tk.IntVar()
        self.exit_retry_interval_entry = ttk.Entry(order_frame, textvariable=self.exit_retry_interval_var, width=20)
        self.exit_retry_interval_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Max Exit Order Attempts
        ttk.Label(order_frame, text="決済注文最大リトライ回数:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.max_exit_attempts_var = tk.IntVar()
        self.max_exit_attempts_entry = ttk.Entry(order_frame, textvariable=self.max_exit_attempts_var, width=20)
        self.max_exit_attempts_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Position Check Interval
        ttk.Label(order_frame, text="ポジション監視間隔 (秒):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.position_check_interval_var = tk.IntVar()
        self.position_check_interval_entry = ttk.Entry(order_frame, textvariable=self.position_check_interval_var, width=20)
        self.position_check_interval_entry.grid(row=4, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Position Check Interval Minutes（定期ポジション監視間隔）
        ttk.Label(order_frame, text="定期ポジション監視間隔 (分):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.position_check_interval_minutes_var = tk.IntVar()
        self.position_check_interval_minutes_entry = ttk.Entry(order_frame, textvariable=self.position_check_interval_minutes_var, width=20)
        self.position_check_interval_minutes_entry.grid(row=5, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # システム設定（右）
        system_frame = ttk.LabelFrame(right_frame, text="システム設定", padding="10")
        system_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # 自動再起動時間
        ttk.Label(system_frame, text="自動再起動時間 (0-24時、空欄で無効):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.auto_restart_hour_var = tk.StringVar()
        self.auto_restart_hour_entry = ttk.Entry(system_frame, textvariable=self.auto_restart_hour_var, width=20)
        self.auto_restart_hour_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        ttk.Label(system_frame, text="※ 毎日指定時刻に自動再起動します。空欄の場合は連続運転", 
                 font=("Arial", 8)).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        # ボタンフレーム（右）
        button_frame = ttk.Frame(right_frame)
        button_frame.grid(row=2, column=0, pady=20)

        # 保存ボタン
        save_button = ttk.Button(button_frame, text="設定を保存", command=self.save_settings)
        save_button.grid(row=0, column=0, padx=(0, 10))

        # リセットボタン
        reset_button = ttk.Button(button_frame, text="デフォルトにリセット", command=self.reset_to_default)
        reset_button.grid(row=0, column=1, padx=(0, 10))

        # 終了ボタン
        exit_button = ttk.Button(button_frame, text="終了", command=self.root.quit)
        exit_button.grid(row=0, column=2)

        # グリッドの重み設定
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        api_frame.columnconfigure(1, weight=1)
        trading_frame.columnconfigure(1, weight=1)
        order_frame.columnconfigure(1, weight=1)
        system_frame.columnconfigure(1, weight=1)
        
    def toggle_password_visibility(self):
        """パスワードの表示/非表示を切り替え"""
        if self.show_password_var.get():
            self.api_key_entry.config(show="")
            self.api_secret_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
            self.api_secret_entry.config(show="*")
    
    def load_current_config(self):
        """現在の設定をフォームに読み込む"""
        self.api_key_var.set(self.config.get('api_key', ''))
        self.api_secret_var.set(self.config.get('api_secret', ''))
        self.discord_webhook_var.set(self.config.get('discord_webhook_url', ''))
        self.discord_bot_token_var.set(self.config.get('discord_bot_token', ''))
        self.spread_threshold_var.set(self.config.get('spread_threshold', 0.01))
        self.jitter_seconds_var.set(self.config.get('jitter_seconds', 3))
        self.stop_loss_pips_var.set(self.config.get('stop_loss_pips', 0))
        self.take_profit_pips_var.set(self.config.get('take_profit_pips', 0))
        self.entry_retry_interval_var.set(self.config.get('entry_order_retry_interval', 5))
        self.max_entry_attempts_var.set(self.config.get('max_entry_order_attempts', 3))
        self.exit_retry_interval_var.set(self.config.get('exit_order_retry_interval', 10))
        self.max_exit_attempts_var.set(self.config.get('max_exit_order_attempts', 3))
        self.position_check_interval_var.set(self.config.get('position_check_interval', 5))
        self.leverage_var.set(self.config.get('leverage', 10))
        self.risk_ratio_var.set(self.config.get('risk_ratio', 1.0))
        # 定期ポジション監視間隔（分）
        self.position_check_interval_minutes_var.set(self.config.get('position_check_interval_minutes', 10))
        # 自動再起動時間の設定
        auto_restart_hour = self.config.get('auto_restart_hour')
        if auto_restart_hour is not None:
            self.auto_restart_hour_var.set(str(auto_restart_hour))
        else:
            self.auto_restart_hour_var.set('')
    
    def save_settings(self):
        """設定を保存"""
        try:
            leverage = self.leverage_var.get()
            if not (1 <= leverage <= 25):
                messagebox.showerror("エラー", "レバレッジは1～25倍で入力してください。")
                return
            # 自動再起動時間の検証
            auto_restart_hour_str = self.auto_restart_hour_var.get().strip()
            auto_restart_hour = None
            if auto_restart_hour_str:
                try:
                    auto_restart_hour = int(auto_restart_hour_str)
                    if not (0 <= auto_restart_hour <= 24):
                        messagebox.showerror("エラー", "自動再起動時間は0～24の範囲で入力してください。")
                        return
                except ValueError:
                    messagebox.showerror("エラー", "自動再起動時間は数値で入力してください。")
                    return
            new_config = {
                'api_key': self.api_key_var.get(),
                'api_secret': self.api_secret_var.get(),
                'discord_webhook_url': self.discord_webhook_var.get(),
                'discord_bot_token': self.discord_bot_token_var.get(),
                'spread_threshold': self.spread_threshold_var.get(),
                'jitter_seconds': self.jitter_seconds_var.get(),
                'stop_loss_pips': self.stop_loss_pips_var.get(),
                'take_profit_pips': self.take_profit_pips_var.get(),
                'entry_order_retry_interval': self.entry_retry_interval_var.get(),
                'max_entry_order_attempts': self.max_entry_attempts_var.get(),
                'exit_order_retry_interval': self.exit_retry_interval_var.get(),
                'max_exit_order_attempts': self.max_exit_attempts_var.get(),
                'position_check_interval': self.position_check_interval_var.get(),
                'position_check_interval_minutes': self.position_check_interval_minutes_var.get(),
                'leverage': leverage,
                'risk_ratio': self.risk_ratio_var.get(),
                'auto_restart_hour': auto_restart_hour
            }
            if self.save_config(new_config):
                messagebox.showinfo("成功", "設定を保存しました。")
                self.config = new_config
            else:
                messagebox.showerror("エラー", "設定の保存に失敗しました。")
        except Exception as e:
            messagebox.showerror("エラー", f"設定保存エラー: {e}")
    
    def reset_to_default(self):
        """デフォルト設定にリセット"""
        if messagebox.askyesno("確認", "デフォルト設定にリセットしますか？"):
            default_config = {
                'api_key': '',
                'api_secret': '',
                'discord_webhook_url': '',
                'discord_bot_token': '',
                'spread_threshold': 0.01,
                'jitter_seconds': 3,
                'stop_loss_pips': 0,
                'take_profit_pips': 0,
                'entry_order_retry_interval': 5,
                'max_entry_order_attempts': 3,
                'exit_order_retry_interval': 10,
                'max_exit_order_attempts': 3,
                'position_check_interval': 5,
                'position_check_interval_minutes': 10,  # デフォルト10分
                'leverage': 10,
                'risk_ratio': 1.0,
                'auto_restart_hour': None # デフォルトでは自動再起動を無効化
            }
            if self.save_config(default_config):
                self.config = default_config
                self.load_current_config()
                messagebox.showinfo("成功", "デフォルト設定にリセットしました。")
            else:
                messagebox.showerror("エラー", "リセットに失敗しました。")

def main():
    root = tk.Tk()
    app = ConfigEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main() 