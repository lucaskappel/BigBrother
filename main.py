import os
import logging

from dotenv import load_dotenv

import discord
from discord.ext import commands

from cogs import cog_configuration, cog_rcon

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s - %(message)s'
log = logging.getLogger(__name__)

def run_bot():
    load_dotenv()  # Load the environment file, which contains the bot token
    _client = commands.Bot(
        command_prefix=')',
        activity=discord.Game(name=')help')
    )

    @_client.event # Let the system know that it's ready to go.
    async def on_ready():
        print(f'System {_client.user} initialized. Beginning guild observation.')
        #print('\n'.join([str(guild.name) for guild in _client.guilds]))

    @_client.event  # handle messages before passing them to the command processing. Just greetings and insult handling
    async def on_message(message):
        if message.author == _client.user: return  # Bot should not respond to itself.
        await _client.process_commands(message) # Pass the message to the command handler.

    @_client.event  # When an error happens, write it to the console
    async def on_error(event, *args):
        with open('err.log', 'a') as f:
            if event == 'on_message':
                f.write(f'Unhandled message: {args[0]}\n')
            else:
                raise

    # Add cogs (modules/commands)
    _client.add_cog(cog_configuration.Configuration(_client))
    _client.add_cog(cog_rcon.Steam_RCON(_client))

    _client.run(os.getenv('TOKEN'))  # Run the client.


run_bot()
