import discord
import datetime
import random
from discord.ext import commands, tasks
from discord.ui import Button, View
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio


welcome_channel = 1270457986908950621
log_channel_id = 1270464124697968734

intents = discord.Intents.all()
intents.members = True
intents.voice_states = True
intents.members = True



antiraid_enabled = False
join_times = defaultdict(list)


bot = commands.Bot(command_prefix="&", intents=intents, description="Bot de Mkazz",)


invite_uses = {}

@bot.event
async def on_ready():
    print("Bot is ready")
    for guild in bot.guilds:
        invites = await guild.invites()
        for invite in invites:
            invite_uses[invite.code] = invite.uses
    print("Invites loaded and ready for tracking")
    await bot.change_presence(activity=discord.Streaming(name="mkazz", url="https://www.twitch.tv/mkazz__"))

# Anti-raid : commande pour activer/désactiver
@bot.command()
@commands.has_permissions(administrator=True)
async def antiraid(ctx, mode: str = None):
    global antiraid_enabled
    if mode is None:
        await ctx.send("Usage: &antiraid <on|off>")
        return

    if mode.lower() == "on":
        antiraid_enabled = True
        await ctx.send("Le mode antiraid est activé.")
    elif mode.lower() == "off":
        antiraid_enabled = False
        await ctx.send("Le mode antiraid est désactivé.")
    else:
        await ctx.send("Usage: &antiraid <on|off>")

# Anti-raid et système de bienvenue
@bot.event
async def on_member_join(member):
    global antiraid_enabled

    if antiraid_enabled:
        now = datetime.utcnow()
        join_times[member.guild.id].append(now)

        # Conserver les arrivées des 10 dernières minutes
        join_times[member.guild.id] = [join_time for join_time in join_times[member.guild.id] if now - join_time < timedelta(minutes=10)]

        # Si plus de 5 membres rejoignent en 10 minutes, active l'anti-raid
        if len(join_times[member.guild.id]) > 5:
            await member.kick(reason="Antiraid activé : trop de membres ont rejoint en peu de temps.")
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(f"{member.name}#{member.discriminator} a été expulsé automatiquement en raison de l'antiraid.")
            return

        # Vérification si le compte est récent
        account_age = (now - member.created_at).days
        if account_age < 7:  # Par exemple, si le compte a moins de 7 jours
            await member.kick(reason="Antiraid activé : compte récent.")
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(f"Le compte {member.name}#{member.discriminator} a été expulsé automatiquement en raison de l'antiraid (compte récent).")
            return
    
    # Message de bienvenue
    channel = bot.get_channel(welcome_channel)
    embed = discord.Embed(
        description=f'Bienvenue **{member.mention}** dans le serveur !',
        color=0x0D0A0B,
        timestamp=datetime.utcnow()
    )
    embed.set_image(url="https://img.ifunny.co/images/09f9bf7cfeca1d548a2d5307b1b8e0b3acff7c69ac6d720d465bb1751caefd9b_1.jpg")
    await channel.send(embed=embed)

# Commande clear
@bot.command()
async def clear(ctx: commands.Context, amount: int = 5):
    if ctx.guild is None:
        return await ctx.send("Vous ne pouvez pas utiliser cette commande en message privé")

    if not ctx.author.guild_permissions.manage_messages:
        return await ctx.send("Vous n'avez pas les permissions pour cette commande.")

    if amount > 100:
        return await ctx.send("Vous ne pouvez pas supprimer plus de 100 messages.")

    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"{amount} messages ont été supprimés.")

# Commande ban
@bot.command()
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = ""):
    if ctx.guild is None:
        return await ctx.send("Cette commande ne peut être utilisée en message privés")

    if not ctx.author.guild_permissions.ban_members:
        return await ctx.send("Vous n'avez pas les permissions pour bannir un membre")

    if ctx.author.top_role <= member.top_role:
        return await ctx.send("Vous ne pouvez pas bannir ce membre")

    if not reason:
        reason = "Aucune raison définie"

    await member.ban(reason=reason)
    await ctx.send(f"{member.name} a été banni pour {reason}")

# Commande unban
@bot.command()
async def unban(ctx: commands.Context, member: str, *, reason: str = ""):
    if ctx.guild is None:
        return await ctx.send("Vous ne pouvez pas utiliser cette commande en message privé")

    if not ctx.author.guild_permissions.ban_members:
        return await ctx.send("Vous n'avez pas les permissions pour cette commande.")

    try:
        member_name, member_discriminator = member.split("#")
    except ValueError:
        return await ctx.send("Le format du membre est incorrect. Veuillez utiliser le format `username#1234`.")

    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user, reason=reason)
            return await ctx.send(f"{user.name}#{user.discriminator} a été débanni.")

    await ctx.send(f"L'utilisateur nommé {member} n'a pas été trouvé.")

# Commande de kick
@bot.command()
async def kick(ctx: commands.Context, member: discord.Member, *, reason: str = ""):
    if ctx.guild is None:
        return await ctx.send("Cette commande ne peut être utilisée en message privés")

    if not ctx.author.guild_permissions.kick_members:
        return await ctx.send("Vous n'avez pas les permissions pour kick un membre")

    if ctx.author.top_role <= member.top_role:
        return await ctx.send("Vous ne pouvez pas kick ce membre")

    if not reason:
        reason = "Aucune raison définie"

    await member.kick(reason=reason)
    await ctx.send(f"{member.name} a été kick pour {reason}")

temporary_bans = []

@bot.command(name="tempban")
@commands.has_permissions(administrator=True)
async def temp_ban(ctx, member: discord.Member, duration: int, *, reason: str = "Aucune raison fournie"):
    """
    Bannis temporairement un membre.
    :param member: Le membre à bannir.
    :param duration: La durée du bannissement en minutes.
    :param reason: La raison du bannissement.
    """
    try:
        # Bannir le membre
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} a été banni pour {duration} minutes. Raison: {reason}")

        # Ajouter le bannissement temporaire à la liste
        unban_time = datetime.utcnow() + timedelta(minutes=duration)
        temporary_bans.append((member.id, ctx.guild.id, unban_time))

        # Optionnel : Envoyer un message privé au membre
        try:
            await member.send(f"Vous avez été banni du serveur {ctx.guild.name} pour {duration} minutes. Raison: {reason}")
        except discord.Forbidden:
            pass  # Si l'utilisateur a désactivé les DM
        
    except discord.Forbidden:
        await ctx.send("Je n'ai pas les permissions nécessaires pour bannir ce membre.")
    except discord.HTTPException as e:
        await ctx.send(f"Une erreur s'est produite: {e}")

@tasks.loop(minutes=1)
async def check_temporary_bans():
    now = datetime.utcnow()
    for member_id, guild_id, unban_time in temporary_bans[:]:
        if now >= unban_time:
            guild = bot.get_guild(guild_id)
            member = await bot.fetch_user(member_id)
            if guild and member:
                try:
                    await guild.unban(member)
                    print(f"Membre {member} débanni automatiquement.")
                except discord.HTTPException:
                    pass
            temporary_bans.remove((member_id, guild_id, unban_time))


# Commande de déconnexion
@bot.command()
async def deco(ctx: commands.Context, member: discord.Member):
    if ctx.guild is None:
        return await ctx.send("Cette commande ne peut être utilisée en message privés")

    if not ctx.author.guild_permissions.move_members:
        return await ctx.send("Vous n'avez pas les permissions pour déconnecter un membre")

    if member.voice and member.voice.channel:
        await member.move_to(None)
        await ctx.send(f'{member.mention} a été déconnecté du salon vocal.')
    else:
        await ctx.send(f'{member.mention} n\'est pas dans un salon vocal.')

# Événement pour les logs de messages supprimés
@bot.event
async def on_message_delete(message):
    if message.guild:
        description = f"Message de {message.author} ({message.author.id}) supprimé\nContenu : {message.content}"
        embed = discord.Embed(title="Message supprimé", description=description, color=random.randint(0, 0xFFFFFF))
        log_channel = bot.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(embed=embed)

# Commande userinfo
@bot.command(aliases=['uinfo', 'whois'])
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.message.author

    roles = [role for role in member.roles if role != ctx.guild.default_role]

    embed = discord.Embed(
        title="User Info",
        description=f"Les informations de {member.mention}",
        color=random.randint(0, 0xFFFFFF),
        timestamp=ctx.message.created_at
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Nom", value=f"{member.name}#{member.discriminator}", inline=False)
    embed.add_field(name="Surnom", value=member.display_name, inline=False)
    embed.add_field(name="Statut", value=str(member.status).capitalize(), inline=False)
    embed.add_field(name="Compte créé le", value=member.created_at.strftime("%d/%m/%Y à %H:%M:%S"), inline=False)
    embed.add_field(name="A rejoint le serveur depuis", value=member.joined_at.strftime("%a, %B %#d, %Y, %I:%M %p"), inline=False)
    embed.add_field(name="Rôle le plus élevé", value=member.top_role.mention, inline=False)
    embed.add_field(name="Rôles", value=", ".join([role.mention for role in roles]) or "Aucun", inline=False)

    await ctx.send(embed=embed)

# Commande aide
@bot.command()
async def aide(ctx: commands.Context):
    embed = discord.Embed(
        title="Commandes du Bot",
        description="Voici la liste des commandes disponibles :",
        color=random.randint(0, 0xFFFFFF),
        timestamp=ctx.message.created_at,
    )

    embed.add_field(name="&ban", value="Bannir un utilisateur. Usage: `&ban @utilisateur [raison]`", inline=False)
    embed.add_field(name="&clear", value="Effacer des messages. Usage: `&clear [nombre de messages]`", inline=False)
    embed.add_field(name="&kick", value="Expulser un utilisateur. Usage: `&kick @utilisateur [raison]`", inline=False)
    embed.add_field(name="&userinfo", value="Afficher les informations d'un utilisateur. Usage: `&userinfo [@utilisateur]`", inline=False)
    embed.add_field(name="&deconnecter", value="Déconnecter un utilisateur d'un salon vocal. Usage: `&deconnecter @utilisateur`", inline=False)
    embed.add_field(name="&avatar", value="Permet de voir votre avatar/photo de profil. Usage: `&avatar @utilisateur`", inline=False)
    embed.add_field(name="&nick", value="Permet renommer un utilisateur. Usage: `&nick @utilisateur`", inline=False)
    embed.add_field(name="&slowmode", value="Définir un mode ralentit. Usage: `&slowmode [valeur]`", inline=False)
    embed.add_field(name="&unban", value="Débannir un utilisateur. Usage: `&unban @utilisateur [raison]`", inline=False)
    embed.add_field(name="&mute", value="Permet de mute un utilisateur dans un salon vocal. Usage: `&mute @utilisateur [raison]`", inline=False)
    embed.add_field(name="&unmute", value="Permet de démute un utilisateur dans un salon vocal. Usage: `&unmute @utilisateur [raison]`", inline=False)


    await ctx.send(embed=embed)

# Commande de mute
@bot.command()
async def mute(ctx : commands.Context, member : discord.Member, *, reason : str = ""):
    is_in_private_message = ctx.guild is None and isinstance(ctx.author, discord.User)
    if is_in_private_message:
        return await ctx.send("Vous ne pouvez pas utliser cette commande en message privés.")
    
    has_permission = ctx.author.guild_permissions.manage_channels
    if not has_permission:
        return await ctx.send("Vous n'avez pas les permissions pour utiliser cette commande.")

    is_mutable = ctx.author.top_role > member.top_role
    if not is_mutable:
        return await ctx.send("Vous ne pouvez pas mute ce membre !")
    
    is_in_voice_channel = member.voice is not None and member.voice.channel is not None
    if not is_in_voice_channel:
        return await ctx.send("Le membre doit être dans un salon vocal !")
    
    if reason == "":
        reason = "Aucune raison donné"

    await member.edit(mute=True, reason=reason)

    return await ctx.send(f"{member.name} a été mute !")

# Commande de unmute
@bot.command()
async def unmute(ctx : commands.Context, member : discord.Member, *, reason : str = ""):
    is_in_private_message = ctx.guild is None and isinstance(ctx.author, discord.User)
    if is_in_private_message:
        return await ctx.send("Vous ne pouvez pas utliser cette commande en message privés.")
    
    has_permission = ctx.author.guild_permissions.manage_channels
    if not has_permission:
        return await ctx.send("Vous n'avez pas les permissions pour utiliser cette commande.")

    await member.edit(mute=False, reason=reason)
    return await ctx.send(f"{member.name} a été unmute !")

# Commande de slow mode
@bot.command()
async def slowmode(ctx : commands.Context, seconds : int, channel : discord.TextChannel =  None) -> discord.Message:
    
    is_in_private_message = ctx.guild is None and isinstance(ctx.author, discord.User)
    if is_in_private_message:
        return await ctx.send("Vous ne pouvez pas utiliser cette commande en message privés")
    
    has_permission = ctx.author.guild_permissions.manage_channels
    if not has_permission:
        return await ctx.send("Vous n'avez pas les permissions pour utiliser cette commande.")
    
    is_time_invalid = seconds < 0 or seconds > 21600
    if is_time_invalid:
        return await ctx.send("Le doit être compris entre 0 et 21600 secondes !")
    
    if channel is None:
        channel = ctx.channel

    await channel.edit(slowmode_delay=seconds)

    if seconds == 0:
        return await ctx.send("Le slowmode a été désactivé !")
    
    return await ctx.send(f"Le slowmode a été définie sur {seconds} secondes !")

# Commande de nick
@bot.command()
async def nick(ctx : commands.Context, member : discord.Member, *, nickname : str = None) -> discord.Message:
    
    is_in_private_message = ctx.guild is None and isinstance(ctx.author, discord.User)
    if is_in_private_message:
        return await ctx.send("Vous ne pouvez pas utiliser cette commande en message privés")
    
    has_permission = ctx.author.guild_permissions.manage_channels
    if not has_permission:
        return await ctx.send("Vous n'avez pas les permissions pour utiliser cette commande.")
    
    is_member_nickable = ctx.author.top_role > member.top_role
    if not is_member_nickable:
        return await ctx.send("Vous ne pouvez pas nick ce membre !")
    
    await member.edit(nick=nickname)

    if nickname is None:
        return await ctx.send(f"Le nickname de {member.name} a été retiré")
    
    return await ctx.send(f"Le nickname de {member.name} a été défini sur {nickname}")

# Commande Avatar
@bot.command(name="avatar")
async def send_avatar(ctx : commands.Context, user : discord.User = None) -> discord.Message:
    if user is None:
        user = ctx.author

    embed = discord.Embed(
        title=f"Avatar de {user.name}",
        description=f"[Lien vers l'avatar]({user.display_avatar.url})",
        color=random.randint(0, 0xFFFFFF)
    )

    embed.set_image(url=user.display_avatar.url)

    return await ctx.send(embed=embed)

# Commande reaction role
@bot.command()
async def reactionrole(ctx):
    embed = discord.Embed(
        title="Réaction Rôle",
        description="Réagissez avec 🎉 pour obtenir ou retirer le rôle Membre",
        color=0x00ff00
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    
    bot.reaction_message_id = msg.id
@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != bot.reaction_message_id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    role = discord.utils.get(guild.roles, name="Membre")

    if member and role:
        await member.add_roles(role)
        await member.send(f"**Vous avez reçu le rôle {role.name}**")
@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != bot.reaction_message_id:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    role = discord.utils.get(guild.roles, name="Membre")

    if member and role:
        await member.remove_roles(role)
        await member.send(f"**Le rôle {role.name} vous a été retiré**")


# Commande anti raid

#Commande ticket
@bot.command()
async def ticket(ctx):
    if ctx.channel.id != 1270660744450670658:
        await ctx.send("Vous ne pouvez utiliser cette commande que dans le salon spécifié ")
        return

    guild = ctx.guild
    author = ctx.author

    existing_channel = discord.utils.get(guild.channels, name=f"ticket-{author.name.lower()}-{author.discriminator}")
    if existing_channel:
        await ctx.send(f"Vous avez déjà un ticket ouvert : {existing_channel.mention}")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    admin_role = discord.utils.get(guild.roles, name="Admin")  
    if admin_role:
        overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel(name=f"ticket-{author.name.lower()}-{author.discriminator}", overwrites=overwrites)
    await channel.send(f"Bonjour {author.mention}, comment pouvons-nous vous aider ?")

    class DeleteButton(Button):
        def __init__(self):
            super().__init__(label="Supprimer le ticket", style=discord.ButtonStyle.danger)

        async def callback(self, interaction: discord.Interaction):
            if interaction.user == author or interaction.user.guild_permissions.administrator:
                await channel.delete()
            else:
                await interaction.response.send_message("Vous n'avez pas la permission de supprimer ce ticket.", ephemeral=True)

    view = View()
    view.add_item(DeleteButton())

    await channel.send(f"Votre ticket a été créé : {channel.mention}", view=view)
    await ctx.send(f"Votre ticket a été créé : {channel.mention}")

# Commande addrole
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await ctx.send(f"{member.mention} a déjà le rôle {role.mention}.")
    else:
        await member.add_roles(role)
        await ctx.send(f"Le rôle {role.mention} a été ajouté à {member.mention}.")

# Invite compteur
@bot.event
async def on_member_join(member):
    guild = member.guild
    
    invites_after_join = await guild.invites()
    for invite in invites_after_join:
        if invite.code in invite_uses and invite.uses > invite_uses[invite.code]:
            inviter = invite.inviter
            invite_uses[invite.code] = invite.uses
            break
    else:
        inviter = None
    
    if inviter:
        inviter_id = inviter.id
        bot.invite_counts[inviter_id] += 1
        print(f"{member.name} joined using an invite from {inviter.name}")
        
        specific_channel = bot.get_channel(1270457986908950621)
        if specific_channel:
            await specific_channel.send(f"{member.mention} a rejoint le serveur grâce à l'invitation de {inviter.mention} !")
        else:
            print(f"Could not find channel with ID 1270457986908950621")
@bot.command()
async def invitecount(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    count = bot.invite_counts.get(member.id, 0)
    await ctx.send(f"{member.mention} a invité {count} personne(s) sur le serveur.")



# Commande giveaway
@bot.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx, duration: str, *, prize: str):
    """Starts a giveaway. Duration is in seconds."""
    try:
        duration = int(duration)
    except ValueError:
        await ctx.send("Veuillez fournir une durée valide en secondes.")
        return

    embed = discord.Embed(title="🎉 Giveaway! 🎉", description=f"Récompense : **{prize}**", color=0x00ff00)
    embed.add_field(name="Réagissez avec 🎉 pour participer!", value=f"Le concours se terminera dans {duration} secondes.", inline=False)
    embed.set_footer(text="Le concours prendra fin")
    embed.set_image(url="https://static.planetminecraft.com/files/image/minecraft/blog/2022/063/15486115-giveaway_l.webp")

    giveaway_message = await ctx.send(embed=embed)
    await giveaway_message.add_reaction("🎉")

    await asyncio.sleep(duration)

    giveaway_message = await ctx.channel.fetch_message(giveaway_message.id)
    users = []
    async for user in giveaway_message.reactions[0].users():
        if user != bot.user:
            users.append(user)

    if len(users) == 0:
        await ctx.send("Personne n'a participé au concours.")
        return

    winner = random.choice(users)
    await ctx.send(f"Bien joué {winner.mention}! Tu as gagné **{prize}**!")

# Commande info serveur
@bot.command(aliases=['sinfo', 'server'])
async def serverinfo(ctx):
    embed = discord.Embed(title="Serveur info", description=f"Voici les informations sur le serveur, {ctx.guild.name}", color=random.randint(0, 0xFFFFFF), timestamp = ctx.message.created_at)
    embed.set_thumbnail(url=ctx.guild.icon)
    embed.add_field(name="Membres", value = ctx.guild.member_count)
    embed.add_field(name="Salons", value = f"{len(ctx.guild.text_channels)} salon | {len(ctx.guild.voice_channels)} salon vocal")
    embed.add_field(name="Propriétaire", value = ctx.guild.owner.mention)
    embed.add_field(name="Description", value = ctx.guild.description)
    embed.add_field(name="Crée le", value = ctx.guild.created_at.strftime("%d/%m/%Y à %H:%M:%S"))
    await ctx.send(embed=embed)

# Commande chifoumi
@bot.command(name="chifoumi")
async def chifoumi(ctx):
    choices = ["Pierre", "Feuille", "Ciseaux"]
    bot_choice = random.choice(choices)

    embed = discord.Embed(
        title="Chifoumi",
        description="Choisissez votre coup !",
        color=random.randint(0, 0xFFFFFF)
    )
    embed.set_footer(text="Réagissez avec : ✊ pour Pierre, ✋ pour Feuille, ✌️ pour Ciseaux")

    message = await ctx.send(embed=embed)
    await message.add_reaction("✊")
    await message.add_reaction("✋")
    await message.add_reaction("✌️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✊", "✋", "✌️"]

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send(f"{ctx.author.mention} vous avez mis trop de temps à répondre !")
        return

    user_choice = ""
    if str(reaction.emoji) == "✊":
        user_choice = "Pierre"
    elif str(reaction.emoji) == "✋":
        user_choice = "Feuille"
    elif str(reaction.emoji) == "✌️":
        user_choice = "Ciseaux"

    if user_choice == bot_choice:
        result = "Égalité !"
    elif (user_choice == "Pierre" and bot_choice == "Ciseaux") or \
         (user_choice == "Feuille" and bot_choice == "Pierre") or \
         (user_choice == "Ciseaux" and bot_choice == "Feuille"):
        result = f"Vous gagnez ! 🎉 {user_choice} bat {bot_choice}"
    else:
        result = f"Vous perdez... 😢 {bot_choice} bat {user_choice}"

    await ctx.send(f"{ctx.author.mention}, vous avez choisi **{user_choice}**.\nLe bot a choisi **{bot_choice}**.\n**{result}**")


# Commande info salon
@bot.command()
async def infosalon(ctx):
    channel = ctx.channel
    embed = discord.Embed(title="Informations sur le salon", color=discord.Color.blue())


    embed.add_field(name="Nom du salon", value=channel.name, inline=True)
    embed.add_field(name="ID", value=channel.id, inline=True)
    embed.add_field(name="Type", value=str(channel.type).capitalize(), inline=True)
    embed.add_field(name="Position", value=channel.position, inline=True)
    embed.add_field(name="Catégorie", value=channel.category.name if channel.category else "Aucune", inline=True)
    embed.add_field(name="NSFW", value="Oui" if channel.is_nsfw() else "Non", inline=True)
    embed.add_field(name="Créé le", value=channel.created_at.strftime("%d/%m/%Y à %H:%M:%S"), inline=True)
    embed.add_field(name="Sujet", value=channel.topic if channel.topic else "Aucun sujet", inline=True)
 
    permissions = channel.overwrites_for(ctx.guild.default_role)
    perm_msg = (
        f"Lire les messages : {'Oui' if permissions.read_messages else 'Non'}\n"
        f"Envoyer des messages : {'Oui' if permissions.send_messages else 'Non'}\n"
        f"Gérer les messages : {'Oui' if permissions.manage_messages else 'Non'}"
    )
    embed.add_field(name="Permissions par défaut", value=perm_msg, inline=False)
    
    if isinstance(channel, discord.VoiceChannel):
        embed.add_field(name="Limite d'utilisateurs", value=channel.user_limit or "Aucune", inline=True)
        embed.add_field(name="Bitrate", value=f"{channel.bitrate / 1000} kbps", inline=True)
    
    await ctx.send(embed=embed)


bot.invite_counts = defaultdict(int)
bot.run('MTI3MDQ1NjA4ODQyODI4NTk4NA.G4UckJ.9UShMvBVBxJr82txzB1qt8GzYHrQa8wLWpIo2A')