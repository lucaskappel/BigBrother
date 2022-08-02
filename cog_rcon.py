import json
import asyncio
import os
from threading import Timer, Event
import discord
from discord.ext import commands
import bec_rcon
import re


class Server_Bridge:
    """Manages the bridge between the dayz and discord servers."""

    def __init__(self, discord_client: discord.Client):

        # keep a reference to the discord client for handling messages
        self.discord_client = discord_client

        # Load the config file, doing all the path stuff as needed
        self.bec_config = dict()
        if not os.path.exists(r'resources'): os.makedirs(r'resources') # Make resources folder if it doesn't exist
        with open(r"resources\bec_server_config.json", encoding='utf8') as json_file:
            self.bec_config = json.load(json_file) # load the config file into memory

        # Create the ARC client, which will be the connection between the dayz server and the bot.
        self.bec_client = bec_rcon.ARC(
            self.bec_config["bec_server_ipv4"],
            self.bec_config["bec_rcon_password"],
            self.bec_config["bec_rcon_port"])

        # When the rcon client receives a server message, determine where it goes.
        self.bec_client.add_Event(
            "received_ServerMessage",
            lambda args: asyncio.run_coroutine_threadsafe(
                self.parse_message_rcon_to_discord(args[0]),
                self.discord_client.loop))

        self.bec_client.add_Event(
            "on_disconnect",
            lambda: ( # Use a tuple so we can run multiple commands in one lambda! :D

                # Let console know the bot disconnected.
                print("Disconnected"),

                # Let the debug channel know the bot disconnected.
                asyncio.run_coroutine_threadsafe(
                    self.get_debug_channel().send('Disconnected, attempting to reconnect...'),
                    self.discord_client.loop),

                # Then execute this ternary command:
                # Check "if", this will attempt to reconnect a certain number of times, defined by the config file.
                # If it successfully reconnects, it returns "True"
                # At that point, the 'successfully reconnected' is sent.
                # If it is unable to reconnect after all its attempts are used, cycle_reconnect returns false
                # At which point, we ask the log channel to manually restart the bot.

                asyncio.run_coroutine_threadsafe(
                    self.get_debug_channel().send('Successfully reconnected.'),
                    self.discord_client.loop)

                if asyncio.run_coroutine_threadsafe(
                    self.cycle_reconnect(),
                    self.discord_client.loop)

                else asyncio.run_coroutine_threadsafe(
                    self.get_debug_channel().send('Unable to reconnect. Use ```)reconnect``` upon server restoration.'),
                    self.discord_client.loop)

            ) # End lambda statement tuple
        ) # End add_Event on_disconnect

        # Add heartbeat; clients need to see a signal every 45 seconds, or they close.
        self.heartbeat()

        return

    def heartbeat(self):
        """The heartbeat keeps the client alive.
        Calls itself every 30 seconds to make sure the clients do not close.
        Also updates the player count at this time."""

        Timer(
            30, # Every thirty seconds...
            lambda _: ( # ... do this set of instructions...

                # update the player count
                asyncio.run_coroutine_threadsafe(
                    self.update_player_count_in_discord_activity(),
                    self.discord_client.loop),

                # Call the keepalive function
                asyncio.run_coroutine_threadsafe(
                    self.update_player_count_in_discord_activity(),
                    self.discord_client.loop),

                # call this timer again to repeat in 30 sec
                self.heartbeat()),
            [Event()]).start()  # ... starting now!

        return

    async def get_debug_channel(self):
        """Get the guild's debug/logs channel"""

        # Get the server according to the config
        target_server = self.discord_client.get_guild(
            self.bec_config['guild_id'])

        # return the first text channel whose id matches the config's debug channel id
        return next(
            text_channel for text_channel in target_server.text_channels
            if text_channel.id == self.bec_config['guild_debug_channel'])

    async def update_player_count_in_discord_activity(self):
        """Update's the client's activity to mirror the number of players on the dayz server."""

        await self.discord_client.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f'over {len(await self.bec_client.getPlayersArray())} survivors...'))

        return

    async def parse_message_rcon_to_discord(self, message: str):
        """Take a message given by the event and print it to the appropriate channels."""

        print(message)

        message = message.replace('@', '') # Don't let it ping people lol

        # Get the target guild for this message
        target_guild = self.discord_client.get_guild(int(self.bec_config["guild_id"]))

        # If it's a global message, also print it to the bridge channel
        if "(Global)" in message and "-discord" not in message:

            # Get the bridge channel by finding its id in the guild's list of text channels
            bridge_channel = next(
                text_channel for text_channel in target_guild.text_channels if text_channel.id == int(
                    self.bec_config["guild_dayz_channel"])) # The channel id according to the config

            # Send the message to the bridge channel, after formatting it to remove the extra stuff
            await bridge_channel.send(re.match(r".*\(Global\) (.*)", message).groups()[0])

        # Send all messages received to the logs channel
        logs_channel = next(
                text_channel for text_channel in target_guild.text_channels if text_channel.id == int(
                    self.bec_config["guild_debug_channel"])) # The channel id according to the config
        await logs_channel.send(message)

        return

    async def parse_message_discord_to_rcon(self, discord_message: discord.Message):
        """This method takes a message sent by a user in the bridge channel, and then sends
        it to the dayz server as a formatted global message."""

        # If the message wasn't sent in one of the valid config channels, ignore it.
        if discord_message.channel.id not in [*self.bec_config.values()]: return

        # Make sure the message isn't a command
        if discord_message.content.startswith(self.discord_client.__getattribute__("command_prefix")): return

        # Set the default values
        username = discord_message.author.name
        source = "-discord"

        # If we want to send a message as big brother, use the debug/logs channel.
        if str(discord_message.channel.id) == str(self.bec_config["guild_debug_channel"]):
            username = "Big Brother"
            source = ""

        # Send the message to the right client! Format it to be hopefully identical to how it prints in game
        await self.bec_client.sayGlobal(f'{username}{source}: {discord_message.content}')

        return

    async def cycle_reconnect(self, reconnect_attempts=0):
        """Try to reconnect once per minute, until reconnect_attempts surpasses the config maximum setting"""

        # Check how many times we've tried to connect
        if reconnect_attempts > self.bec_config["maximum_reconnect_attempts"]: return False

        # Try to reconnect. IF keepAlive returns true, the reconnection was successful.
        await self.bec_client.reconnect()
        if await self.bec_client.keepAlive():
            return True

        # Try again after the specified interval.
        await asyncio.sleep(self.bec_config["reconnect_attempt_interval_s"])
        return await self.cycle_reconnect(reconnect_attempts + 1)


class Steam_RCON(commands.Cog):

    def __init__(self, _client: discord.Client, server_bridge: Server_Bridge):
        """_client is the discord.ext.commands.Bot object which acts as the interface to discord for the bot."""
        self._client = _client
        self.server_bridge = server_bridge
        return

    @commands.command(
        name='initialize_server_configuration',
        aliases=['isc'],
        help='Call this in the channel to be used for server logs.'
             'args[0] = DayZ server ID, ex. 123.456.789.00'
             'args[1] = DayZ server RCON port, ex 9999'
             'args[2] = DayZ server RCON password, surrounded by quotes'
             'args[3] = ID of the text channel to use as the bridge for displaying global chat'
             '\nFull call should look like this in the channel to be used for server logs:'
             ')isc 123.456.789.00 9999 "rcon_password" 1234567890123456789'
    )
    @commands.has_guild_permissions(administrator=True)
    async def initialize_server_configuration(self, command_context: commands.Context, *args):

        if len(args) != 4: # Make sure the command is formatted properly
            await self.server_bridge.get_debug_channel().send(
                'Please format the command correctly:\n' +
                '> )isc <ipv4> <port> "<rcon_password>" <bridge_channel_id>')

        guild_config = {
            "guild_alias": command_context.guild.name,
            "guild_id": command_context.guild.id,
            "bec_server_ipv4": args[0],
            "bec_rcon_port": int(args[1]),
            "bec_rcon_password": args[2],
            "guild_debug_channel": int(command_context.channel.id),
            "guild_dayz_channel": int(args[3]),
            "maximum_reconnect_attempts": 100,
            "reconnect_attempt_interval_s": 60
        }

        # Write the config to the file
        with open(r"resources\bec_server_config.json", encoding='utf8') as json_file:
            json.dump(guild_config, json_file)

        return

    @commands.command(
        name='debug',
        help='Debug command',
        invoke_without_command=True)
    async def debug(self, command_context: commands.Context):
        if command_context.author.id != 183033825108951041: return
        print(self._client.__getattribute__("command_prefix"))
        return

    @commands.command(name='reconnect')
    @commands.has_permissions(view_audit_log=True)
    async def rcon_reconnect(self, command_context: commands.Context):
        print('Attempting to reconnect...')
        await self.server_bridge.get_debug_channel().send('Attempting to reconnect...')
        await self.server_bridge.bec_client.reconnect()
        if self.server_bridge.bec_client.keepAlive():
            print('Reconnected.')
            await self.server_bridge.get_debug_channel().send('Reconnected.')
        else:
            print('Failed to reconnect.')
            await self.server_bridge.get_debug_channel().send('Failed to reconnect.')
        return
