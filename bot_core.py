#!/usr/bin/env python3
"""
GMO Coin Bot Core Functions
Version: 2.0.0
License: MIT License
Copyright (c) 2024 GMO Coin Bot

Core Discord bot functionality for GMO Coin Automated Trading Bot.
Provides bot commands and integration features.

For more information, see README.md
"""

import discord
from discord.ext import commands
import asyncio
import json
import os
import logging
import traceback
import psutil
import gc
import time
from datetime import datetime, timedelta
import threading

class FXBotCore:
    def __init__(self, token, webhook_url=None, command_prefix='', intents=None, case_insensitive=True):
        self.token = token
        self.webhook_url = webhook_url
        self.intents = intents or discord.Intents.default()
        self.intents.message_content = True
        self.bot = commands.Bot(command_prefix=command_prefix, intents=self.intents, case_insensitive=case_insensitive)
        self._register_default_events()
        self._register_default_commands()
        self._external_commands = []

    def _register_default_events(self):
        @self.bot.event
        async def on_ready():
            logging.info(f'Discord Bot connected as {self.bot.user}')
            if self.webhook_url:
                self.send_webhook_message(f"🤖 Botが起動しました: {self.bot.user}")

        @self.bot.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.CommandNotFound):
                await ctx.send("❌ 不明なコマンドです。`command`でコマンド一覧を確認してください。")
            elif isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ このコマンドを実行する権限がありません。")
            else:
                logging.error(f"Discord Bot コマンドエラー: {error}")
                await ctx.send(f"❌ コマンド実行中にエラーが発生しました: {str(error)}")

    def _register_default_commands(self):
        @self.bot.command(name='ping')
        async def ping(ctx):
            await ctx.send('Pong!')

    def add_command(self, func):
        """外部からコマンド関数を追加"""
        self.bot.command()(func)
        self._external_commands.append(func)

    def send_webhook_message(self, content):
        """Webhook経由でDiscordにメッセージ送信（同期）"""
        if not self.webhook_url:
            logging.warning("Webhook URL未設定")
            return
        import requests
        try:
            requests.post(self.webhook_url, json={"content": content})
            logging.info(f"Discord通知送信: {content[:100]}...")
        except Exception as e:
            logging.error(f"Discord通知エラー: {e}")

    def run(self):
        def _run():
            try:
                self.bot.run(self.token)
            except Exception as e:
                logging.error(f"Discord Bot起動エラー: {e}")
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # 他社FX会社用の拡張ポイント例
    def register_fx_company_commands(self, fx_commands):
        """FX会社ごとのコマンド群を一括登録"""
        for func in fx_commands:
            self.add_command(func) 