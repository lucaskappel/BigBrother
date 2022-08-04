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
        self.reconnect_attempts = 0

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

        # Upon disconnect, try to reconnect in intervals defined by the config file.
        self.bec_client.add_Event(
            "on_disconnect",
            lambda: asyncio.run_coroutine_threadsafe(
                self.cycle_reconnect(),
                self.discord_client.loop))

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

    async def get_moderation_channel(self):
        """Get the guild's moderation channel"""

        # Get the server according to the config
        target_server = self.discord_client.get_guild(
            self.bec_config['guild_id'])

        # return the first text channel whose id matches the config's debug channel id
        return next(
            text_channel for text_channel in target_server.text_channels
            if text_channel.id == self.bec_config['guild_moderation_channel'])

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
        if discord_message.channel.id not in [
                self.bec_config['guild_dayz_channel'],
                self.bec_config['guild_debug_channel']]:
            return

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

    async def cycle_reconnect(self):
        """Try to reconnect once per minute, until reconnect_attempts surpasses the config maximum setting"""

        debug_channel = await self.get_debug_channel()

        # Check to see if we've hit the connection attempt limit
        if self.reconnect_attempts > self.bec_config["maximum_reconnect_attempts"]:
            await debug_channel.send('Unable to reconnect. Use ```)reconnect``` upon server restoration.')
            print('Unable to reconnect. Use ```)reconnect``` upon server restoration.')
            return False

        # Let everywhere know we're trying to reconnect
        await debug_channel.send('Disconnected, attempting to reconnect...')
        print('Disconnected, attempting to reconnect...')

        # Wait the specified interval
        await asyncio.sleep(self.bec_config["reconnect_attempt_interval_s"])

        # Try to reconnect.
        await self.bec_client.connect()

        # If the client returns a successful keepAlive, the reconnect was successful. Reset the reconnect attempts.
        if await self.bec_client.keepAlive():
            self.reconnect_attempts = 0
            await debug_channel.send('Successfully reconnected')
            return True

        # Otherwise, try again and increment the attempts
        self.reconnect_attempts += 1
        return await self.cycle_reconnect()


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
             'args[4] = ID of the text channel to use for moderation'
             '\nFull call should look like this in the channel to be used for server logs:'
             ')isc 123.456.789.00 9999 "rcon password" 1234567890123456789 1234567890123456789'
    )
    @commands.has_guild_permissions(administrator=True)
    async def initialize_server_configuration(self, command_context: commands.Context, *args):

        if len(args) != 5: # Make sure the command is formatted properly
            await self.server_bridge.get_debug_channel().send(
                'Please format the command correctly:\n> ' +
                ')isc <ipv4> <port> "<rcon_password>" <bridge_channel_id> <moderation_channel_id>')

        guild_config = {
            "guild_alias": command_context.guild.name,
            "guild_id": command_context.guild.id,
            "bec_server_ipv4": args[0],
            "bec_rcon_port": int(args[1]),
            "bec_rcon_password": args[2],
            "guild_debug_channel": int(command_context.channel.id),
            "guild_dayz_channel": int(args[3]),
            "guild_moderation_channel": int(args[4]),
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
        if command_context.author.id != 183033825108951041: return # Only run if it's me >:L
        self.server_bridge.bec_client.disconnect()
        #await self.debugsub()
        return

    async def debugsub(self, cycle=0):
        print(f'cycle: {cycle} / {self.server_bridge.bec_config["maximum_reconnect_attempts"]}')
        await asyncio.sleep(10)
        if cycle > self.server_bridge.bec_config['maximum_reconnect_attempts']:
            print('Recursion attempts reached')
            return
        await self.debugsub(cycle+1)

    @commands.command(name='rcon_kick')
    @commands.has_permissions(kick_members=True)
    async def rcon_player_kick(self, command_context: commands.Context):

        # Get the moderation channel with which to work, and make sure the command was in it
        moderation_channel = await self.server_bridge.get_moderation_channel()
        if command_context.channel.id != moderation_channel.id: return

        # First, get the list of players on the server. [pid, ip, maybe player's server life id?, BE_UID, name]
        player_list = await self.server_bridge.bec_client.getPlayersArray()

        # print their information out, ordered and selectable.
        kick_choices = 'Select from the list below who to kick. Send a message formatted as:\n> ' \
                       '<#> <Reason for kick>' \
                       '\n'
        for player in player_list: kick_choices += f'\n{player_list.index(player)} : {player[4]} : {player[3]}'
        await moderation_channel.send(kick_choices)

        # Wait for a reply which says which user to kick.
        reply_message = await self._client.wait_for(
            'message',
            check=lambda reply: False not in (
                reply.author.id == command_context.author.id,
                reply.channel.id == command_context.channel.id,
                re.match(r"^\d* .*", reply.content) is not None
            ),
            timeout=120
        )

        # Interpret the reply message above. Get the player from the array.
        reply_message_interpretation = re.match(r"^(?P<index>\d*) (?P<kick_reason>.*)", reply_message.content)
        player_to_kick_raw = player_list[int(reply_message_interpretation.group('index'))]
        player_to_kick = {
            "Name": player_to_kick_raw[4],
            "IP Address": player_to_kick_raw[1],
            "BattleEye ID": player_to_kick_raw[3], # Do not kick using this as an identifier.
            "Server Lifetime ID": player_to_kick_raw[2],
            "Server Instance ID": player_to_kick_raw[0],
        }

        # Confirm the identity of the user to kick.
        kick_embed = discord.Embed(
            color=discord.Color.red(),
            title='Confirm Player Kick',
            description=reply_message_interpretation.group('kick_reason')
        )
        for parameter in [*player_to_kick.keys()]:
            kick_embed.add_field(
                name=parameter,
                value=player_to_kick[parameter],
                inline=False)
        kick_message = await moderation_channel.send(embed=kick_embed)

        # Add reactions to the message and wait for the user to confirm with them.
        for emote in ["✅", "❌"]: await kick_message.add_reaction(emote)

        # Wait for the original author to add a reaction from the above two.
        reply_emote = await self._client.wait_for(
            'reaction_add',
            check=lambda reaction, user: False not in (
                reaction.message.id == kick_message.id, # Make sure the reacted message is the embed
                user.id == reply_message.author.id, # Make sure the reaction was added by the og kicker
            ),
            timeout=120
        )

        # If the added emote is the check mark, perform the kick.
        if reply_emote[0].emoji == "✅":
            await self.server_bridge.bec_client.kickPlayer(player_to_kick["Server Instance ID"])

        return

    @commands.command(name='rcon_ban')
    @commands.has_permissions(ban_members=True)
    async def rcon_player_ban(self, command_context: commands.Context):

        moderation_channel = await self.server_bridge.get_moderation_channel()
        if command_context.channel.id != moderation_channel.id: return

        # First, get the list of players on the server. [pid, ip, a number?, BE_UID, name]
        player_list = await self.server_bridge.bec_client.getPlayersArray()

        # print their information out, ordered and selectable.
        ban_choices = 'Select from the list below who to ban. Send a message formatted as:\n> ' \
                      '<#> <duration in seconds> <Reason for ban>' \
                      '\n'
        for player in player_list: ban_choices += f'\n{player_list.index(player)} : {player[4]} : {player[3]}'
        await moderation_channel.send(ban_choices)

        # Wait for a reply which says which user to kick.
        reply_message = await self._client.wait_for(
            'message',
            check=lambda reply: False not in (
                reply.author.id == command_context.author.id,
                reply.channel.id == command_context.channel.id,
                re.match(r"^\d* \d* .*", reply.content) is not None
            ),
            timeout=120
        )

        # Interpret the reply message above. Get the player from the array.
        reply_message_interpretation = re.match(
            r"^(?P<index>\d*) (?P<ban_duration>\d*) (?P<ban_reason>.*)", reply_message.content)
        player_to_ban_raw = player_list[int(reply_message_interpretation.group('index'))]
        player_to_ban = {
            "Name": player_to_ban_raw[4],
            "IP Address": player_to_ban_raw[1],
            "BattleEye ID": player_to_ban_raw[3],
            "Server Lifetime ID": player_to_ban_raw[2],
            "Server Instance ID": player_to_ban_raw[0],
        }

        # Confirm the identity of the user to kick. Print an embed showing their information.
        ban_embed = discord.Embed(
            color=discord.Color.red(),
            title='Confirm Player Ban',
            description=f'<{reply_message_interpretation.group("ban_duration")}> seconds \n ' +
                        f'{reply_message_interpretation.group("ban_reason")}'
        )
        for parameter in [*player_to_ban.keys()]:
            ban_embed.add_field(
                name=parameter,
                value=player_to_ban[parameter],
                inline=False)
        ban_message = await moderation_channel.send(embed=ban_embed)

        # Add reactions to the message and wait for the user to confirm with them.
        for emote in ["✅", "❌"]: await ban_message.add_reaction(emote)

        # Wait for the original author to add a reaction from the above two.
        reply_emote = await self._client.wait_for(
            'reaction_add',
            check=lambda reaction, user: False not in (
                reaction.message.id == ban_message.id,  # Make sure the reacted message is the embed
                user.id == reply_message.author.id,  # Make sure the reaction was added by the og kicker
            ),
            timeout=120
        )

        # If the added emote is the check mark. Do we need to kick them too?
        if reply_emote[0].emoji == "✅":
            await self.server_bridge.bec_client.addBan(player_to_ban["BattleEye ID"])

        return
