# endcord-server-bot
An extension for [endcord](https://github.com/sparklost/endcord) discord TUI client, that implements bot used in [Endcord Testing Ground](https://discord.gg/judQSxw5K2) server.  
This extension is intended **for bots only**.  


## Features
- "Thank you mooncake" - user receives mooncake when someone thanks to them. Mooncakes can be eaten or gifted.
- Show system stats
- Show battery info (in termux only)
- Ping
- Admin: start/stop ssh server over TOR hidden service and show address
- Admin: start/stop ssh server over ngrok and show address


## Installing
See [official extensions documentation](https://github.com/sparklost/endcord/blob/main/extensions.md#installing-extensions) for installing instructions.
Available options:
- Git clone into `Extensions` directory located in endcord config directory.
- Run `endcord -i https://github.com/sparklost/endcord-bot`
- Or use endcord client-side command `install_extension sparklost/endcord-bot`


## Configuration
Edit `commands.json` to add commands, but it wont do anything on its own.  
After updating `commands.json` run bot inside endcord, and run `bot_register_commands`. It will register new and update old commands one-by-one. Check log for any issues.  
Note that there is a limit of 200 command registrations per day.  

### Settings options
- `ext_endcord_server_bot_guild_id = None`  
- `ext_endcord_server_bot_admin_id = None`  
- `ext_endcord_server_bot_mooncake_cooldown = 15`  
- `ext_endcord_server_bot_ui = True`  
- `ext_endcord_server_bot_db_postgresql_host = None`  
- `ext_endcord_server_bot_db_postgresql_user = "user"`  
- `ext_endcord_server_bot_db_postgresql_password = "password"`  
- `ext_endcord_server_bot_db_dir_path = None`  


## Disclaimer
This extension is usable only by bots which should not be breaking any ToS, byt here's a warning anyway:  
> [!WARNING]
> Using third-party client is against Discord's Terms of Service and may cause your account to be banned!  
> **Use endcord and/or this extension at your own risk!**  
> If this extension is modified, it may be used for harmful or unintended purposes.  
> **The developer is not responsible for any misuse or for actions taken by users.**  
