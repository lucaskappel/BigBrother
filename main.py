import os
import logging

from dotenv import load_dotenv

import discord
from discord.ext import commands

from cog_rcon import Server_Bridge, Steam_RCON

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s - %(message)s'
log = logging.getLogger(__name__)

def run_bot():
    load_dotenv()  # Load the environment file, which contains the bot token

    # Create the client through which the bot can communicate with discord
    _client = commands.Bot(
        command_prefix=')',
        activity=discord.Game(name=')help')
    )

    # Create the client through which the bot can commmunicate with DayZ
    server_bridge = Server_Bridge(_client)

    @_client.event # Let the system know that it's ready to go.
    async def on_ready():

        # Once the client is ready, add the cog with the server bridge attached to it.
        _client.add_cog(Steam_RCON(_client, server_bridge))

        print(f'System {_client.user} initialized. Beginning guild observation.')

        return

    @_client.event  # handle messages before passing them to the command processing.
    async def on_message(message):
        if message.author == _client.user: return  # Bot should not respond to itself.
        elif message.author.bot: return
        await server_bridge.parse_message_discord_to_rcon(message)
        await _client.process_commands(message) # Pass the message to the command handler.

    @_client.event  # When an error happens, write it to the console
    async def on_error(event, *args):
        with open('err.log', 'a') as f:
            if event == 'on_message':
                f.write(f'Unhandled message: {args[0]}\n')
            else:
                raise

    _client.run(os.getenv('TOKEN'))  # Run the client.

run_bot()
