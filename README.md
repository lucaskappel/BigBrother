# BigBrother

Another discord bot :corn:

This bot was made to support the City of Wolves DayZSA Server.

<h3>Bot Features</h3>

- Mirrors the DayZ server's global and local chat to a text "bridge" channel in Discord

- Discord users can type in this bridge channel to message the DayZ server's global chat right back.

- RCON Kick and Ban commands in the moderation channel by members with the same guild permissions.

- Prints RCON logs to a dedicated channel on the discord server.

- Bot is a very goode boye and tries to reconnect on its own if it disconnects :3



<h2>How to Use</h2>

1) Install python3 on your computer or whatever

2) Download this repo as a zip in the top right corner under "code"

3) create a file called '.env' in the folder where this readme is.

4) Copy and paste this into .env: 'TOKEN=putyourtokenhere'

5) Make sure the bot is in your server, then run main.py

6) Call this command wherever you want to use as the server's log channel:

   )isc {ipv4} {port} "{rcon_password}" {bridge_channel_id} {moderation_channel_id}
   
   - You can get the ipv4, port, and rcon_password from your rcon configuration file in battleeye extended controls I think
   
   - Get the channel id's by right clicking on the channels with developer mode enabled in discord
   
8) Restart the bot, because it only creates the connection to the DayZ server on startup because I am neither a CS major nor a wizard


TODO
----
- Figure out a way to get the bot to kick the DayZ server if it goes down or freezes.

- Learn about whatever cursed mechanics are behind how DayZ events work and integrate those or something

- Get a gf

- Add more personality to the code through commenting

- Add creepy/unsettling lore features to add to the atmosphere