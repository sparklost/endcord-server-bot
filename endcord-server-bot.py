import logging
import os
import re
import shutil
import subprocess
import threading
import time

from endcord import peripherals, utils

import stats

EXT_NAME = "Endcord Server Bot"
EXT_VERSION = "0.1.2"
EXT_ENDCORD_VERSION = "1.4.2"
EXT_DESCRIPTION = "Custom discord bot for official Endcord server"
EXT_SOURCE = "https://github.com/sparklost/endcord-server-bot"
EXT_COMMAND_ASSIST = (
    ("bot_register_commands - register all bot commands from commands.json", "bot_register_commands"),
    ("bot_toggle_ui - toggle UI drawing", "bot_toggle_ui"),
)
logger = logging.getLogger(__name__)

THANKYOUS = ("thank you", "thankyou", "thanks", "ty", "tysm", "thx", "tnx", "tyy", "thanx")
BATTERY_CHECK_INTERVAL = 10 * 60
# extra deps: apsw psycopg[binary,pool]

class Extension:
    """Main extension class"""

    def __init__(self, app):
        self.app = app

        self.run = True
        if not self.app.token.startswith("Bot"):
            logger.info("Not running on user accounts!")
            self.run = False
            del (type(self).on_execute_command, type(self).on_message_event, type(self).on_message_event_is_irrelevant)
            return

        self.guild_id = app.config.get("ext_endcord_server_bot_guild_id", None)
        self.admin_id = app.config.get("ext_endcord_server_bot_admin_id", None)
        self.alerts_channel = app.config.get("ext_endcord_server_bot_alerts_channel_id", None)
        self.mooncake_cooldown = app.config.get("ext_endcord_server_bot_mooncake_cooldown", 15) * 60   # default 15 min

        if app.config.get("ext_endcord_server_bot_db_postgresql_host", None):
            import database_postgres
            host = app.config.get("ext_endcord_server_bot_db_postgresql_host")
            user = app.config.get("ext_endcord_server_bot_db_postgresql_user", "user")
            password = app.config.get("ext_endcord_server_bot_db_postgresql_password", "password")
            self.mooncakes_db = database_postgres.MooncakeStore(host, user, password, "mooncake-store")
        else:
            import database_sqlite
            database_path = app.config.get("ext_endcord_server_bot_db_dir_path")
            if not database_path:
                database_path = f"{os.path.expanduser(peripherals.config_path)}/db/"
            database_path = os.path.expanduser(database_path)
            if not os.path.exists(database_path):
                os.makedirs(database_path, exist_ok=True)
            database_path = os.path.join(database_path, "discord.db")
            self.mooncakes_db = database_sqlite.MooncakeStore(database_path)

        if app.config.get("ext_endcord_server_bot_monitor_battery") and self.alerts_channel:
            threading.Thread(target=self.battery_watcher, daemon=True).start()

        extension_dir = os.path.dirname(os.path.abspath(__file__))
        self.commands = utils.load_json("commands.json", dir_path=extension_dir)
        # self.command_perms = utils.load_json("command_perms.json", dir_path=extension_dir)
        self.cooldown = {}
        self.members_nonce = None
        self.start_time = int(time.time())

        self.ui = True
        if app.config.get("ext_endcord_server_bot_ui", True):
            if self.ui:
                self.app.tui.pause_curses()
            else:
                self.app.tui.resume_curses()
            self.ui = not self.ui

        threading.Thread(target=self.bot, daemon=True).start()


    def battery_watcher(self):
        """Periodically check battery state and send warning to alerts channel"""
        prev_status = "Charging"
        prev_percentage = 0
        while self.run:
            status, percentage, _, _, _ = stats.get_termux_battery()
            if status is None:
                return
            if prev_status != status:
                prev_status = status
                if status == "Discharging":
                    self.app.discord.send_message(
                        self.alerts_channel,
                        "**WARNING: Power supply is disconnected! Server is now running on battery!**",
                    )
            if percentage <= 30 and prev_percentage > 30:
                self.app.discord.send_message(
                    self.alerts_channel,
                    "**WARNING: Power supply is disconnected! Less than 30% battery remaining!**",
                )
            elif percentage <= 10 and prev_percentage > 10:
                self.app.discord.send_message(
                    self.alerts_channel,
                    "**WARNING: Power supply is disconnected! Less than 10% battery remaining!**",
                )
            elif percentage <= 5 and prev_percentage > 5:
                self.app.discord.send_message(
                    self.alerts_channel,
                    "**WARNING: Power supply is disconnected! Less than 5% battery remaining!**",
                )
            prev_percentage = percentage
            time.sleep(BATTERY_CHECK_INTERVAL)


    def on_execute_command(self, command_text, chat_sel, tree_sel):   # noqa
        """Handle commands"""
        if command_text.startswith("bot_register_commands"):
            if not self.commands:
                return False
            for num, command in enumerate(self.commands):
                command_id = self.app.discord.bot_register_command(command)
                if command_id and command_id is not True:
                    self.commands[num]["id"] = command_id
                    # if self.command_perms and command["name"] in self.command_perms:   # need MANAGE_GUILD and MANAGE_ROLES perms for this
                    #     self.app.discord.bot_update_command(self.command_perms[command["name"]], command_id, self.guild_id, resource="permissions")
                self.app.update_extra_line(f"Registered {num}/{len(self.commands)}", timed=False)
                time.sleep(2)   # to not get rate_limited
            self.app.update_extra_line()
            return True
        if command_text.startswith("bot_toggle_ui"):
            if self.ui:
                self.app.tui.pause_curses()
            else:
                self.app.tui.resume_curses()
            self.ui = not self.ui
        return False


    def on_message_event_is_irrelevant(self, message, optext):
        """Check if message is relevant or not"""
        return optext == "MESSAGE_CREATE" and message["guild_id"] == self.guild_id


    def on_message_event(self, new_message):
        """Ran when message event is received"""
        if new_message["op"] != "MESSAGE_CREATE":
            return

        data = new_message["d"]
        if not data["mentions"]:
            return

        content = data["content"].lower()
        if not any(keyword in content for keyword in THANKYOUS):
            return

        text_words = re.findall(r"\b\w+\b", content)
        for word in THANKYOUS:
            if word in text_words:
                break
        else:
            return

        user_id = data["user_id"]
        for mention in data["mentions"]:
            if mention["id"] == user_id:
                continue
            if user_id in self.cooldown and user_id != self.admin_id:
                if self.cooldown[user_id] + self.mooncake_cooldown < int(time.time()):
                    del self.cooldown[user_id]
                else:
                    self.app.discord.send_message(
                        data["channel_id"],
                        "You're thanking too fast!",
                    )
                    continue
            else:
                self.cooldown[user_id] = int(time.time())

            self.mooncakes_db.increment(mention["id"])
            name = mention.get("global_name")
            if not name:
                name = mention.get("username")
            self.app.discord.send_message(
                data["channel_id"],
                f"**{name}** received a *thank you* mooncake!",
            )

    def bot(self):
        """Main bot loop"""
        while self.run:
            interaction = self.app.gateway.bot_get_interactions()
            if not interaction:
                time.sleep(0.1)
                continue
            interaction_id = interaction["id"]
            interaction_token = interaction["token"]
            data = interaction["data"]
            if interaction["type"] == 1:   # PING
                self.app.discord.bot_respond_interaction(1, None, interaction_id, interaction_token)   # PONG
            elif interaction["type"] == 2:   # APPLICATION_COMMAND
                command_name = data["name"]
                user_id = interaction["member"]["user"]["id"]
                if command_name == "ping":
                    response = {"content": "Pong!"}
                    self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)   # CHANNEL_MESSAGE_WITH_SOURCE

                elif command_name == "system-stats":
                    response = {"content": "Gathering data..."}
                    self.app.discord.bot_respond_interaction(5, response, interaction_id, interaction_token)   # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
                    ram_used, ram_total, cpu_used, ping, uptime = stats.get_system_stats()
                    text = f"RAM usage: `{ram_used}/{ram_total} MB`\n"
                    if cpu_used is not None:
                        text += f"CPU usage: `{cpu_used}%`\n"
                    else:
                        text += "CPU usage: `unknown`\n"
                    text += f"Ping: `{ping} ms` (1.1.1.1)\n"
                    text += f"Uptime: `{uptime}`"
                    bat_status, bat_percentage, bat_voltage, bat_current, bat_temperature = stats.get_termux_battery()
                    if bat_status:
                        text += f"\nBattery: {bat_status}; {bat_percentage}%; {bat_voltage} V; {bat_current} mA; {bat_temperature} °C"
                    self.app.discord.bot_edit_interaction({"content": text}, interaction_token)

                elif command_name == "nom":
                    name = interaction["member"].get("nick")
                    if not name:
                        name = interaction["member"]["user"].get("global_name")
                    if not name:
                        name = interaction["member"]["user"].get("username")
                    if user_id == self.admin_id:
                        response = {"content": f"**{name}** ate one of their mooncakes, **infinite** left."}
                    else:
                        mooncake_num = self.mooncakes_db.get_value(user_id)
                        if mooncake_num > 0:
                            self.mooncakes_db.decrement(user_id)
                            mooncake_num -= 1
                            response = {"content": f"**{name}** ate one of their mooncakes, {mooncake_num} left."}
                        else:
                            response = {"content": "Sorry you have no more mooncakes 😭."}
                    self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)

                elif command_name == "give":
                    name_give = interaction["member"].get("nick")
                    if not name_give:
                        name_give = interaction["member"]["user"].get("global_name")
                    if not name_give:
                        name_give = interaction["member"]["user"].get("username")
                    user_id_take = None
                    give_num = 1
                    for option in data["options"]:
                        if option["name"] == "user":
                            user_id_take = option["value"]
                        if option["name"] == "amount":
                            give_num = option["value"]
                    if not user_id_take:
                        response = {"content": "User not specified."}
                        self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)
                        continue
                    name_take = data["resolved"]["members"][user_id_take].get("nick")
                    if not name_take:
                        name_take = data["resolved"]["users"][user_id_take].get("global_name")
                    if not name_take:
                        name_take = data["resolved"]["users"][user_id_take].get("username")
                    if user_id == self.admin_id:
                        mooncake_num = give_num + 1
                    else:
                        mooncake_num = self.mooncakes_db.get_value(user_id)
                    if mooncake_num >= give_num:
                        if user_id != self.admin_id:
                            self.mooncakes_db.decrement(user_id, amount=give_num)
                        self.mooncakes_db.increment(user_id_take, amount=give_num)
                        response = {"content": f"**{name_take}** received *{give_num} mooncake{"s" if give_num != 1 else ""}* as a gift from **{name_give}**"}
                    else:
                        response = {"content": "Sorry, you have no more mooncakes 😭."}
                    self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)

                elif command_name == "mooncakes":
                    mooncake_num = self.mooncakes_db.get_value(user_id)
                    if user_id == self.admin_id:
                        response = {"content": "You currently have **infinite** mooncakes!"}
                    else:
                        if not mooncake_num:
                            mooncake_num = 0
                        response = {"content": f"You currently have **{mooncake_num}** mooncake" + ("s" if mooncake_num != 1 else "") + "."}
                    self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)

                elif command_name == "top-mooncakers":
                    users = self.mooncakes_db.get_top(10)
                    users.insert(0, (self.admin_id, "infinite"))
                    members_ids = []
                    for user in users:
                        members_ids.append(user[0])
                    self.app.gateway.request_members(self.guild_id, members_ids, force_query=True)
                    members = []
                    i = 0
                    while i < 15:
                        new_members = self.app.gateway.get_member_query_results()
                        if new_members:
                            members = new_members
                            break
                        time.sleep(0.1)
                        i += 1
                    text = "Top 10 mooncake holders:\n"
                    for num, user in enumerate(users):
                        name = user[0]
                        for member in members:
                            if member["id"] == str(user[0]):
                                name = member["name"]
                                break
                        text += f"{num}) {name}: `{user[1]}`\n"
                    response = {"content": text.strip("\n")}
                    self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)

                elif command_name == "ssh":
                    if user_id != self.admin_id:
                        response = {
                            "content": "You are not allowed to run this command.",
                            "flags": 1 << 6,
                        }
                        self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)
                        continue
                    if "options" in data and data["options"][0]["name"] == "tor":
                        if not shutil.which("ssh-tor"):
                            response = {
                                "content": "ssh-tor script is missing",
                                "flags": 1 << 6,
                            }
                            self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)
                            continue
                        if data["options"][0]["value"] == "start":
                            cmd = ["ssh-tor"]
                        else:
                            cmd = ["ssh-tor", "--stop"]
                        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                        response = {
                            "content": result.stdout + result.stderr,
                            "flags": 1 << 6,
                        }
                        if not response["content"]:
                            response["content"] = f"Command {" ".join(cmd)} executed successfully"
                        self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)
                    elif "options" in data and data["options"][0]["name"] == "ngrok":
                        if not shutil.which("ssh-ngrok"):
                            response = {
                                "content": "ssh-ngrok script is missing",
                                "flags": 1 << 6,
                            }
                            self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)
                            continue
                        if data["options"][0]["value"] == "start":
                            cmd = ["ssh-ngrok"]
                        else:
                            cmd = ["ssh-ngrok", "--stop"]
                        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                        response = {
                            "content": result.stdout + result.stderr,
                            "flags": 1 << 6,
                        }
                        if not response["content"]:
                            response["content"] = f"Command {" ".join(cmd)} executed successfully"
                        self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)
                    else:
                        response = {
                            "content": "Specify at least one option.",
                            "flags": 1 << 6,
                        }
                        self.app.discord.bot_respond_interaction(4, response, interaction_id, interaction_token)
