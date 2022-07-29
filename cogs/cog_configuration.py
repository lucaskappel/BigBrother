import json
import discord
from discord.ext import commands


def new_guild_config(new_guild: discord.guild.Guild):
    """Create a new config file for the parameter guild using the default template.
\nvalue: Configuration value
\nvalue_type:
\t'string'->When setting, requires a string parameter after the command.
\n\t'channel'->When setting, the argument is the channel in which the command is called.
\nform:
\t0 : Highlander : There can only be one value. Setting a different value will overwrite the previous.
\n\t1 : List : Providing an argument not in the list adds it, otherwise removes it from the list.
\nmutable : 0 if false, 1 if true. A non-mutable configuration cannot be changed externally.
\nhelp : description of the configuration setting."""
    return {
        'guild_alias': {
            'value': new_guild.name,
            'value_type': 'string',
            'form': 0,
            'mutable': 0,
            'help': 'Name of this guild.'
        },
        'channel_bot': {
            'value': -1,
            'value_type': 'channel',
            'form': 0,
            'mutable': 1,
            'help': 'Call "+c set channel_bot" in a channel to mark it for bot spam.'
        },
        'channel_audit': {
            'value': -1,
            'value_type': 'channel',
            'form': 1,
            'mutable': 1,
            'help': 'Call "+c set channel_audit" in a channel to mark it for bot audit.'
        }
    }


class Configuration(commands.Cog):
    """Configuration class for handling guild configs. Allows users to set parameters related to this bot."""

    def __init__(self, _client: discord.Client):
        """_client is the discord.ext.commands.Bot object which acts as the interface to discord for the bot."""
        self._client = _client
        self.GuildConfigurations = dict()

        # Load the guild configurations from the json file
        with open(r"resources\guild_configurations.json", encoding='utf8') as json_file:
            self.GuildConfigurations = json.load(json_file)
        return

    def __del__(self):
        """When the bot shuts down, write the current configuration object to a json file.
        Overwrites the previous one to keep track of any changes made while running."""

        with open(r"resources\guild_configurations.json", 'w', encoding='utf8') as json_file:
            json.dump(self.GuildConfigurations, json_file, indent=1, sort_keys=True)
        return

    def initialize_guild_config_if_not_exist(self, guild: discord.Guild):
        if str(guild.id) not in [*self.GuildConfigurations.keys()]:
            self.GuildConfigurations[str(guild.id)] = new_guild_config(guild)
        return

    async def bot_log(self, context: commands.Context, message, delete_context_message=True):
        """Use this to keep stuff clean. Deletes the calling message, prints the desired text."""

        # channel_audit == -1 ? use the channel from which the command was called. (default)
        response_channel = context.channel

        # Get this server's audit channel
        audit_channel = self.GuildConfigurations[str(context.guild.id)]["channel_audit"]["value"]
        # channel_audit == 0 ? use the DM channel of the user who called the command
        if audit_channel == 0: response_channel = context.author.dm_channel
        # channel_audit is an id of a text channel ? use that channel
        elif audit_channel > 0: response_channel = context.guild.get_channel(audit_channel)

        # Depending on whether the message is a string or an embed, send the response appropriately.
        if isinstance(message, str):
            await response_channel.send(message)
        elif isinstance(message, discord.Embed):
            await response_channel.send(embed=message)

        # If desired, delete the message from which the command was called (for cleanliness)
        if context is not None and delete_context_message: await context.message.delete()

        return

    @commands.Cog.listener()
    async def on_guild_join(self, joined_guild: discord.guild):
        """Whenever a new guild is joined, create a configuration for it."""
        if joined_guild.id in [*self.GuildConfigurations.keys()]: return
        self.GuildConfigurations[str(joined_guild.id)] = new_guild_config(joined_guild)

    @commands.group(
        name='configuration',
        aliases=['c', 'config'],
        help='Bot configuration tools.',
        invoke_without_command=True
    )
    @commands.has_guild_permissions(view_audit_log=True)
    async def config(self, command_context: commands.Context):
        self.initialize_guild_config_if_not_exist(command_context.guild)
        help_embed = discord.Embed(
            title='[+c | +config | +configuration] : Configuration Commands',
            description='List the commands available within the configuration cog.',
            color=discord.colour.Color.blue()
        )
        help_embed.add_field(
            name='+c [set | s]',
            value='Sets a configuration setting for this guild.'
        )
        help_embed.add_field(
            name='+c [get | g]',
            value='Gets a configuration setting for this guild.'
        )
        await self.bot_log(command_context, help_embed)
        return

    @config.command(
        name='set',
        aliases=['s'],
        help='Set a configuration setting for this guild.'
    )
    async def setconfig(self, command_context: commands.Context, *args):
        """Set one of the configuration settings for this guild appropriately"""
        self.initialize_guild_config_if_not_exist(command_context.guild)
        guild_config = self.GuildConfigurations[str(command_context.guild.id)]

        # If no parameters are provided, show what parameters are available to set
        if len(args) == 0:
            help_embed = discord.Embed(
                title='+c [set | s] <parameter> <value?>: Set Guild Configuration',
                description='Set a setting for this guild\'s configuration',
                color=discord.colour.Color.blue()
            )
            for config_setting in [*guild_config.keys()]:
                help_embed.add_field(
                    name=config_setting,
                    value=guild_config[config_setting]["help"]
                )
            await self.bot_log(command_context, help_embed)
            return

        # Make sure the setting exists
        if args[0] not in [*guild_config.keys()]:
            await self.bot_log(command_context, f'Configuration setting "{args[0]}" was not found.')
            return

        # Make sure the setting is mutable
        if guild_config[args[0]]['mutable'] == 0:
            await self.bot_log(command_context, f'Setting "{args[0]}" is not mutable')
            return

        # Figure out what the value being set is.
        setting_value = ''
        if guild_config[args[0]]['value_type'] == 'string':

            # If it's a string an argument must be provided
            if len(args) < 2:
                await self.bot_log(
                    command_context,
                    f'config ```{args[0]}``` type is a string, but no argument was provided.')
                return

            # Assume everything after the config setting is the value.
            else: setting_value = ' '.join(args[1:len(args)])
        elif guild_config[args[0]]['value_type'] == 'channel': setting_value = command_context.channel.id

        # Now set the value based on the form
        # For highlander, overwrite previous, or un-set it.
        if guild_config[args[0]]['form'] == 0:
            if setting_value == guild_config[args[0]]['value']: guild_config[args[0]]['value'] = -1
            else: guild_config[args[0]]['value'] = setting_value
        # For list, remove the value if it's already in the list, or add it if it isn't.
        elif guild_config[args[0]]['form'] == 1:
            if setting_value in guild_config[args[0]]['value']: guild_config[args[0]]['value'].pop(setting_value)
            else: guild_config[args[0]]['value'].append(setting_value)

        await self.bot_log(
            command_context,
            f'Setting ```{args[0]}``` has been set to ```{guild_config[args[0]]["value"]}```'
        )
        return

    @config.command(
        name='get',
        aliases=['g'],
        help='Get a configuration setting for this guild.'
    )
    async def getconfig(self, command_context, *args):
        """Get one of the configuration settings for this guild appropriately"""
        self.initialize_guild_config_if_not_exist(command_context.guild)
        guild_config = self.GuildConfigurations[str(command_context.guild.id)]

        # If no arguments are passed, print the full configuration
        if len(args) == 0:
            help_embed = discord.Embed(
                title='+c [get | g] <parameter> <value?>: Set Guild Configuration',
                description='Get a setting for this guild\'s configuration',
                color=discord.colour.Color.blue()
            )
            for config_setting in [*guild_config.keys()]:
                help_embed.add_field(
                    name=config_setting,
                    value='\n'.join(
                        [f'{attribute} : {guild_config[config_setting][attribute]}'
                         for attribute in [*guild_config[config_setting].keys()]])
                )
            await self.bot_log(command_context, help_embed)
            return

        # If the argument passed is not a valid parameter, return
        if args[0] not in [*guild_config.keys()]: return

        # Build the embed to display the config setting.
        config_setting = guild_config[args[0]]
        help_embed = discord.Embed(
            title=args[0],
            description=config_setting['help'],
            color=discord.colour.Color.blue()
        )
        help_embed.add_field(
            name=config_setting['value'],
            value=f'value_type : {config_setting["value_type"]}\n' +
                  f'form : {config_setting["form"]}\n' +
                  f'mutable: {str(config_setting["mutable"])}'
        )
        await self.bot_log(command_context, help_embed)

        return
