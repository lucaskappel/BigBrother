import json

import discord
from discord.ext import commands

from rcon import bec_rcon


class Steam_RCON(commands.Cog):

    def __init__(self, _client: discord.Client):
        """_client is the discord.ext.commands.Bot object which acts as the interface to discord for the bot."""
        self._client = _client
        self.BEC_Server_Configurations = dict()
        self.BEC_Clients = dict()

        # Load the server configuration list.
        with open(r"resources\bec_server_configurations.json", encoding='utf8') as json_file:
            self.BEC_Server_Configurations = json.load(json_file)

        # For each of the server configurations in the 'bec_server_configurations.json' file, create an RCON client.
        for GuildID in [*self.BEC_Server_Configurations.keys()]:
            rcon_client = bec_rcon.ARC(
                self.BEC_Server_Configurations[GuildID]["bec_rcon_ipv4"],
                self.BEC_Server_Configurations[GuildID]["bec_rcon_password"],
                self.BEC_Server_Configurations[GuildID]["bec_rcon_port"])

            # Add these two events like the tutorial told me to.
            rcon_client.add_Event(
                "received_ServerMessage",
                lambda args: print(args[0]))
            rcon_client.add_Event(
                "on_disconnect",
                lambda: print("Disconnected"))

            # Add it to the list of clients
            self.BEC_Clients[GuildID] = rcon_client

        return

    def __del__(self):
        """When the bot shuts down, write the current configuration object to a json file.
        Overwrites the previous one to keep track of any changes made while running.
        The RCON Clients will disconnect themselves upon termination, so don't need to do anything,\n
        unless we want to do something when they do."""

        with open(r"resources\BEC_Server_Configurations.json", 'w', encoding='utf8') as json_file:
            json.dump(self.BEC_Server_Configurations, json_file, indent=1, sort_keys=False)
        return

    async def PrintServerConfigDebug(self, guild_id):
        if guild_id not in self.BEC_Clients.keys(): return

        this_rcon_client = self.BEC_Clients[str(guild_id)]
        server_status = {
            'player_count': len(await this_rcon_client.getPlayersArray()),
            'player_list': await this_rcon_client.getPlayersArray(),
            'admin_count': len(await this_rcon_client.getAdminsArray()),
            'admin_list': await this_rcon_client.getAdminsArray(),
            'ban_count': len(await this_rcon_client.getBansArray()),
            'ban_list': await this_rcon_client.getBansArray(),
            # 'sorry': await rcon_client.sayGlobal('Please DM Bard#3883 on Discord to let him know you saw this message! uwu rawr XD')
        }

        print('\n'.join(
            [f'{SSKey} : {server_status[SSKey]}' for SSKey in [*server_status.keys()]]
        ))

        print('\n'.join(str(m) for m in this_rcon_client.serverMessage))

        return

    @commands.command(
        name='debug',
        help='Debug command',
        invoke_without_command=True
    )
    async def debug(self, command_context: commands.Context, *args):
        if command_context.author.id != 183033825108951041: return
        if len(args) > 0:
            await self.PrintServerConfigDebug(args[0])
        else: await self.PrintServerConfigDebug(command_context.guild.id)
        return