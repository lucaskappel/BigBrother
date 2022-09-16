# BigBrother

Another discord bot :corn:

This bot was made to support the City of Wolves DayZSA Server. I made my own instead of using someone else's because everyone else's didn't work and were complicated and messy and I only have so many brain cells. I made this one so it could be simple to set up and run and modify for your own server and I don't know why doing that is so hard for other developers. Sure, it's not perfectly generic and can only handle one dayz server at a time, but even though I'm single I still busy and what I made here is like ten times more organized and well-documented than the other stuff I saw. buy my mixtape

The actual RCON parts are done in bec_rcon.py, made by Yoshi-E:
https://github.com/Yoshi-E/Python-BEC-RCon

<h3>Bot Features</h3>

- Mirrors the DayZ server's global and local chat to a text "bridge" channel in Discord

- Discord users can type in this bridge channel to message the DayZ server's global chat right back.

- RCON Kick and Ban commands in the moderation channel by members with the same guild permissions.

- Prints RCON logs to a dedicated channel on the discord server.

- Bot is a very goode boye and tries to reconnect on its own if it disconnects :3
-- Bot is not a very goode boye and cant reconnect on its own atm



<h2>How to Use</h2>

1) Install python3 on your computer or whatever

2) Download this repo as a zip in the top right corner under "code"

3) create a file called '.env' in the folder where this readme is.

4) Copy and paste this into .env: 'TOKEN=putyourbottokenhere'

5) Make sure the bot is in your server, then run *the batch file which is not made yet* ;(

6) Call this command wherever you want to use as the server's log channel:

   )isc {rcon_ipv4} {rcon_port} "{rcon_password}" {bridge_channel_id} {moderation_channel_id}
   
   example:
   )isc 127.08.01.1 2564 "password_lol" 1234567890 0987654321
   
   - You can get the ipv4, port, and rcon_password from your rcon configuration file in battleeye extended controls I think, it should be in a config file somewhere for the server i just had someone get the info for me
   
   - Get the channel id s by right clicking on the channels with developer mode enabled in discord
   
8) Restart the bot, because it only creates the connection to the DayZ server on startup because I am neither a CS major nor a wizard, just a guy who knows a little bit of python and friends


TODO
----
- Figure out a way to get the bot to kick the DayZ server if it goes down or freezes.

- Learn about whatever cursed mechanics are behind how DayZ events work and integrate those or something

- Get a gf

- Add more personality to the code through commenting

- Add creepy/unsettling lore features to add to the atmosphere
