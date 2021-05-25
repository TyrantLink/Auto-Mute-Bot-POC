import discord,os,asyncio,json
from datetime import datetime
from discord.ext import commands
from discord.ext.commands.core import guild_only
from discord_slash import cog_ext,SlashCommand,SlashContext

client = commands.Bot(command_prefix='mute ') # establish client coroutine
slash = SlashCommand(client,sync_commands=True) # establish slash command coroutine

try: data = json.loads(open('save.json','r').read()) # tries to load save file
except: data = {'usersMuted':False,'defaultServer':{'muteRole':0,'muteList':[]},'servers':{}} # on fail, sets to default file

def save(): json.dump(data,open('save.json','w+'),indent=2) # saves all data to save.json

class events(commands.Cog): # main class for all events
	def __init__(self,client): self.client = client # required for all classes

	@commands.Cog.listener()
	async def on_ready(self): # runs on bot startup
		print(f'{client.user.name} connected to discord!')

	@commands.Cog.listener()
	async def on_guild_join(self,guild): # runs when bot joins a guild
		data['servers'][str(guild.id)] = data['defaultServer'] # initializes new server to save file.

	@commands.Cog.listener() 
	async def on_command_error(self,ctx,error): # runs on legacy command error
		await ctx.send('all commands are slash commands, type "/" to see a list of commands.')

	@commands.Cog.listener()
	async def on_slash_command_error(self,ctx:SlashContext,error): # runs on command error
		await ctx.send(f'error: {error}',hidden=True) # responds with error, visible only to issuer of command
		print(f'error in {ctx.guild.name}: {error}') # logs error and origin server to console

	async def mute(mode): # called when ready to mute users
		for guild in data['servers']: # loops through all joined servers
			guildID = data['servers'][guild] # sets guildID to specifc location in save file
			guild = await client.fetch_guild(guild) # gets guild object from id
			if guildID['muteRole'] == 0: # checks if muted role is valid
				await (await guild.fetch_member(guild.owner_id)).send(f'error: unspecified mute role in {guild.name}.\nplease run `/mute setup`') # DMs server owner telling them the mute role is invalid.
			if mode == 'mute': # mode to mute users
				for user in guildID['muteList']: # cycles through list of auto mute users
					await (await guild.fetch_member(user)).add_roles(discord.Object(guildID['muteRole'])) # gives auto mute role
					data['usersMuted'] = True
			if mode == 'unmute': # mode to unmute users
				for user in guildID['muteList']: # cycles through list of auto mute users
					await (await guild.fetch_member(user)).remove_roles(discord.Object(guildID['muteRole'])) # removes auto mute role
					data['usersMuted'] = False
			save() # saves to file after completion
	async def autoMuteLoop(): # main loop for auto mute function
		await client.wait_until_ready() # waits until bot has connected to discord
		while client.is_ready: # runs while the bot is connected to discord
			await asyncio.sleep(180) # checks hour ever 180 seconds and mutes / unmutes accordingly
			if datetime.now().strftime('%H') == '22' and not data['usersMuted']: await events.mute('mute')
			if datetime.now().strftime('%H') == '06' and data['usersMuted']: await events.mute('unmute')
class command(commands.Cog): # main class for slash commands
	def __init__(self,client): self.client = client # required for all classes

	@cog_ext.cog_subcommand(base='mute',name='setup',description='setup automuting') # establishes command /mute setup
	@guild_only() # makes command only available in guilds (not DMs)
	async def mute_setup(self,ctx:SlashContext,role:discord.Role): 
		data['servers'][str(ctx.guild.id)]['muteRole'] = role.id # adds muted role to save file
		await ctx.send('setup complete.')

	@cog_ext.cog_subcommand(base='mute',name='list',description='list users on auto mute list') # establishes command /mute list
	@guild_only() # makes command only available in guilds (not DMs)
	async def mute_list(self,ctx:SlashContext): # responds with an embed list of auto mute users
		await ctx.send(embed=discord.Embed(title='Auto Mute List:',description='\n'.join(data['servers']['muteList'])))

	@cog_ext.cog_subcommand(base='mute',name='add',description='add user to auto mute list') # establishes command /mute add
	@guild_only() # makes command only available in guilds (not DMs)
	async def mute_add(self,ctx:SlashContext,user:discord.User):
		if str(user.id) in data['servers'][str(ctx.guild.id)]['muteList']: # checks if user is already in auto mute list
			await ctx.send('this user is already on the auto mute list!',hidden=True)
			return
		data['servers'][str(ctx.guild.id)]['muteList'].append(str(user.id)) # adds user to auto mute list
		save()
		await ctx.send('added user to auto mute list.',hidden=True) 

	@cog_ext.cog_subcommand(base='mute',name='remove',description='remove user from auto mute list') # establishes command /mute remove
	@guild_only() # makes command only available in guilds (not DMs)
	async def mute_remove(self,ctx:SlashContext,user:discord.User):
		if str(user.id) not in data['servers'][str(ctx.guild.id)]['muteList']: # checks if user is already in auto mute list
			await ctx.send('this user is not on the auto mute list!',hidden=True)
			return
		data['servers'][str(ctx.guild.id)]['muteList'].remove(str(user.id)) # removes user from auto mute list
		save()
		await ctx.send('removed user from auto mute list.',hidden=True)

client.loop.create_task(events.autoMuteLoop())
client.add_cog(events(client))
client.add_cog(command(client))

try: client.run(os.getenv('token')) # runs the client
except AttributeError: # runs on failure to load token
	with open('.env','w') as envFile: envFile.write('token=') # creates .env file with line token= inside
	print('\nerror: please specify token in .env file.\n') # prints out error to console 
	exit() # exits program.
finally: save() # saves on client exit